from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 絶対インポートに変更
import config
from models import AnalyticsResponse, ClickData
from utils import get_db_connection, get_url_info, format_datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/analytics/{short_code}", response_class=HTMLResponse)
async def analytics_page(short_code: str, request: Request):
    """分析ページの表示"""
    try:
        # URL情報を取得
        url_info = get_url_info(short_code)
        if not url_info:
            raise HTTPException(status_code=404, detail="短縮URLが見つかりません")
        
        # 分析データを取得
        analytics_data = await get_analytics_data(short_code)
        
        return templates.TemplateResponse("analytics.html", {
            "request": request,
            "short_code": short_code,
            "url_info": url_info,
            "analytics": analytics_data,
            "base_url": config.BASE_URL
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析ページの表示でエラーが発生しました: {str(e)}")

@router.get("/api/analytics/{short_code}", response_model=AnalyticsResponse)
async def get_analytics_api(short_code: str):
    """分析データAPIエンドポイント"""
    try:
        # URL情報を確認
        url_info = get_url_info(short_code)
        if not url_info:
            raise HTTPException(status_code=404, detail="短縮URLが見つかりません")
        
        # 分析データを取得
        analytics_data = await get_analytics_data(short_code)
        
        return AnalyticsResponse(
            short_code=short_code,
            total_clicks=analytics_data["total_clicks"],
            unique_visitors=analytics_data["unique_visitors"],
            qr_clicks=analytics_data["qr_clicks"],
            click_data=[
                ClickData(
                    id=click["id"],
                    ip_address=click["ip_address"],
                    user_agent=click["user_agent"],
                    referrer=click["referrer"],
                    source=click["source"],
                    clicked_at=datetime.fromisoformat(click["clicked_at"])
                ) for click in analytics_data["recent_clicks"]
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析データの取得でエラーが発生しました: {str(e)}")

async def get_analytics_data(short_code: str) -> Dict[str, Any]:
    """指定した短縮コードの詳細な分析データを取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # URL IDを取得
        cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
        url_result = cursor.fetchone()
        if not url_result:
            raise HTTPException(status_code=404, detail="URLが見つかりません")
        
        url_id = url_result[0]
        
        # 基本統計
        cursor.execute("""
            SELECT 
                COUNT(*) as total_clicks,
                COUNT(DISTINCT ip_address) as unique_visitors,
                COUNT(CASE WHEN source = 'qr_code' THEN 1 END) as qr_clicks,
                MIN(clicked_at) as first_clicked,
                MAX(clicked_at) as last_clicked
            FROM clicks 
            WHERE url_id = ?
        """, (url_id,))
        
        basic_stats = dict(cursor.fetchone())
        
        # ソース別統計
        cursor.execute("""
            SELECT source, COUNT(*) as count, COUNT(DISTINCT ip_address) as unique_count
            FROM clicks 
            WHERE url_id = ?
            GROUP BY source
            ORDER BY count DESC
        """, (url_id,))
        
        source_stats = [dict(row) for row in cursor.fetchall()]
        
        # 時間別統計（過去7日間）
        cursor.execute("""
            SELECT 
                DATE(clicked_at) as date,
                CAST(strftime('%H', clicked_at) AS INTEGER) as hour,
                COUNT(*) as count
            FROM clicks 
            WHERE url_id = ? 
            AND DATE(clicked_at) >= DATE('now', '-7 days')
            GROUP BY DATE(clicked_at), CAST(strftime('%H', clicked_at) AS INTEGER)
            ORDER BY date, hour
        """, (url_id,))
        
        hourly_stats = [dict(row) for row in cursor.fetchall()]
        
        # 日別統計（過去30日間）
        cursor.execute("""
            SELECT 
                DATE(clicked_at) as date,
                COUNT(*) as clicks,
                COUNT(DISTINCT ip_address) as unique_visitors
            FROM clicks 
            WHERE url_id = ? 
            AND DATE(clicked_at) >= DATE('now', '-30 days')
            GROUP BY DATE(clicked_at)
            ORDER BY date
        """, (url_id,))
        
        daily_stats = [dict(row) for row in cursor.fetchall()]
        
        # 最近のクリック詳細（最新50件）
        cursor.execute("""
            SELECT id, ip_address, user_agent, referrer, source, clicked_at
            FROM clicks 
            WHERE url_id = ?
            ORDER BY clicked_at DESC
            LIMIT 50
        """, (url_id,))
        
        recent_clicks = [dict(row) for row in cursor.fetchall()]
        
        # リファラー分析
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN referrer = '' OR referrer IS NULL THEN 'Direct'
                    ELSE referrer
                END as referrer_domain,
                COUNT(*) as count
            FROM clicks 
            WHERE url_id = ?
            GROUP BY referrer_domain
            ORDER BY count DESC
            LIMIT 10
        """, (url_id,))
        
        referrer_stats = [dict(row) for row in cursor.fetchall()]
        
        # デバイス分析（User-Agentから推定）
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN LOWER(user_agent) LIKE '%mobile%' OR LOWER(user_agent) LIKE '%iphone%' OR LOWER(user_agent) LIKE '%android%' THEN 'Mobile'
                    WHEN LOWER(user_agent) LIKE '%tablet%' OR LOWER(user_agent) LIKE '%ipad%' THEN 'Tablet'
                    ELSE 'Desktop'
                END as device_type,
                COUNT(*) as count
            FROM clicks 
            WHERE url_id = ?
            GROUP BY device_type
            ORDER BY count DESC
        """, (url_id,))
        
        device_stats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # データを整理して返す
        return {
            "total_clicks": basic_stats["total_clicks"] or 0,
            "unique_visitors": basic_stats["unique_visitors"] or 0,
            "qr_clicks": basic_stats["qr_clicks"] or 0,
            "first_clicked": basic_stats["first_clicked"],
            "last_clicked": basic_stats["last_clicked"],
            "source_stats": source_stats,
            "hourly_stats": hourly_stats,
            "daily_stats": daily_stats,
            "recent_clicks": recent_clicks,
            "referrer_stats": referrer_stats,
            "device_stats": device_stats
        }
        
    except Exception as e:
        print(f"分析データ取得エラー: {e}")
        raise HTTPException(status_code=500, detail="分析データの取得に失敗しました")

@router.get("/api/analytics/{short_code}/summary")
async def get_analytics_summary(short_code: str):
    """分析データのサマリーを取得"""
    try:
        analytics_data = await get_analytics_data(short_code)
        
        return JSONResponse({
            "short_code": short_code,
            "summary": {
                "total_clicks": analytics_data["total_clicks"],
                "unique_visitors": analytics_data["unique_visitors"],
                "qr_clicks": analytics_data["qr_clicks"],
                "conversion_rate": round((analytics_data["unique_visitors"] / max(analytics_data["total_clicks"], 1)) * 100, 2),
                "qr_rate": round((analytics_data["qr_clicks"] / max(analytics_data["total_clicks"], 1)) * 100, 2),
                "first_clicked": analytics_data["first_clicked"],
                "last_clicked": analytics_data["last_clicked"]
            },
            "top_sources": analytics_data["source_stats"][:5],
            "device_breakdown": analytics_data["device_stats"]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"サマリーデータの取得でエラーが発生しました: {str(e)}")

@router.get("/api/analytics/{short_code}/chart-data")
async def get_chart_data(short_code: str, period: str = "7d"):
    """チャート用のデータを取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # URL IDを取得
        cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
        url_result = cursor.fetchone()
        if not url_result:
            raise HTTPException(status_code=404, detail="URLが見つかりません")
        
        url_id = url_result[0]
        
        # 期間に応じてデータを取得
        if period == "24h":
            # 24時間の時間別データ
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', clicked_at) as time_period,
                    COUNT(*) as clicks
                FROM clicks 
                WHERE url_id = ? 
                AND clicked_at >= datetime('now', '-24 hours')
                GROUP BY strftime('%Y-%m-%d %H:00:00', clicked_at)
                ORDER BY time_period
            """, (url_id,))
        elif period == "30d":
            # 30日間の日別データ
            cursor.execute("""
                SELECT 
                    DATE(clicked_at) as time_period,
                    COUNT(*) as clicks
                FROM clicks 
                WHERE url_id = ? 
                AND DATE(clicked_at) >= DATE('now', '-30 days')
                GROUP BY DATE(clicked_at)
                ORDER BY time_period
            """, (url_id,))
        else:  # デフォルト: 7d
            # 7日間の日別データ
            cursor.execute("""
                SELECT 
                    DATE(clicked_at) as time_period,
                    COUNT(*) as clicks
                FROM clicks 
                WHERE url_id = ? 
                AND DATE(clicked_at) >= DATE('now', '-7 days')
                GROUP BY DATE(clicked_at)
                ORDER BY time_period
            """, (url_id,))
        
        chart_data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return JSONResponse({
            "short_code": short_code,
            "period": period,
            "data": chart_data
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"チャートデータの取得でエラーが発生しました: {str(e)}")

@router.get("/api/system/analytics")
async def get_system_analytics():
    """システム全体の分析データを取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # システム全体の統計
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as total_urls,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                COUNT(CASE WHEN c.source = 'qr_code' THEN 1 END) as qr_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
        """)
        
        system_stats = dict(cursor.fetchone())
        
        # 今日の統計
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as urls_created_today,
                COUNT(c.id) as clicks_today
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id AND DATE(c.clicked_at) = DATE('now')
            WHERE DATE(u.created_at) = DATE('now')
        """)
        
        today_stats = dict(cursor.fetchone())
        
        # トップパフォーマンスURL
        cursor.execute("""
            SELECT 
                u.short_code,
                u.custom_name,
                u.original_url,
                COUNT(c.id) as clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            ORDER BY clicks DESC
            LIMIT 10
        """)
        
        top_urls = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return JSONResponse({
            "system_stats": system_stats,
            "today_stats": today_stats,
            "top_urls": top_urls,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"システム分析データの取得でエラーが発生しました: {str(e)}")
