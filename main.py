# main.py - 高品質UI/UX統合版
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

# 高品質HTMLテンプレート
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkTrack Pro - URL短縮・分析プラットフォーム</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6; color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; color: white; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; font-weight: 300; }}
        .header p {{ font-size: 1.2em; opacity: 0.9; }}
        .main-content {{
            background: white; border-radius: 20px; padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1); margin-bottom: 30px;
        }}
        .stats-grid {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #ff6b6b 0%, #ffa726 100%);
            color: white; padding: 20px; border-radius: 15px; text-align: center;
            transition: transform 0.3s ease;
        }}
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-card:nth-child(2) {{ background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%); }}
        .stat-card:nth-child(3) {{ background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color: #333; }}
        .stat-card:nth-child(4) {{ background: linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%); color: #333; }}
        .stat-number {{ font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }}
        .stat-label {{ font-size: 1.1em; opacity: 0.9; }}
        .navigation {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; }}
        .nav-link {{
            color: white; text-decoration: none; padding: 10px 20px;
            background: rgba(255,255,255,0.2); border-radius: 25px; transition: all 0.3s;
        }}
        .nav-link:hover {{ background: rgba(255,255,255,0.3); transform: translateY(-2px); }}
        .url-form {{ background: #f8f9fa; padding: 30px; border-radius: 15px; margin-bottom: 30px; }}
        .form-group {{ margin-bottom: 20px; }}
        .form-group label {{ display: block; margin-bottom: 8px; font-weight: 600; color: #555; }}
        .form-group input {{ 
            width: 100%; padding: 12px 15px; border: 2px solid #e1e5e9; 
            border-radius: 8px; font-size: 16px; transition: border-color 0.3s;
        }}
        .form-group input:focus {{ outline: none; border-color: #667eea; }}
        .btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 12px 30px; border: none; border-radius: 8px;
            font-size: 16px; font-weight: 600; cursor: pointer; 
            transition: all 0.3s; text-decoration: none; display: inline-block;
        }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }}
        .btn-secondary {{ background: linear-gradient(135deg, #6c757d 0%, #495057 100%); margin-left: 10px; }}
        .btn-success {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); }}
        .btn-warning {{ background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%); }}
        .result-section {{ 
            background: #f8f9fa; padding: 20px; border-radius: 10px; 
            margin-top: 20px; display: none; animation: fadeIn 0.5s;
        }}
        .result-success {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }}
        .result-error {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }}
        .copy-button {{ 
            background: #28a745; color: white; border: none; padding: 8px 16px; 
            border-radius: 5px; cursor: pointer; margin-left: 10px; transition: all 0.3s;
        }}
        .copy-button:hover {{ background: #218838; }}
        .footer {{ text-align: center; color: white; margin-top: 30px; opacity: 0.8; }}
        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        .loading {{ text-align: center; padding: 20px; }}
        .spinner {{ 
            border: 4px solid #f3f3f3; border-top: 4px solid #3498db; 
            border-radius: 50%; width: 40px; height: 40px; 
            animation: spin 2s linear infinite; margin: 0 auto;
        }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
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
        document.getElementById('shortenForm').addEventListener('submit', async function(e) {{
            e.preventDefault();
            const formData = new FormData(this);
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            
            submitButton.textContent = '🔄 処理中...';
            submitButton.disabled = true;
            
            try {{
                const response = await fetch('/api/shorten-form', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                if (response.ok) {{
                    showResult(result, 'success');
                }} else {{
                    showResult({{error: result.detail || '処理に失敗しました'}}, 'error');
                }}
            }} catch (error) {{
                showResult({{error: 'ネットワークエラーが発生しました'}}, 'error');
            }} finally {{
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }}
        }});
        
        function showResult(data, type) {{
            const section = document.getElementById('resultSection');
            const content = document.getElementById('resultContent');
            
            section.className = `result-section result-${{type}}`;
            section.style.display = 'block';
            
            if (type === 'success') {{
                content.innerHTML = `
                    <h3>✅ 短縮URL生成完了</h3>
                    <div style="margin: 15px 0;">
                        <strong>短縮URL:</strong> 
                        <span id="shortUrl">${{data.short_url}}</span>
                        <button class="copy-button" onclick="copyToClipboard('${{data.short_url}}')">📋 コピー</button>
                    </div>
                    <div style="margin: 15px 0;">
                        <strong>元のURL:</strong> ${{data.original_url}}
                    </div>
                    ${{data.custom_name ? \`<div><strong>カスタム名:</strong> ${{data.custom_name}}</div>\` : ''}}
                    ${{data.campaign_name ? \`<div><strong>キャンペーン:</strong> ${{data.campaign_name}}</div>\` : ''}}
                    <div style="margin-top: 20px;">
                        <a href="/analytics/${{data.short_code}}" class="btn btn-success">📈 分析ページ</a>
                    </div>
                `;
            }} else {{
                content.innerHTML = `
                    <h3>❌ エラーが発生しました</h3>
                    <p>${{data.error}}</p>
                `;
            }}
            section.scrollIntoView({{ behavior: 'smooth' }});
        }}
        
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(function() {{
                alert('📋 クリップボードにコピーしました！');
            }}).catch(function() {{
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                alert('📋 クリップボードにコピーしました！');
            }});
        }}
        
        function clearForm() {{
            document.getElementById('shortenForm').reset();
            document.getElementById('resultSection').style.display = 'none';
        }}
    </script>
</body>
</html>
"""

# 高品質管理画面HTML
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>管理画面 - LinkTrack Pro</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f9f9f9; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }}
        .stat-number {{ font-size: 2.5em; font-weight: bold; color: #4CAF50; }}
        .stat-label {{ color: #666; margin-top: 10px; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #4CAF50; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .action-btn {{ 
            padding: 5px 10px; margin: 2px; border: none; border-radius: 3px; 
            cursor: pointer; text-decoration: none; display: inline-block; color: white;
        }}
        .analytics-btn {{ background: #2196F3; }}
        .qr-btn {{ background: #FF9800; }}
        .export-btn {{ background: #4CAF50; }}
        .refresh-btn {{ background: #9C27B0; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 10px 0; }}
        .nav-buttons {{ text-align: center; margin: 20px 0; }}
        .nav-buttons a {{ margin: 0 10px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 管理画面 - LinkTrack Pro</h1>
        
        <div class="nav-buttons">
            <a href="/">🏠 ホーム</a>
            <a href="/bulk">📦 一括生成</a>
            <a href="/docs">📚 API文書</a>
            <button class="refresh-btn" onclick="location.reload()">🔄 データ更新</button>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_urls}</div>
                <div class="stat-label">総URL数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_clicks}</div>
                <div class="stat-label">総クリック数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{unique_clicks}</div>
                <div class="stat-label">ユニーク訪問者</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{qr_clicks}</div>
                <div class="stat-label">QRコードクリック</div>
            </div>
        </div>

        <h2>📋 URL一覧</h2>
        <table>
            <thead>
                <tr>
                    <th>短縮コード</th>
                    <th>元URL</th>
                    <th>カスタム名</th>
                    <th>キャンペーン</th>
                    <th>作成日</th>
                    <th>クリック数</th>
                    <th>ユニーク</th>
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

# ローカル風高品質一括生成HTML（ボタン修正版）
BULK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>一括リンク生成システム</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; display: flex; align-items: center; }}
        h1::before {{ content: '🚀'; margin-right: 10px; }}
        .instructions {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .instructions h3 {{ margin-bottom: 15px; display: flex; align-items: center; }}
        .instructions h3::before {{ content: '📋'; margin-right: 8px; }}
        .action-buttons {{ text-align: center; margin: 20px 0; }}
        .btn {{ 
            padding: 8px 16px; margin: 3px; border: none; border-radius: 4px; 
            cursor: pointer; font-size: 13px; font-weight: 500;
            transition: all 0.2s ease;
        }}
        .btn:hover {{ transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
        .btn-add {{ background: #2196F3; color: white; }}
        .btn-clear {{ background: #FF9800; color: white; }}
        .btn-generate {{ background: #f44336; color: white; font-weight: bold; }}
        .btn-admin {{ background: #4CAF50; color: white; }}
        .spreadsheet-container {{ margin: 20px 0; overflow-x: auto; border: 1px solid #ddd; border-radius: 8px; }}
        .spreadsheet-table {{ width: 100%; border-collapse: collapse; min-width: 1400px; }}
        .spreadsheet-table th {{ 
            background: #4CAF50; color: white; text-align: center; 
            padding: 12px 8px; border: 1px solid #45a049; font-weight: 600;
        }}
        .spreadsheet-table td {{ border: 1px solid #ddd; padding: 4px; }}
        .spreadsheet-table input {{ 
            width: 100%; border: none; padding: 8px 6px; font-size: 13px;
            outline: none; background: transparent;
        }}
        .spreadsheet-table input:focus {{ background: #fff3cd; }}
        .row-number {{ background: #f8f9fa; text-align: center; font-weight: bold; width: 60px; }}
        .delete-btn {{ 
            background: #dc3545; color: white; border: none; 
            padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 11px;
        }}
        .results-section {{ margin: 30px 0; display: none; }}
        .result-item {{ 
            background: #d4edda; padding: 15px; margin: 10px 0; 
            border-radius: 5px; border-left: 4px solid #28a745; 
        }}
        .error-item {{ background: #f8d7da; border-left: 4px solid #dc3545; color: #721c24; }}
        .copy-btn {{ 
            background: #fd7e14; color: white; border: none; 
            padding: 4px 8px; border-radius: 3px; cursor: pointer; margin-left: 8px; 
        }}
        .loading {{ text-align: center; padding: 20px; }}
        .spinner {{ 
            border: 3px solid #f3f3f3; border-top: 3px solid #4CAF50; 
            border-radius: 50%; width: 30px; height: 30px; 
            animation: spin 1s linear infinite; margin: 0 auto; 
        }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>一括リンク生成システム</h1>
        
        <div class="instructions">
            <h3>使い方</h3>
            <ol>
                <li><strong>B列（必須）</strong>: 短縮したい元のURLを入力（http:// または https:// で始めてください）</li>
                <li><strong>C列（任意）</strong>: カスタム短縮コードを入力（空白の場合は自動生成）</li>
                <li><strong>D列（任意）</strong>: カスタム名を入力（管理画面で識別しやすくします）</li>
                <li><strong>E列（任意）</strong>: キャンペーン名を入力（同じキャンペーンのURLをグループ化）</li>
                <li><strong>F列（任意）</strong>: 生成数量を入力（空白の場合は1個生成）</li>
                <li><strong>「🚀 一括生成開始」</strong>ボタンをクリック</li>
            </ol>
        </div>

        <div class="action-buttons">
            <button type="button" class="btn btn-add" onclick="addRows(1)">➕ 1行追加</button>
            <button type="button" class="btn btn-add" onclick="addRows(5)">➕ 5行追加</button>
            <button type="button" class="btn btn-add" onclick="addRows(10)">➕ 10行追加</button>
            <button type="button" class="btn btn-clear" onclick="clearAllData()">🗑️ 全削除</button>
            <button type="button" class="btn btn-generate" onclick="startGeneration()">🚀 一括生成開始</button>
            <button type="button" class="btn btn-admin" onclick="location.href='/admin'">📊 管理画面へ</button>
        </div>

        <div class="spreadsheet-container">
            <table class="spreadsheet-table">
                <thead>
                    <tr>
                        <th style="width: 50px;">A<br>行番号</th>
                        <th style="width: 35%;">B<br>オリジナルURL ※必須</th>
                        <th style="width: 12%;">C<br>カスタム短縮コード<br>(任意)</th>
                        <th style="width: 12%;">D<br>カスタム名<br>(任意)</th>
                        <th style="width: 12%;">E<br>キャンペーン名<br>(任意)</th>
                        <th style="width: 8%;">F<br>生成数量<br>(任意)</th>
                        <th style="width: 11%;">操作</th>
                    </tr>
                </thead>
                <tbody id="dataTable">
                    <tr>
                        <td class="row-number">1</td>
                        <td><input type="url" placeholder="https://example.com" /></td>
                        <td><input type="text" placeholder="例: product01" /></td>
                        <td><input type="text" placeholder="例: 商品A" /></td>
                        <td><input type="text" placeholder="例: 春キャンペーン" /></td>
                        <td><input type="number" min="1" max="20" value="1" /></td>
                        <td><button class="delete-btn" onclick="deleteRow(this)">🗑️ 削除</button></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="action-buttons">
            <button type="button" class="btn btn-add" onclick="addRows(1)">➕ 1行追加</button>
            <button type="button" class="btn btn-add" onclick="addRows(5)">➕ 5行追加</button>
            <button type="button" class="btn btn-add" onclick="addRows(10)">➕ 10行追加</button>
            <button type="button" class="btn btn-clear" onclick="clearAllData()">🗑️ 全削除</button>
            <button type="button" class="btn btn-generate" onclick="startGeneration()">🚀 一括生成開始</button>
        </div>

        <div class="results-section" id="resultsArea">
            <h2>📈 生成結果</h2>
            <div id="resultsContent"></div>
        </div>
    </div>

    <script>
        let rowCount = 1;
        
        // 行追加機能
        function addRows(count) {{
            const table = document.getElementById('dataTable');
            
            for (let i = 0; i < count; i++) {{
                rowCount++;
                const newRow = table.insertRow();
                newRow.innerHTML = `
                    <td class="row-number">${{rowCount}}</td>
                    <td><input type="url" placeholder="https://example.com" /></td>
                    <td><input type="text" placeholder="例: product${{rowCount.toString().padStart(2, '0')}}" /></td>
                    <td><input type="text" placeholder="例: 商品${{String.fromCharCode(65 + (rowCount % 26))}}" /></td>
                    <td><input type="text" placeholder="例: 春キャンペーン" /></td>
                    <td><input type="number" min="1" max="20" value="1" /></td>
                    <td><button class="delete-btn" onclick="deleteRow(this)">🗑️ 削除</button></td>
                `;
            }}
            updateRowNumbers();
        }}
        
        // 行削除機能
        function deleteRow(button) {{
            const table = document.getElementById('dataTable');
            if (table.rows.length > 1) {{
                button.closest('tr').remove();
                updateRowNumbers();
            }} else {{
                alert('最低1行は必要です');
            }}
        }}
        
        // 行番号更新
        function updateRowNumbers() {{
            const table = document.getElementById('dataTable');
            for (let i = 0; i < table.rows.length; i++) {{
                table.rows[i].cells[0].textContent = i + 1;
            }}
            rowCount = table.rows.length;
        }}
        
        // 全削除機能
        function clearAllData() {{
            if (confirm('全てのデータを削除しますか？')) {{
                const table = document.getElementById('dataTable');
                table.innerHTML = `
                    <tr>
                        <td class="row-number">1</td>
                        <td><input type="url" placeholder="https://example.com" /></td>
                        <td><input type="text" placeholder="例: product01" /></td>
                        <td><input type="text" placeholder="例: 商品A" /></td>
                        <td><input type="text" placeholder="例: 春キャンペーン" /></td>
                        <td><input type="number" min="1" max="20" value="1" /></td>
                        <td><button class="delete-btn" onclick="deleteRow(this)">🗑️ 削除</button></td>
                    </tr>
                `;
                rowCount = 1;
                document.getElementById('resultsArea').style.display = 'none';
            }}
        }}
        
        // 一括生成機能
        async function startGeneration() {{
            const table = document.getElementById('dataTable');
            const urlList = [];
            
            // データ収集
            for (let i = 0; i < table.rows.length; i++) {{
                const row = table.rows[i];
                const url = row.cells[1].querySelector('input').value.trim();
                
                if (url) {{
                    if (!url.startsWith('http://') && !url.startsWith('https://')) {{
                        alert(`行 ${{i + 1}}: URLは http:// または https:// で始めてください`);
                        return;
                    }}
                    urlList.push(url);
                }}
            }}
            
            if (urlList.length === 0) {{
                alert('少なくとも1つのURLを入力してください');
                return;
            }}
            
            // 生成処理
            const generateBtns = document.querySelectorAll('.btn-generate');
            generateBtns.forEach(btn => {{
                btn.disabled = true;
                btn.textContent = '⏳ 生成中...';
            }});
            
            const resultsArea = document.getElementById('resultsArea');
            const resultsContent = document.getElementById('resultsContent');
            resultsArea.style.display = 'block';
            resultsContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>リンクを生成しています...</p></div>';
            
            try {{
                const formData = new FormData();
                formData.append('urls', urlList.join('\\n'));
                
                const response = await fetch('/api/bulk-process', {{
                    method: 'POST',
                    body: formData
                }});
                
                if (!response.ok) {{
                    throw new Error(`処理エラー: ${{response.status}}`);
                }}
                
                const result = await response.json();
                showResults(result);
                
            }} catch (error) {{
                resultsContent.innerHTML = `<div class="error-item">エラーが発生しました: ${{error.message}}</div>`;
            }} finally {{
                generateBtns.forEach(btn => {{
                    btn.disabled = false;
                    btn.textContent = '🚀 一括生成開始';
                }});
            }}
        }}
        
        // 結果表示
        function showResults(result) {{
            const resultsContent = document.getElementById('resultsContent');
            let successCount = 0;
            let errorCount = 0;
            
            if (result.results) {{
                result.results.forEach(item => {{
                    if (item.success) successCount++;
                    else errorCount++;
                }});
            }}
            
            let html = `
                <div style="background: #e7f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3>📊 生成結果サマリー</h3>
                    <p>成功: <strong>${{successCount}}</strong> | エラー: <strong>${{errorCount}}</strong> | 合計: <strong>${{successCount + errorCount}}</strong></p>
                </div>
            `;
            
            if (result.results) {{
                result.results.forEach((item, index) => {{
                    if (item.success) {{
                        html += `
                            <div class="result-item">
                                <p><strong>${{index + 1}}. 元URL:</strong> ${{item.url}}</p>
                                <p><strong>短縮URL:</strong> 
                                    <a href="${{item.short_url}}" target="_blank">${{item.short_url}}</a>
                                    <button class="copy-btn" onclick="copyText('${{item.short_url}}')">📋 コピー</button>
                                </p>
                            </div>
                        `;
                    }} else {{
                        html += `<div class="error-item">❌ ${{item.url}} - ${{item.error}}</div>`;
                    }}
                }});
            }}
            
            resultsContent.innerHTML = html;
        }}
        
        // コピー機能
        function copyText(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                alert(`クリップボードにコピーしました: ${{text}}`);
            }}).catch(() => {{
                prompt('以下のURLをコピーしてください:', text);
            }});
        }}
        
        // 初期化
        window.addEventListener('load', function() {{
            console.log('一括生成システム準備完了');
            // 初期表示で4行追加
            addRows(4);
        }});
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
    except:
        html_content = INDEX_HTML.format(
            total_links=0, total_clicks=0, unique_visitors=0,
            system_status="初期化中", base_url=BASE_URL
        )
        return HTMLResponse(content=html_content)

@app.post("/api/shorten-form")
async def shorten_form(url: str = Form(...), custom_name: str = Form(""), campaign_name: str = Form("")):
    try:
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="無効なURLです")
        
        # 短縮コード生成
        short_code = generate_short_code()
        
        # 保存
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO urls (short_code, original_url, custom_name, campaign_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (short_code, clean_url(url), custom_name or None, campaign_name or None, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return JSONResponse({{
            "success": True,
            "short_code": short_code,
            "short_url": f"{BASE_URL}/{short_code}",
            "original_url": url,
            "custom_name": custom_name,
            "campaign_name": campaign_name
        }})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 統計取得
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as total_urls,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_clicks,
                COUNT(CASE WHEN c.source = 'qr' THEN 1 END) as qr_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
        """)
        
        stats = cursor.fetchone()
        total_urls, total_clicks, unique_clicks, qr_clicks = stats if stats else (0, 0, 0, 0)
        
        # URL一覧取得
        cursor.execute("""
            SELECT u.short_code, u.original_url, u.created_at, u.custom_name, u.campaign_name,
                   COUNT(c.id) as click_count,
                   COUNT(DISTINCT c.ip_address) as unique_count
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            ORDER BY u.created_at DESC
            LIMIT 50
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        # テーブル行生成
        table_rows = ""
        for row in results:
            short_code, original_url, created_at, custom_name, campaign_name, click_count, unique_count = row
            
            # URLを50文字に制限
            display_url = original_url[:50] + "..." if len(original_url) > 50 else original_url
            
            table_rows += f"""
            <tr>
                <td><strong>{short_code}</strong></td>
                <td><a href="{original_url}" target="_blank" title="{original_url}">{display_url}</a></td>
                <td>{custom_name or '-'}</td>
                <td>{campaign_name or '-'}</td>
                <td>{created_at}</td>
                <td>{click_count}</td>
                <td>{unique_count}</td>
                <td>
                    <a href="/analytics/{short_code}" target="_blank" class="action-btn analytics-btn">📈 分析</a>
                    <a href="/{short_code}" target="_blank" class="action-btn qr-btn">🔗 テスト</a>
                </td>
            </tr>
            """
        
        html_content = ADMIN_HTML.format(
            total_urls=total_urls,
            total_clicks=total_clicks,
            unique_clicks=unique_clicks,
            qr_clicks=qr_clicks,
            table_rows=table_rows
        )
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
                
                cursor.execute("""
                    INSERT INTO urls (short_code, original_url, created_at)
                    VALUES (?, ?, ?)
                """, (short_code, clean_url(url), datetime.now().isoformat()))
                
                results.append({{
                    "url": url,
                    "short_url": f"{BASE_URL}/{short_code}",
                    "success": True
                }})
            else:
                results.append({{"url": url, "success": False, "error": "無効なURL"}})
        
        conn.commit()
        conn.close()
        
        return JSONResponse({{"results": results}})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/{{short_code}}", response_class=HTMLResponse)
async def analytics_page(short_code: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT original_url, created_at, custom_name FROM urls WHERE short_code = ?", (short_code,))
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
        <head>
            <title>分析 - {short_code}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                h1 {{ color: #333; text-align: center; }}
                .info-box {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 8px; }}
                .stat-number {{ font-size: 2em; color: #007bff; font-weight: bold; }}
                .btn {{ padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📈 分析: {short_code}</h1>
                
                <div style="text-align: center;">
                    <a href="/admin" class="btn">📊 管理画面に戻る</a>
                    <a href="/" class="btn">🏠 ホーム</a>
                </div>
                
                <div class="info-box">
                    <p><strong>短縮URL:</strong> <a href="{BASE_URL}/{short_code}" target="_blank">{BASE_URL}/{short_code}</a></p>
                    <p><strong>元URL:</strong> <a href="{url_data[0]}" target="_blank">{url_data[0]}</a></p>
                    <p><strong>カスタム名:</strong> {url_data[2] or 'なし'}</p>
                    <p><strong>作成日:</strong> {url_data[1]}</p>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{stats[0] if stats else 0}</div>
                        <div>総クリック数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats[1] if stats else 0}</div>
                        <div>ユニーク訪問者</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except Exception as e:
        return HTMLResponse(content=f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

@app.get("/health")
async def health_check():
    return JSONResponse({{"status": "healthy", "timestamp": datetime.now().isoformat()}})

# リダイレクト処理（最後に配置）
@app.get("/{{short_code}}")
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
        source = request.query_params.get("source", "direct")
        
        cursor.execute("""
            INSERT INTO clicks (url_id, ip_address, user_agent, referrer, source, clicked_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (url_id, client_ip, user_agent, referrer, source, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return RedirectResponse(url=original_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="リダイレクトエラー")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
