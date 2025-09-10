# Link_shortcut_flow_analysis

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
