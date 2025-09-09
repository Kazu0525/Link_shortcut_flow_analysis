import sqlite3
import config
import os

def init_db():
    """データベースを初期化"""
    try:
        # データベースファイルが存在しない場合は作成
        if not os.path.exists(config.DB_PATH):
            print(f"📂 新しいデータベースを作成: {config.DB_PATH}")
        
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        
        # URLsテーブル作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                custom_name TEXT,
                campaign_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Clicksテーブル作成
        cursor.execute("""
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
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_short_code ON urls(short_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_url_id ON clicks(url_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clicked_at ON clicks(clicked_at)")
        
        conn.commit()
        conn.close()
        
        print("✅ データベース初期化成功")
        return True
        
    except Exception as e:
        print(f"❌ データベース初期化失敗: {e}")
        return False

def get_db_connection():
    """データベース接続を取得"""
    return sqlite3.connect(config.DB_PATH)

def test_connection():
    """データベース接続テスト"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM urls")
        result = cursor.fetchone()
        conn.close()
        print(f"🔗 データベース接続OK - URL数: {result[0]}")
        return True
    except Exception as e:
        print(f"❌ データベース接続失敗: {e}")
        return False
