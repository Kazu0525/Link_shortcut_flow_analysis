from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import hashlib
import random
import string
from typing import Dict, List, Optional
from datetime import datetime
import json
import os

app = FastAPI()

# テンプレート設定
templates = Jinja2Templates(directory="templates")

# メモリ内データベース（本番環境では実際のDBを使用）
url_database: Dict[str, dict] = {}
analytics: Dict[str, dict] = {}

def generate_short_code(length: int = 6) -> str:
    """ランダムな短縮コード生成"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def validate_url(url: str) -> bool:
    """URL検証"""
    return url.startswith(('http://', 'https://'))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ホームページ表示"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/bulk-process")
async def bulk_process(urls: str = Form(...)):
    """一括URL短縮処理"""
    url_list = [url.strip() for url in urls.split('\n') if url.strip()]
    results = []
    
    for url in url_list:
        if not validate_url(url):
            results.append({
                "url": url,
                "success": False,
                "error": "無効なURL形式です"
            })
            continue
        
        # 短縮コード生成
        short_code = generate_short_code()
        while short_code in url_database:
            short_code = generate_short_code()
        
        # データベースに保存
        url_database[short_code] = {
            "original_url": url,
            "created_at": datetime.now().isoformat(),
            "clicks": 0
        }
        
        # 結果に追加
        short_url = f"https://yourapp.onrender.com/s/{short_code}"
        results.append({
            "url": url,
            "success": True,
            "short_url": short_url,
            "short_code": short_code
        })
    
    return JSONResponse(content={"results": results})

@app.get("/s/{short_code}")
async def redirect_url(short_code: str):
    """短縮URLからリダイレクト"""
    if short_code not in url_database:
        raise HTTPException(status_code=404, detail="URL not found")
    
    # クリック数を増やす
    url_database[short_code]["clicks"] += 1
    
    # アナリティクス記録
    if short_code not in analytics:
        analytics[short_code] = []
    
    analytics[short_code].append({
        "timestamp": datetime.now().isoformat(),
        "ip": "hidden"  # プライバシー保護
    })
    
    # リダイレクト
    original_url = url_database[short_code]["original_url"]
    return RedirectResponse(url=original_url, status_code=302)

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """管理画面（簡易版）"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>管理画面</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2c3e50;
                border-bottom: 4px solid #9C27B0;
                padding-bottom: 15px;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            .stat-number {
                font-size: 2.5em;
                font-weight: bold;
                margin: 10px 0;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 30px;
            }
            th {
                background: #9C27B0;
                color: white;
                padding: 12px;
                text-align: left;
            }
            td {
                padding: 12px;
                border-bottom: 1px solid #e0e0e0;
            }
            .btn-back {
                background: #4CAF50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin-top: 20px;
            }
            .btn-back:hover {
                background: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 URL短縮サービス管理画面</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div>総URL数</div>
                    <div class="stat-number">""" + str(len(url_database)) + """</div>
                </div>
                <div class="stat-card">
                    <div>総クリック数</div>
                    <div class="stat-number">""" + str(sum(url["clicks"] for url in url_database.values())) + """</div>
                </div>
            </div>
            
            <h2>登録済みURL一覧</h2>
            <table>
                <thead>
                    <tr>
                        <th>短縮コード</th>
                        <th>元のURL</th>
                        <th>作成日時</th>
                        <th>クリック数</th>
                    </tr>
                </thead>
                <tbody>"""
    
    for code, data in url_database.items():
        html_content += f"""
                    <tr>
                        <td>{code}</td>
                        <td style="max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            {data['original_url']}
                        </td>
                        <td>{data['created_at'][:19]}</td>
                        <td>{data['clicks']}</td>
                    </tr>"""
    
    html_content += """
                </tbody>
            </table>
            
            <a href="/" class="btn-back">🏠 ホームに戻る</a>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/api/stats")
async def get_stats():
    """統計情報API"""
    return {
        "total_urls": len(url_database),
        "total_clicks": sum(url["clicks"] for url in url_database.values()),
        "urls": url_database
    }

# Health check endpoint for Render
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
