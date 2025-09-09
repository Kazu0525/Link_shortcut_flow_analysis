import sqlite3
import os
from datetime import datetime

# 絶対インポートに変更
import config

def init_db():
    """データベースとテーブルを初期化"""
    try:
        print(f"🗄️ データベースを初期化中: {config.DB_PATH}")
        
        # データベース接続
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
                created_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_date DATE GENERATED ALWAYS AS (DATE(created_at)) STORED
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
                clicked_at TEXT NOT NULL,
                clicked_date DATE GENERATED ALWAYS AS (DATE(clicked_at)) STORED,
                FOREIGN KEY (url_id) REFERENCES urls (id) ON DELETE CASCADE
            )
        """)
        
        # インデックス作成（パフォーマンス向上）
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code)",
            "CREATE INDEX IF NOT EXISTS idx_urls_created_at ON urls(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_urls_campaign ON urls(campaign_name)",
            "CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id)",
            "CREATE INDEX IF NOT EXISTS idx_clicks_clicked_at ON clicks(clicked_at)",
            "CREATE INDEX IF NOT EXISTS idx_clicks_source ON clicks(source)",
            "CREATE INDEX IF NOT EXISTS idx_clicks_ip_address ON clicks(ip_address)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # テーブル情報を確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ 作成済みテーブル: {[table[0] for table in tables]}")
        
        # 基本統計を表示
        cursor.execute("SELECT COUNT(*) FROM urls")
        url_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clicks")
        click_count = cursor.fetchone()[0]
        
        print(f"📊 現在のデータ: URLs={url_count}件, Clicks={click_count}件")
        
        conn.commit()
        conn.close()
        
        print("✅ データベース初期化完了")
        return True
        
    except Exception as e:
        print(f"❌ データベース初期化エラー: {e}")
        return False

def create_sample_data():
    """サンプルデータを作成（開発・テスト用）"""
    try:
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        
        # サンプルURL追加
        sample_urls = [
            {
                "short_code": "TEST01",
                "original_url": "https://www.google.com",
                "custom_name": "Google検索",
                "campaign_name": "テストキャンペーン"
            },
            {
                "short_code": "TEST02", 
                "original_url": "https://github.com",
                "custom_name": "GitHub",
                "campaign_name": "開発ツール"
            },
            {
                "short_code": "TEST03",
                "original_url": "https://www.youtube.com",
                "custom_name": "YouTube",
                "campaign_name": "動画サービス"
            }
        ]
        
        for url_data in sample_urls:
            cursor.execute("""
                INSERT OR IGNORE INTO urls 
                (short_code, original_url, custom_name, campaign_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                url_data["short_code"],
                url_data["original_url"],
                url_data["custom_name"],
                url_data["campaign_name"],
                datetime.now().isoformat()
            ))
        
        # サンプルクリックデータ追加
        cursor.execute("SELECT id FROM urls WHERE short_code = 'TEST01'")
        test_url_id = cursor.fetchone()
        
        if test_url_id:
            sample_clicks = [
                {
                    "url_id": test_url_id[0],
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "referrer": "https://twitter.com",
                    "source": "twitter"
                },
                {
                    "url_id": test_url_id[0],
                    "ip_address": "192.168.1.101",
                    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
                    "referrer": "",
                    "source": "direct"
                }
            ]
            
            for click_data in sample_clicks:
                cursor.execute("""
                    INSERT INTO clicks 
                    (url_id, ip_address, user_agent, referrer, source, clicked_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    click_data["url_id"],
                    click_data["ip_address"],
                    click_data["user_agent"],
                    click_data["referrer"],
                    click_data["source"],
                    datetime.now().isoformat()
                ))
        
        conn.commit()
        conn.close()
        
        print("✅ サンプルデータ作成完了")
        return True
        
    except Exception as e:
        print(f"❌ サンプルデータ作成エラー: {e}")
        return False

def backup_database():
    """データベースをバックアップ"""
    try:
        if not os.path.exists(config.DB_PATH):
            print("❌ データベースファイルが存在しません")
            return False
        
        backup_path = f"{config.DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # ファイルコピー
        import shutil
        shutil.copy2(config.DB_PATH, backup_path)
        
        print(f"✅ データベースバックアップ完了: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ データベースバックアップエラー: {e}")
        return False

def check_database_health():
    """データベースの健全性をチェック"""
    try:
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        
        # テーブル存在確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['urls', 'clicks']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ 不足しているテーブル: {missing_tables}")
            conn.close()
            return False
        
        # データ整合性チェック
        cursor.execute("""
            SELECT COUNT(*) FROM clicks c
            LEFT JOIN urls u ON c.url_id = u.id
            WHERE u.id IS NULL
        """)
        orphaned_clicks = cursor.fetchone()[0]
        
        if orphaned_clicks > 0:
            print(f"⚠️ 孤立したクリックデータ: {orphaned_clicks}件")
        
        # 統計情報
        cursor.execute("SELECT COUNT(*) FROM urls WHERE is_active = 1")
        active_urls = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clicks")
        total_clicks = cursor.fetchone()[0]
        
        print(f"✅ データベース健全性チェック完了")
        print(f"📊 アクティブURL: {active_urls}件, 総クリック数: {total_clicks}件")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ データベース健全性チェックエラー: {e}")
        return False

def cleanup_old_data():
    """古いデータをクリーンアップ"""
    try:
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        
        # 設定された日数より古いクリックデータを削除
        cutoff_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute(f"""
            DELETE FROM clicks 
            WHERE DATE(clicked_at) < DATE('{cutoff_date}', '-{config.CLICK_DATA_RETENTION_DAYS} days')
        """)
        
        deleted_clicks = cursor.rowcount
        
        # 非アクティブなURLで古いものを削除
        cursor.execute(f"""
            DELETE FROM urls 
            WHERE is_active = 0 
            AND DATE(created_at) < DATE('{cutoff_date}', '-{config.INACTIVE_URL_RETENTION_DAYS} days')
        """)
        
        deleted_urls = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ データクリーンアップ完了: クリック{deleted_clicks}件, URL{deleted_urls}件を削除")
        return True
        
    except Exception as e:
        print(f"❌ データクリーンアップエラー: {e}")
        return False

# 開発モードの場合は追加情報を表示
if config.DEBUG:
    print("🔧 データベースモジュール読み込み完了")
