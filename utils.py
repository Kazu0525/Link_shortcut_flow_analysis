import pyqrcode
import io
import base64
from PIL import Image
import string
import random
import sqlite3
import config
from datetime import datetime

def generate_short_code(length: int = 6) -> str:
    """短縮コードを生成"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_qr_code(url: str) -> str:
    """QRコードを生成してBase64エンコードされた文字列を返す（純Python版）"""
    try:
        # pyqrcodeを使用（純Python実装）
        qr = pyqrcode.create(url)
        
        # PNG形式でバイトストリームに出力
        buffer = io.BytesIO()
        qr.png(buffer, scale=8)
        
        # Base64エンコード
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"QRコード生成エラー: {e}")
        # フォールバック：シンプルなSVG QRコード
        try:
            qr_svg = pyqrcode.create(url)
            svg_string = qr_svg.svg(scale=4)
            svg_base64 = base64.b64encode(svg_string.encode()).decode()
            return f"data:image/svg+xml;base64,{svg_base64}"
        except:
            return ""

def get_db_connection():
    """データベース接続を取得"""
    return sqlite3.connect(config.DB_PATH)

def get_url_stats(short_code: str) -> dict:
    """URL統計を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # URL情報取得
        cursor.execute("""
            SELECT id, original_url, custom_name, campaign_name, created_at
            FROM urls 
            WHERE short_code = ? AND is_active = 1
        """, (short_code,))
        
        url_info = cursor.fetchone()
        if not url_info:
            conn.close()
            return None
        
        url_id = url_info[0]
        
        # クリック統計取得
        cursor.execute("""
            SELECT 
                COUNT(*) as total_clicks,
                COUNT(DISTINCT ip_address) as unique_clicks,
                COUNT(CASE WHEN source = 'qr' THEN 1 END) as qr_clicks
            FROM clicks 
            WHERE url_id = ?
        """, (url_id,))
        
        stats = cursor.fetchone()
        
        # 最近のクリック履歴
        cursor.execute("""
            SELECT ip_address, user_agent, referrer, source, clicked_at
            FROM clicks 
            WHERE url_id = ?
            ORDER BY clicked_at DESC
            LIMIT 10
        """, (url_id,))
        
        click_history = cursor.fetchall()
        
        conn.close()
        
        return {
            "url_id": url_id,
            "original_url": url_info[1],
            "custom_name": url_info[2],
            "campaign_name": url_info[3],
            "created_at": url_info[4],
            "total_clicks": stats[0] or 0,
            "unique_clicks": stats[1] or 0,
            "qr_clicks": stats[2] or 0,
            "click_history": [
                {
                    "ip_address": click[0],
                    "user_agent": click[1],
                    "referrer": click[2],
                    "source": click[3],
                    "clicked_at": click[4]
                }
                for click in click_history
            ]
        }
        
    except Exception as e:
        print(f"統計取得エラー: {e}")
        return None

def record_click(url_id: int, ip_address: str, user_agent: str = None, referrer: str = None, source: str = "direct"):
    """クリックを記録"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO clicks (url_id, ip_address, user_agent, referrer, source, clicked_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (url_id, ip_address, user_agent, referrer, source, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"クリック記録エラー: {e}")
        return False
