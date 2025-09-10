# LinkTrack Pro - URL短縮・分析プラットフォーム

## 概要
LinkTrack Proは、マーケティング効果測定のためのURL短縮・分析プラットフォームです。個人、企業のマーケティングキャンペーンでのURL管理を効率化します。

## 主要機能

### 🔗 URL短縮
- 長いURLを短く変換
- カスタム名・キャンペーン名の設定
- 即座にコピー可能

### 📊 分析・管理
- リアルタイムクリック数追跡
- ユニーク訪問者数計測
- 管理画面での一覧表示

### 📦 一括生成
- 複数URLの同時短縮
- スプレッドシート風のUI
- CSV形式でのデータ管理

## 技術スタック

- **バックエンド**: FastAPI (Python)
- **データベース**: SQLite
- **フロントエンド**: HTML/CSS/JavaScript
- **デプロイ**: Render.com

## GitHub + Render デプロイ手順

### 1. GitHubリポジトリ作成

```bash
# ローカルでGitリポジトリ初期化（任意）
git init
git add .
git commit -m "Initial commit"

# GitHubでリポジトリ作成後
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 2. Renderでの設定

#### Renderアカウント作成・ログイン
1. [Render.com](https://render.com) にアクセス
2. GitHubアカウントで連携

#### Web Service作成
1. ダッシュボードで「New +」→「Web Service」
2. GitHubリポジトリを選択
3. 以下の設定を入力：

```
Name: linktrack-pro (任意)
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

#### 環境変数設定
Renderの「Environment」タブで以下を設定：

```
RENDER_EXTERNAL_URL = https://YOUR_APP_NAME.onrender.com
```

### 3. デプロイ完了
- 自動でビルド・デプロイが開始
- 完了すると公開URLが発行される

## ローカル開発（任意）

```bash
# 依存関係インストール
pip install -r requirements.txt

# 開発サーバー起動
uvicorn main:app --reload

# ブラウザでアクセス
# http://localhost:8000
```

## ファイル構成

```
.
├── main.py              # メインアプリケーション
├── requirements.txt     # Python依存関係
├── .gitignore          # Git無視ファイル
├── README.md           # プロジェクト説明
└── url_shortener.db    # データベース（自動生成）
```

## API仕様

### 短縮URL生成
```
POST /api/shorten-form
Content-Type: application/x-www-form-urlencoded

url=https://example.com&custom_name=商品A&campaign_name=春キャンペーン
```

### 一括生成
```
POST /api/bulk-process
Content-Type: application/x-www-form-urlencoded

urls=https://example1.com
https://example2.com
```

### リダイレクト
```
GET /{short_code}
→ 302 Redirect to original URL
```

## データベーススキーマ

### urls テーブル
- `id`: 主キー
- `short_code`: 短縮コード（ユニーク）
- `original_url`: 元URL
- `custom_name`: カスタム名
- `campaign_name`: キャンペーン名
- `created_at`: 作成日時
- `is_active`: アクティブフラグ

### clicks テーブル
- `id`: 主キー
- `url_id`: URL ID（外部キー）
- `ip_address`: IPアドレス
- `user_agent`: ユーザーエージェント
- `referrer`: リファラー
- `clicked_at`: クリック日時

## 使用方法

### 1. 個別URL短縮
1. ホームページにアクセス
2. 「短縮したいURL」に入力
3. 「🔗 短縮URLを生成」をクリック
4. 結果をコピーして使用

### 2. 一括生成
1. 「📦 一括生成」メニューをクリック
2. スプレッドシート風の画面で複数URL入力
3. 「🚀 一括生成開始」で処理実行
4. 結果を一括取得

### 3. 分析・管理
1. 「📊 管理ダッシュボード」で全体統計確認
2. 個別URLの「📈 分析」でクリック詳細表示

## トラブルシューティング

### デプロイエラー
```
Failed to build: pip install failed
```
**対処法**: `requirements.txt`の依存関係を確認

### データベースエラー
```
no such table: urls
```
**対処法**: アプリケーション初回起動時に自動作成されるので、Renderを再デプロイ

### URL生成エラー
```
無効なURLです
```
**対処法**: URLが`http://`または`https://`で始まることを確認

## セキュリティ・制限事項

- SQLiteファイルデータベース（小規模利用向け）
- 短縮コードは6文字ランダム生成
- IPアドレス記録（匿名化推奨）
- Render無料プランの制限あり

## ライセンス

MIT License

## 作成者

FastAPI + Render.com MVPソリューション

---

**注意**: このMVPは開発・テスト用途向けです。商用利用の場合は、セキュリティ強化とスケーラビリティの検討が必要です。

---------------
# 🚀 GitHub + Render デプロイ完全ガイド

このガイドに従って、初心者でも確実にURL短縮サービスをデプロイできます。

## ✅ 事前準備

### 必要なアカウント
1. **GitHubアカウント** - [github.com](https://github.com)で作成
2. **Renderアカウント** - [render.com](https://render.com)で作成（GitHubと連携）

### 必要なファイル
以下4つのファイルをGitHubリポジトリに配置：
- `main.py` （メインアプリケーション）
- `requirements.txt` （依存関係）
- `.gitignore` （Git無視設定）
- `README.md` （説明書）

## 📂 STEP 1: GitHubリポジトリ作成

### 1-1. 新しいリポジトリ作成
1. [GitHub](https://github.com)にログイン
2. 右上「+」→「New repository」
3. 以下の設定：
   ```
   Repository name: url-shortener-mvp
   Description: URL短縮サービスMVP
   Public にチェック
   Add a README file にチェックしない
   ```
4. 「Create repository」をクリック

### 1-2. ファイルアップロード方法

#### 方法A: Web画面から直接アップロード
1. 作成したリポジトリページで「uploading an existing file」をクリック
2. 4つのファイル（main.py, requirements.txt, .gitignore, README.md）をドラッグ&ドロップ
3. コミットメッセージ: `Initial commit`
4. 「Commit changes」をクリック

#### 方法B: コマンドライン（上級者向け）
```bash
git clone https://github.com/YOUR_USERNAME/url-shortener-mvp.git
cd url-shortener-mvp
# ファイルをコピー
git add .
git commit -m "Initial commit"
git push origin main
```

## 🚀 STEP 2: Render設定

### 2-1. Renderアカウント作成
1. [render.com](https://render.com)にアクセス
2. 「Sign up」→「Continue with GitHub」
3. GitHubアカウントと連携

### 2-2. Web Service作成
1. Renderダッシュボードで「New +」ボタン
2. 「Web Service」を選択
3. 「Connect a repository」セクションで作成したリポジトリを選択
4. 「Connect」をクリック

### 2-3. 設定入力
以下の設定を**正確に**入力：

```
Name: url-shortener-mvp
Environment: Python 3
Branch: main
Root Directory: （空欄のまま）
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 2-4. プラン選択
- **Free** プランを選択（無料）
- 「Create Web Service」をクリック

## ⚙️ STEP 3: 環境変数設定

### 3-1. 環境変数追加
1. 作成されたサービスの「Environment」タブをクリック
2. 「Add Environment Variable」をクリック
3. 以下を入力：
   ```
   Key: RENDER_EXTERNAL_URL
   Value: https://YOUR_APP_NAME.onrender.com
   ```
   ※ YOUR_APP_NAMEは実際のアプリ名に変更

### 3-2. デプロイ開始
- 設定完了後、自動的にビルドが開始されます
- 「Events」タブでビルドログを確認できます

## ✅ STEP 4: デプロイ完了確認

### 4-1. ビルド成功確認
- 「Events」タブで以下が表示されればOK：
  ```
  Deploy live for service 'url-shortener-mvp'
  ```

### 4-2. アプリケーション動作確認
1. 発行されたURLにアクセス
2. ホームページが表示されることを確認
3. 「📦 一括生成」「📊 管理ダッシュボード」のリンク動作確認
4. 実際にURL短縮機能をテスト

## 🐛 トラブルシューティング

### エラー1: Build failed
```
Error: pip install failed
```
**原因**: requirements.txtの内容に誤りがある
**解決法**: 
1. GitHubで`requirements.txt`の内容を確認
2. 以下の通りであることを確認：
   ```
   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   python-multipart==0.0.6
   ```

### エラー2: Application failed to start
```
Error: ModuleNotFoundError: No module named 'main'
```
**原因**: main.pyファイルが見つからない
**解決法**: 
1. GitHubリポジトリに`main.py`があることを確認
2. Renderの「Settings」で「Root Directory」が空欄であることを確認

### エラー3: Start command failed
```
Error: uvicorn command not found
```
**原因**: Start Commandが間違っている
**解決法**: 
1. Renderの「Settings」で「Start Command」を確認
2. 以下の通りに修正：
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### エラー4: 502 Bad Gateway
**原因**: アプリケーションが正しく起動していない
**解決法**: 
1. 「Events」タブでエラーログを確認
2. コードに構文エラーがないかチェック
3. 必要に応じてGitHubのコードを修正してプッシュ

## 🔄 更新・修正方法

### コード修正時
1. GitHubでファイルを編集
2. コミット
3. Renderで自動的に再デプロイが開始されます

### 手動再デプロイ
1. Renderダッシュボードの「Manual Deploy」→「Deploy latest commit」

## 📋 デプロイ後のチェックリスト

- [ ] ホームページにアクセスできる
- [ ] URL短縮機能が動作する
- [ ] 短縮URLでリダイレクトされる
- [ ] 一括生成ページが表示される
- [ ] 管理画面でデータが表示される
- [ ] APIエンドポイント（/docs）にアクセスできる

## 🎯 成功時の確認URL

アプリが正常にデプロイされた場合、以下のURLで動作確認：

```
https://YOUR_APP_NAME.onrender.com/          # ホームページ
https://YOUR_APP_NAME.onrender.com/bulk      # 一括生成
https://YOUR_APP_NAME.onrender.com/admin     # 管理画面
https://YOUR_APP_NAME.onrender.com/docs      # API文書
https://YOUR_APP_NAME.onrender.com/health    # ヘルスチェック
```

## 💡 重要な注意点

### Render無料プランの制限
- **スリープ機能**: 15分間アクセスがないとアプリがスリープ
- **初回アクセス**: スリープ後の初回アクセスは30秒程度かかる場合あり
- **帯域制限**: 月100GBまで
- **ビルド時間**: 月500分まで

### データベースについて
- SQLiteファイルはアプリと同じディスクに保存
- 永続化されますが、定期的なバックアップ推奨
- 大量データにはPostgreSQLへの移行を検討

## 🆘 サポート情報

### Render公式ドキュメント
- [Renderヘルプセンター](https://render.com/docs)
- [Python デプロイガイド](https://render.com/docs/deploy-fastapi)

### よくある質問
**Q: デプロイ後にアクセスできない**
A: 数分待ってから再度アクセス。Renderの初回デプロイは時間がかかります。

**Q: データベースが初期化される**
A: アプリケーション再起動時は正常動作。データ永続化されています。

**Q: カスタムドメインを使いたい**
A: Render有料プランで可能。無料プランでは `onrender.com` サブドメインのみ。

---

**このガイドに従えば、技術初心者でも確実にURL短縮サービスをデプロイできます。**
