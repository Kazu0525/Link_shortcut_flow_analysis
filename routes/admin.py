from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import sqlite3
from datetime import datetime
from config import DB_PATH, BASE_URL
from utils import generate_qr_code_base64

router = APIRouter()

# 管理画面HTML（省略版 - 実際には完全なHTMLが必要）
ADMIN_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>管理ダッシュボード - Link Tracker</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; padding: 20px; background: #f5f5f5; 
        }
        .container { 
            max-width: 1400px; margin: 0 auto; background: white; 
            padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }
        h1 { 
            color: #333; border-bottom: 3px solid #4CAF50; 
            padding-bottom: 10px; margin-bottom: 30px; 
        }
        .stats-cards { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; margin-bottom: 30px; 
        }
        .stat-card { 
            background: #f8f9fa; padding: 20px; border-radius: 8px; 
            text-align: center; border-left: 4px solid #4CAF50; 
        }
        .stat-number { font-size: 2em; font-weight: bold; color: #4CAF50; }
        .stat-label { color: #666; margin-top: 5px; }
        .navigation { 
            display: flex; gap: 10px; margin-bottom: 30px; 
            flex-wrap: wrap; align-items: center; 
        }
        .nav-btn { 
            padding: 10px 20px; border: none; border-radius: 5px; 
            cursor: pointer; text-decoration: none; font-size: 14px; 
        }
        .btn-primary { background: #4CAF50; color: white; }
        .btn-secondary { background: #2196F3; color: white; }
        .btn-info { background: #17a2b8; color: white; }
        .table-container { overflow-x: auto; }
        .urls-table { 
            width: 100%; border-collapse: collapse; margin-top: 20px; 
            min-width: 1200px; 
        }
        .urls-table th, .urls-table td { 
            border: 1px solid #ddd; padding: 12px; text-align: left; 
        }
        .urls-table th { 
            background: #4CAF50; color: white; font-weight: bold; 
            position: sticky; top: 0; 
        }
        .urls-table tr:nth-child(even) { background: #f9f9f9; }
        .urls-table tr:hover { background: #e3f2fd; }
        .short-link { 
            color: #1976d2; font-weight: bold; text-decoration: none; 
        }
        .short-link:hover { text-decoration: underline; }
        .action-btn { 
            padding: 5px 10px; margin: 2px; border: none; 
            border-radius: 3px; cursor: pointer; font-size: 12px; 
        }
        .btn-stats { background: #FF9800; color: white; }
        .btn-qr { background: #9C27B0; color: white; }
        .btn-copy { background: #607D8B; color: white; }
        .original-url { 
            max-width: 200px; overflow: hidden; 
            text-overflow: ellipsis; white-space: nowrap; 
        }
        .click-count { 
            background: #e8f5e8; padding: 5px 10px; 
            border-radius: 15px; font-weight: bold; 
        }
        .message { 
            padding: 15px; margin: 20px 0; border-radius: 5px; 
        }
        .message.success { 
            background: #d4edda; color: #155724; border: 1px solid #c3e6cb; 
        }
        .message.error { 
            background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; 
        }
        @media (max-width: 768px) {
            .navigation { flex-direction: column; }
            .nav-btn { width: 100%; }
            .stats-cards { grid-template-columns: 1fr; }
        }
    </style>
    <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('コピーしました: ' + text);
            });
        }
        
        function showQR(short_code) {
            const qrUrl = `{base_url}/${short_code}?source=qr`;
            window.open(`/qr/${short_code}`, '_blank', 'width=400,height=500');
        }
        
        function refreshStats() {
            location.reload();
        }
        
        // 自動更新（5分ごと）
        setInterval(refreshStats, 300000);
    </script>
</head>
<body>
    <div class="container">
        <h1>📊 管理ダッシュボード</h1>
        
        <div class="stats-cards">
            <div class="stat-card">
                <div class="stat-number">{total_urls}</div>
                <div class="stat-label">総リンク数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_clicks}</div>
                <div class="stat-label">総クリック数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{today_clicks}</div>
                <div class="stat-label">今日のクリック</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{active_urls}</div>
                <div class="stat-label">アクティブなリンク</div>
            </div>
        </div>
        
        <div class="navigation">
            <a href="/bulk" class="nav-btn btn-primary">🚀 一括生成</a>
            <a href="/api/shorten" class="nav-btn btn-secondary">🔗 API短縮</a>
            <a href="/docs" class="nav-btn btn-info" target="_blank">📖 API Docs</a>
            <button class="nav-btn btn-secondary" onclick="refreshStats()">🔄 更新</button>
        </div>
        
        <div class="table-container">
            <table class="urls-table">
                <thead>
                    <tr>
                        <th>短縮コード</th>
                        <th>元URL</th>
                        <th>カスタム名</th>
                        <th>キャンペーン</th>
                        <th>クリック数</th>
                        <th>ユニーク</th>
                        <th>QRクリック</th>
                        <th>作成日</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        
        <div style="text-align: center; margin-top: 30px; color: #666;">
            <p>最終更新: {last_updated}</p>
            <p>データは5分ごとに自動更新されます</p>
        </div>
    </div>
</body>
</html>"""

# **重要: パス変更**
@router.get("/admin")  # ← ""から"/admin"に変更
async def admin_dashboard():
    """管理ダッシュボード"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 統計情報取得
        cursor.execute("SELECT COUNT(*) FROM urls WHERE is_active = TRUE")
        total_urls = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM urls WHERE is_active = TRUE")
        active_urls = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clicks")
        total_clicks = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM clicks 
            WHERE DATE(clicked_at) = DATE('now')
        """)
        today_clicks = cursor.fetchone()[0]
        
        # URL一覧取得（クリック数込み）
        cursor.execute('''
            SELECT 
                u.short_code,
                u.original_url,
                u.custom_name,
                u.campaign_name,
                u.created_at,
                COALESCE(c.total_clicks, 0) as total_clicks,
                COALESCE(c.unique_clicks, 0) as unique_clicks,
                COALESCE(c.qr_clicks, 0) as qr_clicks
            FROM urls u
            LEFT JOIN (
                SELECT 
                    url_id,
                    COUNT(*) as total_clicks,
                    COUNT(DISTINCT ip_address) as unique_clicks,
                    COUNT(CASE WHEN source = 'qr' THEN 1 END) as qr_clicks
                FROM clicks
                GROUP BY url_id
            ) c ON u.id = c.url_id
            WHERE u.is_active = TRUE
            ORDER BY u.created_at DESC
            LIMIT 100
        ''')
        
        urls_data = cursor.fetchall()
        conn.close()
        
        # テーブル行生成
        table_rows = ""
        for row in urls_data:
            short_code, original_url, custom_name, campaign_name, created_at, clicks, unique, qr_clicks = row
            short_url = f"{BASE_URL}/{short_code}"
            
            # URLを短縮表示
            display_url = original_url[:50] + "..." if len(original_url) > 50 else original_url
            
            table_rows += f'''
            <tr>
                <td>
                    <a href="{short_url}" target="_blank" class="short-link">{short_code}</a>
                </td>
                <td class="original-url" title="{original_url}">{display_url}</td>
                <td>{custom_name or '-'}</td>
                <td>{campaign_name or '-'}</td>
                <td><span class="click-count">{clicks}</span></td>
                <td>{unique}</td>
                <td>{qr_clicks}</td>
                <td>{created_at}</td>
                <td>
                    <button class="action-btn btn-copy" onclick="copyToClipboard('{short_url}')">📋</button>
                    <button class="action-btn btn-qr" onclick="showQR('{short_code}')">📱</button>
                    <a href="/analytics/{short_code}" target="_blank" class="action-btn btn-stats">📈</a>
                </td>
            </tr>
            '''
        
        # HTMLレンダリング
        html_content = ADMIN_HTML.format(
            total_urls=total_urls,
            total_clicks=total_clicks,
            today_clicks=today_clicks,
            active_urls=active_urls,
            table_rows=table_rows,
            base_url=BASE_URL,
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        error_html = f"""
        <html><body>
        <h1>エラーが発生しました</h1>
        <p>{str(e)}</p>
        <a href="/">ホームに戻る</a>
        </body></html>
        """
        return HTMLResponse(content=error_html, status_code=500)

# QRコード表示用エンドポイント
@router.get("/qr/{short_code}")
async def qr_code_page(short_code: str):
    """QRコード表示ページ"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT original_url, custom_name, campaign_name
            FROM urls WHERE short_code = ? AND is_active = TRUE
        ''', (short_code,))
        
        result = cursor.fetchone()
        if not result:
            return HTMLResponse(content="<h1>エラー</h1><p>短縮URLが見つかりません</p>", status_code=404)
        
        original_url, custom_name, campaign_name = result
        conn.close()
        
        qr_url = f"{BASE_URL}/{short_code}?source=qr"
        qr_code_base64 = generate_qr_code_base64(qr_url)
        
        qr_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>QRコード - {short_code}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; }}
                .qr-container {{ max-width: 400px; margin: 0 auto; }}
                .qr-code {{ border: 1px solid #ddd; padding: 20px; border-radius: 8px; }}
                .info {{ background: #f9f9f9; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="qr-container">
                <h1>QRコード</h1>
                <div class="info">
                    <p><strong>短縮コード:</strong> {short_code}</p>
                    <p><strong>元URL:</strong> {original_url}</p>
                    <p><strong>カスタム名:</strong> {custom_name or 'なし'}</p>
                    <p><strong>キャンペーン:</strong> {campaign_name or 'なし'}</p>
                </div>
                <div class="qr-code">
                    <img src="data:image/png;base64,{qr_code_base64}" alt="QR Code" />
                </div>
                <p>QR URL: <a href="{qr_url}" target="_blank">{qr_url}</a></p>
                <button onclick="window.print()">印刷</button>
                <button onclick="window.close()">閉じる</button>
            </div>
        </body>
        </html>
        '''
        
        return HTMLResponse(content=qr_html)
        
    except Exception as e:
        error_html = f"<h1>エラー</h1><p>{str(e)}</p>"
        return HTMLResponse(content=error_html, status_code=500)
