from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime
from contextlib import asynccontextmanager
import config
from database import init_db
# 個別にルーターをインポート
from routes.redirect import router as redirect_router
from routes.shorten import router as shorten_router
from routes.analytics import router as analytics_router
from routes.bulk import router as bulk_router
from routes.export import router as export_router
from routes.admin import router as admin_router
# ライフスパンハンドラーを使用
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時処理
    print("🚀 Starting Enhanced Link Tracker API...")
    print(f"🌐 Base URL: {config.BASE_URL}")
    print(f"🔧 Initializing enhanced database at: {config.DB_PATH}")

    success = init_db()
    if success:
        print("✅ Enhanced database initialized successfully!")
        print(f"📊 管理画面: {config.BASE_URL}/admin")
        print(f"🔗 一括生成: {config.BASE_URL}/bulk")
        print(f"📈 分析例: {config.BASE_URL}/analytics/test123")
        print(f"📊 API Docs: {config.BASE_URL}/docs")
    else:
        print("❌ Database initialization failed!")

    yield  # アプリケーション実行中

    # シャットダウン時処理
    print("🛑 Shutting down...")
app = FastAPI(
    title="Enhanced Link Tracker API", 
    version="2.0.0",
    lifespan=lifespan
)
# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[""],
    allow_credentials=True,
    allow_methods=[""],
    allow_headers=[""],
)
# 修正版ルーター登録 - 適切なprefixを使用
# 1. 管理系エンドポイント（具体的なパス）
app.include_router(admin_router)           # 各ルーターファイル内で完全パス指定
app.include_router(bulk_router)            # /bulk, /bulk-generate
app.include_router(export_router)          # /export/
app.include_router(shorten_router)         # /api/shorten
app.include_router(analytics_router)       # /analytics/{short_code}
# 2. 最後にワイルドカードルーター
app.include_router(redirect_router)        # /{short_code} リダイレクト
# ルートページ
@app.get("/")
async def root():
    return {
        "message": "Enhanced Link Tracker API v2.0",
        "status": "running",
        "endpoints": {
            "admin_dashboard": f"{config.BASE_URL}/admin",
            "bulk_generation": f"{config.BASE_URL}/bulk", 
            "api_docs": f"{config.BASE_URL}/docs",
            "health_check": f"{config.BASE_URL}/health"
        },
        "available_routes": [
            "GET / - システム情報",
            "GET /health - ヘルスチェック",
            "GET /admin - 管理ダッシュボード",
            "GET /bulk - 一括生成ページ",
            "POST /bulk-generate - 一括生成API",
            "GET /analytics/{short_code} - 分析画面",
            "POST /api/shorten - URL短縮API",
            "GET /{short_code} - リダイレクト処理"
        ]
    }
# ヘルスチェック
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "base_url": config.BASE_URL,
        "database": config.DB_PATH
    }
if name == "main":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
