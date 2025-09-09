from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import JSONResponse
import string
import random
import sqlite3
import qrcode
import io
import base64
from datetime import datetime
import aiofiles
import os
from urllib.parse import urlparse

# 相対インポートを絶対インポートに変更
import config  # from .. import config から変更
from models import ShortenRequest, ShortenResponse  # from ..models import から変更
from utils import generate_short_code, get_db_connection  # from ..utils import から変更

router = APIRouter()

@router.post("/api/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest):
    """URL短縮APIエンドポイント"""
    try:
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
            str(request.original_url),
            request.custom_name,
            request.campaign_name,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return ShortenResponse(
            short_code=short_code,
            short_url=f"{config.BASE_URL}/{short_code}",
            original_url=str(request.original_url),
            qr_code_url=qr_code_data,
            created_at=datetime.now().isoformat(),
            custom_name=request.custom_name,
            campaign_name=request.campaign_name
        )
        
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

def generate_qr_code(url):
    """QRコード生成（Base64エンコード）"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Base64エンコード
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_data = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_data}"
        
    except Exception as e:
        print(f"QRコード生成エラー: {e}")
        return ""

@router.post("/api/shorten-form")
async def shorten_url_form(
    url: str = Form(...),
    custom_name: str = Form(None),
    campaign_name: str = Form(None)
):
    """フォームからのURL短縮処理"""
    try:
        # URLバリデーション
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        request_data = ShortenRequest(
            original_url=url,
            custom_name=custom_name if custom_name else None,
            campaign_name=campaign_name if campaign_name else None
        )
        
        result = await shorten_url(request_data)
        return JSONResponse(content=result.dict())
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"フォーム処理エラー: {str(e)}")
