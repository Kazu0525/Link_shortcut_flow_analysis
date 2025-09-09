from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# 絶対インポートに変更
import config
from utils import get_db_connection, get_all_urls_stats, format_datetime, truncate_text
from models import SystemStats

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """管理ダッシュボードページの表示"""
    try:
        # システム統計を取得
        system_stats = await get_system_statistics()
        
        # URL一覧を取得
        urls_data = get_all_urls_stats()
        
        # 最近のクリック履歴を取得
        recent_clicks = await get_recent_clicks(limit=20)
        
        # トップパフォーマンスURLを取得
        top_urls = await get_top_performing_urls(limit=10)
        
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "system_stats": system_stats,
            "urls_data": urls_data,
            "recent_clicks": recent_clicks,
            "top_urls": top_urls,
            "base_url": config.BASE_URL,
            "current_time": datetime.now().strftime("%Y/%m/%d %H:%M")
        })
        
    except Exception as e:
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "error": f"管理ダッシュボードの読み込みでエラーが発生しました: {str(e)}",
            "system_stats": {"total_links": 0, "total_clicks": 0, "system_status": "エラー"},
            "urls_data": [],
            "recent_clicks": [],
            "top_urls": [],
            "base_url": config.BASE_URL
        })

@router.post("/admin/url/{short_code}/toggle")
async def toggle_url_status(short_code: str):
    """URLの有効/無効を切り替え"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 現在の状態を取得
        cursor.execute("SELECT is_active FROM urls WHERE short_code = ?", (short_code,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="URLが見つかりません")
        
        current_status = result[0]
        new_status = 0 if current_status else 1
        
        # ステータスを更新
        cursor.execute("""
            UPDATE urls 
            SET is_active = ?
            WHERE short_code = ?
        """, (new_status, short_code))
        
        conn.commit()
        conn.close()
        
        status_text = "有効" if new_status else "無効"
        
        return JSONResponse({
            "success": True,
            "message": f"URL '{short_code}' を{status_text}にしました",
            "new_status": new_status
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ステータス変更でエラーが発生しました: {str(e)}")

@router.delete("/admin/url/{short_code}")
async def delete_url(short_code: str):
    """URLを削除（論理削除）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # URLを無効化
        cursor.execute("""
            UPDATE urls 
            SET is_active = 0
            WHERE short_code = ?
        """, (short_code,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="URLが見つかりません")
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "message": f"URL '{short_code}' を削除しました"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL削除でエラーが発生しました: {str(e)}")

@router.post("/admin/url/{short_code}/edit")
async def edit_url(
    short_code: str,
    custom_name: str = Form(None),
    campaign_name: str = Form(None)
):
    """URLの詳細情報を編集"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 存在確認
        cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="URLが見つかりません")
        
        # 更新
        cursor.execute("""
            UPDATE urls 
            SET custom_name = ?, campaign_name = ?
            WHERE short_code = ?
        """, (custom_name or None, campaign_name or None, short_code))
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "message": f"URL '{short_code}' の情報を更新しました"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL編集でエラーが発生しました: {str(e)}")

@router.get("/api/admin/stats")
async def get_admin_stats():
    """管理用統計データAPI"""
    try:
        stats = await get_system_statistics()
        return JSONResponse(stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"統計データの取得でエラーが発生しました: {str(e)}")

@router.get("/api/admin/urls")
async def get_urls_list(
    page: int = 1,
    limit: int = 50,
    campaign: Optional[str] = None,
    search: Optional[str] = None
):
    """URL一覧API（ページング対応）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ベースクエリ
        base_query = """
            SELECT 
                u.id,
                u.short_code,
                u.original_url,
                u.custom_name,
                u.campaign_name,
                u.created_at,
                u.is_active,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                MAX(c.clicked_at) as last_clicked
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE 1=1
        """
        
        count_query = "SELECT COUNT(*) FROM urls WHERE 1=1"
        
        conditions = []
        params = []
        
        # 検索条件
        if campaign:
            conditions.append("u.campaign_name = ?")
            params.append(campaign)
        
        if search:
            conditions.append("(u.original_url LIKE ? OR u.custom_name LIKE ? OR u.short_code LIKE ?)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        if conditions:
            condition_str = " AND " + " AND ".join(conditions)
            base_query += condition_str
            count_query += condition_str
        
        # 総数を取得
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # ページング
        offset = (page - 1) * limit
        base_query += " GROUP BY u.id ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(base_query, params)
        urls = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return JSONResponse({
            "urls": urls,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL一覧の取得でエラーが発生しました: {str(e)}")

async def get_system_statistics():
    """システム全体の統計を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as total_links,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                COUNT(CASE WHEN c.source = 'qr_code' THEN 1 END) as qr_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
        """)
        
        basic_stats = dict(cursor.fetchone())
        
        # 今日の統計
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as links_created_today,
                COUNT(c.id) as clicks_today,
                COUNT(DISTINCT c.ip_address) as visitors_today
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id AND DATE(c.clicked_at) = DATE('now')
            WHERE DATE(u.created_at) = DATE('now')
        """)
        
        today_stats = dict(cursor.fetchone())
        
        # 過去7日間のトレンド
        cursor.execute("""
            SELECT 
                DATE(clicked_at) as date,
                COUNT(*) as clicks
            FROM clicks 
            WHERE DATE(clicked_at) >= DATE('now', '-7 days')
            GROUP BY DATE(clicked_at)
            ORDER BY date
        """)
        
        trend_data = [dict(row) for row in cursor.fetchall()]
        
        # トップソース
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM clicks 
            WHERE DATE(clicked_at) >= DATE('now', '-30 days')
            GROUP BY source
            ORDER BY count DESC
            LIMIT 5
        """)
        
        top_sources = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            **basic_stats,
            **today_stats,
            "trend_data": trend_data,
            "top_sources": top_sources,
            "system_status": "正常稼働中",
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"システム統計取得エラー: {e}")
        return {
            "total_links": 0,
            "total_clicks": 0,
            "unique_visitors": 0,
            "qr_clicks": 0,
            "system_status": "エラー"
        }

async def get_recent_clicks(limit: int = 20):
    """最近のクリック履歴を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.short_code,
                u.custom_name,
                c.ip_address,
                c.source,
                c.clicked_at,
                c.referrer
            FROM clicks c
            JOIN urls u ON c.url_id = u.id
            ORDER BY c.clicked_at DESC
            LIMIT ?
        """, (limit,))
        
        clicks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return clicks
        
    except Exception as e:
        print(f"最近のクリック取得エラー: {e}")
        return []

async def get_top_performing_urls(limit: int = 10):
    """トップパフォーマンスURLを取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.short_code,
                u.original_url,
                u.custom_name,
                u.campaign_name,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                MAX(c.clicked_at) as last_clicked
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            HAVING COUNT(c.id) > 0
            ORDER BY total_clicks DESC
            LIMIT ?
        """, (limit,))
        
        top_urls = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return top_urls
        
    except Exception as e:
        print(f"トップURL取得エラー: {e}")
        return []

@router.post("/admin/bulk-delete")
async def bulk_delete_urls(short_codes: List[str]):
    """複数URLの一括削除"""
    try:
        if not short_codes:
            raise HTTPException(status_code=400, detail="削除対象のURLを指定してください")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # プレースホルダー作成
        placeholders = ','.join(['?' for _ in short_codes])
        
        cursor.execute(f"""
            UPDATE urls 
            SET is_active = 0
            WHERE short_code IN ({placeholders})
        """, short_codes)
        
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "message": f"{deleted_count}件のURLを削除しました",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"一括削除でエラーが発生しました: {str(e)}")

@router.get("/admin/maintenance")
async def maintenance_page(request: Request):
    """メンテナンスページ"""
    try:
        # データベース健全性チェック
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # テーブルサイズ
        cursor.execute("SELECT COUNT(*) FROM urls")
        urls_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clicks")
        clicks_count = cursor.fetchone()[0]
        
        # 孤立データチェック
        cursor.execute("""
            SELECT COUNT(*) FROM clicks c
            LEFT JOIN urls u ON c.url_id = u.id
            WHERE u.id IS NULL
        """)
        orphaned_clicks = cursor.fetchone()[0]
        
        conn.close()
        
        maintenance_info = {
            "database_size": {
                "urls": urls_count,
                "clicks": clicks_count,
                "orphaned_clicks": orphaned_clicks
            },
            "last_backup": "未実装",
            "system_health": "正常" if orphaned_clicks == 0 else "要注意"
        }
        
        return templates.TemplateResponse("maintenance.html", {
            "request": request,
            "maintenance_info": maintenance_info,
            "base_url": config.BASE_URL
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"メンテナンスページの表示でエラーが発生しました: {str(e)}")

@router.post("/admin/cleanup")
async def cleanup_old_data():
    """古いデータのクリーンアップ"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 30日以上前の無効URLを削除
        cursor.execute("""
            DELETE FROM urls 
            WHERE is_active = 0 
            AND DATE(created_at) < DATE('now', '-30 days')
        """)
        deleted_urls = cursor.rowcount
        
        # 孤立したクリックデータを削除
        cursor.execute("""
            DELETE FROM clicks 
            WHERE url_id NOT IN (SELECT id FROM urls)
        """)
        deleted_clicks = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "message": "データクリーンアップが完了しました",
            "deleted_urls": deleted_urls,
            "deleted_clicks": deleted_clicks
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"データクリーンアップでエラーが発生しました: {str(e)}")
