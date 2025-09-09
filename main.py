from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import sqlite3
from datetime import datetime
import uvicorn

# 設定とデータベース初期化
import config
import database

# 初期化時にデータベースを作成
database.init_db()

# FastAPIアプリケーション作成
app = FastAPI(
    title="LinkTrack Pro",
    description="マーケティング効果測定のためのURL短縮・分析プラットフォーム",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ルーターのインポート（絶対インポートに統一）
from routes.redirect import router as redirect_router
from routes.shorten import router as shorten_router
from routes.analytics import router as analytics_router
from routes.bulk import router as bulk_router
from routes.export import router as export_router
from routes.admin import router as admin_router

# ルーターを登録
app.include_router(redirect_router)
app.include_router(shorten_router)
app.include_router(analytics_router)
app.include_router(bulk_router)
app.include_router(export_router)
app.include_router(admin_router)

# テンプレート設定
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """メインページ"""
    try:
        # システム統計取得
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        
        # 基本統計を取得
        cursor.execute("SELECT COUNT(*) FROM urls")
        total_links = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clicks")
        total_clicks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM clicks")
        unique_visitors = cursor.fetchone()[0]
        
        conn.close()
        
        stats = {
            "total_links": total_links,
            "total_clicks": total_clicks,
            "unique_visitors": unique_visitors,
            "system_status": "正常稼働中"
        }
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "stats": stats,
            "base_url": config.BASE_URL
        })
        
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "stats": {
                "total_links": 0,
                "total_clicks": 0,
                "unique_visitors": 0,
                "system_status": "初期化中"
            },
            "base_url": config.BASE_URL,
            "error": f"統計データの取得でエラーが発生しました: {str(e)}"
        })

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # データベース接続確認
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return JSONResponse({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "version": "1.0.0"
        })
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy", 
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }, status_code=500)

@app.get("/api/info")
async def api_info():
    """API情報エンドポイント"""
    return JSONResponse({
        "name": "LinkTrack Pro API",
        "version": "1.0.0",
        "description": "URL短縮・分析プラットフォーム",
        "base_url": config.BASE_URL,
        "endpoints": {
            "shorten": "/api/shorten",
            "analytics": "/analytics/{short_code}",
            "admin": "/admin",
            "bulk": "/bulk",
            "export": "/api/export",
            "health": "/health"
        }
    })

# デバッグ用エンドポイント
@app.get("/debug/db")
async def debug_database():
    """データベース状態確認（開発用）"""
    try:
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        
        # テーブル一覧取得
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        result = {"tables": tables, "data": {}}
        
        # 各テーブルのレコード数取得
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            result["data"][table] = {"count": count}
        
        conn.close()
        return JSONResponse(result)
        
    except Exception as e:
        return JSONResponse({
            "error": f"データベース確認エラー: {str(e)}"
        }, status_code=500)

if __name__ == "__main__":
    # 開発サーバー起動（本番ではuvicornコマンドを使用）
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
