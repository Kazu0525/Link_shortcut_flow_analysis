from fastapi import APIRouter, HTTPException
from models import ShortenRequest, ShortenResponse, ErrorResponse
import sqlite3
import string
import random
import qrcode
import io
import base64
from datetime import datetime
import config
import os

router = APIRouter()

def generate_short_code(length: int = 6) -> str:
    """短縮コードを生成"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_qr_code(url: str) -> str:
    """QRコードを生成してBase64エンコードされた文字列を返す"""
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
        
        # BytesIOを使用してBase64エンコード
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"QRコード生成エラー: {e}")
        return ""

@router.post("/api/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest):
    """URL短縮API"""
    try:
        # データベース接続
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        
        # 短縮コード生成（重複チェック付き）
        short_code = generate_short_code()
        while True:
            cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
            if not cursor.fetchone():
                break
            short_code = generate_short_code()
        
        # URLをデータベースに保存
        cursor.execute("""
            INSERT INTO urls (short_code, original_url, custom_name, campaign_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            short_code,
            str(request.url),
            request.custom_name,
            request.campaign_name,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # 短縮URLの生成
        short_url = f"{config.BASE_URL}/{short_code}"
        
        # QRコード生成
        qr_code_url = create_qr_code(short_url)
        
        return ShortenResponse(
            success=True,
            short_url=short_url,
            short_code=short_code,
            original_url=str(request.url),
            qr_code_url=qr_code_url,
            created_at=datetime.now().isoformat(),
            custom_name=request.custom_name,
            campaign_name=request.campaign_name
        )
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"データベースエラー: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")

@router.get("/api/urls")
async def get_all_urls():
    """全URL一覧取得API"""
    try:
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.id, u.short_code, u.original_url, u.custom_name, u.campaign_name, 
                u.created_at, u.is_active,
                COUNT(c.id) as total_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        urls = []
        for row in results:
            urls.append({
                "id": row[0],
                "short_code": row[1],
                "original_url": row[2],
                "custom_name": row[3],
                "campaign_name": row[4],
                "created_at": row[5],
                "is_active": bool(row[6]),
                "total_clicks": row[7],
                "short_url": f"{config.BASE_URL}/{row[1]}"
            })
        
        return {"success": True, "urls": urls}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エラー: {str(e)}")
