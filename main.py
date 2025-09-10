<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>一括リンク生成システム</title>
  <style>
    body { 
      font-family: Arial, sans-serif; 
      margin: 20px; 
      background: #f5f5f5; 
      color: #333;
    }
    .container { 
      max-width: 1800px; 
      margin: 0 auto; 
      background: white; 
      padding: 30px; 
      border-radius: 12px; 
      box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    h1 { 
      color: #2c3e50; 
      border-bottom: 4px solid #4CAF50; 
      padding-bottom: 15px; 
      margin-bottom: 25px;
    }
    .instructions { 
      background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
      padding: 20px; 
      border-radius: 10px; 
      margin: 25px 0; 
      border-left: 5px solid #2196F3;
    }
    .action-buttons { 
      display: flex; 
      flex-wrap: wrap; 
      gap: 12px; 
      margin: 25px 0; 
      justify-content: center;
    }
    .btn { 
      padding: 12px 20px; 
      border: none; 
      border-radius: 8px; 
      cursor: pointer; 
      font-size: 14px; 
      font-weight: 600;
      transition: all 0.3s ease;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 120px;
      justify-content: center;
    }
    .btn:hover { 
      transform: translateY(-2px); 
      box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    .btn-add { 
      background: linear-gradient(135deg, #2196F3 0%, #1976d2 100%);
      color: white; 
    }
    .btn-clear { 
      background: linear-gradient(135deg, #FF9800 0%, #f57c00 100%);
      color: white; 
    }
    .btn-generate { 
      background: linear-gradient(135deg, #4CAF50 0%, #388e3c 100%);
      color: white; 
      font-weight: bold;
      font-size: 16px;
      padding: 15px 25px;
    }
    .btn-admin { 
      background: linear-gradient(135deg, #9C27B0 0%, #7b1fa2 100%);
      color: white; 
    }
    .spreadsheet-container { 
      margin: 25px 0; 
      overflow-x: auto; 
      border: 2px solid #e0e0e0; 
      border-radius: 10px;
      background: white;
      box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .spreadsheet-table { 
      width: 100%; 
      border-collapse: separate;
      border-spacing: 0;
      min-width: 1400px;
    }
    .spreadsheet-table th { 
      background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
      color: white; 
      text-align: center; 
      padding: 16px 12px; 
      border: 1px solid #388e3c;
      font-weight: 600;
      font-size: 14px;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .spreadsheet-table td { 
      border: 1px solid #e0e0e0; 
      padding: 8px;
      background: white;
    }
    .spreadsheet-table input { 
      width: 100%; 
      border: 2px solid transparent; 
      padding: 10px 8px; 
      font-size: 14px;
      outline: none; 
      background: transparent;
      border-radius: 4px;
      transition: all 0.2s ease;
    }
    .spreadsheet-table input:focus { 
      background: #fff3cd; 
      border-color: #ffc107;
    }
    .row-number { 
      background: #f8f9fa; 
      text-align: center; 
      font-weight: bold; 
      width: 70px;
      color: #495057;
      font-size: 14px;
    }
    .delete-btn { 
      background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
      color: white; 
      border: none; 
      padding: 8px 16px; 
      border-radius: 6px; 
      cursor: pointer; 
      font-size: 12px;
      font-weight: 600;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .delete-btn:hover { 
      transform: scale(1.05);
      box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
    }
    .results-section { 
      margin: 35px 0; 
      display: none; 
      background: white;
      border-radius: 10px;
      padding: 25px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .result-item { 
      background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
      padding: 20px; 
      margin: 15px 0; 
      border-radius: 8px; 
      border-left: 5px solid #28a745;
      box-shadow: 0 2px 8px rgba(40, 167, 69, 0.2);
    }
    .error-item { 
      background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
      border-left: 5px solid #dc3545;
      color: #721c24;
      box-shadow: 0 2px 8px rgba(220, 53, 69, 0.2);
    }
    .copy-btn { 
      background: linear-gradient(135deg, #fd7e14 0%, #f39c12 100%);
      color: white; 
      border: none; 
      padding: 8px 16px; 
      border-radius: 6px; 
      cursor: pointer; 
      margin-left: 12px; 
      font-size: 12px;
      font-weight: 600;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .copy-btn:hover { 
      transform: scale(1.05);
      box-shadow: 0 4px 12px rgba(253, 126, 20, 0.3);
    }
    .loading { 
      text-align: center; 
      padding: 30px; 
      background: #f8f9fa;
      border-radius: 10px;
      margin: 20px 0;
    }
    .spinner { 
      border: 4px solid #f3f3f3; 
      border-top: 4px solid #4CAF50; 
      border-radius: 50%; 
      width: 40px; 
      height: 40px; 
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
      <button type="button" class="btn btn-add" id="add1Row">➕ 1行追加</button>
      <button type="button" class="btn btn-add" id="add5Rows">➕ 5行追加</button>
      <button type="button" class="btn btn-add" id="add10Rows">➕ 10行追加</button>
      <button type="button" class="btn btn-clear" id="clearAll">🗑️ 全削除</button>
      <button type="button" class="btn btn-generate" id="generateBtn">🚀 一括生成開始</button>
      <button type="button" class="btn btn-admin" id="adminBtn">📊 管理画面へ</button>
    </div>

    <div class="spreadsheet-container">
      <table class="spreadsheet-table">
        <thead>
          <tr>
            <th style="width: 70px;">A<br>行番号</th>
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
            <td><button class="delete-btn">🗑️ 削除</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="action-buttons">
      <button type="button" class="btn btn-add" id="add1RowBottom">➕ 1行追加</button>
      <button type="button" class="btn btn-add" id="add5RowsBottom">➕ 5行追加</button>
      <button type="button" class="btn btn-add" id="add10RowsBottom">➕ 10行追加</button>
      <button type="button" class="btn btn-clear" id="clearAllBottom">🗑️ 全削除</button>
      <button type="button" class="btn btn-generate" id="generateBtnBottom">🚀 一括生成開始</button>
    </div>

    <div class="results-section" id="resultsArea">
      <h2>📈 生成結果</h2>
      <div id="resultsContent"></div>
    </div>
  </div>

  <script>
    // グローバル変数
    let rowCount = 1;
    
    // DOMの読み込み完了後に実行
    document.addEventListener('DOMContentLoaded', function() {
      console.log('DOM fully loaded');
      
      // イベントリスナーの設定
      document.getElementById('add1Row').addEventListener('click', function() { addRows(1); });
      document.getElementById('add5Rows').addEventListener('click', function() { addRows(5); });
      document.getElementById('add10Rows').addEventListener('click', function() { addRows(10); });
      document.getElementById('add1RowBottom').addEventListener('click', function() { addRows(1); });
      document.getElementById('add5RowsBottom').addEventListener('click', function() { addRows(5); });
      document.getElementById('add10RowsBottom').addEventListener('click', function() { addRows(10); });
      
      document.getElementById('clearAll').addEventListener('click', clearAllData);
      document.getElementById('clearAllBottom').addEventListener('click', clearAllData);
      
      document.getElementById('generateBtn').addEventListener('click', startGeneration);
      document.getElementById('generateBtnBottom').addEventListener('click', startGeneration);
      
      document.getElementById('adminBtn').addEventListener('click', function() {
        window.location.href = '/admin';
      });
      
      // 削除ボタンのイベントデリゲーション
      document.getElementById('dataTable').addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-btn')) {
          deleteRow(e.target);
        }
      });
      
      // 初期表示で4行追加
      addRows(4);
    });
    
    // 行追加機能
    function addRows(count) {
      const table = document.getElementById('dataTable');
      
      for (let i = 0; i < count; i++) {
        rowCount++;
        const newRow = table.insertRow();
        newRow.innerHTML = `
          <td class="row-number">${rowCount}</td>
          <td><input type="url" placeholder="https://example.com" /></td>
          <td><input type="text" placeholder="例: product${rowCount.toString().padStart(2, '0')}" /></td>
          <td><input type="text" placeholder="例: 商品${String.fromCharCode(65 + (rowCount % 26))}" /></td>
          <td><input type="text" placeholder="例: 春キャンペーン" /></td>
          <td><input type="number" min="1" max="20" value="1" /></td>
          <td><button class="delete-btn">🗑️ 削除</button></td>
        `;
      }
      updateRowNumbers();
    }
    
    // 行削除機能
    function deleteRow(button) {
      const table = document.getElementById('dataTable');
      if (table.rows.length > 1) {
        button.closest('tr').remove();
        updateRowNumbers();
      } else {
        alert('最低1行は必要です');
      }
    }
    
    // 行番号更新
    function updateRowNumbers() {
      const table = document.getElementById('dataTable');
      const rows = table.getElementsByTagName('tr');
      for (let i = 0; i < rows.length; i++) {
        rows[i].cells[0].textContent = i + 1;
      }
      rowCount = rows.length;
    }
    
    // 全削除機能
    function clearAllData() {
      if (confirm('全てのデータを削除しますか？')) {
        const table = document.getElementById('dataTable');
        table.innerHTML = `
          <tr>
            <td class="row-number">1</td>
            <td><input type="url" placeholder="https://example.com" /></td>
            <td><input type="text" placeholder="例: product01" /></td>
            <td><input type="text" placeholder="例: 商品A" /></td>
            <td><input type="text" placeholder="例: 春キャンペーン" /></td>
            <td><input type="number" min="1" max="20" value="1" /></td>
            <td><button class="delete-btn">🗑️ 削除</button></td>
          </tr>
        `;
        rowCount = 1;
        document.getElementById('resultsArea').style.display = 'none';
      }
    }
    
    // 一括生成機能
    async function startGeneration() {
      const table = document.getElementById('dataTable');
      const rows = table.getElementsByTagName('tr');
      const urlList = [];
      
      // データ収集
      for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const urlInput = row.cells[1].querySelector('input');
        const url = urlInput ? urlInput.value.trim() : '';
        
        if (url) {
          if (!url.startsWith('http://') && !url.startsWith('https://')) {
            alert(`行 ${i + 1}: URLは http:// または https:// で始めてください`);
            return;
          }
          urlList.push(url);
        }
      }
      
      if (urlList.length === 0) {
        alert('少なくとも1つのURLを入力してください');
        return;
      }
      
      // 生成処理
      const generateBtns = document.querySelectorAll('.btn-generate');
      generateBtns.forEach(btn => {
        btn.disabled = true;
        btn.textContent = '⏳ 生成中...';
      });
      
      const resultsArea = document.getElementById('resultsArea');
      const resultsContent = document.getElementById('resultsContent');
      resultsArea.style.display = 'block';
      resultsContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>リンクを生成しています...</p></div>';
      
      try {
        const formData = new FormData();
        formData.append('urls', urlList.join('\n'));
        
        const response = await fetch('/api/bulk-process', {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          throw new Error(`処理エラー: ${response.status}`);
        }
        
        const result = await response.json();
        showResults(result);
        
      } catch (error) {
        resultsContent.innerHTML = `<div class="error-item">エラーが発生しました: ${error.message}</div>`;
      } finally {
        generateBtns.forEach(btn => {
          btn.disabled = false;
          btn.textContent = '🚀 一括生成開始';
        });
      }
    }
    
    // 結果表示
    function showResults(result) {
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
        <div style="background: #e7f3ff; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
          <h3 style="margin: 0 0 15px 0; color: #1976d2;">📊 生成結果サマリー</h3>
          <p style="margin: 0; font-size: 16px;">
            成功: <strong style="color: #28a745;">${successCount}</strong> | 
            エラー: <strong style="color: #dc3545;">${errorCount}</strong> | 
            合計: <strong>${successCount + errorCount}</strong>
          </p>
        </div>
      `;
      
      if (result.results) {
        result.results.forEach((item, index) => {
          if (item.success) {
            html += `
              <div class="result-item">
                <p style="margin: 0 0 12px 0;"><strong>${index + 1}. 元URL:</strong> ${item.url}</p>
                <p style="margin: 0;">
                  <strong>短縮URL:</strong> 
                  <a href="${item.short_url}" target="_blank" style="color: #007bff; text-decoration: none;">${item.short_url}</a>
                  <button class="copy-btn" onclick="copyText('${item.short_url}')">📋 コピー</button>
                </p>
              </div>
            `;
          } else {
            html += `
              <div class="error-item">
                <p style="margin: 0;">❌ ${item.url} - ${item.error}</p>
              </div>
            `;
          }
        });
      }
      
      resultsContent.innerHTML = html;
    }
    
    // コピー機能
    function copyText(text) {
      navigator.clipboard.writeText(text).then(() => {
        alert(`クリップボードにコピーしました: ${text}`);
      }).catch(() => {
        prompt('以下のURLをコピーしてください:', text);
      });
    }
  </script>
</body>
</html>
