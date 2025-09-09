import sqlite3
import string
import random
from datetime import datetime
import hashlib
import re
from urllib.parse import urlparse

# 絶対インポートに変更
import config

def get_db_connection():
    """データベース接続を取得"""
    try:
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
        return conn
    except Exception as e:
        print(f"データベース接続エラー: {e}")
        raise

def generate_short_code(length=6):
    """ランダムな短縮コードを生成"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def validate_url(url: str) -> bool:
    """URLの形式をバリデーション"""
    try:
        parsed = urlparse(url)
        return all([
            parsed.scheme in ['http', 'https'],
            parsed.netloc,
            len(url) <= 2048  # URL長制限
        ])
    except Exception:
        return False

def sanitize_custom_name(custom_name: str) -> str:
    """カスタム名をサニタイズ"""
    if not custom_name:
        return None
    
    # 不正な文字を除去
    sanitized = re.sub(r'[<>"\'/\\&]', '', custom_name)
    
    # 長さ制限
    return sanitized[:50] if sanitized else None

def get_url_info(short_code: str):
    """短縮コードからURL情報を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, short_code, original_url, custom_name, campaign_name, 
                   created_at, is_active
            FROM urls 
            WHERE short_code = ?
        """, (short_code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        print(f"URL情報取得エラー: {e}")
        return None

def get_click_stats(url_id: int):
    """指定URLのクリック統計を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute("""
            SELECT 
                COUNT(*) as total_clicks,
                COUNT(DISTINCT ip_address) as unique_visitors,
                COUNT(CASE WHEN source = 'qr_code' THEN 1 END) as qr_clicks,
                MAX(clicked_at) as last_clicked
            FROM clicks 
            WHERE url_id = ?
        """, (url_id,))
        
        stats = dict(cursor.fetchone())
        
        # ソース別統計
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM clicks 
            WHERE url_id = ?
            GROUP BY source
            ORDER BY count DESC
        """, (url_id,))
        
        sources = [dict(row) for row in cursor.fetchall()]
        stats['sources'] = sources
        
        conn.close()
        return stats
        
    except Exception as e:
        print(f"クリック統計取得エラー: {e}")
        return None

def get_all_urls_stats():
    """全URL統計を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.id,
                u.short_code,
                u.original_url,
                u.custom_name,
                u.campaign_name,
                u.created_at,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                COUNT(CASE WHEN c.source = 'qr_code' THEN 1 END) as qr_clicks,
                MAX(c.clicked_at) as last_clicked
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """, ())
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
        
    except Exception as e:
        print(f"全URL統計取得エラー: {e}")
        return []

def format_datetime(dt_string: str, format_type="display"):
    """日時文字列をフォーマット"""
    try:
        if not dt_string:
            return ""
        
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        
        if format_type == "display":
            return dt.strftime("%Y/%m/%d %H:%M")
        elif format_type == "date":
            return dt.strftime("%Y/%m/%d")
        elif format_type == "time":
            return dt.strftime("%H:%M")
        else:
            return dt.isoformat()
            
    except Exception:
        return dt_string

def generate_hash(data: str) -> str:
    """データのハッシュ値を生成"""
    return hashlib.md5(data.encode()).hexdigest()

def is_safe_url(url: str) -> bool:
    """URLの安全性をチェック"""
    try:
        parsed = urlparse(url)
        
        # 危険なスキームをブロック
        dangerous_schemes = ['javascript', 'data', 'file', 'ftp']
        if parsed.scheme.lower() in dangerous_schemes:
            return False
        
        # ローカルIPアドレスをブロック
        host = parsed.netloc.lower()
        local_patterns = [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            '10.',
            '192.168.',
            '172.16.',
            '172.17.',
            '172.18.',
            '172.19.',
            '172.20.',
            '172.21.',
            '172.22.',
            '172.23.',
            '172.24.',
            '172.25.',
            '172.26.',
            '172.27.',
            '172.28.',
            '172.29.',
            '172.30.',
            '172.31.'
        ]
        
        for pattern in local_patterns:
            if host.startswith(pattern):
                return False
        
        return True
        
    except Exception:
        return False

def clean_url(url: str) -> str:
    """URLをクリーンアップ"""
    # 先頭・末尾の空白を除去
    url = url.strip()
    
    # プロトコルが無い場合はhttpsを追加
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url

def get_domain_from_url(url: str) -> str:
    """URLからドメイン名を抽出"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return ""

def truncate_text(text: str, max_length: int = 50) -> str:
    """テキストを指定長で切り詰め"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def export_to_csv_format(data: list) -> str:
    """データをCSV形式の文字列に変換"""
    if not data:
        return ""
    
    # ヘッダー
    headers = list(data[0].keys())
    csv_lines = [",".join(headers)]
    
    # データ行
    for row in data:
        values = [str(row.get(header, "")).replace(",", ";") for header in headers]
        csv_lines.append(",".join(values))
    
    return "\n".join(csv_lines)

def parse_user_agent(user_agent: str) -> dict:
    """User-Agentを解析してデバイス情報を取得"""
    if not user_agent:
        return {"device": "unknown", "browser": "unknown", "os": "unknown"}
    
    ua_lower = user_agent.lower()
    
    # デバイス判定
    device = "desktop"
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        device = "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device = "tablet"
    
    # ブラウザ判定
    browser = "unknown"
    if "chrome" in ua_lower:
        browser = "chrome"
    elif "firefox" in ua_lower:
        browser = "firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = "safari"
    elif "edge" in ua_lower:
        browser = "edge"
    
    # OS判定
    os_name = "unknown"
    if "windows" in ua_lower:
        os_name = "windows"
    elif "mac" in ua_lower:
        os_name = "macos"
    elif "linux" in ua_lower:
        os_name = "linux"
    elif "android" in ua_lower:
        os_name = "android"
    elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "ios"
    
    return {
        "device": device,
        "browser": browser,
        "os": os_name
    }
