import os
import sqlite3
from config import DB_PATH

def init_database():
    """データベースの初期化とバックアップ復元"""
    # データベースディレクトリの確認
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # バックアップファイルがあれば復元
    backup_path = DB_PATH + '.backup'
    if os.path.exists(backup_path):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        os.rename(backup_path, DB_PATH)
    
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
    
    # バックアップ作成
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
