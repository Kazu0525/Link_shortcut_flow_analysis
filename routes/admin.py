from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# 絶対インポートに変更
import config
from utils import get_db_connection, get_all_urls_stats, format_datetime, truncate_text

router = APIRouter()

# 管理画面HTML - インライン版
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>管理ダッシュボード - LinkTrack Pro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f6fa; color: #333; line-height: 1.6; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; font-weight: 300; }
        .navigation { display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; }
        .nav-link { color: #333; text-decoration: none; padding: 10px 20px; background: white; border-radius: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); transition: all 0.3s; }
        .nav-link:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); text-align: center; position: relative; overflow: hidden; }
        .stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .stat-number { font-size: 2.5em; font-weight: bold; color: #667eea; margin-bottom: 5px; }
        .stat-label { font-size: 1.1em; color: #666; }
        .dashboard-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 30px; margin-bottom: 30px; }
        .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); }
        .card h2 { color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #f1f2f6; }
        .url-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .url-table th, .url-table td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        .url-table th { background: #f8f9fa; font-weight: 600; color: #555; }
        .url-table tr:hover { background: #f8f9fa; }
        .status-active { color: #28a745; font-weight: bold; }
        .status-inactive { color: #dc3545; font-weight: bold; }
        .btn { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; transition: all 0.3s; }
        .btn-primary { background: #667eea; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-info { background: #17a2b8; color: white; }
        .btn:hover { transform: translateY(-1px); opacity: 0.9; }
        .recent-activity { max-height: 400px; overflow-y: auto; }
        .activity-item { padding: 12px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .activity-item:last-child { border-bottom: none; }
        .activity-content { flex: 1; }
        .activity-time { color: #666; font-size: 0.9em; }
        .url-code { font-family: 'Courier New', monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
        .truncate { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .search-box { width: 100%; padding: 12px 15px; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 16px; margin-bottom: 20px; }
        .filter-section { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
        .filter-section select { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; }
        .loading { text-align: center; padding: 40px; color: #666; }
        .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        @media (max-width: 1024px) { .dashboard-grid { grid-template-columns: 1fr; } }
        @media (max-width: 768px) { .container { padding: 10px; } .navigation { flex-direction: column; align-items: center; } .filter-section { flex-direction: column; } .url-table { font-size: 14px; } .url-table th, .url-table td { padding: 8px; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 管理ダッシュボード</h1>
            <p>URL短縮サービスの統計と管理</p>
            <p>最終更新: {current_time}</p>
        </div>
        
        <div class="navigation">
            <a href="/" class="nav-link">🏠 ホーム</a>
            <a href="/admin" class="nav-link">📊 ダッシュボード</a>
            <a href="/bulk" class="nav-link">📦 一括生成</a>
            <a href="/docs" class="nav-link">📚 API文書</a>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_links}</div>
                <div class="stat-label">📎 総短縮URL数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_clicks}</div>
                <div class="stat-label">👆 総クリック数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{unique_visitors}</div>
                <div class="stat-label">👥 ユニーク訪問者</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{qr_clicks}</div>
                <div class="stat-label">📱 QRクリック数</div>
            </div>
        </div>
        
        <div class="dashboard-grid">
            <div class="card">
                <h2>🔗 URL一覧</h2>
                <div class="filter-section">
                    <input type="text" class="search-box" placeholder="🔍 URLを検索..." id="searchBox">
                    <button class="btn btn-primary" onclick="refreshData()">🔄 更新</button>
                </div>
                
                <div style="overflow-x: auto;">
                    <table class="url-table">
                        <thead>
                            <tr>
                                <th>短縮コード</th>
                                <th>元のURL</th>
                                <th>カスタム名</th>
                                <th>クリック数</th>
                                <th>ステータス</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="urlTableBody">
                            {url_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div>
                <div class="card">
                    <h2>🕒 最近のクリック</h2>
                    <div class="recent-activity">
                        {recent_clicks}
                    </div>
                </div>
                
                <div class="card">
                    <h2>🏆 トップパフォーマンス</h2>
                    <div class="recent-activity">
                        {top_urls}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>⚡ クイック操作</h2>
            <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                <a href="/bulk" class="btn btn-primary">📦 一括生成</a>
                <button class="btn btn-success" onclick="exportData()">💾 データエクスポート</button>
                <button class="btn btn-info" onclick="showSystemInfo()">ℹ️ システム情報</button>
                <button class="btn btn-danger" onclick="cleanupData()">🧹 データクリーンアップ</button>
            </div>
        </div>
    </div>

    <script>
        function refreshData() { location.reload(); }
        
        async function toggleStatus(shortCode) {
            if (!confirm(`URL '${{shortCode}}' のステータスを変更しますか？`)) return;
            try {
                const response = await fetch(`/admin/url/${{shortCode}}/toggle`, { method: 'POST' });
                const result = await response.json();
                if (result.success) { alert(result.message); location.reload(); } else { alert('エラー: ' + result.message); }
            } catch (error) { alert('ネットワークエラーが発生しました'); }
        }
        
        function exportData() { window.open('/api/export/all?format=csv', '_blank'); }
        
        async function showSystemInfo() {
            try {
                const response = await fetch('/api/admin/stats');
                const stats = await response.json();
                alert(`システム情報:\n\n総URL数: ${{stats.total_links}}\n総クリック数: ${{stats.total_clicks}}\nユニーク訪問者: ${{stats.unique_visitors}}\nシステム状態: ${{stats.system_status}}\n最終更新: ${{new Date(stats.last_updated).toLocaleString()}}`);
            } catch (error) { alert('システム情報の取得に失敗しました'); }
        }
        
        async function cleanupData() {
            if (!confirm('古いデータをクリーンアップしますか？この操作は元に戻せません。')) return;
            try {
                const response = await fetch('/admin/cleanup', { method: 'POST' });
                const result = await response.json();
                if (result.success) { alert(`クリーンアップ完了:\n\n削除したURL: ${{result.deleted_urls}}件\n削除したクリック: ${{result.deleted_clicks}}件`); location.reload(); } else { alert('クリーンアップに失敗しました'); }
            } catch (error) { alert('ネットワークエラーが発生しました'); }
        }
        
        document.getElementById('searchBox').addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#urlTableBody tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    </script>
</body>
</html>
"""

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """管理ダッシュボードページの表示（インライン版）"""
    try:
        # システム統計を取得
        system_stats = await get_system_statistics()
        
        # URL一覧を取得
        urls_data = get_all_urls_stats()
        
        # 最近のクリック履歴を取得
        recent_clicks = await get_recent_clicks(limit=10)
        
        # トップパフォーマンスURLを取得
        top_urls = await get_top_performing_urls(limit=5)
        
        # URL一覧のHTMLを生成
        url_rows = ""
        for url in urls_data[:20]:  # 最初の20件のみ表示
            status_text = '<span class="status-active">🟢 有効</span>' if url.get('is_active', 1) else '<span class="status-inactive">🔴 無効</span>'
            url_rows += f"""
            <tr>
                <td><span class="url-code">{url.get('short_code', '')}</span></td>
                <td class="truncate" title="{url.get('original_url', '')}">{url.get('original_url', '')[:50]}...</td>
                <td>{url.get('custom_name', '') or '-'}</td>
                <td>{url.get('total_clicks', 0)}</td>
                <td>{status_text}</td>
                <td>
                    <a href="/analytics/{url.get('short_code', '')}" class="btn btn-info">📈 分析</a>
                    <button class="btn btn-danger" onclick="toggleStatus('{url.get('short_code', '')}')">⏸️ 切替</button>
                </td>
            </tr>
            """
        
        # 最近のクリックのHTMLを生成
        recent_clicks_html = ""
        for click in recent_clicks:
            recent_clicks_html += f"""
            <div class="activity-item">
                <div class="activity-content">
                    <strong>{click.get('short_code', '')}</strong>
                    {f"({click.get('custom_name', '')})" if click.get('custom_name') else ''}
                    <br>
                    <small>{click.get('source', '')} - {click.get('ip_address', '')}</small>
                </div>
                <div class="activity-time">{click.get('clicked_at', '')}</div>
            </div>
            """
        
        # トップURLのHTMLを生成
        top_urls_html = ""
        for url in top_urls:
            top_urls_html += f"""
            <div class="activity-item">
                <div class="activity-content">
                    <strong>{url.get('short_code', '')}</strong>
                    {f"({url.get('custom_name', '')})" if url.get('custom_name') else ''}
                    <br>
                    <small>{url.get('total_clicks', 0)}クリック / {url.get('unique_visitors', 0)}ユニーク</small>
                </div>
                <div>
                    <a href="/analytics/{url.get('short_code', '')}" class="btn btn-info">📈</a>
                </div>
            </div>
            """
        
        # HTMLを生成
        html_content = ADMIN_HTML.format(
            current_time=datetime.now().strftime("%Y/%m/%d %H:%M"),
            total_links=system_stats.get("total_links", 0),
            total_clicks=system_stats.get("total_clicks", 0),
            unique_visitors=system_stats.get("unique_visitors", 0),
            qr_clicks=system_stats.get("qr_clicks", 0),
            url_rows=url_rows,
            recent_clicks=recent_clicks_html,
            top_urls=top_urls_html
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        # エラー時のフォールバック
        error_html = f'<h1>エラー</h1><p>管理ダッシュボードの読み込みでエラーが発生しました: {str(e)}</p>'
        return HTMLResponse(content=error_html, status_code=500)

@router.post("/admin/url/{short_code}/toggle")
async def toggle_url_status(short_code: str):
    """URLの有効/無効を切り替え"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 現在の状態を取得
        cursor.execute("SELECT is_active FROM urls WHERE short_code = ?", (short_code,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="URLが見つかりません")
        
        current_status = result[0]
        new_status = 0 if current_status else 1
        
        # ステータスを更新
        cursor.execute("""
            UPDATE urls 
            SET is_active = ?
            WHERE short_code = ?
        """, (new_status, short_code))
        
        conn.commit()
        conn.close()
        
        status_text = "有効" if new_status else "無効"
        
        return JSONResponse({
            "success": True,
            "message": f"URL '{short_code}' を{status_text}にしました",
            "new_status": new_status
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ステータス変更でエラーが発生しました: {str(e)}")

async def get_system_statistics():
    """システム全体の統計を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as total_links,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                COUNT(CASE WHEN c.source = 'qr_code' THEN 1 END) as qr_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
        """)
        
        basic_stats = dict(cursor.fetchone())
        conn.close()
        
        return {
            **basic_stats,
            "system_status": "正常稼働中",
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"システム統計取得エラー: {e}")
        return {
            "total_links": 0,
            "total_clicks": 0,
            "unique_visitors": 0,
            "qr_clicks": 0,
            "system_status": "エラー"
        }

async def get_recent_clicks(limit: int = 20):
    """最近のクリック履歴を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.short_code,
                u.custom_name,
                c.ip_address,
                c.source,
                c.clicked_at,
                c.referrer
            FROM clicks c
            JOIN urls u ON c.url_id = u.id
            ORDER BY c.clicked_at DESC
            LIMIT ?
        """, (limit,))
        
        clicks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return clicks
        
    except Exception as e:
        print(f"最近のクリック取得エラー: {e}")
        return []

async def get_top_performing_urls(limit: int = 10):
    """トップパフォーマンスURLを取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.short_code,
                u.original_url,
                u.custom_name,
                u.campaign_name,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_visitors,
                MAX(c.clicked_at) as last_clicked
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = 1
            GROUP BY u.id
            HAVING COUNT(c.id) > 0
            ORDER BY total_clicks DESC
            LIMIT ?
        """, (limit,))
        
        top_urls = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return top_urls
        
    except Exception as e:
        print(f"トップURL取得エラー: {e}")
        return []

@router.get("/api/admin/stats")
async def get_admin_stats():
    """管理用統計データAPI"""
    try:
        stats = await get_system_statistics()
        return JSONResponse(stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"統計データの取得でエラーが発生しました: {str(e)}")

@router.post("/admin/cleanup")
async def cleanup_old_data():
    """古いデータのクリーンアップ"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 30日以上前の無効URLを削除
        cursor.execute("""
            DELETE FROM urls 
            WHERE is_active = 0 
            AND DATE(created_at) < DATE('now', '-30 days')
        """)
        deleted_urls = cursor.rowcount
        
        # 孤立したクリックデータを削除
        cursor.execute("""
            DELETE FROM clicks 
            WHERE url_id NOT IN (SELECT id FROM urls)
        """)
        deleted_clicks = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "message": "データクリーンアップが完了しました",
            "deleted_urls": deleted_urls,
            "deleted_clicks": deleted_clicks
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"データクリーンアップでエラーが発生しました: {str(e)}")
