# Twix Saver

2025年版の高度なアンチ検知対策を備えたX.com（旧Twitter）スクレイピングシステム + React WebUI

## 🚀 主要機能

- **🌐 WebUI**: React + TypeScript による直感的な管理画面
- **🔄 リアルタイム**: WebSocket による進捗のリアルタイム更新
- **🤖 データベース駆動**: WebUI からジョブを作成・管理
- **🛡️ アンチ検知対策**: 多層的な検知回避システム
- **📊 データ可視化**: チャートとダッシュボードによる統計表示
- **🔍 高度な検索**: 全文検索・フィルタ・無限スクロール
- **📱 レスポンシブ**: デスクトップ・タブレット・モバイル対応

## 📁 プロジェクト構造

```
twix-saver/
├── frontend/              # React + TypeScript WebUI
│   ├── src/
│   │   ├── components/    # UIコンポーネント
│   │   ├── hooks/         # カスタムフック
│   │   ├── stores/        # Zustand状態管理
│   │   └── types/         # TypeScript型定義
│   └── package.json
├── backend/               # Python FastAPI バックエンド
│   ├── src/
│   │   ├── scrapers/      # スクレイピングエンジン
│   │   ├── services/      # ビジネスロジック
│   │   └── web/           # FastAPI アプリ
│   ├── scripts/           # 管理スクリプト
│   ├── main.py            # メイン実行スクリプト
│   └── requirements.txt
└── docs/                  # ドキュメント
```

## 🛡️ アンチ検知対策

1. **ネットワーク層**: レジデンシャルプロキシローテーション
2. **ブラウザ層**: playwright-stealth によるフィンガープリント対策
3. **行動層**: 人間らしい遅延とランダム化
4. **アカウント層**: 使い捨てアカウントプール管理
5. **緊急対応**: CAPTCHA解決サービス統合（オプション）

## 📋 システム要件

- **Python**: 3.9以上
- **Node.js**: 18以上
- **MongoDB**: 5.0以上
- **メモリ**: 最低2GB (4GB推奨)
- **ディスク**: 10GB以上の空き容量

## ⚡ クイックスタート

### 1. Docker Compose（推奨）

```bash
# 環境変数ファイルを作成
cp backend/.env.example backend/.env
# .envファイルを編集してTwitter認証情報を設定

# Docker Composeで全サービスを起動
docker-compose up -d

# ログ確認
docker-compose logs -f backend
```

### 2. 従来の開発環境セットアップ

```bash
# ルートディレクトリで依存関係をまとめてインストール
pnpm run setup

# バックエンドの環境設定ファイル作成
cd backend
cp .env.example .env
# .envファイルを編集してTwitter認証情報を設定

# MongoDB起動確認
mongosh --eval "db.runCommand({ping: 1})"
```

### 3. 開発サーバー起動（従来方式）

```bash
# Terminal 1: バックエンドAPI
pnpm run dev:backend

# Terminal 2: フロントエンド
pnpm run dev:frontend
```

### 3. 個別セットアップ（詳細制御が必要な場合）

```bash
# バックエンドのみ
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# フロントエンドのみ  
cd frontend
pnpm install

# 型定義生成
pnpm run generate-types
```

### 4. アクセス

- **WebUI**: http://localhost:5173
- **API ドキュメント**: http://localhost:8000/docs

## 🔧 使用方法

### WebUI経由（推奨）

1. http://localhost:5173 にアクセス
2. 「ユーザー管理」でスクレイピング対象を追加
3. 「ダッシュボード」で「新規ジョブ作成」をクリック
4. リアルタイムで進捗を監視

### コマンドライン

```bash
cd backend

# データベースの待機ジョブを実行
python main.py --run-jobs

# 特定ユーザーを直接スクレイピング（従来方式）
python main.py --users elonmusk jack

# データインジェストのみ
python main.py --ingest-only

# 統計情報表示
python main.py --stats
```
## 📝 設定ファイル（backend/.env）

```env
# MongoDB設定
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=twitter_scraper

# Twitterアカウント（使い捨てアカウント推奨）
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
TWITTER_EMAIL=your_email@example.com

# プロキシ設定（推奨）
PROXY_SERVER=proxy.example.com:8080
PROXY_USERNAME=proxy_user
PROXY_PASSWORD=proxy_pass

# CAPTCHA解決サービス（オプション）
CAPTCHA_SERVICE_API_KEY=your_2captcha_api_key
```

## 🔧 自動運用（systemd）

```bash
# systemd サービスインストール
./install_systemd.sh

# サービス状態確認
systemctl --user status twix-scraper.timer

# ログ確認
journalctl --user -u twix-scraper.service -f
```

## 🔧 高度な設定

### 複数アカウントプール

```env
# メインアカウント
TWITTER_USERNAME=account1
TWITTER_PASSWORD=password1
TWITTER_EMAIL=account1@example.com

# 追加アカウント
TWITTER_ACCOUNT_1_USERNAME=account2
TWITTER_ACCOUNT_1_PASSWORD=password2
TWITTER_ACCOUNT_1_EMAIL=account2@example.com

TWITTER_ACCOUNT_2_USERNAME=account3
TWITTER_ACCOUNT_2_PASSWORD=password3
TWITTER_ACCOUNT_2_EMAIL=account3@example.com
```

### プロキシ設定

レジデンシャルプロキシサービスの使用を強く推奨:

- [Bright Data](https://brightdata.com/)
- [NodeMaven](https://nodemaven.com/)
- [Smartproxy](https://smartproxy.com/)

```env
PROXY_SERVER=residential-proxy.provider.com:8000
PROXY_USERNAME=your_proxy_username
PROXY_PASSWORD=your_proxy_password
```

### CAPTCHA解決サービス

```env
CAPTCHA_SERVICE_API_KEY=your_2captcha_api_key
```

対応サービス:
- 2Captcha
- Anti-Captcha
- Bright Data CAPTCHA Solver

## 📊 WebUIの機能

### ダッシュボード
- システム統計の可視化
- リアルタイム進捗監視  
- クイックアクション

### ユーザー管理
- スクレイピング対象ユーザーの追加・編集・削除
- 一括操作（有効化・無効化）
- 検索・フィルタ機能

### ツイート表示
- 収集したツイートの検索・閲覧
- メディア・記事プレビュー
- 高度なフィルタリング（日付範囲、エンゲージメント等）

### ジョブ管理
- スクレイピングジョブの作成・監視
- リアルタイム進捗表示
- ログ確認

## 📊 データ構造

### MongoDB コレクション

#### tweets
```javascript
{
  "id_str": "1234567890",
  "username": "elonmusk",
  "text": "ツイート本文",
  "created_at": "2025-08-24T12:00:00Z",
  "public_metrics": {
    "like_count": 1500,
    "retweet_count": 300,
    "reply_count": 50
  },
  "media_urls": ["https://..."],
  "extracted_articles": [...]
}
```

#### scraping_jobs
```javascript
{
  "job_id": "uuid-string",
  "target_usernames": ["elonmusk", "jack"],
  "status": "completed",
  "stats": {
    "tweets_collected": 150,
    "articles_extracted": 25
  },
  "created_at": "2025-08-24T12:00:00Z"
}
```

## ⚠️ 重要な注意事項

### セキュリティ

1. **個人アカウントの使用禁止**: メインのTwitterアカウントは絶対に使用しないでください
2. **使い捨てアカウント**: スクレイピング専用のアカウントを作成してください
3. **プロキシの使用**: データセンターIPではなく、レジデンシャルプロキシを使用してください
4. **認証情報の管理**: `.env`ファイルをGitにコミットしないでください

### リーガル

1. **利用規約の確認**: X.com の利用規約を必ず確認してください
2. **レート制限の遵守**: 過度なリクエストは避けてください
3. **データの取り扱い**: 取得したデータの使用目的を明確にしてください

### パフォーマンス

1. **リソース監視**: メモリとCPU使用量を定期的に確認してください
2. **ディスク容量**: データの蓄積によりディスク容量が増加します
3. **ネットワーク**: プロキシサービスの帯域制限に注意してください

## 🐛 トラブルシューティング

### よくある問題

#### ログインエラー
```bash
# セッションファイルを削除して再試行
rm -rf sessions/
```

#### プロキシ接続エラー
```bash
# プロキシ設定を確認
echo $PROXY_SERVER
ping proxy.example.com
```

#### MongoDB接続エラー
```bash
# MongoDB起動状況確認
systemctl status mongodb
# または
systemctl status mongod
```

#### Playwright エラー
```bash
# ブラウザを再インストール
source venv/bin/activate
playwright install
playwright install-deps  # Linux
```

## 🔄 アップデート

```bash
# コードアップデート
git pull origin main

# 依存関係アップデート
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Playwrightブラウザ更新
playwright install

# systemdサービス再起動
systemctl --user daemon-reload
systemctl --user restart twix-scraper.timer
```

## 📈 監視とメトリクス

### 基本監視

```bash
# 統計確認
python main.py --stats

# リアルタイムログ
journalctl --user -u twix-scraper.service -f

# ディスク使用量
du -sh data/ logs/
```

### 高度な監視

- **MongoDB統計**: `db.tweets.stats()`
- **システムリソース**: `htop`, `iotop`
- **ネットワーク監視**: `nethogs`, `iftop`

## 🤝 貢献

1. Fork このリポジトリ
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

## 📝 ライセンス

このプロジェクトは研究・教育目的で公開されています。商用利用や大規模なデータ収集を行う前に、必ずX.comの利用規約を確認してください。

## 🙏 謝辞

- [Playwright](https://playwright.dev/) - モダンブラウザ自動化
- [playwright-stealth](https://github.com/Granitosaurus/playwright-stealth) - アンチ検知対策
- [readability-lxml](https://github.com/predatell/python-readability-lxml) - 記事抽出
- [MongoDB](https://www.mongodb.com/) - ドキュメントデータベース

---

**免責事項**: このツールは教育・研究目的で提供されます。利用者はX.comの利用規約および適用される法律を遵守する責任があります。