# routes/bulk.py
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3
import json
import csv
import io
from datetime import datetime
from typing import List, Dict, Any

# 絶対インポートに変更
import config
from utils import get_db_connection, generate_short_code, validate_url, clean_url

router = APIRouter()

# 一括生成画面HTML - 完全な修正版（インライン版）
BULK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>一括リンク生成 - Link Tracker</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        .form-section { background: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .spreadsheet-container { margin: 20px 0; overflow-x: auto; }
        .spreadsheet-table { width: 100%; border-collapse: collapse; min-width: 1500px; }
        .spreadsheet-table th, .spreadsheet-table td { border: 1px solid #ddd; padding: 8px; }
        .spreadsheet-table th { background: #4CAF50; color: white; text-align: center; position: sticky; top: 0; }
        .spreadsheet-table input, .spreadsheet-table select { width: 100%; border: 1px solid #ccc; padding: 6px; box-sizing: border-box; }
        .spreadsheet-table input:focus, .spreadsheet-table select:focus { border-color: #2196F3; outline: none; }
        .required { border-left: 3px solid #f44336; }
        .row-number { background: #f5f5f5; text-align: center; font-weight: bold; width: 50px; }
        .quantity-column { width: 80px; text-align: center; }
        .action-buttons { text-align: center; margin: 20px 0; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }
        .btn-primary { background: #4CAF50; color: white; }
        .btn-secondary { background: #2196F3; color: white; }
        .btn-danger { background: #f44336; color: white; }
        .btn-warning { background: #FF9800; color: white; }
        .results-section { margin: 30px 0; }
        .result-item { background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }
        .error-item { background: #ffebee; border-left: 4px solid #f44336; }
        .copy-btn { background: #FF9800; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; margin-left: 5px; }
        .stats-link { color: #1976d2; text-decoration: none; font-weight: bold; }
        .stats-link:hover { text-decoration: underline; }
        .loading { text-align: center; padding: 20px; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 2s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .instructions { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 一括リンク生成システム</h1>
        
        <div class="instructions">
            <h3>📋 使い方</h3>
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
            <button class="btn btn-secondary" id="addRowBtn">➕ 1行追加</button>
            <button class="btn btn-secondary" id="add5RowsBtn">➕ 5行追加</button>
            <button class="btn btn-secondary" id="add10RowsBtn">➕ 10行追加</button>
            <button class="btn btn-warning" id="clearAllBtn">🗑️ 全削除</button>
            <button class="btn btn-danger" id="generateBtn">🚀 一括生成開始</button>
            <button class="btn btn-primary" onclick="window.location.href='/admin'">📊 管理画面へ</button>
        </div>

        <div class="spreadsheet-container">
            <table class="spreadsheet-table" id="spreadsheetTable">
                <thead>
                    <tr>
                        <th class="row-number">A<br>行番号</th>
                        <th style="width: 40%;">B<br>オリジナルURL ※必須</th>
                        <th style="width: 12%;">C<br>カスタム短縮コード<br>(任意)</th>
                        <th style="width: 12%;">D<br>カスタム名<br>(任意)</th>
                        <th style="width: 12%;">E<br>キャンペーン名<br>(任意)</th>
                        <th style="width: 8%;" class="quantity-column">F<br>生成数量<br>(任意)</th>
                        <th style="width: 10%;">操作</th>
                    </tr>
                </thead>
                <tbody id="spreadsheetBody">
                    <tr>
                        <td class="row-number">1</td>
                        <td><input type="url" class="required" placeholder="https://example.com" required /></td>
                        <td><input type="text" placeholder="例: product01" /></td>
                        <td><input type="text" placeholder="例: 商品A" /></td>
                        <td><input type="text" placeholder="例: 春キャンペーン" /></td>
                        <td><input type="number" min="1" max="20" value="1" class="quantity-column" /></td>
                        <td><button class="btn btn-danger delete-row-btn">⌫ 削除</button></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="action-buttons">
            <button class="btn btn-secondary" id="addRowBtn2">➕ 1行追加</button>
            <button class="btn btn-secondary" id="add5RowsBtn2">➕ 5行追加</button>
            <button class="btn btn-secondary" id="add10RowsBtn2">➕ 10行追加</button>
            <button class="btn btn-warning" id="clearAllBtn2">🗑️ 全削除</button>
            <button class="btn btn-danger" id="generateBtn2">🚀 一括生成開始</button>
        </div>

        <div class="results-section" id="resultsSection" style="display: none;">
            <h2>📈 生成結果</h2>
            <div id="resultsContent"></div>
        </div>
    </div>

    <script>
        let rowCounter = 1;
        
        function addRow() {
            console.log('addRow function called');
            rowCounter++;
            const tbody = document.getElementById('spreadsheetBody');
            const newRow = tbody.insertRow();
            newRow.innerHTML = 
                '<td class="row-number">' + rowCounter + '</td>' +
                '<td><input type="url" class="required" placeholder="https://example.com" required /></td>' +
                '<td><input type="text" placeholder="例: product' + rowCounter.toString().padStart(2, '0') + '" /></td>' +
                '<td><input type="text" placeholder="例: 商品' + String.fromCharCode(64 + rowCounter) + '" /></td>' +
                '<td><input type="text" placeholder="例: 春キャンペーン" /></td>' +
                '<td><input type="number" min="1" max="20" value="1" class="quantity-column" /></td>' +
                '<td><button class="btn btn-danger delete-row-btn">⌫ 削除</button></td>';
            updateRowNumbers();
            attachDeleteHandler(newRow);
        }
        
        function addMultipleRows(count) {
            console.log('addMultipleRows function called with count:', count);
            for (let i = 0; i < count; i++) {
                addRow();
            }
        }
        
        function removeRow(button) {
            console.log('removeRow function called');
            const row = button.closest('tr');
            if (document.getElementById('spreadsheetBody').rows.length > 1) {
                row.remove();
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
            console.log('clearAll function called');
            if (confirm('全てのデータを削除しますか？')) {
                document.getElementById('spreadsheetBody').innerHTML = 
                    '<tr>' +
                        '<td class="row-number">1</td>' +
                        '<td><input type="url" class="required" placeholder="https://example.com" required /></td>' +
                        '<td><input type="text" placeholder="例: product01" /></td>' +
                        '<td><input type="text" placeholder="例: 商品A" /></td>' +
                        '<td><input type="text" placeholder="例: 春キャンペーン" /></td>' +
                        '<td><input type="number" min="1" max="20" value="1" class="quantity-column" /></td>' +
                        '<td><button class="btn btn-danger delete-row-btn">⌫ 削除</button></td>' +
                    '</tr>';
                rowCounter = 1;
                document.getElementById('resultsSection').style.display = 'none';
                attachDeleteHandler(document.querySelector('#spreadsheetBody tr'));
            }
        }
        
        function validateAndGenerate() {
            console.log('validateAndGenerate function called');
            const rows = document.querySelectorAll('#spreadsheetBody tr');
            const data = [];
            let hasError = false;
            
            for (let row of rows) {
                const inputs = row.querySelectorAll('input');
                const originalUrl = inputs[0].value.trim();
                const customSlug = inputs[1].value.trim();
                const customName = inputs[2].value.trim();
                const campaignName = inputs[3].value.trim();
                const quantity = parseInt(inputs[4].value) || 1;
                
                if (originalUrl) {
                    if (!originalUrl.startsWith('http://') && !originalUrl.startsWith('https://')) {
                        alert('URLは http:// または https:// で始めてください');
                        inputs[0].focus();
                        hasError = true;
                        break;
                    }
                    
                    for (let i = 0; i < quantity; i++) {
                        let finalCustomSlug = customSlug;
                        let finalCustomName = customName;
                        
                        if (quantity > 1) {
                            if (customSlug) finalCustomSlug = customSlug + '_' + (i+1);
                            if (customName) finalCustomName = customName + '_' + (i+1);
                        }
                        
                        data.push({
                            url: originalUrl,
                            custom_name: finalCustomName || null
                        });
                    }
                }
            }
            
            if (hasError) return;
            
            if (data.length === 0) {
                alert('少なくとも1つのURLを入力してください');
                return;
            }
            
            if (data.length > 100) {
                if (!confirm('一度に ' + data.length + ' 個のURLを生成します。よろしいですか？')) {
                    return;
                }
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
                const response = await fetch('/api/bulk', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ urls: data })
                });
                
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                
                const result = await response.json();
                displayResults(result);
                
            } catch (error) {
                resultsContent.innerHTML = '<div class="error-item">エラー: ' + error.message + '</div>';
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🚀 一括生成開始';
            }
        }
        
        function displayResults(result) {
            const resultsContent = document.getElementById('resultsContent');
            
            let html = 
                '<div style="background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px;">' +
                    '<h3>📊 生成サマリー</h3>' +
                    '<p>成功: <strong>' + result.success_count + '</strong> | エラー: <strong>' + result.failed_count + '</strong> | 総生成数: <strong>' + result.total_count + '</strong></p>' +
                '</div>';
            
            if (result.results && result.results.length > 0) {
                html += '<h3>✅ 生成成功</h3>';
                result.results.forEach((item, index) => {
                    if (item.success) {
                        html += 
                            '<div class="result-item">' +
                                '<p><strong>' + (index + 1) + '. 元URL:</strong> ' + item.original_url + '</p>' +
                                '<p><strong>カスタム名:</strong> ' + (item.custom_name || 'なし') + '</p>' +
                                '<p><strong>短縮URL:</strong> ' +
                                    '<a href="' + item.short_url + '" target="_blank">' + item.short_url + '</a>' +
                                    '<button class="copy-btn" onclick="copyToClipboard(\'' + item.short_url + '\')">📋 コピー</button>' +
                                    '<a href="/analytics/' + item.short_code + '" target="_blank" class="stats-link">📈 分析</a>' +
                                '</p>' +
                            '</div>';
                    }
                });
            }
            
            // エラー表示
            if (result.results && result.results.some(item => !item.success)) {
                html += '<h3>❌ エラー</h3>';
                result.results.forEach(item => {
                    if (!item.success) {
                        html += '<div class="error-item">URL: ' + item.original_url + ' - エラー: ' + item.error_message + '</div>';
                    }
                });
            }
            
            resultsContent.innerHTML = html;
        }
        
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('クリップボードにコピーしました: ' + text);
            });
        }
        
        function attachDeleteHandler(row) {
            const deleteBtn = row.querySelector('.delete-row-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', function() {
                    removeRow(this);
                });
            }
        }
        
        // イベントリスナーの設定
        document.addEventListener('DOMContentLoaded', function() {
            // ボタンにイベントリスナーを追加
            document.getElementById('addRowBtn').addEventListener('click', addRow);
            document.getElementById('add5RowsBtn').addEventListener('click', () => addMultipleRows(5));
            document.getElementById('add10RowsBtn').addEventListener('click', () => addMultipleRows(10));
            document.getElementById('clearAllBtn').addEventListener('click', clearAll);
            document.getElementById('generateBtn').addEventListener('click', validateAndGenerate);
            
            document.getElementById('addRowBtn2').addEventListener('click', addRow);
            document.getElementById('add5RowsBtn2').addEventListener('click', () => addMultipleRows(5));
            document.getElementById('add10RowsBtn2').addEventListener('click', () => addMultipleRows(10));
            document.getElementById('clearAllBtn2').addEventListener('click', clearAll);
            document.getElementById('generateBtn2').addEventListener('click', validateAndGenerate);
            
            // 初期行の削除ボタンにハンドラーを追加
            attachDeleteHandler(document.querySelector('#spreadsheetBody tr'));
            
            // 初期表示時に4行追加（合計5行）
            addMultipleRows(4);
            console.log('ページ読み込み完了');
        });
    </script>
</body>
</html>
"""

@router.get("/bulk")
async def bulk_generation_page():
    """一括生成ページ"""
    return HTMLResponse(content=BULK_HTML)

@router.post("/api/bulk")
async def bulk_generate_urls(request: dict):
    """複数URLを一括生成（response_model完全除去版）"""
    results = []
    success_count = 0
    failed_count = 0
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for item in request.get("urls", []):
            try:
                original_url = item.get("url", "").strip()
                custom_name = item.get("custom_name", "").strip() or None
                
                if not original_url:
                    continue
                
                if not validate_url(original_url):
                    results.append({
                        "original_url": original_url,
                        "short_code": "",
                        "short_url": "",
                        "custom_name": custom_name,
                        "success": False,
                        "error_message": "無効なURLです"
                    })
                    failed_count += 1
                    continue
                
                # 短縮コード生成
                short_code = await generate_unique_short_code_bulk(cursor)
                
                # データベースに保存
                cursor.execute("""
                    INSERT INTO urls (short_code, original_url, custom_name, created_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    short_code,
                    clean_url(original_url),
                    custom_name,
                    datetime.now().isoformat()
                ))
                
                results.append({
                    "original_url": original_url,
                    "short_code": short_code,
                    "short_url": f"{config.BASE_URL}/{short_code}",
                    "custom_name": custom_name,
                    "success": True,
                    "error_message": None
                })
                success_count += 1
                
            except Exception as item_error:
                results.append({
                    "original_url": item.get("url", ""),
                    "short_code": "",
                    "short_url": "",
                    "custom_name": item.get("custom_name"),
                    "success": False,
                    "error_message": str(item_error)
                })
                failed_count += 1
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success_count": success_count,
            "failed_count": failed_count,
            "total_count": len(request.get("urls", [])),
            "results": results
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"一括処理でエラーが発生しました: {str(e)}")

async def generate_unique_short_code_bulk(cursor, length=6):
    """バルク処理用の重複しない短縮コードを生成"""
    import string
    import random
    
    chars = string.ascii_letters + string.digits
    max_attempts = 50
    
    for _ in range(max_attempts):
        code = ''.join(random.choices(chars, k=length))
        
        # データベースで重複チェック
        cursor.execute("SELECT 1 FROM urls WHERE short_code = ?", (code,))
        exists = cursor.fetchone()
        
        if not exists:
            return code
    
    raise HTTPException(status_code=500, detail="短縮コードの生成に失敗しました")

