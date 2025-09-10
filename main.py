from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
import os
import sqlite3
from datetime import datetime, timedelta
import string
import random
import re
import json
import csv
import io
from urllib.parse import urlparse, parse_qs
import base64

# 条件付きインポート - エラー回避
try:
    import qrcode
    from io import BytesIO
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    import user_agents
    UA_AVAILABLE = True
except ImportError:
    UA_AVAILABLE = False

# 設定
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
DB_PATH = "url_shortener.db"

# データベース初期化（拡張版）
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # URLsテーブル（QRコード対応）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            custom_name TEXT,
            campaign_name TEXT,
            qr_code_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # Clicksテーブル（詳細分析対応）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            referrer TEXT,
            source TEXT DEFAULT 'direct',
            device_type TEXT,
            browser TEXT,
            os TEXT,
            country TEXT,
            city TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_term TEXT,
            utm_content TEXT,
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

def generate_qr_code(url):
    """QRコード生成（Base64エンコード）"""
    if not QR_AVAILABLE:
        return None
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    except:
        return None

def analyze_user_agent(user_agent_string):
    """User-Agent解析"""
    if not UA_AVAILABLE or not user_agent_string:
        return {
            'device_type': 'Unknown',
            'browser': 'Unknown',
            'os': 'Unknown'
        }
    
    try:
        ua = user_agents.parse(user_agent_string)
        return {
            'device_type': 'Mobile' if ua.is_mobile else 'Desktop' if ua.is_pc else 'Tablet' if ua.is_tablet else 'Unknown',
            'browser': ua.browser.family,
            'os': ua.os.family
        }
    except:
        return {
            'device_type': 'Unknown',
            'browser': 'Unknown',
            'os': 'Unknown'
        }

def extract_utm_params(referrer):
    """UTMパラメータ抽出"""
    if not referrer:
        return {}
    
    try:
        parsed = urlparse(referrer)
        params = parse_qs(parsed.query)
        return {
            'utm_source': params.get('utm_source', [''])[0],
            'utm_medium': params.get('utm_medium', [''])[0],
            'utm_campaign': params.get('utm_campaign', [''])[0],
            'utm_term': params.get('utm_term', [''])[0],
            'utm_content': params.get('utm_content', [''])[0]
        }
    except:
        return {}

def get_location_from_ip(ip_address):
    """IP から地域推定（簡易版）"""
    if ip_address.startswith('127.') or ip_address.startswith('192.168.'):
        return {'country': 'Local', 'city': 'Local'}
    elif ip_address.startswith('35.') or ip_address.startswith('34.'):
        return {'country': 'US', 'city': 'Unknown'}
    else:
        return {'country': 'Unknown', 'city': 'Unknown'}

# データベース初期化
init_db()

# FastAPIアプリ
app = FastAPI(
    title="LinkTrack Pro Advanced",
    description="QRコード・詳細分析対応URL短縮プラットフォーム",
    version="2.0.0"
)

# ホームページHTML（QRコード対応）
def get_index_html(total_links, total_clicks, unique_visitors, qr_clicks):
    qr_section = ""
    if QR_AVAILABLE:
        qr_section = f"""
                    <div class="qr-section">
                        <h4>📱 QRコード</h4>
                        <img src="data:image/png;base64,${{data.qr_code}}" class="qr-code" alt="QRコード" />
                        <br>
                        <button class="copy-button" onclick="downloadQR('${{data.qr_code}}', '${{data.short_code}}')">💾 QR画像をダウンロード</button>
                    </div>
        """
    
    return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkTrack Pro Advanced - QRコード対応URL短縮サービス</title>
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
        .qr-section {{
            text-align: center; margin: 20px 0; padding: 20px;
            background: #f8f9fa; border-radius: 10px;
        }}
        .qr-code {{ max-width: 200px; margin: 10px auto; }}
        .footer {{ text-align: center; color: white; margin-top: 30px; opacity: 0.8; }}
        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔗 LinkTrack Pro Advanced</h1>
            <p>QRコード対応・詳細分析機能付きURL短縮プラットフォーム</p>
        </div>
        
        <div class="navigation">
            <a href="/" class="nav-link">🏠 ホーム</a>
            <a href="/admin" class="nav-link">📊 管理ダッシュボード</a>
            <a href="/bulk" class="nav-link">📦 一括生成</a>
            <a href="/export" class="nav-link">📁 データエクスポート</a>
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
                    <div class="stat-number">{qr_clicks}</div>
                    <div class="stat-label">QR経由アクセス</div>
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
                    <button type="submit" class="btn">🔗 短縮URL・QRコードを生成</button>
                    <button type="button" class="btn btn-secondary" onclick="clearForm()">🗑️ クリア</button>
                </form>
            </div>
            
            <div id="resultSection" class="result-section">
                <div id="resultContent"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2025 LinkTrack Pro Advanced - QRコード・詳細分析対応</p>
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
                let qrSection = '';
                if (data.qr_code) {{
                    qrSection = `{qr_section}`;
                }}
                
                content.innerHTML = `
                    <h3>✅ 短縮URL・QRコード生成完了</h3>
                    <div style="margin: 15px 0;">
                        <strong>短縮URL:</strong> 
                        <span id="shortUrl">${{data.short_url}}</span>
                        <button class="copy-button" onclick="copyToClipboard('${{data.short_url}}')">📋 コピー</button>
                    </div>
                    <div style="margin: 15px 0;">
                        <strong>元のURL:</strong> ${{data.original_url}}
                    </div>
                    ${{data.custom_name ? '<div><strong>カスタム名:</strong> ' + data.custom_name + '</div>' : ''}}
                    ${{data.campaign_name ? '<div><strong>キャンペーン:</strong> ' + data.campaign_name + '</div>' : ''}}
                    ${{qrSection}}
                    <div style="margin-top: 20px;">
                        <a href="/analytics/${{data.short_code}}" class="btn">📈 詳細分析ページ</a>
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
        
        function downloadQR(base64Data, shortCode) {{
            const link = document.createElement('a');
            link.download = `qr_${{shortCode}}.png`;
            link.href = `data:image/png;base64,${{base64Data}}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}
        
        function clearForm() {{
            document.getElementById('shortenForm').reset();
            document.getElementById('resultSection').style.display = 'none';
        }}
    </script>
</body>
</html>
"""

# 簡易管理画面HTML（エラー回避版）
def get_admin_html(stats, table_rows):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>管理ダッシュボード - LinkTrack Pro Advanced</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background: #f9f9f9; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #4CAF50; }}
        .stat-label {{ color: #666; margin-top: 5px; font-weight: bold; font-size: 0.9em; }}
        .export-section {{ 
            background: linear-gradient(135deg, #e3f2fd 0%, #e8eaf6 100%); 
            padding: 20px; border-radius: 10px; margin: 20px 0; 
            border-left: 5px solid #2196F3;
        }}
        .export-buttons {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 15px; }}
        .export-btn {{ 
            padding: 10px 15px; background: #2196F3; color: white; text-decoration: none; 
            border-radius: 5px; text-align: center; font-weight: 600; transition: all 0.3s;
        }}
        .export-btn:hover {{ background: #1976D2; transform: translateY(-2px); }}
        .export-btn.basic {{ background: #4CAF50; }}
        .export-btn.basic:hover {{ background: #388E3C; }}
        .export-btn.detailed {{ background: #FF9800; }}
        .export-btn.detailed:hover {{ background: #F57C00; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; font-size: 14px; }}
        th {{ background: #4CAF50; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .action-btn {{ 
            padding: 4px 8px; margin: 1px; border: none; border-radius: 3px; 
            cursor: pointer; text-decoration: none; display: inline-block; color: white; font-size: 12px;
        }}
        .analytics-btn {{ background: #2196F3; }}
        .qr-btn {{ background: #FF9800; }}
        .nav-buttons {{ text-align: center; margin: 20px 0; }}
        .nav-buttons a {{ margin: 0 5px; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; font-size: 14px; }}
        .url-cell {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .qr-instructions {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ffc107; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 管理ダッシュボード - LinkTrack Pro Advanced</h1>
        
        <div class="nav-buttons">
            <a href="/">🏠 ホーム</a>
            <a href="/bulk">📦 一括生成</a>
            <a href="/docs">📚 API文書</a>
            <button onclick="location.reload()" style="background: #9C27B0; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">🔄 データ更新</button>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{stats['total_urls']}</div>
                <div class="stat-label">総URL数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['total_clicks']}</div>
                <div class="stat-label">総クリック数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['unique_visitors']}</div>
                <div class="stat-label">ユニーク訪問者</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['qr_clicks']}</div>
                <div class="stat-label">QR経由アクセス</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['mobile_clicks']}</div>
                <div class="stat-label">モバイルアクセス</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['today_clicks']}</div>
                <div class="stat-label">本日のクリック</div>
            </div>
        </div>

        <div class="qr-instructions">
            <h3>📱 QRコード生成方法</h3>
            <p><strong>自動生成:</strong> URL短縮時に自動でQRコード生成されます</p>
            <p><strong>表示方法:</strong> 下記テーブルの「📱 QR」ボタンをクリック</p>
            <p><strong>ダウンロード:</strong> QRコード表示ページでダウンロード可能</p>
        </div>

        <div class="export-section">
            <h3>📁 データエクスポート機能</h3>
            <p>各種分析データをCSV形式でダウンロードできます。</p>
            <div class="export-buttons">
                <a href="/export" class="export-btn basic">📊 基本統計データ</a>
                <a href="/export/detailed" class="export-btn detailed">🔍 詳細分析データ</a>
                <a href="/export/hourly" class="export-btn">⏰ 時間帯別データ</a>
                <a href="/export/devices" class="export-btn">📱 デバイス別データ</a>
                <a href="/export/utm" class="export-btn">🎯 UTMパラメータ</a>
            </div>
        </div>

        <h2>📋 URL一覧・詳細管理</h2>
        <table>
            <thead>
                <tr>
                    <th>短縮コード</th>
                    <th>元URL</th>
                    <th>カスタム名</th>
                    <th>キャンペーン</th>
                    <th>作成日</th>
                    <th>総クリック</th>
                    <th>ユニーク</th>
                    <th>QR</th>
                    <th>モバイル</th>
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

# 詳細分析ページHTML
def get_analytics_html(short_code, url_data, analytics_data):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>詳細分析 - {short_code}</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #333; text-align: center; border-bottom: 3px solid #2196F3; padding-bottom: 15px; }}
        .info-box {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; text-align: center; border-radius: 8px; border-left: 4px solid #2196F3; }}
        .stat-number {{ font-size: 1.8em; color: #2196F3; font-weight: bold; }}
        .chart-section {{ margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; }}
        .btn {{ padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; display: inline-block; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #2196F3; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 詳細分析: {short_code}</h1>
        
        <div style="text-align: center; margin: 20px 0;">
            <a href="/admin" class="btn">📊 管理画面に戻る</a>
            <a href="/" class="btn">🏠 ホーム</a>
            <a href="/qr/{short_code}" class="btn" style="background: #FF9800;">📱 QRコード表示</a>
        </div>
        
        <div class="info-box">
            <p><strong>短縮URL:</strong> <a href="{BASE_URL}/{short_code}" target="_blank">{BASE_URL}/{short_code}</a></p>
            <p><strong>元URL:</strong> <a href="{url_data['original_url']}" target="_blank">{url_data['original_url']}</a></p>
            <p><strong>カスタム名:</strong> {url_data['custom_name'] or 'なし'}</p>
            <p><strong>キャンペーン:</strong> {url_data['campaign_name'] or 'なし'}</p>
            <p><strong>作成日:</strong> {url_data['created_at']}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{analytics_data['total_clicks']}</div>
                <div>総クリック数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{analytics_data['unique_visitors']}</div>
                <div>ユニーク訪問者</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{analytics_data['qr_clicks']}</div>
                <div>QR経由アクセス</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{analytics_data['mobile_percentage']}%</div>
                <div>モバイル率</div>
            </div>
        </div>

        <div class="chart-section">
            <h3>📱 デバイス別アクセス</h3>
            <table>
                <tr><th>デバイス</th><th>クリック数</th><th>割合</th></tr>
                {analytics_data['device_breakdown']}
            </table>
        </div>

        <div class="chart-section">
            <h3>🌐 ブラウザ別アクセス</h3>
            <table>
                <tr><th>ブラウザ</th><th>クリック数</th><th>割合</th></tr>
                {analytics_data['browser_breakdown']}
            </table>
        </div>

        <div class="chart-section">
            <h3>🔗 参照元分析</h3>
            <table>
                <tr><th>参照元</th><th>クリック数</th></tr>
                {analytics_data['referrer_breakdown']}
            </table>
        </div>
    </div>
</body>
</html>
"""

# 一括生成HTML（生成数機能復活版）
def get_bulk_html():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>一括リンク生成 - LinkTracker Pro Advanced</title>
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
        }
        .btn-primary { background: #28a745; color: white; }
        .btn-secondary { background: #17a2b8; color: white; }
        .btn-warning { background: #ffc107; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        
        .spreadsheet-container { 
            margin: 30px 0; 
            border: 3px solid #28a745;
            border-radius: 12px;
            overflow: hidden;
        }
        .spreadsheet-table { 
            width: 100%; 
            border-collapse: collapse; 
            font-size: 14px;
            background: white;
        }
        .spreadsheet-table th { 
            background: #28a745;
            color: white; 
            padding: 15px 10px;
            text-align: center; 
            font-weight: 600;
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
        .spreadsheet-table input { 
            width: 100%; 
            border: 2px solid #e9ecef; 
            padding: 8px 10px; 
            border-radius: 6px;
            font-size: 13px;
        }
        .spreadsheet-table input:focus { 
            border-color: #28a745; 
            outline: none; 
        }
        .quantity-input {
            text-align: center;
            font-weight: 600;
        }
        .delete-row-btn { 
            background: #dc3545;
            color: white; 
            border: none; 
            padding: 6px 12px; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 12px;
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
        }
        .error-item { 
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border-left: 5px solid #dc3545; 
        }
        .copy-btn { 
            background: #fd7e14;
            color: white; 
            border: none; 
            padding: 6px 12px; 
            border-radius: 5px; 
            cursor: pointer; 
            margin-left: 10px;
            font-weight: 600;
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
            <p>QRコード対応・効率的なURL短縮プラットフォーム</p>
        </div>
        
        <div class="content">
            <div class="instructions">
                <h3>📋 操作ガイド</h3>
                <ol>
                    <li><strong>B列（オリジナルURL）</strong>: 短縮したい元のURLを入力してください（http:// または https:// で始めること）</li>
                    <li><strong>C列（カスタム名）</strong>: 管理しやすい名前を入力してください</li>
                    <li><strong>D列（キャンペーン名）</strong>: マーケティングキャンペーンのグループ名を入力</li>
                    <li><strong>E列（生成数）</strong>: 同じURLから何個の短縮リンクを作るかを入力（1〜10個）</li>
                    <li><strong>「🚀 一括生成開始」</strong>ボタンをクリックして処理を実行</li>
                </ol>
                <div style="margin-top: 15px; padding: 10px; background: #fff3cd; border-radius: 5px;">
                    <strong>💡 生成数の使い方:</strong> 例えば「商品A」で生成数3を設定すると、「商品A_1」「商品A_2」「商品A_3」として3つの短縮リンクが生成されます。
                </div>
            </div>

            <div class="action-buttons">
                <button class="btn btn-secondary" onclick="addRow()">➕ 1行追加</button>
                <button class="btn btn-secondary" onclick="addRows(5)">➕ 5行追加</button>
                <button class="btn btn-warning" onclick="clearAll()">🗑️ 全クリア</button>
                <button class="btn btn-danger" onclick="generateLinks()">🚀 一括生成開始</button>
                <button class="btn btn-primary" onclick="window.location.href='/admin'">📊 管理画面へ</button>
            </div>

            <div class="spreadsheet-container">
                <table class="spreadsheet-table" id="spreadsheetTable">
                    <thead>
                        <tr>
                            <th style="width: 50px;">A<br>行番号</th>
                            <th style="width: 35%;">B<br>オリジナルURL ※必須</th>
                            <th style="width: 15%;">C<br>カスタム名<br>（任意）</th>
                            <th style="width: 15%;">D<br>キャンペーン名<br>（任意）</th>
                            <th style="width: 10%;">E<br>生成数<br>（1〜10）</th>
                            <th style="width: 15%;">操作</th>
                        </tr>
                    </thead>
                    <tbody id="spreadsheetBody">
                        <tr>
                            <td>1</td>
                            <td><input type="url" placeholder="https://example.com" required /></td>
                            <td><input type="text" placeholder="商品A" /></td>
                            <td><input type="text" placeholder="春キャンペーン" /></td>
                            <td><input type="number" class="quantity-input" min="1" max="10" value="1" /></td>
                            <td><button class="delete-row-btn" onclick="deleteRow(this)">🗑️ 削除</button></td>
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
        let rowCount = 1;
        
        function addRow() {
            rowCount++;
            const tbody = document.getElementById('spreadsheetBody');
            const newRow = tbody.insertRow();
            newRow.innerHTML = `
                <td>${rowCount}</td>
                <td><input type="url" placeholder="https://example${rowCount}.com" required /></td>
                <td><input type="text" placeholder="商品${String.fromCharCode(64 + rowCount)}" /></td>
                <td><input type="text" placeholder="キャンペーン${rowCount}" /></td>
                <td><input type="number" class="quantity-input" min="1" max="10" value="1" /></td>
                <td><button class="delete-row-btn" onclick="deleteRow(this)">🗑️ 削除</button></td>
            `;
        }
        
        function addRows(count) {
            for (let i = 0; i < count; i++) {
                addRow();
            }
        }
        
        function deleteRow(button) {
            const tbody = document.getElementById('spreadsheetBody');
            if (tbody.rows.length > 1) {
                button.closest('tr').remove();
                updateRowNumbers();
            }
        }
        
        function updateRowNumbers() {
            const rows = document.querySelectorAll('#spreadsheetBody tr');
            rows.forEach((row, index) => {
                row.cells[0].textContent = index + 1;
            });
            rowCount = rows.length;
        }
        
        function clearAll() {
            if (confirm('全てのデータを削除しますか？')) {
                const tbody = document.getElementById('spreadsheetBody');
                tbody.innerHTML = `
                    <tr>
                        <td>1</td>
                        <td><input type="url" placeholder="https://example.com" required /></td>
                        <td><input type="text" placeholder="商品A" /></td>
                        <td><input type="text" placeholder="春キャンペーン" /></td>
                        <td><input type="number" class="quantity-input" min="1" max="10" value="1" /></td>
                        <td><button class="delete-row-btn" onclick="deleteRow(this)">🗑️ 削除</button></td>
                    </tr>
                `;
                rowCount = 1;
                document.getElementById('resultsSection').style.display = 'none';
            }
        }
        
        async function generateLinks() {
            const rows = document.querySelectorAll('#spreadsheetBody tr');
            const expandedData = [];
            let hasError = false;
            let totalToGenerate = 0;
            
            for (let row of rows) {
                const inputs = row.querySelectorAll('input');
                const originalUrl = inputs[0].value.trim();
                const customName = inputs[1].value.trim();
                const campaignName = inputs[2].value.trim();
                const quantity = parseInt(inputs[3].value) || 1;
                
                if (originalUrl) {
                    if (!originalUrl.startsWith('http://') && !originalUrl.startsWith('https://')) {
                        alert('URLは http:// または https:// で始めてください');
                        inputs[0].focus();
                        hasError = true;
                        break;
                    }
                    
                    if (quantity < 1 || quantity > 10) {
                        alert('生成数は1〜10の範囲で入力してください');
                        inputs[3].focus();
                        hasError = true;
                        break;
                    }
                    
                    totalToGenerate += quantity;
                    
                    // 指定された数量分だけURLを複製
                    for (let i = 1; i <= quantity; i++) {
                        let finalCustomName = customName;
                        if (quantity > 1 && customName) {
                            finalCustomName = `${customName}_${i}`;
                        }
                        
                        expandedData.push({
                            url: originalUrl,
                            custom_name: finalCustomName || null,
                            campaign_name: campaignName || null,
                            originalCustomName: customName,
                            index: i,
                            total: quantity
                        });
                    }
                }
            }
            
            if (hasError) return;
            
            if (expandedData.length === 0) {
                alert('少なくとも1つのURLを入力してください');
                return;
            }
            
            if (totalToGenerate > 50) {
                if (!confirm(`合計${totalToGenerate}個の短縮リンク・QRコードを生成します。よろしいですか？`)) {
                    return;
                }
            }
            
            const resultsSection = document.getElementById('resultsSection');
            const resultsContent = document.getElementById('resultsContent');
            
            resultsSection.style.display = 'block';
            resultsContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>短縮リンク・QRコードを生成しています...</p></div>';
            
            try {
                const formData = new FormData();
                const urlList = expandedData.map(item => item.url).join('\\n');
                formData.append('urls', urlList);
                
                const response = await fetch('/api/bulk-process', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.json();
                
                // 結果にカスタム名情報を追加
                if (result.results) {
                    result.results.forEach((item, index) => {
                        if (expandedData[index]) {
                            item.customName = expandedData[index].originalCustomName;
                            item.index = expandedData[index].index;
                            item.total = expandedData[index].total;
                        }
                    });
                }
                
                displayResults(result);
                
            } catch (error) {
                resultsContent.innerHTML = `<div class="error-item">エラー: ${error.message}</div>`;
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
                    <p style="color: #666; margin-top: 5px;">※各短縮URLにQRコードも生成されています。管理画面で確認できます。</p>
                </div>
            `;
            
            if (result.results && result.results.length > 0) {
                html += '<h3 style="color: #28a745; margin-bottom: 20px;">✅ 生成成功</h3>';
                
                // グループ化して表示
                let currentGroup = null;
                let groupIndex = 1;
                
                result.results.forEach((item, index) => {
                    if (item.success) {
                        const displayName = item.customName || `URL${groupIndex}`;
                        const isNewGroup = currentGroup !== item.url;
                        
                        if (isNewGroup) {
                            currentGroup = item.url;
                            if (index > 0) html += '<hr style="margin: 20px 0; border: 1px solid #e0e0e0;">';
                        }
                        
                        const title = item.total > 1 ? `${displayName} (${item.index}/${item.total})` : displayName;
                        
                        html += `
                            <div class="result-item">
                                <p><strong>${title}</strong></p>
                                <p><strong>元URL:</strong> <a href="${item.url}" target="_blank">${item.url}</a></p>
                                <p><strong>短縮URL:</strong> 
                                    <a href="${item.short_url}" target="_blank" style="color: #1976d2; font-weight: bold;">${item.short_url}</a>
                                    <button class="copy-btn" onclick="copyToClipboard('${item.short_url}')">📋 コピー</button>
                                    <button class="copy-btn" onclick="window.open('/qr/${item.short_url.split('/').pop()}', '_blank')" style="background: #FF9800;">📱 QR表示</button>
                                </p>
                            </div>
                        `;
                        
                        if (isNewGroup) groupIndex++;
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
        
        // 初期化
        addRows(4);
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
        
        cursor.execute("SELECT COUNT(*) FROM clicks WHERE source = 'qr'")
        qr_clicks = cursor.fetchone()[0]
        
        conn.close()
        
        return HTMLResponse(content=get_index_html(total_links, total_clicks, unique_visitors, qr_clicks))
    except:
        return HTMLResponse(content=get_index_html(0, 0, 0, 0))

@app.post("/api/shorten-form")
async def shorten_form(url: str = Form(...), custom_name: str = Form(""), campaign_name: str = Form("")):
    try:
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="無効なURLです")
        
        short_code = generate_short_code()
        short_url = f"{BASE_URL}/{short_code}"
        
        # QRコード生成（エラー回避）
        qr_code_data = generate_qr_code(short_url) if QR_AVAILABLE else None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO urls (short_code, original_url, custom_name, campaign_name, qr_code_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (short_code, url.strip(), custom_name or None, campaign_name or None, qr_code_data, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        result = {
            "success": True,
            "short_code": short_code,
            "short_url": short_url,
            "original_url": url,
            "custom_name": custom_name,
            "campaign_name": campaign_name
        }
        
        if qr_code_data:
            result["qr_code"] = qr_code_data
        
        return JSONResponse(result)
        
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
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                COUNT(CASE WHEN c.source = 'qr' THEN 1 END) as qr_clicks,
                COUNT(CASE WHEN c.device_type = 'Mobile' THEN 1 END) as mobile_clicks,
                COUNT(CASE WHEN DATE(c.clicked_at) = DATE('now') THEN 1 END) as today_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
        """)
        
        stats_row = cursor.fetchone()
        stats = {
            'total_urls': stats_row[0] if stats_row else 0,
            'total_clicks': stats_row[1] if stats_row else 0,
            'unique_visitors': stats_row[2] if stats_row else 0,
            'qr_clicks': stats_row[3] if stats_row else 0,
            'mobile_clicks': stats_row[4] if stats_row else 0,
            'today_clicks': stats_row[5] if stats_row else 0
        }
        
        # URL一覧取得
        cursor.execute("""
            SELECT u.short_code, u.original_url, u.created_at, u.custom_name, u.campaign_name,
                   COUNT(c.id) as total_clicks,
                   COUNT(DISTINCT c.ip_address) as unique_clicks,
                   COUNT(CASE WHEN c.source = 'qr' THEN 1 END) as qr_clicks,
                   COUNT(CASE WHEN c.device_type = 'Mobile' THEN 1 END) as mobile_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            ORDER BY u.created_at DESC
            LIMIT 100
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        # テーブル行生成
        table_rows = ""
        for row in results:
            short_code, original_url, created_at, custom_name, campaign_name, total_clicks, unique_clicks, qr_clicks, mobile_clicks = row
            
            display_url = original_url[:40] + "..." if len(original_url) > 40 else original_url
            
            table_rows += f"""
            <tr>
                <td><strong>{short_code}</strong></td>
                <td class="url-cell"><a href="{original_url}" target="_blank" title="{original_url}">{display_url}</a></td>
                <td>{custom_name or '-'}</td>
                <td>{campaign_name or '-'}</td>
                <td>{created_at[:10]}</td>
                <td>{total_clicks}</td>
                <td>{unique_clicks}</td>
                <td>{qr_clicks}</td>
                <td>{mobile_clicks}</td>
                <td>
                    <a href="/analytics/{short_code}" target="_blank" class="action-btn analytics-btn">📈 分析</a>
                    <a href="/qr/{short_code}" target="_blank" class="action-btn qr-btn">📱 QR</a>
                </td>
            </tr>
            """
        
        return HTMLResponse(content=get_admin_html(stats, table_rows))
        
    except Exception as e:
        return HTMLResponse(content=f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

@app.get("/bulk", response_class=HTMLResponse)
async def bulk_page():
    return HTMLResponse(content=get_bulk_html())

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
                short_url = f"{BASE_URL}/{short_code}"
                
                # QRコード生成（エラー回避）
                qr_code_data = generate_qr_code(short_url) if QR_AVAILABLE else None
                
                cursor.execute("""
                    INSERT INTO urls (short_code, original_url, qr_code_data, created_at)
                    VALUES (?, ?, ?, ?)
                """, (short_code, url, qr_code_data, datetime.now().isoformat()))
                
                results.append({
                    "url": url,
                    "short_url": short_url,
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
        
        # URL基本情報
        cursor.execute("SELECT original_url, created_at, custom_name, campaign_name FROM urls WHERE short_code = ?", (short_code,))
        url_data = cursor.fetchone()
        
        if not url_data:
            return HTMLResponse(content="<h1>404</h1><p>URLが見つかりません</p>", status_code=404)
        
        url_info = {
            'original_url': url_data[0],
            'created_at': url_data[1],
            'custom_name': url_data[2],
            'campaign_name': url_data[3]
        }
        
        # 統計取得
        cursor.execute("""
            SELECT 
                COUNT(*) as total_clicks,
                COUNT(DISTINCT ip_address) as unique_visitors,
                COUNT(CASE WHEN source = 'qr' THEN 1 END) as qr_clicks,
                COUNT(CASE WHEN device_type = 'Mobile' THEN 1 END) as mobile_clicks
            FROM clicks c
            JOIN urls u ON c.url_id = u.id
            WHERE u.short_code = ?
        """, (short_code,))
        
        stats = cursor.fetchone()
        total_clicks = stats[0] if stats else 0
        mobile_percentage = round((stats[3] / max(stats[0], 1)) * 100) if stats else 0
        
        analytics_data = {
            'total_clicks': stats[0] if stats else 0,
            'unique_visitors': stats[1] if stats else 0,
            'qr_clicks': stats[2] if stats else 0,
            'mobile_percentage': mobile_percentage,
            'device_breakdown': '<tr><td>データなし</td><td>0</td><td>0%</td></tr>',
            'browser_breakdown': '<tr><td>データなし</td><td>0</td><td>0%</td></tr>',
            'referrer_breakdown': '<tr><td>データなし</td><td>0</td></tr>'
        }
        
        conn.close()
        
        return HTMLResponse(content=get_analytics_html(short_code, url_info, analytics_data))
        
    except Exception as e:
        return HTMLResponse(content=f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

@app.get("/qr/{short_code}")
async def qr_code_page(short_code: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT qr_code_data, original_url FROM urls WHERE short_code = ?", (short_code,))
        result = cursor.fetchone()
        
        if not result:
            return HTMLResponse(content="<h1>404</h1><p>URLが見つかりません</p>", status_code=404)
        
        qr_code_data = result[0]
        
        if not qr_code_data and QR_AVAILABLE:
            # QRコードが存在しない場合は生成
            short_url = f"{BASE_URL}/{short_code}"
            qr_code_data = generate_qr_code(short_url)
            
            if qr_code_data:
                cursor.execute("UPDATE urls SET qr_code_data = ? WHERE short_code = ?", (qr_code_data, short_code))
                conn.commit()
        
        conn.close()
        
        if not qr_code_data:
            return HTMLResponse(content="<h1>QRコード生成不可</h1><p>QRコードライブラリが利用できません</p>", status_code=500)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>QRコード - {short_code}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 40px; background: #f5f5f5; }}
                .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; margin-bottom: 30px; }}
                .qr-code {{ max-width: 300px; margin: 20px auto; border: 10px solid white; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
                .info {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .btn {{ padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 8px; margin: 10px; display: inline-block; }}
                .btn-download {{ background: #28a745; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📱 QRコード</h1>
                <div class="info">
                    <p><strong>短縮URL:</strong> {BASE_URL}/{short_code}</p>
                </div>
                <img src="data:image/png;base64,{qr_code_data}" class="qr-code" alt="QRコード" />
                <div>
                    <a href="/admin" class="btn">📊 管理画面に戻る</a>
                    <a href="/analytics/{short_code}" class="btn">📈 分析ページ</a>
                    <a href="data:image/png;base64,{qr_code_data}" download="qr_{short_code}.png" class="btn btn-download">💾 画像をダウンロード</a>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except Exception as e:
        return HTMLResponse(content=f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

# CSVエクスポート（基本版のみ - エラー回避）
@app.get("/export")
async def export_basic_data():
    """基本統計データのCSVエクスポート"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.short_code, u.original_url, u.custom_name, u.campaign_name, u.created_at,
                   COUNT(c.id) as total_clicks,
                   COUNT(DISTINCT c.ip_address) as unique_visitors,
                   COUNT(CASE WHEN c.source = 'qr' THEN 1 END) as qr_clicks,
                   COUNT(CASE WHEN c.device_type = 'Mobile' THEN 1 END) as mobile_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        # CSV生成
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            '短縮コード', '元URL', 'カスタム名', 'キャンペーン名', '作成日',
            '総クリック数', 'ユニーク訪問者', 'QR経由アクセス', 'モバイルアクセス'
        ])
        
        # データ
        for row in results:
            writer.writerow([
                row[0], row[1], row[2] or '', row[3] or '', row[4],
                row[5], row[6], row[7], row[8]
            ])
        
        output.seek(0)
        
        filename = f"linktrack_basic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    features = ["basic_analytics", "bulk_processing"]
    if QR_AVAILABLE:
        features.append("qr_codes")
    if UA_AVAILABLE:
        features.append("user_agent_analysis")
    
    return JSONResponse({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(), 
        "features": features
    })

# リダイレクト処理（拡張分析対応）
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
        
        # 基本分析データ収集
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        referrer = request.headers.get("referer", "")
        source = request.query_params.get("source", "direct")
        
        # User-Agent解析
        ua_info = analyze_user_agent(user_agent)
        
        # UTMパラメータ抽出
        utm_params = extract_utm_params(referrer)
        
        # 地域情報取得
        location_info = get_location_from_ip(client_ip)
        
        # QRコード経由の判定
        if source == "qr" or "qr" in request.query_params:
            source = "qr"
        
        cursor.execute("""
            INSERT INTO clicks (
                url_id, ip_address, user_agent, referrer, source,
                device_type, browser, os, country, city,
                utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                clicked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            url_id, client_ip, user_agent, referrer, source,
            ua_info['device_type'], ua_info['browser'], ua_info['os'],
            location_info['country'], location_info['city'],
            utm_params.get('utm_source'), utm_params.get('utm_medium'),
            utm_params.get('utm_campaign'), utm_params.get('utm_term'),
            utm_params.get('utm_content'), datetime.now().isoformat()
        ))
        
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
