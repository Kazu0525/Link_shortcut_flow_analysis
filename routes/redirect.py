from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import sqlite3
from datetime import datetime
from urllib.parse import urlparse
import re

# 絶対インポートに変更
import config
from utils import get_db_connection

router = APIRouter()

@router.get("/{short_code}")
async def redirect_url(short_code: str, request: Request):
    """短縮URLのリダイレクト処理"""
    try:
        # 短縮コードのバリデーション
        if not validate_short_code(short_code):
            raise HTTPException(status_code=404, detail="無効な短縮コードです")
        
        # データベースから元のURLを取得
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, original_url, is_active 
            FROM urls 
            WHERE short_code = ?
        """, (short_code,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="短縮URLが見つかりません")
        
        url_id, original_url, is_active = result
        
        if not is_active:
            conn.close()
            raise HTTPException(status_code=410, detail="この短縮URLは無効になっています")
        
        # クリック情報を記録
        await record_click(cursor, url_id, request)
        
        conn.commit()
        conn.close()
        
        # リダイレクト実行
        return RedirectResponse(
            url=original_url,
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"リダイレクト処理でエラーが発生しました: {str(e)}")

async def record_click(cursor, url_id: int, request: Request):
    """クリック情報をデータベースに記録"""
    try:
        # リクエスト情報を取得
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        referrer = request.headers.get("referer", "")
        
        # トラフィック元の判定
        source = determine_traffic_source(referrer, user_agent)
        
        # クリック情報を挿入
        cursor.execute("""
            INSERT INTO clicks (url_id, ip_address, user_agent, referrer, source, clicked_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            url_id,
            client_ip,
            user_agent[:500],  # 長すぎるuser-agentを制限
            referrer[:500],    # 長すぎるreferrerを制限
            source,
            datetime.now().isoformat()
        ))
        
    except Exception as e:
        print(f"クリック記録エラー: {e}")
        # クリック記録のエラーはリダイレクトを阻害しない

def get_client_ip(request: Request) -> str:
    """クライアントIPアドレスを取得"""
    # プロキシ経由の場合のヘッダーを確認
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # 最初のIPアドレスを取得
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    # 直接接続の場合
    return request.client.host if request.client else "unknown"

def determine_traffic_source(referrer: str, user_agent: str) -> str:
    """トラフィック元を判定"""
    if not referrer:
        return "direct"
    
    try:
        parsed = urlparse(referrer)
        domain = parsed.netloc.lower()
        
        # 主要なソーシャルメディア
        social_platforms = {
            "twitter.com": "twitter",
            "t.co": "twitter",
            "facebook.com": "facebook",
            "instagram.com": "instagram",
            "linkedin.com": "linkedin",
            "youtube.com": "youtube",
            "tiktok.com": "tiktok",
            "line.me": "line"
        }
        
        for platform_domain, platform_name in social_platforms.items():
            if platform_domain in domain:
                return platform_name
        
        # 検索エンジン
        search_engines = {
            "google": "google",
            "yahoo": "yahoo",
            "bing": "bing",
            "duckduckgo": "duckduckgo"
        }
        
        for engine_name, engine_source in search_engines.items():
            if engine_name in domain:
                return f"search_{engine_source}"
        
        # メールクライアント
        if "mail" in domain or "outlook" in domain or "gmail" in domain:
            return "email"
        
        # QRコードスキャナーの検出
        if "qr" in user_agent.lower() or "scanner" in user_agent.lower():
            return "qr_code"
        
        # その他の参照元
        return f"referral_{domain}"
        
    except Exception:
        return "unknown"

def validate_short_code(short_code: str) -> bool:
    """短縮コードの形式をバリデーション"""
    # 英数字のみ、6-10文字
    pattern = r'^[a-zA-Z0-9]{6,10}$'
    return bool(re.match(pattern, short_code))

@router.get("/qr/{short_code}")
async def redirect_from_qr(short_code: str, request: Request):
    """QRコード経由のリダイレクト処理"""
    try:
        # 通常のリダイレクト処理を実行
        response = await redirect_url(short_code, request)
        
        # QRコード経由であることを記録するため、sourceを更新
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 最新のクリック記録を更新
        cursor.execute("""
            UPDATE clicks 
            SET source = 'qr_code'
            WHERE url_id = (
                SELECT id FROM urls WHERE short_code = ?
            )
            AND clicked_at = (
                SELECT MAX(clicked_at) FROM clicks 
                WHERE url_id = (SELECT id FROM urls WHERE short_code = ?)
            )
        """, (short_code, short_code))
        
        conn.commit()
        conn.close()
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QRリダイレクト処理でエラーが発生しました: {str(e)}")
