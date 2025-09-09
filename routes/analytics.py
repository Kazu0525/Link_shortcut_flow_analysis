from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 絶対インポートに変更
import config
from utils import get_db_connection, get_url_info, format_datetime

router = APIRouter()

# 分析画面HTMLテンプレート - 完全修正版（インライン版）
ANALYTICS_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>分析画面 - {short_code}</title>
    <meta charset="UTF-8">
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 20px; 
            background: #f5f5f5; 
        }}
        .container {{ 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }}
        h1 {{ 
            color: #333; 
            border-bottom: 3px solid #4CAF50; 
            padding-bottom: 10px; 
        }}
        .info-box {{ 
            background: #e3f2fd; 
            padding: 15px; 
            border-radius: 5px; 
            margin: 20px 0; 
        }}
        .stats-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin: 20px 0; 
        }}
        .stat-card {{ 
            background: #f9f9f9; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            text-align: center; 
        }}
        .stat-number {{ 
            font-size: 2em; 
            font-weight: bold; 
            color: #4CAF50; 
        }}
        .stat-label {{ 
            color: #666; 
            margin-top: 10px; 
        }}
        .back-btn {{ 
            background: #4CAF50; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            text-decoration: none; 
            display: inline-block; 
            margin: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 分析画面: {short_code}</h1>
        
        <div class="info-box">
            <p><strong>元URL:</strong> <a href="{original_url}" target="_blank">{original_url}</a></p>
            <p><strong>短縮URL:</strong> <a href="{short_url}" target="_blank">{short_url}</a></p>
            <p><strong>作成日:</strong> {created_at}</p>
            <div style="text-align: center; margin-top: 15px;">
                <a href="/admin" class="back-btn">📊 管理画面に戻る</a>
                <button class="back-btn" onclick="location.reload()">🔄 更新</button>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_clicks}</div>
                <div class="stat-label">総クリック数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{unique_clicks}</div>
                <div class="stat-label">ユニーク訪問者</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{qr_clicks}</div>
                <div class="stat-label">QRコードクリック</div>
            </div>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <p>詳細な分析グラフは近日実装予定です。</p>
            <p>現在は基本統計のみ表示しています。</p>
        </div>
    </div>
</body>
</html>"""

@router.get("/analytics/{short_code}")
async def analytics_page(short_code: str):
    """分析画面"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # URL情報取得
        cursor.execute('''
            SELECT original_url, created_at, custom_name, campaign_name
            FROM urls WHERE short_code = ? AND is_active = 1
        ''', (short_code,))
        
        result = cursor.fetchone()
        if not result:
            return HTMLResponse(content="<h1>エラー</h1><p>短縮URLが見つかりません</p>", status_code=404)
        
        original_url, created_at, custom_name, campaign_name = result
        
        # 統計情報取得
        cursor.execute('''
            SELECT 
                COUNT(*) as total_clicks,
                COUNT(DISTINCT ip_address) as unique_clicks,
                COUNT(CASE WHEN source = 'qr_code' THEN 1 END) as qr_clicks
            FROM clicks 
            WHERE url_id = (SELECT id FROM urls WHERE short_code = ?)
        ''', (short_code,))
        
        stats = cursor.fetchone()
        total_clicks, unique_clicks, qr_clicks = stats if stats else (0, 0, 0)
        
        conn.close()
        
        # HTMLをレンダリング
        html_content = ANALYTICS_HTML.format(
            short_code=short_code,
            original_url=original_url,
            short_url=f"{config.BASE_URL}/{short_code}",
            created_at=created_at,
            total_clicks=total_clicks,
            unique_clicks=unique_clicks,
            qr_clicks=qr_clicks
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        error_html = f"<h1>Error</h1><p>{str(e)}</p>"
        return HTMLResponse(content=error_html, status_code=500)

@router.get("/api/analytics/{short_code}")
async def get_analytics_api(short_code: str):
    """分析データAPIエンドポイント"""
    try:
        # URL情報を確認
        url_info = get_url_info(short_code)
        if not url_info:
            raise HTTPException(status_code=404, detail="短縮URLが見つかりません")
        
        # 分析データを取得
        analytics_data = await get_analytics_data(short_code)
        
        return JSONResponse({
            "short_code": short_code,
            "total_clicks": analytics_data["total_clicks"],
            "unique_visitors": analytics_data["unique_visitors"],
            "qr_clicks": analytics_data["qr_clicks"],
            "click_data": analytics_data["recent_clicks"]
        })
        
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
        
        # 最近のクリック詳細（最新20件）
        cursor.execute("""
            SELECT id, ip_address, user_agent, referrer, source, clicked_at
            FROM clicks 
            WHERE url_id = ?
            ORDER BY clicked_at DESC
            LIMIT 20
        """, (url_id,))
        
        recent_clicks = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_clicks": basic_stats["total_clicks"] or 0,
            "unique_visitors": basic_stats["unique_visitors"] or 0,
            "qr_clicks": basic_stats["qr_clicks"] or 0,
            "first_clicked": basic_stats["first_clicked"],
            "last_clicked": basic_stats["last_clicked"],
            "source_stats": source_stats,
            "recent_clicks": recent_clicks
        }
        
    except Exception as e:
        print(f"分析データ取得エラー: {e}")
        raise HTTPException(status_code=500, detail="分析データの取得に失敗しました")
