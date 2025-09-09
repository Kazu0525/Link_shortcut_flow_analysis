# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
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

# シンプルなインライン HTML（テンプレート不要版）
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkTrack Pro - URL短縮・分析プラットフォーム</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6; color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; font-weight: 300; }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .main-content {
            background: white; border-radius: 20px; padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1); margin-bottom: 30px;
        }
        .url-form { background: #f8f9fa; padding: 30px; border-radius: 15px; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: 600; color: #555; }
        .form-group input { width: 100%; padding: 12px 15px; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 16px; }
        .form-group input:focus { outline: none; border-color: #667eea; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 12px 30px; border: none; border-radius: 8px;
            font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.2s;
        }
        .btn:hover { transform: translateY(-2px); }
        .btn-secondary { background: #6c757d; margin-left: 10px; }
        .stats-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #ff6b6b 0%, #ffa726 100%);
            color: white; padding: 20px; border-radius: 15px; text-align: center;
        }
        .stat-card:nth-child(2) { background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%); }
        .stat-card:nth-child(3) { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color: #333; }
        .stat-card:nth-child(4) { background: linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%); color: #333; }
        .stat-number { font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }
        .stat-label { font-size: 1.1em; opacity: 0.9; }
        .navigation { display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; }
        .nav-link {
            color: white; text-decoration: none; padding: 10px 20px;
            background: rgba(255,255,255,0.2); border-radius: 25px; transition: background 0.3s;
        }
        .nav-link:hover { background: rgba(255,255,255,0.3); }
        .result-section { background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px; display: none; }
        .result-success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .result-error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .copy-button { background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; margin-left: 10px; }
        .footer { text-align: center; color: white; margin-top: 30px; opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔗 LinkTrack Pro</h1>
            <p>マーケティング効果測定のためのURL短縮・分析プラットフォーム</p>
        </div>
        
        <div class="navigation">
            <a href="/" class="nav-link">🏠 ホーム</a>
            <a href="/admin" class="nav-link">📊 管理ダッシュボード</a>
            <a href="/bulk" class="nav-link">📦 一括生成</a>
            <a href="/docs" class="nav-link">📚 API文書</a>
        </div>
        
        <div class="main-content">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{total_links}</div>
                    <div class="stat-label">総短縮URL数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_clicks}</div>
                    <div class="stat-label">総クリック数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{unique_visitors}</div>
                    <div class="stat-label">ユニーク訪問者</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">🟢</div>
                    <div class="stat-label">{system_status}</div>
                </div>
            </div>
            
            <div class="url-form">
                <h2>🚀 URL短縮サービス</h2>
                <form id="shortenForm">
                    <div class="form-group">
                        <label for="url">短縮したいURL *</label>
                        <input type="url" id="url" name="url" required placeholder="https://example.com">
                    </div>
                    <div class="form-group">
                        <label for="custom_name">カスタム名（任意）</label>
                        <input type="text" id="custom_name" name="custom_name" placeholder="わかりやすい名前">
                    </div>
                    <div class="form-group">
                        <label for="campaign_name">キャンペーン名（任意）</label>
                        <input type="text" id="campaign_name" name="campaign_name" placeholder="マーケティングキャンペーン名">
                    </div>
                    <button type="submit" class="btn">🔗 短縮URLを生成</button>
                    <button type="button" class="btn btn-secondary" onclick="clearForm()">🗑️ クリア</button>
                </form>
            </div>
            
            <div id="resultSection" class="result-section">
                <div id="resultContent"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2025 LinkTrack Pro - Powered by FastAPI & Render.com</p>
            <p>Base URL: {base_url}</p>
        </div>
    </div>

    <script>
        document.getElementById('shortenForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            
            submitButton.textContent = '🔄 処理中...';
            submitButton.disabled = true;
            
            try {
                const response = await fetch('/api/shorten-form', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showResult(result, 'success');
                } else {
                    showResult({error: result.detail || '処理に失敗しました'}, 'error');
                }
            } catch (error) {
                showResult({error: 'ネットワークエラーが発生しました'}, 'error');
            } finally {
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }
        });
        
        function showResult(data, type) {
            const section = document.getElementById('resultSection');
            const content = document.getElementById('resultContent');
            
            section.className = `result-section result-${type}`;
            section.style.display = 'block';
            
            if (type === 'success') {
                content.innerHTML = `
                    <h3>✅ 短縮URL生成完了</h3>
                    <div style="margin: 15px 0;">
                        <strong>短縮URL:</strong> 
                        <span id="shortUrl">${data.short_url}</span>
                        <button class="copy-button" onclick="copyToClipboard('${data.short_url}')">📋 コピー</button>
                    </div>
                    <div style="margin: 15px 0;">
                        <strong>元のURL:</strong> ${data.original_url}
                    </div>
                    ${data.custom_name ? `<div><strong>カスタム名:</strong> ${data.custom_name}</div>` : ''}
                    ${data.campaign_name ? `<div><strong>キャンペーン:</strong> ${data.campaign_name}</div>` : ''}
                    <div style="margin-top: 20px;">
                        <a href="/analytics/${data.short_code}" class="btn">📈 分析ページ</a>
                    </div>
                `;
            } else {
                content.innerHTML = `
                    <h3>❌ エラーが発生しました</h3>
                    <p>${data.error}</p>
                `;
            }
            section.scrollIntoView({ behavior: 'smooth' });
        }
        
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(function() {
                alert('📋 クリップボードにコピーしました！');
            }).catch(function() {
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                alert('📋 クリップボードにコピーしました！');
            });
        }
        
        function clearForm() {
            document.getElementById('shortenForm').reset();
            document.getElementById('resultSection').style.display = 'none';
        }
    </script>
</body>
</html>
"""

# ★★★ 重要: @router.get を @app.get に変更 ★★★
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """メインページ（インライン版）"""
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
        
        # HTMLに統計を埋め込み
        html_content = INDEX_HTML.format(
            total_links=total_links,
            total_clicks=total_clicks,
            unique_visitors=unique_visitors,
            system_status="正常稼働中",
            base_url=config.BASE_URL
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        # エラー時のフォールバック
        html_content = INDEX_HTML.format(
            total_links=0,
            total_clicks=0,
            unique_visitors=0,
            system_status="初期化中",
            base_url=config.BASE_URL
        )
        return HTMLResponse(content=html_content)

# ★★★ 重要: @router.get を @app.get に変更 ★★★
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

# ★★★ 重要: @router.get を @app.get に変更 ★★★
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

if __name__ == "__main__":
    # 開発サーバー起動（本番ではuvicornコマンドを使用）
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
