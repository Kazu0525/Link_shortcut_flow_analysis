from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
import sqlite3
from datetime import datetime
from config import DB_PATH

router = APIRouter()

def get_client_ip(request: Request) -> str:
    """クライアントIPアドレスを取得"""
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()
    return request.client.host if request.client else "unknown"

def get_source_from_request(request: Request) -> str:
    """リクエストからソースを判定"""
    source = request.query_params.get("source", "direct")
    
    # UTMパラメータからの判定
    utm_source = request.query_params.get("utm_source")
    if utm_source:
        return utm_source
    
    # Refererからの判定
    referer = request.headers.get("referer", "")
    if "qr" in source.lower():
        return "qr"
    elif "facebook.com" in referer:
        return "facebook"
    elif "twitter.com" in referer or "x.com" in referer:
        return "twitter"
    elif "instagram.com" in referer:
        return "instagram"
    elif "linkedin.com" in referer:
        return "linkedin"
    elif "youtube.com" in referer:
        return "youtube"
    elif referer and referer != "":
        return "referral"
    
    return source

@router.get("/{short_code}")
async def redirect_to_original(short_code: str, request: Request):
    """短縮URLから元URLへリダイレクト"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # URLを検索
        cursor.execute('''
            SELECT id, original_url, is_active 
            FROM urls 
            WHERE short_code = ?
        ''', (short_code,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Short URL not found")
        
        url_id, original_url, is_active = result
        
        if not is_active:
            conn.close()
            raise HTTPException(status_code=410, detail="Short URL has been deactivated")
        
        # クリック情報を記録
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        referer = request.headers.get("referer", "")
        source = get_source_from_request(request)
        
        cursor.execute('''
            INSERT INTO clicks (url_id, ip_address, user_agent, referrer, source, clicked_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (url_id, client_ip, user_agent, referer, source, datetime.now()))
        
        conn.commit()
        conn.close()
        
        # 元URLにリダイレクト
        return RedirectResponse(url=original_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        raise HTTPException(status_code=500, detail=f"Redirect failed: {str(e)}")

# ヘルスチェック用の詳細エンドポイント
@router.get("/system/status")
async def system_status():
    """システム状態チェック"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # データベース接続テスト
        cursor.execute("SELECT COUNT(*) FROM urls")
        url_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clicks")
        click_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_urls": url_count,
            "total_clicks": click_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
