from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import sqlite3
from datetime import datetime
from models import ShortenRequest, ShortenResponse
from config import DB_PATH, BASE_URL
from utils import generate_short_code, generate_qr_code_base64, is_valid_url

router = APIRouter()

@router.post("/api/shorten")
async def shorten_url(request: ShortenRequest):
    """URL短縮API"""
    try:
        # URL検証
        if not is_valid_url(request.url):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # カスタムスラッグのチェック
        short_code = request.custom_slug
        if short_code:
            cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
            if cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=400, detail="Custom slug already exists")
        else:
            short_code = generate_short_code(conn=conn)
        
        # URLを保存
        cursor.execute('''
            INSERT INTO urls (short_code, original_url, custom_name, campaign_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            short_code, 
            request.url, 
            request.custom_name, 
            request.campaign_name,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        # レスポンス生成
        short_url = f"{BASE_URL}/{short_code}"
        qr_url = f"{BASE_URL}/{short_code}?source=qr"
        qr_code_base64 = generate_qr_code_base64(qr_url)
        
        response = ShortenResponse(
            short_url=short_url,
            short_code=short_code,
            original_url=request.url,
            qr_code_url=qr_url,
            qr_code_base64=qr_code_base64,
            custom_name=request.custom_name,
            campaign_name=request.campaign_name,
            created_at=datetime.now().isoformat()
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL shortening failed: {str(e)}")

@router.get("/api/urls/{short_code}")
async def get_url_info(short_code: str):
    """短縮URL情報取得API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT short_code, original_url, custom_name, campaign_name, created_at, is_active
            FROM urls WHERE short_code = ?
        ''', (short_code,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Short URL not found")
        
        short_code_db, original_url, custom_name, campaign_name, created_at, is_active = result
        
        # クリック統計取得
        cursor.execute('''
            SELECT 
                COUNT(*) as total_clicks,
                COUNT(DISTINCT ip_address) as unique_clicks,
                COUNT(CASE WHEN source = 'qr' THEN 1 END) as qr_clicks
            FROM clicks 
            WHERE url_id = (SELECT id FROM urls WHERE short_code = ?)
        ''', (short_code,))
        
        stats = cursor.fetchone()
        total_clicks, unique_clicks, qr_clicks = stats if stats else (0, 0, 0)
        
        conn.close()
        
        return {
            "short_code": short_code_db,
            "short_url": f"{BASE_URL}/{short_code_db}",
            "original_url": original_url,
            "custom_name": custom_name,
            "campaign_name": campaign_name,
            "created_at": created_at,
            "is_active": is_active,
            "qr_code_url": f"{BASE_URL}/{short_code_db}?source=qr",
            "analytics_url": f"{BASE_URL}/analytics/{short_code_db}",
            "statistics": {
                "total_clicks": total_clicks,
                "unique_clicks": unique_clicks,
                "qr_clicks": qr_clicks
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL info retrieval failed: {str(e)}")

@router.get("/api/urls")
async def list_urls(limit: int = 50, offset: int = 0, campaign: str = None):
    """URL一覧取得API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # ベースクエリ
        base_query = '''
            SELECT u.short_code, u.original_url, u.custom_name, u.campaign_name, 
                   u.created_at, u.is_active,
                   COALESCE(c.total_clicks, 0) as total_clicks,
                   COALESCE(c.unique_clicks, 0) as unique_clicks,
                   COALESCE(c.qr_clicks, 0) as qr_clicks
            FROM urls u
            LEFT JOIN (
                SELECT url_id,
                       COUNT(*) as total_clicks,
                       COUNT(DISTINCT ip_address) as unique_clicks,
                       COUNT(CASE WHEN source = 'qr' THEN 1 END) as qr_clicks
                FROM clicks
                GROUP BY url_id
            ) c ON u.id = c.url_id
        '''
        
        # キャンペーンフィルター
        params = []
        if campaign:
            base_query += " WHERE u.campaign_name = ?"
            params.append(campaign)
        
        # ソートと制限
        base_query += " ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        
        # 総数取得
        count_query = "SELECT COUNT(*) FROM urls"
        count_params = []
        if campaign:
            count_query += " WHERE campaign_name = ?"
            count_params.append(campaign)
            
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        # レスポンス整形
        urls = []
        for row in results:
            short_code, original_url, custom_name, campaign_name, created_at, is_active, total_clicks, unique_clicks, qr_clicks = row
            
            urls.append({
                "short_code": short_code,
                "short_url": f"{BASE_URL}/{short_code}",
                "original_url": original_url,
                "custom_name": custom_name,
                "campaign_name": campaign_name,
                "created_at": created_at,
                "is_active": is_active,
                "qr_code_url": f"{BASE_URL}/{short_code}?source=qr",
                "analytics_url": f"{BASE_URL}/analytics/{short_code}",
                "statistics": {
                    "total_clicks": total_clicks,
                    "unique_clicks": unique_clicks,
                    "qr_clicks": qr_clicks
                }
            })
        
        return {
            "urls": urls,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filter": {
                "campaign": campaign
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL listing failed: {str(e)}")

@router.delete("/api/urls/{short_code}")
async def delete_url(short_code: str):
    """URL削除API（非アクティブ化）"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # URLの存在チェック
        cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Short URL not found")
        
        # 非アクティブ化（物理削除はしない）
        cursor.execute('''
            UPDATE urls SET is_active = FALSE 
            WHERE short_code = ?
        ''', (short_code,))
        
        conn.commit()
        conn.close()
        
        return {
            "message": f"Short URL '{short_code}' has been deactivated",
            "short_code": short_code,
            "status": "deactivated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL deletion failed: {str(e)}")
