from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import JSONResponse
import string
import random
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

# 絶対インポートに変更（qrcode完全除去）
import config
from models import ShortenRequest, ShortenResponse
from utils import generate_short_code, get_db_connection

router = APIRouter()

def generate_qr_code(url):
    """QRコード生成（軽量版：プレースホルダー）"""
    # 軽量化のためQRコード生成を無効化
    return f"QR_CODE_PLACEHOLDER_{url}"

@router.post("/api/shorten")
async def shorten_url(data: dict):
    """URL短縮APIエンドポイント（軽量版）"""
    try:
        # 入力データの検証
        original_url = data.get("original_url", "").strip()
        custom_name = data.get("custom_name", "").strip() or None
        campaign_name = data.get("campaign_name", "").strip() or None
        
        if not original_url:
            raise HTTPException(status_code=400, detail="URLが必要です")
        
        # URLの基本検証
        if not original_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="URLはhttp://またはhttps://で始まる必要があります")
        
        # 短縮コード生成（重複チェック付き）
        short_code = await generate_unique_short_code()
        
        # QRコード生成（軽量版）
        qr_code_data = generate_qr_code(f"{config.BASE_URL}/{short_code}")
        
        # データベースに保存
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO urls (short_code, original_url, custom_name, campaign_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            short_code,
            original_url,
            custom_name,
            campaign_name,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # レスポンス作成
        response = ShortenResponse(
            short_code=short_code,
            short_url=f"{config.BASE_URL}/{short_code}",
            original_url=original_url,
            qr_code_url=qr_code_data,
            created_at=datetime.now().isoformat(),
            custom_name=custom_name,
            campaign_name=campaign_name
        )
        
        return JSONResponse(content=response.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL短縮処理でエラーが発生しました: {str(e)}")

async def generate_unique_short_code(length=6):
    """重複しない短縮コードを生成"""
    chars = string.ascii_letters + string.digits
    max_attempts = 100
    
    for _ in range(max_attempts):
        code = ''.join(random.choices(chars, k=length))
        
        # データベースで重複チェック
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM urls WHERE short_code = ?", (code,))
        exists = cursor.fetchone()
        conn.close()
        
        if not exists:
            return code
    
    raise HTTPException(status_code=500, detail="短縮コードの生成に失敗しました")

@router.post("/api/shorten-form")
async def shorten_url_form(
    url: str = Form(...),
    custom_name: str = Form(None),
    campaign_name: str = Form(None)
):
    """フォームからのURL短縮処理"""
    try:
        # URLの前処理
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # 辞書形式でAPIを呼び出し
        request_data = {
            "original_url": url,
            "custom_name": custom_name if custom_name else None,
            "campaign_name": campaign_name if campaign_name else None
        }
        
        result = await shorten_url(request_data)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"フォーム処理エラー: {str(e)}")
