# main.py - 完全統合版
from fastapi import FastAPI, Request, HTTPException, Form, File, UploadFile
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

# HTMLテンプレート
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkTrack Pro</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        input {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .btn {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }}
        .btn:hover {{ background: #0056b3; }}
        .nav {{ text-align: center; margin-bottom: 20px; }}
        .nav a {{ margin: 0 10px; text-decoration: none; color: #007bff; }}
        .result {{ margin-top: 20px; padding: 15px; background: #d4edda; border-radius: 5px; }}
        .error {{ background: #f8d7da; color: #721c24; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 LinkTrack Pro</h1>
        <div class="nav">
            <a href="/">ホーム</a>
            <a href="/admin">管理</a>
            <a href="/bulk">一括生成</a>
        </div>
        
        <div class="stats">
            <p>総URL数: {total_links} | 総クリック数: {total_clicks}</p>
        </div>
        
        <form id="urlForm" method="post" action="/api/shorten-form">
            <div class="form-group">
                <label for="url">URL *</label>
                <input type="url" id="url" name="url" required placeholder="https://example.com">
            </div>
            <div class="form-group">
                <label for="custom_name">カスタム名</label>
                <input type="text" id="custom_name" name="custom_name" placeholder="わかりやすい名前">
            </div>
            <button type="submit" class="btn">短縮URLを生成</button>
        </form>
        
        <div id="result" style="display:none;"></div>
    </div>
    
    <script>
    document.getElementById('urlForm').addEventListener('submit', async function(e) {{
        e.preventDefault();
        const formData = new FormData(this);
        
        try {{
            const response = await fetch('/api/shorten-form', {{
                method: 'POST',
                body: formData
            }});
            
            const result = await response.json();
            const resultDiv = document.getElementById('result');
            
            if (response.ok) {{
                resultDiv.innerHTML = `
                    <div class="result">
                        <h3>✅ 生成完了</h3>
                        <p><strong>短縮URL:</strong> <a href="${{result.short_url}}" target="_blank">${{result.short_url}}</a></p>
                        <p><strong>元URL:</strong> ${{result.original_url}}</p>
                    </div>
                `;
            }} else {{
                resultDiv.innerHTML = `<div class="result error">エラー: ${{result.detail}}</div>`;
            }}
            resultDiv.style.display = 'block';
        }} catch (error) {{
            document.getElementById('result').innerHTML = `<div class="result error">ネットワークエラー</div>`;
            document.getElementById('result').style.display = 'block';
        }}
    }});
    </script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>管理画面</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .btn {{ background: #007bff; color: white; padding: 5px 10px; border: none; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>📊 管理画面</h1>
    <p><a href="/">← ホームに戻る</a></p>
    
    <table>
        <tr>
            <th>短縮コード</th>
            <th>元URL</th>
            <th>カスタム名</th>
            <th>クリック数</th>
            <th>作成日</th>
            <th>操作</th>
        </tr>
        {table_rows}
    </table>
</body>
</html>
"""

BULK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>一括生成</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .form-group {{ margin-bottom: 15px; }}
        textarea {{ width: 100%; height: 200px; }}
        .btn {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>📦 一括生成</h1>
    <p><a href="/">← ホームに戻る</a></p>
    
    <form method="post" action="/api/bulk-process">
        <div class="form-group">
            <label>URLリスト (1行に1URL)</label>
            <textarea name="urls" placeholder="https://example1.com&#10;https://example2.com&#10;https://example3.com" required></textarea>
        </div>
        <button type="submit" class="btn">一括生成</button>
    </form>
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
        
        html_content = INDEX_HTML.format(
            total_links=total_links,
            total_clicks=total_clicks
        )
        return HTMLResponse(content=html_content)
    except:
        html_content = INDEX_HTML.format(total_links=0, total_clicks=0)
        return HTMLResponse(content=html_content)

@app.post("/api/shorten-form")
async def shorten_form(url: str = Form(...), custom_name: str = Form("")):
    try:
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="無効なURLです")
        
        # 短縮コード生成
        conn = get_db_connection()
        cursor = conn.cursor()
        
        short_code = generate_short_code()
        while True:
            cursor.execute("SELECT 1 FROM urls WHERE short_code = ?", (short_code,))
            if not cursor.fetchone():
                break
            short_code = generate_short_code()
        
        # 保存
        cursor.execute("""
            INSERT INTO urls (short_code, original_url, custom_name, created_at)
            VALUES (?, ?, ?, ?)
        """, (short_code, clean_url(url), custom_name or None, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "short_code": short_code,
            "short_url": f"{BASE_URL}/{short_code}",
            "original_url": url,
            "custom_name": custom_name
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.short_code, u.original_url, u.custom_name, u.created_at,
                   COUNT(c.id) as click_count
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            ORDER BY u.created_at DESC
            LIMIT 50
        """)
        
        urls = cursor.fetchall()
        conn.close()
        
        table_rows = ""
        for url in urls:
            table_rows += f"""
            <tr>
                <td>{url[0]}</td>
                <td><a href="{url[1]}" target="_blank">{url[1][:50]}...</a></td>
                <td>{url[2] or '-'}</td>
                <td>{url[4]}</td>
                <td>{url[3]}</td>
                <td><a href="/analytics/{url[0]}" class="btn">分析</a></td>
            </tr>
            """
        
        html_content = ADMIN_HTML.format(table_rows=table_rows)
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        return HTMLResponse(content=f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

@app.get("/bulk", response_class=HTMLResponse)
async def bulk_page():
    return HTMLResponse(content=BULK_HTML)

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
                while True:
                    cursor.execute("SELECT 1 FROM urls WHERE short_code = ?", (short_code,))
                    if not cursor.fetchone():
                        break
                    short_code = generate_short_code()
                
                cursor.execute("""
                    INSERT INTO urls (short_code, original_url, created_at)
                    VALUES (?, ?, ?)
                """, (short_code, clean_url(url), datetime.now().isoformat()))
                
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/{short_code}", response_class=HTMLResponse)
async def analytics_page(short_code: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT original_url, created_at FROM urls WHERE short_code = ?", (short_code,))
        url_data = cursor.fetchone()
        
        if not url_data:
            return HTMLResponse(content="<h1>404</h1><p>URLが見つかりません</p>", status_code=404)
        
        cursor.execute("""
            SELECT COUNT(*) as total_clicks, COUNT(DISTINCT ip_address) as unique_visitors
            FROM clicks c
            JOIN urls u ON c.url_id = u.id
            WHERE u.short_code = ?
        """, (short_code,))
        
        stats = cursor.fetchone()
        conn.close()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>分析 - {short_code}</title></head>
        <body style="font-family: Arial; margin: 20px;">
            <h1>📈 分析: {short_code}</h1>
            <p><a href="/admin">← 管理画面に戻る</a></p>
            <p><strong>元URL:</strong> <a href="{url_data[0]}" target="_blank">{url_data[0]}</a></p>
            <p><strong>短縮URL:</strong> <a href="{BASE_URL}/{short_code}" target="_blank">{BASE_URL}/{short_code}</a></p>
            <p><strong>総クリック数:</strong> {stats[0] if stats else 0}</p>
            <p><strong>ユニーク訪問者:</strong> {stats[1] if stats else 0}</p>
            <p><strong>作成日:</strong> {url_data[1]}</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except Exception as e:
        return HTMLResponse(content=f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy", "timestamp": datetime.now().isoformat()})

# リダイレクト処理（最後に配置）
@app.get("/{short_code}")
async def redirect_url(short_code: str, request: Request):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, original_url FROM urls WHERE short_code = ? AND is_active = 1", (short_code,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="無効な短縮コードです")
        
        url_id, original_url = result
        
        # クリック記録
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        referrer = request.headers.get("referer", "")
        
        cursor.execute("""
            INSERT INTO clicks (url_id, ip_address, user_agent, referrer, clicked_at)
            VALUES (?, ?, ?, ?, ?)
        """, (url_id, client_ip, user_agent, referrer, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return RedirectResponse(url=original_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="リダイレクトエラー")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
