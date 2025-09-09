import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# 基本設定
BASE_URL = os.getenv("BASE_URL", "https://link-shortcut-flow-analysis.onrender.com")
DB_PATH = os.getenv("DB_PATH", "url_shortener.db")

# データベース設定
DATABASE_URL = f"sqlite:///{DB_PATH}"

# QRコード設定
QR_CODE_SIZE = 10
QR_CODE_BORDER = 4

# セキュリティ設定
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

# デバッグモード
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
