from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response
import sqlite3
import json
import csv
import io
from datetime import datetime
from typing import List, Optional

# 絶対インポートに変更（pydantic完全除去）
import config
from utils import get_db_connection, export_to_csv_format

router = APIRouter()

@router.post("/api/export")
async def export_data(request: dict):
    """データエクスポートAPIエンドポイント（軽量版）"""
    try:
        short_codes = request.get("short_codes", [])
        format_type = request.get("format", "json")
        
        if not short_codes:
            raise HTTPException(status_code=400, detail="エクスポートする短縮コードを指定してください")
        
        if len(short_codes) > config.MAX_EXPORT_RECORDS:
            raise HTTPException(status_code=400, detail=f"一度にエクスポートできるのは{config.MAX_EXPORT_RECORDS}件までです")
        
        # データベースからデータを取得
        export_data_result = await get_export_data(short_codes)
        
        if not export_data_result:
            raise HTTPException(status_code=404, detail="エクスポート対象のデータが見つかりません")
        
        # フォーマットに応じてデータを変換
        if format_type.lower() == "json":
            return JSONResponse({
                "export_date": datetime.now().isoformat(),
                "total_records": len(export_data_result),
                "data": export_data_result
            })
        
        elif format_type.lower() == "csv":
            csv_content = export_to_csv_format(export_data_result)
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=url_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail="サポートされていない形式です（json, csvのみ）")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エクスポート処理でエラーが発生しました: {str(e)}")

@router.get("/api/export/all")
async def export_all_data(
    format: str = Query("json", description="エクスポート形式 (json, csv)"),
    campaign: Optional[str] = Query(None, description="特定のキャンペーンのみエクスポート"),
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    include_clicks: bool = Query(False, description="クリックデータも含める")
):
    """全データのエクスポート"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ベースクエリ
        base_query = """
            SELECT 
                u.short_code,
                u.original_url,
                u.custom_name,
                u.campaign_name,
                u.created_at,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                COUNT(CASE WHEN c.source = 'qr_code' THEN 1 END) as qr_clicks,
                MAX(c.clicked_at) as last_clicked
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
        """
        
        conditions = []
        params = []
        
        # 条件追加
        if campaign:
            conditions.append("u.campaign_name = ?")
            params.append(campaign)
        
        if start_date:
            conditions.append("DATE(u.created_at) >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("DATE(u.created_at) <= ?")
            params.append(end_date)
        
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        base_query += " GROUP BY u.id ORDER BY u.created_at DESC"
        
        cursor.execute(base_query, params)
        urls_data = [dict(row) for row in cursor.fetchall()]
        
        export_result = {
            "export_metadata": {
                "export_date": datetime.now().isoformat(),
                "total_records": len(urls_data),
                "filters": {
                    "campaign": campaign,
                    "start_date": start_date,
                    "end_date": end_date,
                    "include_clicks": include_clicks
                }
            },
            "urls": urls_data
        }
        
        # クリックデータも含める場合
        if include_clicks and urls_data:
            short_codes = [url['short_code'] for url in urls_data]
            placeholders = ','.join(['?' for _ in short_codes])
            
            cursor.execute(f"""
                SELECT 
                    u.short_code,
                    c.ip_address,
                    c.user_agent,
                    c.referrer,
                    c.source,
                    c.clicked_at
                FROM clicks c
                JOIN urls u ON c.url_id = u.id
                WHERE u.short_code IN ({placeholders})
                ORDER BY c.clicked_at DESC
            """, short_codes)
            
            clicks_data = [dict(row) for row in cursor.fetchall()]
            export_result["clicks"] = clicks_data
        
        conn.close()
        
        # フォーマットに応じて返す
        if format.lower() == "json":
            return JSONResponse(export_result)
        
        elif format.lower() == "csv":
            # URLデータのCSV
            csv_content = export_to_csv_format(urls_data)
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=all_urls_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail="サポートされていない形式です")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"全データエクスポートでエラーが発生しました: {str(e)}")

@router.get("/api/export/analytics/{short_code}")
async def export_analytics_data(
    short_code: str,
    format: str = Query("json", description="エクスポート形式 (json, csv)"),
    period: str = Query("all", description="期間 (7d, 30d, all)")
):
    """指定したURLの分析データをエクスポート"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # URL情報を取得
        cursor.execute("SELECT id, short_code, original_url, custom_name, campaign_name, created_at FROM urls WHERE short_code = ?", (short_code,))
        url_info = cursor.fetchone()
        
        if not url_info:
            raise HTTPException(status_code=404, detail="短縮URLが見つかりません")
        
        url_id = url_info[0]
        
        # 期間フィルター
        date_filter = ""
        if period == "7d":
            date_filter = "AND DATE(clicked_at) >= DATE('now', '-7 days')"
        elif period == "30d":
            date_filter = "AND DATE(clicked_at) >= DATE('now', '-30 days')"
        
        # クリックデータを取得
        cursor.execute(f"""
            SELECT 
                ip_address,
                user_agent,
                referrer,
                source,
                clicked_at,
                DATE(clicked_at) as click_date,
                CAST(strftime('%H', clicked_at) AS INTEGER) as click_hour
            FROM clicks 
            WHERE url_id = ? {date_filter}
            ORDER BY clicked_at DESC
        """, (url_id,))
        
        clicks_data = [dict(row) for row in cursor.fetchall()]
        
        # 統計データを取得
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_clicks,
                COUNT(DISTINCT ip_address) as unique_visitors,
                COUNT(CASE WHEN source = 'qr_code' THEN 1 END) as qr_clicks,
                MIN(clicked_at) as first_click,
                MAX(clicked_at) as last_click
            FROM clicks 
            WHERE url_id = ? {date_filter}
        """, (url_id,))
        
        stats = dict(cursor.fetchone())
        
        # ソース別統計
        cursor.execute(f"""
            SELECT source, COUNT(*) as count
            FROM clicks 
            WHERE url_id = ? {date_filter}
            GROUP BY source
            ORDER BY count DESC
        """, (url_id,))
        
        source_stats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        analytics_data = {
            "url_info": dict(url_info),
            "period": period,
            "export_date": datetime.now().isoformat(),
            "statistics": stats,
            "source_breakdown": source_stats,
            "clicks": clicks_data
        }
        
        if format.lower() == "json":
            return JSONResponse(analytics_data)
        
        elif format.lower() == "csv":
            # クリックデータのCSV
            csv_content = export_to_csv_format(clicks_data)
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=analytics_{short_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail="サポートされていない形式です")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析データエクスポートでエラーが発生しました: {str(e)}")

async def get_export_data(short_codes: List[str]):
    """指定した短縮コードのデータを取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # プレースホルダーを作成
        placeholders = ','.join(['?' for _ in short_codes])
        
        cursor.execute(f"""
            SELECT 
                u.short_code,
                u.original_url,
                u.custom_name,
                u.campaign_name,
                u.created_at,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                COUNT(CASE WHEN c.source = 'qr_code' THEN 1 END) as qr_clicks,
                MAX(c.clicked_at) as last_clicked
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.short_code IN ({placeholders}) AND u.is_active = 1
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """, short_codes)
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
        
    except Exception as e:
        print(f"エクスポートデータ取得エラー: {e}")
        return []

@router.get("/api/export/formats")
async def get_export_formats():
    """利用可能なエクスポート形式一覧"""
    return JSONResponse({
        "formats": config.EXPORT_FORMATS,
        "max_records": config.MAX_EXPORT_RECORDS,
        "description": {
            "json": "JSON形式（プログラム処理に最適）",
            "csv": "CSV形式（Excelで開けます）",
            "xlsx": "Excel形式（予定）"
        }
    })

@router.get("/api/export/campaigns")
async def get_exportable_campaigns():
    """エクスポート可能なキャンペーン一覧"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                campaign_name,
                COUNT(*) as url_count,
                MIN(created_at) as start_date,
                MAX(created_at) as end_date
            FROM urls 
            WHERE campaign_name IS NOT NULL AND campaign_name != '' AND is_active = 1
            GROUP BY campaign_name
            ORDER BY url_count DESC
        """)
        
        campaigns = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return JSONResponse({
            "campaigns": campaigns
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キャンペーン一覧の取得でエラーが発生しました: {str(e)}")
