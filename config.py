import os
from pathlib import Path

# 基本設定（python-dotenv除去、os.getenv直接使用）
BASE_URL = os.getenv("BASE_URL", "https://link-shortcut-flow-analysis.onrender.com")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# データベース設定
DB_PATH = os.getenv("DB_PATH", "url_shortener.db")

# セキュリティ設定
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# URL短縮設定
SHORT_CODE_LENGTH = int(os.getenv("SHORT_CODE_LENGTH", "6"))
MAX_URL_LENGTH = int(os.getenv("MAX_URL_LENGTH", "2048"))
MAX_CUSTOM_NAME_LENGTH = int(os.getenv("MAX_CUSTOM_NAME_LENGTH", "50"))

# 制限設定
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))
MAX_URLS_PER_USER = int(os.getenv("MAX_URLS_PER_USER", "1000"))

# QRコード設定（軽量版）
QR_CODE_SIZE = int(os.getenv("QR_CODE_SIZE", "10"))
QR_CODE_BORDER = int(os.getenv("QR_CODE_BORDER", "4"))

# データ保持設定
CLICK_DATA_RETENTION_DAYS = int(os.getenv("CLICK_DATA_RETENTION_DAYS", "365"))
INACTIVE_URL_RETENTION_DAYS = int(os.getenv("INACTIVE_URL_RETENTION_DAYS", "730"))

# 分析設定
ANALYTICS_UPDATE_INTERVAL = int(os.getenv("ANALYTICS_UPDATE_INTERVAL", "60"))  # 秒
MAX_ANALYTICS_RECORDS = int(os.getenv("MAX_ANALYTICS_RECORDS", "10000"))

# エクスポート設定
MAX_EXPORT_RECORDS = int(os.getenv("MAX_EXPORT_RECORDS", "10000"))
EXPORT_FORMATS = ["json", "csv", "xlsx"]

# ログ設定
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "app.log")

# 危険なURL検出設定
MALICIOUS_DOMAINS = [
    "malware.com",
    "phishing.com", 
    "spam.com"
]

# 許可されるドメイン（空の場合は全て許可）
ALLOWED_DOMAINS = os.getenv("ALLOWED_DOMAINS", "").split(",") if os.getenv("ALLOWED_DOMAINS") else []

# ブロックするドメイン
BLOCKED_DOMAINS = os.getenv("BLOCKED_DOMAINS", "").split(",") if os.getenv("BLOCKED_DOMAINS") else []

# データベースディレクトリの作成
db_dir = Path(DB_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

# 設定検証
def validate_config():
    """設定の妥当性をチェック"""
    errors = []
    
    if not BASE_URL:
        errors.append("BASE_URLが設定されていません")
    
    if SHORT_CODE_LENGTH < 4 or SHORT_CODE_LENGTH > 20:
        errors.append("SHORT_CODE_LENGTHは4-20の範囲で設定してください")
    
    if MAX_URL_LENGTH < 100:
        errors.append("MAX_URL_LENGTHは100以上に設定してください")
    
    if errors:
        raise ValueError(f"設定エラー: {', '.join(errors)}")

# アプリケーション起動時に設定を検証
try:
    validate_config()
except ValueError as e:
    print(f"設定エラー: {e}")
    print("デフォルト設定で続行します...")

# 開発環境用の設定上書き
if DEBUG:
    print("🔧 デバッグモードで実行中")
    print(f"📍 BASE_URL: {BASE_URL}")
    print(f"🗄️ DB_PATH: {DB_PATH}")

# 本番環境用の設定確認
if ENVIRONMENT == "production":
    print("🚀 本番環境で実行中")
    if SECRET_KEY == "your-secret-key-change-in-production":
        print("⚠️ 警告: SECRET_KEYを本番用に変更してください")
