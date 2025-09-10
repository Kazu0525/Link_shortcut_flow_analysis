from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import os
import sqlite3
from datetime import datetime
import string
import random
import re

# 設定
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
DB_PATH = "url_shortener.db"

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
    
    for _ in range(50):
        code = ''.join(random.choices(chars, k=length))
        cursor.execute("SELECT 1 FROM urls WHERE short_code = ?", (code,))
        if not cursor.fetchone():
            conn.close()
            return code
    
    conn.close()
    raise HTTPException(status_code=500, detail="短縮コード生成に失敗しました")

def validate_url(url):
    pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))

# データベース初期化
init_db()

# FastAPIアプリ
app = FastAPI(
    title="LinkTrack Pro",
    description="URL短縮・分析プラットフォーム",
    version="1.0.0"
)

# ホームページHTML
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkTrack Pro - URL短縮サービス</title>
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

# 管理画面HTML（文書2から最良部分を採用）
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>管理画面 - LinkTrack Pro</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: #f9f9f9; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
        .stat-number { font-size: 2.5em; font-weight: bold; color: #4CAF50; }
        .stat-label { color: #666; margin-top: 10px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
        tr:hover { background: #f5f5f5; }
        .action-btn { 
            padding: 5px 10px; margin: 2px; border: none; border-radius: 3px; 
            cursor: pointer; text-decoration: none; display: inline-block; color: white;
        }
        .analytics-btn { background: #2196F3; }
        .refresh-btn { background: #9C27B0; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 10px 0; }
        .nav-buttons { text-align: center; margin: 20px 0; }
        .nav-buttons a { margin: 0 10px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
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

# 一括生成HTML（文書1の最良UIを採用）
BULK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>一括リンク生成 - LinkTracker Pro</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1800px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 15px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { 
            font-size: 2.5em; 
            margin-bottom: 10px; 
            font-weight: 300; 
        }
        .header p { 
            font-size: 1.2em; 
            opacity: 0.9; 
        }
        .content {
            padding: 40px;
        }
        .instructions { 
            background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
            padding: 25px; 
            border-radius: 10px; 
            margin-bottom: 30px;
            border-left: 5px solid #28a745;
        }
        .action-buttons { 
            text-align: center; 
            margin: 30px 0;
        }
        .btn { 
            padding: 12px 24px; 
            margin: 5px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .btn-primary { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; }
        .btn-secondary { background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); color: white; }
        .btn-warning { background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%); color: white; }
        .btn-danger { background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; }
        
        .spreadsheet-container { 
            margin: 30px 0; 
            border: 3px solid #28a745;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 25px rgba(40, 167, 69, 0.15);
        }
        .spreadsheet-table { 
            width: 100%; 
            border-collapse: collapse; 
            font-size: 14px;
            background: white;
        }
        .spreadsheet-table th { 
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white; 
            padding: 15px 10px;
            text-align: center; 
            font-weight: 600;
            font-size: 13px;
            border-right: 1px solid rgba(255,255,255,0.2);
        }
        .spreadsheet-table td { 
            border: 1px solid #e0e0e0; 
            padding: 8px;
            vertical-align: middle;
        }
        .spreadsheet-table tr:nth-child(even) {
            background: #f8f9fa;
        }
        .spreadsheet-table tr:hover {
            background: #e8f5e9;
        }
        
        .row-number { 
            width: 60px; 
            text-align: center; 
            font-weight: bold;
            background: #f8f9fa !important;
            color: #495057;
        }
        .url-column { width: 45%; }
        .custom-name-column { width: 15%; }
        .campaign-column { width: 15%; }
        .action-column { width: 15%; text-align: center; }
        
        .spreadsheet-table input { 
            width: 100%; 
            border: 2px solid #e9ecef; 
            padding: 8px 10px; 
            border-radius: 6px;
            font-size: 13px;
            transition: all 0.3s ease;
        }
        .spreadsheet-table input:focus { 
            border-color: #28a745; 
            outline: none; 
            box-shadow: 0 0 0 3px rgba(40, 167, 69, 0.1);
        }
        .url-input {
            font-family: monospace;
        }
        .required { 
            border-left: 4px solid #dc3545 !important; 
        }
        
        .delete-row-btn { 
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white; 
            border: none; 
            padding: 6px 12px; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .delete-row-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 3px 10px rgba(220, 53, 69, 0.3);
        }
        
        .results-section { 
            margin: 40px 0;
            border-top: 3px solid #28a745;
            padding-top: 30px;
        }
        .result-item { 
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 10px; 
            border-left: 5px solid #28a745;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }
        .error-item { 
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border-left: 5px solid #dc3545; 
        }
        .copy-btn { 
            background: linear-gradient(135deg, #fd7e14 0%, #e55100 100%);
            color: white; 
            border: none; 
            padding: 6px 12px; 
            border-radius: 5px; 
            cursor: pointer; 
            margin-left: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .copy-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 3px 8px rgba(253, 126, 20, 0.3);
        }
        
        .loading { 
            text-align: center; 
            padding: 30px; 
        }
        .spinner { 
            border: 4px solid #f3f3f3; 
            border-top: 4px solid #28a745; 
            border-radius: 50%; 
            width: 50px; 
            height: 50px; 
            animation: spin 1s linear infinite; 
            margin: 0 auto 20px;
        }
        @keyframes spin { 
            0% { transform: rotate(0deg); } 
            100% { transform: rotate(360deg); } 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 一括リンク生成システム</h1>
            <p>効率的なURL短縮・管理プラットフォーム</p>
        </div>
        
        <div class="content">
            <div class="instructions">
                <h3>📋 操作ガイド</h3>
                <ol>
                    <li><strong>B列（オリジナルURL）</strong>: 短縮したい元のURLを入力してください（http:// または https:// で始めること）</li>
                    <li><strong>C列（カスタム名）</strong>: 管理しやすい名前を入力してください</li>
                    <li><strong>D列（キャンペーン名）</strong>: マーケティングキャンペーンのグループ名を入力</li>
                    <li><strong>「🚀 一括生成開始」</strong>ボタンをクリックして処理を実行</li>
                </ol>
            </div>

            <div class="action-buttons">
                <button class="btn btn-secondary" id="addRowBtn">➕ 1行追加</button>
                <button class="btn btn-secondary" id="add5RowsBtn">➕ 5行追加</button>
                <button class="btn btn-warning" id="clearAllBtn">🗑️ 全クリア</button>
                <button class="btn btn-danger" id="generateBtn">🚀 一括生成開始</button>
                <button class="btn btn-primary" onclick="window.location.href='/admin'">📊 管理画面へ</button>
            </div>

            <div class="spreadsheet-container">
                <table class="spreadsheet-table" id="spreadsheetTable">
                    <thead>
                        <tr>
                            <th class="row-number">A<br>行番号</th>
                            <th class="url-column">B<br>オリジナルURL ※必須</th>
                            <th class="custom-name-column">C<br>カスタム名<br>（任意）</th>
                            <th class="campaign-column">D<br>キャンペーン名<br>（任意）</th>
                            <th class="action-column">操作</th>
                        </tr>
                    </thead>
                    <tbody id="spreadsheetBody">
                        <tr>
                            <td class="row-number">1</td>
                            <td><input type="url" class="required url-input" placeholder="https://example.com" required /></td>
                            <td><input type="text" placeholder="商品A" /></td>
                            <td><input type="text" placeholder="春キャンペーン" /></td>
                            <td><button class="delete-row-btn" onclick="removeRow(this)">🗑️ 削除</button></td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="results-section" id="resultsSection" style="display: none;">
                <h2>📈 生成結果</h2>
                <div id="resultsContent"></div>
            </div>
        </div>
    </div>

    <script>
        let rowCounter = 1;
        
        function addRow() {
            rowCounter++;
            const tbody = document.getElementById('spreadsheetBody');
            const newRow = tbody.insertRow();
            newRow.innerHTML = `
                <td class="row-number">${rowCounter}</td>
                <td><input type="url" class="required url-input" placeholder="https://example${rowCounter}.com" required /></td>
                <td><input type="text" placeholder="商品${String.fromCharCode(64 + rowCounter)}" /></td>
                <td><input type="text" placeholder="キャンペーン${rowCounter}" /></td>
                <td><button class="delete-row-btn" onclick="removeRow(this)">🗑️ 削除</button></td>
            `;
            updateRowNumbers();
        }
        
        function addMultipleRows(count) {
            for (let i = 0; i < count; i++) {
                addRow();
            }
        }
        
        function removeRow(button) {
            const tbody = document.getElementById('spreadsheetBody');
            if (tbody.rows.length > 1) {
                button.closest('tr').remove();
                updateRowNumbers();
            } else {
                alert('最低1行は必要です');
            }
        }
        
        function updateRowNumbers() {
            const rows = document.querySelectorAll('#spreadsheetBody tr');
            rows.forEach((row, index) => {
                row.cells[0].textContent = index + 1;
            });
            rowCounter = rows.length;
        }
        
        function clearAll() {
            if (confirm('全てのデータを削除しますか？')) {
                document.getElementById('spreadsheetBody').innerHTML = `
                    <tr>
                        <td class="row-number">1</td>
                        <td><input type="url" class="required url-input" placeholder="https://example.com" required /></td>
                        <td><input type="text" placeholder="商品A" /></td>
                        <td><input type="text" placeholder="春キャンペーン" /></td>
                        <td><button class="delete-row-btn" onclick="removeRow(this)">🗑️ 削除</button></td>
                    </tr>
                `;
                rowCounter = 1;
                document.getElementById('resultsSection').style.display = 'none';
            }
        }
        
        async function validateAndGenerate() {
            const rows = document.querySelectorAll('#spreadsheetBody tr');
            const data = [];
            let hasError = false;
            
            for (let row of rows) {
                const inputs = row.querySelectorAll('input');
                const originalUrl = inputs[0].value.trim();
                const customName = inputs[1].value.trim();
                const campaignName = inputs[2].value.trim();
                
                if (originalUrl) {
                    if (!originalUrl.startsWith('http://') && !originalUrl.startsWith('https://')) {
                        alert('URLは http:// または https:// で始めてください');
                        inputs[0].focus();
                        hasError = true;
                        break;
                    }
                    
                    data.push({
                        url: originalUrl,
                        custom_name: customName || null,
                        campaign_name: campaignName || null
                    });
                }
            }
            
            if (hasError) return;
            
            if (data.length === 0) {
                alert('少なくとも1つのURLを入力してください');
                return;
            }
            
            generateLinks(data);
        }
        
        async function generateLinks(data) {
            const btn = document.getElementById('generateBtn');
            const resultsSection = document.getElementById('resultsSection');
            const resultsContent = document.getElementById('resultsContent');
            
            btn.disabled = true;
            btn.innerHTML = '⏳ 生成中...';
            
            resultsSection.style.display = 'block';
            resultsContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>リンクを生成しています...</p></div>';
            
            try {
                const formData = new FormData();
                const urlList = data.map(item => item.url).join('\\n');
                formData.append('urls', urlList);
                
                const response = await fetch('/api/bulk-process', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.json();
                displayResults(result);
                
            } catch (error) {
                resultsContent.innerHTML = `<div class="error-item">エラー: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🚀 一括生成開始';
            }
        }
        
        function displayResults(result) {
            const resultsContent = document.getElementById('resultsContent');
            
            let successCount = 0;
            let errorCount = 0;
            
            if (result.results) {
                result.results.forEach(item => {
                    if (item.success) successCount++;
                    else errorCount++;
                });
            }
            
            let html = `
                <div style="background: linear-gradient(135deg, #e3f2fd 0%, #e8eaf6 100%); padding: 20px; border-radius: 10px; margin-bottom: 25px; border-left: 5px solid #1976d2;">
                    <h3>📊 生成サマリー</h3>
                    <p style="font-size: 1.1em; margin-top: 10px;">成功: <strong style="color: #28a745;">${successCount}</strong> | エラー: <strong style="color: #dc3545;">${errorCount}</strong> | 総生成数: <strong>${successCount + errorCount}</strong></p>
                </div>
            `;
            
            if (result.results && result.results.length > 0) {
                html += '<h3 style="color: #28a745; margin-bottom: 20px;">✅ 生成成功</h3>';
                result.results.forEach((item, index) => {
                    if (item.success) {
                        html += `
                            <div class="result-item">
                                <p><strong>${index + 1}. 元URL:</strong> <a href="${item.url}" target="_blank">${item.url}</a></p>
                                <p><strong>短縮URL:</strong> 
                                    <a href="${item.short_url}" target="_blank" style="color: #1976d2; font-weight: bold;">${item.short_url}</a>
                                    <button class="copy-btn" onclick="copyToClipboard('${item.short_url}')">📋 コピー</button>
                                </p>
                            </div>
                        `;
                    }
                });
                
                const errors = result.results.filter(item => !item.success);
                if (errors.length > 0) {
                    html += '<h3 style="color: #dc3545; margin: 30px 0 20px;">❌ エラー</h3>';
                    errors.forEach(item => {
                        html += `<div class="error-item"><strong>URL:</strong> ${item.url}<br><strong>エラー:</strong> ${item.error}</div>`;
                    });
                }
            }
            
            resultsContent.innerHTML = html;
        }
        
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('クリップボードにコピーしました: ' + text);
            });
        }
        
        // Event Listeners
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('addRowBtn').addEventListener('click', addRow);
            document.getElementById('add5RowsBtn').addEventListener('click', () => addMultipleRows(5));
            document.getElementById('clearAllBtn').addEventListener('click', clearAll);
            document.getElementById('generateBtn').addEventListener('click', validateAndGenerate);
            
            // 初期化で追加行を作成
            addMultipleRows(4);
        });
    </script>
</body>
</html>
"""

# ルートエンドポイント
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
            unique_visitors=unique_visitors
        )
        return HTMLResponse(content=html_content)
    except:
        html_content = INDEX_HTML.format(
            total_links=0, total_clicks=0, unique_visitors=0
        )
        return HTMLResponse(content=html_content)

@app.post("/api/shorten-form")
async def shorten_form(url: str = Form(...), custom_name: str = Form(""), campaign_name: str = Form("")):
    try:
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="無効なURLです")
        
        short_code = generate_short_code()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO urls (short_code, original_url, custom_name, campaign_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (short_code, url.strip(), custom_name or None, campaign_name or None, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "short_code": short_code,
            "short_url": f"{BASE_URL}/{short_code}",
            "original_url": url,
            "custom_name": custom_name,
            "campaign_name": campaign_name
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as total_urls,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
        """)
        
        stats = cursor.fetchone()
        total_urls, total_clicks, unique_clicks = stats if stats else (0, 0, 0)
        
        cursor.execute("""
            SELECT u.short_code, u.original_url, u.created_at, u.custom_name, u.campaign_name,
                   COUNT(c.id) as click_count
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            ORDER BY u.created_at DESC
            LIMIT 50
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        table_rows = ""
        for row in results:
            short_code, original_url, created_at, custom_name, campaign_name, click_count = row
            
            display_url = original_url[:50] + "..." if len(original_url) > 50 else original_url
            
            table_rows += f"""
            <tr>
                <td><strong>{short_code}</strong></td>
                <td><a href="{original_url}" target="_blank" title="{original_url}">{display_url}</a></td>
                <td>{custom_name or '-'}</td>
                <td>{campaign_name or '-'}</td>
                <td>{created_at}</td>
                <td>{click_count}</td>
                <td>
                    <a href="/analytics/{short_code}" target="_blank" class="action-btn analytics-btn">📈 分析</a>
                </td>
            </tr>
            """
        
        html_content = ADMIN_HTML.format(
            total_urls=total_urls,
            total_clicks=total_clicks,
            unique_clicks=unique_clicks,
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
                """, (short_code, url, datetime.now().isoformat()))
                
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
    return JSONResponse({"status": "healthy", "timestamp": datetime.now().isoformat()})

# リダイレクト処理
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
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
