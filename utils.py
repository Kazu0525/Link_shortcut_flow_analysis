import os
import sqlite3
import logging
import re
from typing import Dict, Any
from config import DB_PATH

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_location_info(ip_address: str) -> Dict[str, str]:
    """
    IPアドレスから位置情報を取得（簡易版）
    実際の実装ではIP Geolocation APIを使用する
    """
    # 簡易的な実装 - 本番環境では専用のAPIを使用
    if ip_address == "127.0.0.1":
        return {"country": "Local", "city": "Localhost"}
    
    # ここで実際のIP位置情報APIを呼び出す
    # 例: ipinfo.io, ipapi.co など
    return {"country": "Unknown", "city": "Unknown"}

def parse_user_agent(user_agent: str) -> Dict[str, str]:
    """
    ユーザーエージェント文字列を解析
    """
    if not user_agent:
        return {"browser": "Unknown", "device": "Unknown", "os": "Unknown"}
    
    result = {"browser": "Unknown", "device": "Unknown", "os": "Unknown"}
    
    # ブラウザ判定
    if "Chrome" in user_agent:
        result["browser"] = "Chrome"
    elif "Firefox" in user_agent:
        result["browser"] = "Firefox"
    elif "Safari" in user_agent:
        result["browser"] = "Safari"
    elif "Edge" in user_agent:
        result["browser"] = "Edge"
    
    # OS判定
    if "Windows" in user_agent:
        result["os"] = "Windows"
    elif "Mac" in user_agent:
        result["os"] = "Mac"
    elif "Linux" in user_agent:
        result["os"] = "Linux"
    elif "iPhone" in user_agent or "iPad" in user_agent:
        result["os"] = "iOS"
    elif "Android" in user_agent:
        result["os"] = "Android"
    
    # デバイス判定
    if "Mobile" in user_agent:
        result["device"] = "Mobile"
    elif "Tablet" in user_agent:
        result["device"] = "Tablet"
    else:
        result["device"] = "Desktop"
    
    return result

def parse_utm_parameters(referrer: str) -> Dict[str, str]:
    """
    UTMパラメータを解析
    """
    if not referrer:
        return {}
    
    utm_params = {}
    
    # 簡易的なUTMパラメータ解析
    utm_patterns = {
        'utm_source': r'[?&]utm_source=([^&]*)',
        'utm_medium': r'[?&]utm_medium=([^&]*)',
        'utm_campaign': r'[?&]utm_campaign=([^&]*)',
        'utm_term': r'[?&]utm_term=([^&]*)',
        'utm_content': r'[?&]utm_content=([^&]*)'
    }
    
    for key, pattern in utm_patterns.items():
        match = re.search(pattern, referrer)
        if match:
            utm_params[key] = match.group(1)
    
    return utm_params

def init_database():
    """データベースの初期化とバックアップ復元"""
    try:
        # データベースディレクトリの確認
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Created database directory: {db_dir}")
        
        # バックアップファイルのパス
        backup_path = DB_PATH + '.backup'
        
        # バックアップから復元（バックアップがあり、メインデータベースがない場合）
        if os.path.exists(backup_path) and not os.path.exists(DB_PATH):
            with open(backup_path, 'rb') as src, open(DB_PATH, 'wb') as dst:
                dst.write(src.read())
            logger.info("Database restored from backup")
        
        # データベース接続とテーブル作成
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # URLsテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            custom_name TEXT,
            campaign_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
        ''')
        
        # クリック履歴テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            referrer TEXT,
            source TEXT DEFAULT 'direct',
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (url_id) REFERENCES urls (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database tables initialized successfully")
        
        # バックアップ作成（データベースが存在する場合）
        if os.path.exists(DB_PATH):
            with open(DB_PATH, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
            logger.info("Database backup created")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

# その他のユーティリティ関数があればここに追加
