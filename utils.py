import os
import sqlite3
import logging
from config import DB_PATH

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
