# main.py - 完全修正版（ボタン動作+デプロイ対応）
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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
    return ''.join(random.choices(chars, k=length))

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

# シンプルなホームページHTML
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkTrack Pro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #667eea; color: white; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .nav { display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; }
        .nav a { color: white; padding: 10px 20px; background: rgba(255,255,255,0.2); 
                border-radius: 25px; text-decoration: none; }
        .nav a:hover { background: rgba(255,255,255,0.3); }
        .main { background: white; padding: 30px; border-radius: 15px; color: #333; }
        .stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat { background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 5px; }
        .btn { background: #007bff; color: white; padding: 12px 25px; border: none; 
              border-radius: 5px; cursor: pointer; margin-right: 10px; }
        .btn:hover { background: #0056b3; }
        .btn-secondary { background: #6c757d; }
        .result { margin-top: 20px; padding: 15px; border-radius: 5px; display: none; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .footer { text-align: center; margin-top: 30px; opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔗 LinkTrack Pro</h1>
            <p>URL短縮・分析プラットフォーム</p>
        </div>
        
        <div class="nav">
            <a href="/">🏠 ホーム</a>
            <a href="/admin">📊 管理画面</a>
            <a href="/bulk">📦 一括生成</a>
        </div>
        
        <div class="main">
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{total_links}</div>
                    <div>総URL数</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{total_clicks}</div>
                    <div>総クリック数</div>
                </div>
            </div>
            
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
                    <input type="text" id="campaign_name" name="campaign_name" placeholder="キャンペーン名">
                </div>
                <button type="submit" class="btn">🔗 短縮URLを生成</button>
                <button type="button" class="btn btn-secondary" onclick="clearForm()">🗑️ クリア</button>
            </form>
            
            <div id="resultSection" class="result">
                <div id="resultContent"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2025 LinkTrack Pro - Powered by FastAPI & Render.com</p>
        </div>
    </div>

    <script>
        // フォーム送信処理
        document.getElementById('shortenForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            
            submitButton.textContent = '処理中...';
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
                    showResult({error: result.detail || 'エラーが発生しました'}, 'error');
                }
            } catch (error) {
                showResult({error: 'ネットワークエラー'}, 'error');
            } finally {
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }
        });
        
        function showResult(data, type) {
            const section = document.getElementById('resultSection');
            const content = document.getElementById('resultContent');
            
            section.className = `result ${type}`;
            section.style.display = 'block';
            
            if (type === 'success') {
                content.innerHTML = `
                    <h3>✅ 生成完了</h3>
                    <p><strong>短縮URL:</strong> ${data.short_url}</p>
                    <p><strong>元URL:</strong> ${data.original_url}</p>
                    <button onclick="copyToClipboard('${data.short_url}')" class="btn">📋 コピー</button>
                `;
            } else {
                content.innerHTML = `<h3>❌ エラー</h3><p>${data.error}</p>`;
            }
        }
        
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('クリップボードにコピーしました！');
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

# シンプルな管理画面HTML
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>管理画面</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
        .stat { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #007bff; color: white; }
        .btn { padding: 5px 10px; background: #28a745; color: white; text-decoration: none; border-radius: 3px; }
        .nav { margin: 20px 0; }
        .nav a { margin-right: 15px; padding: 10px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 管理画面</h1>
        
        <div class="nav">
            <a href="/">🏠 ホーム</a>
            <a href="/bulk">📦 一括生成</a>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-number">{total_urls}</div>
                <div>総URL数</div>
            </div>
            <div class="stat">
                <div class="stat-number">{total_clicks}</div>
                <div>総クリック数</div>
            </div>
            <div class="stat">
                <div class="stat-number">{unique_clicks}</div>
                <div>ユニーク訪問者</div>
            </div>
            <div class="stat">
                <div class="stat-number">{qr_clicks}</div>
                <div>QRクリック</div>
            </div>
        </div>

        <h2>📋 URL一覧</h2>
        <table>
            <thead>
                <tr>
                    <th>短縮コード</th>
                    <th>元URL</th>
                    <th>カスタム名</th>
                    <th>作成日</th>
                    <th>クリック数</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

# シンプルな一括生成HTML
BULK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>一括生成</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; }
        .instructions { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .action-buttons { margin: 20px 0; }
        .btn { padding: 10px 15px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px; }
        .btn:hover { background: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 8px; border: 1px solid #ddd; }
        th { background: #007bff; color: white; }
        input { width: 100%; padding: 5px; }
        .results { margin: 20px 0; }
        .result-item { background: #d4edda; padding: 10px; margin: 5px 0; border-radius: 3px; }
        .error-item { background: #f8d7da; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📦 一括リンク生成</h1>
        
        <div class="instructions">
            <h3>📋 使い方</h3>
            <p>1. URLを入力（http:// または https:// で始めてください）</p>
            <p>2. 「🚀 一括生成開始」ボタンをクリック</p>
        </div>

        <div class="action-buttons">
            <button class="btn" onclick="addRow()">➕ 行追加</button>
            <button class="btn" onclick="clearAll()">🗑️ 全削除</button>
            <button class="btn" onclick="generateLinks()">🚀 一括生成開始</button>
            <button class="btn" onclick="location.href='/admin'">📊 管理画面へ</button>
        </div>

        <table id="urlTable">
            <thead>
                <tr>
                    <th>URL ※必須</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><input type="url" placeholder="https://example.com" /></td>
                    <td><button onclick="deleteRow(this)">削除</button></td>
                </tr>
            </tbody>
        </table>

        <div class="results" id="resultsArea" style="display: none;">
            <h2>📈 生成結果</h2>
            <div id="resultsContent"></div>
        </div>
    </div>

    <script>
        function addRow() {
            const table = document.getElementById('urlTable').getElementsByTagName('tbody')[0];
            const newRow = table.insertRow();
            newRow.innerHTML = `
                <td><input type="url" placeholder="https://example.com" /></td>
                <td><button onclick="deleteRow(this)">削除</button></td>
            `;
        }
        
        function deleteRow(button) {
            const table = document.getElementById('urlTable').getElementsByTagName('tbody')[0];
            if (table.rows.length > 1) {
                button.closest('tr').remove();
            }
        }
        
        function clearAll() {
            if (confirm('全て削除しますか？')) {
                const table = document.getElementById('urlTable').getElementsByTagName('tbody')[0];
                table.innerHTML = `
                    <tr>
                        <td><input type="url" placeholder="https://example.com" /></td>
                        <td><button onclick="deleteRow(this)">削除</button></td>
                    </tr>
                `;
                document.getElementById('resultsArea').style.display = 'none';
            }
        }
        
        async function generateLinks() {
            const table = document.getElementById('urlTable').getElementsByTagName('tbody')[0];
            const rows = table.getElementsByTagName('tr');
            const urls = [];
            
            for (let i = 0; i < rows.length; i++) {
                const input = rows[i].cells[0].querySelector('input');
                const url = input.value.trim();
                if (url) {
                    if (!url.startsWith('http://') && !url.startsWith('https://')) {
                        alert(`行 ${i + 1}: URLは http:// または https:// で始めてください`);
                        return;
                    }
                    urls.push(url);
                }
            }
            
            if (urls.length === 0) {
                alert('少なくとも1つのURLを入力してください');
                return;
            }
            
            const button = document.querySelector('button[onclick="generateLinks()"]');
            button.disabled = true;
            button.textContent = '生成中...';
            
            try {
                const formData = new FormData();
                formData.append('urls', urls.join('\n'));
                
                const response = await fetch('/api/bulk-process', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                showResults(result);
                
            } catch (error) {
                alert('エラーが発生しました: ' + error.message);
            } finally {
                button.disabled = false;
                button.textContent = '🚀 一括生成開始';
            }
        }
        
        function showResults(result) {
            const resultsArea = document.getElementById('resultsArea');
            const resultsContent = document.getElementById('resultsContent');
            
            resultsArea.style.display = 'block';
            let html = '';
            
            if (result.results) {
                result.results.forEach(item => {
                    if (item.success) {
                        html += `
                            <div class="result-item">
                                <p><strong>元URL:</strong> ${item.url}</p>
                                <p><strong>短縮URL:</strong> ${item.short_url}</p>
                                <button onclick="copyText('${item.short_url}')">📋 コピー</button>
                            </div>
                        `;
                    } else {
                        html += `<div class="error-item">❌ ${item.url} - ${item.error}</div>`;
                    }
                });
            }
            
            resultsContent.innerHTML = html;
        }
        
        function copyText(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('クリップボードにコピーしました: ' + text);
            });
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
        
        conn.close()
        
        return HTMLResponse(INDEX_HTML.format(
            total_links=total_links,
            total_clicks=total_clicks
        ))
    except:
        return HTMLResponse(INDEX_HTML.format(total_links=0, total_clicks=0))

@app.post("/api/shorten-form")
async def shorten_form(url: str = Form(...), custom_name: str = Form(""), campaign_name: str = Form("")):
    try:
        if not validate_url(url):
            return JSONResponse({"error": "無効なURLです"}, status_code=400)
        
        short_code = generate_short_code()
        clean_url_str = clean_url(url)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO urls (short_code, original_url, custom_name, campaign_name)
            VALUES (?, ?, ?, ?)
        """, (short_code, clean_url_str, custom_name or None, campaign_name or None))
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "short_code": short_code,
            "short_url": f"{BASE_URL}/{short_code}",
            "original_url": clean_url_str,
            "custom_name": custom_name,
            "campaign_name": campaign_name
        })
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM urls")
        total_urls = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clicks")
        total_clicks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM clicks")
        unique_clicks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clicks WHERE source = 'qr'")
        qr_clicks = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT short_code, original_url, created_at, custom_name, 
                   (SELECT COUNT(*) FROM clicks WHERE url_id = urls.id) as click_count
            FROM urls ORDER BY created_at DESC LIMIT 20
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        table_rows = ""
        for row in rows:
            table_rows += f"""
            <tr>
                <td>{row['short_code']}</td>
                <td><a href="{row['original_url']}" target="_blank">{row['original_url'][:50]}...</a></td>
                <td>{row['custom_name'] or '-'}</td>
                <td>{row['created_at']}</td>
                <td>{row['click_count']}</td>
                <td><a href="/analytics/{row['short_code']}" class="btn">分析</a></td>
            </tr>
            """
        
        return HTMLResponse(ADMIN_HTML.format(
            total_urls=total_urls,
            total_clicks=total_clicks,
            unique_clicks=unique_clicks,
            qr_clicks=qr_clicks,
            table_rows=table_rows
        ))
        
    except Exception as e:
        return HTMLResponse(f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

@app.get("/bulk", response_class=HTMLResponse)
async def bulk_page():
    return HTMLResponse(BULK_HTML)

@app.post("/api/bulk-process")
async def bulk_process(urls: str = Form(...)):
    try:
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        results = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for url in url_list:
            if validate_url(url):
                short_code = generate_short_code()
                clean_url_str = clean_url(url)
                
                cursor.execute("""
                    INSERT INTO urls (short_code, original_url)
                    VALUES (?, ?)
                """, (short_code, clean_url_str))
                
                results.append({
                    "url": url,
                    "short_url": f"{BASE_URL}/{short_code}",
                    "success": True
                })
            else:
                results.append({"url": url, "success": False, "error": "無効なURL"})
        
        conn.commit()
        conn.close()
        
        return JSONResponse({"results": results})
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/analytics/{short_code}", response_class=HTMLResponse)
async def analytics_page(short_code: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT original_url, created_at FROM urls WHERE short_code = ?", (short_code,))
        url_data = cursor.fetchone()
        
        if not url_data:
            return HTMLResponse("<h1>404</h1><p>URLが見つかりません</p>", status_code=404)
        
        cursor.execute("""
            SELECT COUNT(*) as total_clicks, COUNT(DISTINCT ip_address) as unique_visitors
            FROM clicks WHERE url_id = (SELECT id FROM urls WHERE short_code = ?)
        """, (short_code,))
        
        stats = cursor.fetchone()
        conn.close()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>分析 - {short_code}</title>
        <style>body{{font-family:Arial;margin:20px}}</style>
        </head>
        <body>
            <h1>📈 分析: {short_code}</h1>
            <p><strong>短縮URL:</strong> <a href="{BASE_URL}/{short_code}">{BASE_URL}/{short_code}</a></p>
            <p><strong>元URL:</strong> <a href="{url_data['original_url']}">{url_data['original_url']}</a></p>
            <p><strong>作成日:</strong> {url_data['created_at']}</p>
            <p><strong>総クリック数:</strong> {stats['total_clicks']}</p>
            <p><strong>ユニーク訪問者:</strong> {stats['unique_visitors']}</p>
            <p><a href="/admin">← 管理画面に戻る</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except Exception as e:
        return HTMLResponse(f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.get("/{short_code}")
async def redirect_url(short_code: str, request: Request):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, original_url FROM urls WHERE short_code = ?", (short_code,))
        result = cursor.fetchone()
        
        if not result:
            return HTMLResponse("<h1>404</h1><p>URLが見つかりません</p>", status_code=404)
        
        url_id, original_url = result
        
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        referrer = request.headers.get("referer", "")
        
        cursor.execute("""
            INSERT INTO clicks (url_id, ip_address, user_agent, referrer)
            VALUES (?, ?, ?, ?)
        """, (url_id, client_ip, user_agent, referrer))
        
        conn.commit()
        conn.close()
        
        return RedirectResponse(url=original_url)
        
    except Exception as e:
        return HTMLResponse(f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
