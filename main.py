# main.py - ボタン動作修正版
from fastapi import FastAPI, Request, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import sqlite3
from datetime import datetime
import uvicorn
import string
import random
import re

# 設定
BASE_URL = os.getenv("BASE_URL", "https://link-shortcut-flow-analysis.onrender.com")
DB_PATH = os.getenv("DB_PATH", "url_shortener.db")

# データベース初期化
def init_db():
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
    
    # Clicksテーブル
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

# ユーティリティ関数
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for _ in range(50):  # 最大50回試行
        code = ''.join(random.choices(chars, k=length))
        cursor.execute("SELECT 1 FROM urls WHERE short_code = ?", (code,))
        if not cursor.fetchone():
            conn.close()
            return code
    
    conn.close()
    raise HTTPException(status_code=500, detail="短縮コード生成に失敗しました")

def validate_url(url):
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))

def clean_url(url):
    return url.strip()

# データベース初期化
init_db()

# FastAPIアプリ
app = FastAPI(
    title="LinkTrack Pro",
    description="URL短縮・分析プラットフォーム",
    version="1.0.0"
)

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# シンプルなホームページHTML
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
        .stats-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #ff6b6b 0%, #ffa726 100%);
            color: white; padding: 20px; border-radius: 15px; text-align: center;
            transition: transform 0.3s ease;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-card:nth-child(2) { background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%); }
        .stat-card:nth-child(3) { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color: #333; }
        .stat-card:nth-child(4) { background: linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%); color: #333; }
        .stat-number { font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }
        .stat-label { font-size: 1.1em; opacity: 0.9; }
        .navigation { display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; }
        .nav-link {
            color: white; text-decoration: none; padding: 10px 20px;
            background: rgba(255,255,255,0.2); border-radius: 25px; transition: all 0.3s;
        }
        .nav-link:hover { background: rgba(255,255,255,0.3); transform: translateY(-2px); }
        .url-form { background: #f8f9fa; padding: 30px; border-radius: 15px; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: 600; color: #555; }
        .form-group input { 
            width: 100%; padding: 12px 15px; border: 2px solid #e1e5e9; 
            border-radius: 8px; font-size: 16px; transition: border-color 0.3s;
        }
        .form-group input:focus { outline: none; border-color: #667eea; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 12px 30px; border: none; border-radius: 8px;
            font-size: 16px; font-weight: 600; cursor: pointer; 
            transition: all 0.3s; text-decoration: none; display: inline-block;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .btn-secondary { background: linear-gradient(135deg, #6c757d 0%, #495057 100%); margin-left: 10px; }
        .btn-success { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); }
        .btn-warning { background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%); }
        .result-section { 
            background: #f8f9fa; padding: 20px; border-radius: 10px; 
            margin-top: 20px; display: none; animation: fadeIn 0.5s;
        }
        .result-success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .result-error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .copy-button { 
            background: #28a745; color: white; border: none; padding: 8px 16px; 
            border-radius: 5px; cursor: pointer; margin-left: 10px; transition: all 0.3s;
        }
        .copy-button:hover { background: #218838; }
        .footer { text-align: center; color: white; margin-top: 30px; opacity: 0.8; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .loading { text-align: center; padding: 20px; }
        .spinner { 
            border: 4px solid #f3f3f3; border-top: 4px solid #3498db; 
            border-radius: 50%; width: 40px; height: 40px; 
            animation: spin 2s linear infinite; margin: 0 auto;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
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
        // DOMが完全に読み込まれた後に実行
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM fully loaded');
            
            const form = document.getElementById('shortenForm');
            if (form) {
                console.log('Form found, adding event listener');
                form.addEventListener('submit', handleFormSubmit);
            } else {
                console.error('Form not found!');
            }
            
            // グローバル関数として登録
            window.clearForm = clearForm;
            window.copyToClipboard = copyToClipboard;
        });
        
        async function handleFormSubmit(e) {
            console.log('Form submitted');
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
                console.error('Error:', error);
                showResult({error: 'ネットワークエラーが発生しました'}, 'error');
            } finally {
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }
        }
        
        function showResult(data, type) {
            const section = document.getElementById('resultSection');
            const content = document.getElementById('resultContent');
            
            if (!section || !content) {
                console.error('Result elements not found');
                return;
            }
            
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
                        <a href="/analytics/${data.short_code}" class="btn btn-success">📈 分析ページ</a>
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
            const form = document.getElementById('shortenForm');
            const resultSection = document.getElementById('resultSection');
            
            if (form) form.reset();
            if (resultSection) resultSection.style.display = 'none';
        }
    </script>
</body>
</html>
"""

# ルート定義

@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM urls")
        total_links = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clicks")
        total_clicks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM clicks")
        unique_visitors = cursor.fetchone()[0]
        
        conn.close()
        
        html_content = INDEX_HTML.format(
            total_links=total_links,
            total_clicks=total_clicks,
            unique_visitors=unique_visitors,
            system_status="正常稼働中",
            base_url=BASE_URL
        )
        return HTMLResponse(content=html_content)
    except Exception as e:
        print(f"Error in root: {e}")
        html_content = INDEX_HTML.format(
            total_links=0, total_clicks=0, unique_visitors=0,
            system_status="初期化中", base_url=BASE_URL
        )
        return HTMLResponse(content=html_content)

# 他のルートは変更なし（admin, bulk, api/shorten-formなど）

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
