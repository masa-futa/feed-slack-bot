# リポジトリ構成の説明

```
feed-slack-bot/
├── .github/
│   └── workflows/
│       └── feed-bot.yml          # GitHub Actions のワークフロー定義
├── .gitignore                     # Git 管理対象外のファイル指定
├── LICENSE                        # ライセンス（MIT）
├── README.md                      # プロジェクト概要・クイックスタート
├── SETUP_GUIDE.md                 # 詳細セットアップ手順
├── feed_bot.py                    # メインスクリプト（RSS取得→Slack投稿）
├── requirements.txt               # Python 依存ライブラリ
├── seen_entries.json              # 既読管理ファイル（自動更新される）
└── REPOSITORY_STRUCTURE.md        # このファイル
```

## 各ファイルの役割

### `.github/workflows/feed-bot.yml`
GitHub Actions の設定ファイル。以下を定義:
- 実行スケジュール（デフォルト: 毎日 朝8時 JST）
- Python 環境のセットアップ
- スクリプト実行
- 既読ファイルの Git コミット

### `feed_bot.py`
メインロジック:
1. 環境変数 `SLACK_WEBHOOK_URL` から Webhook URL を取得
2. `FEEDS` リストに定義された RSS/Atom フィードを順に取得
3. `seen_entries.json` と照合して新着のみ抽出
4. Slack に投稿
5. 既読情報を更新

### `seen_entries.json`
既読管理ファイル。形式:
```json
{
  "https://example.com/article1": true,
  "https://example.com/article2": true,
  ...
}
```
- キー: 記事の URL（ユニーク ID）
- 値: `true`（既読フラグ）
- GitHub Actions が自動で Git にコミット

### `requirements.txt`
Python ライブラリの依存関係:
- `feedparser`: RSS/Atom フィードのパース
- `requests`: HTTP リクエスト（Slack への POST）

### `README.md`
- プロジェクト概要
- 特徴
- クイックスタート
- カスタマイズ方法
- トラブルシューティング

### `SETUP_GUIDE.md`
- 初心者向けの詳細手順
- GitHub Actions の仕組み解説
- Slack Webhook の作成方法
- cron 記法の説明
- よくある問題と解決策

## データフロー

```
GitHub Actions (スケジュール)
  ↓
feed_bot.py 実行
  ↓
各フィードから RSS/Atom を取得
  ↓
seen_entries.json と照合
  ↓
新着記事のみ抽出
  ↓
Slack に Block Kit 形式で投稿
  ↓
seen_entries.json を更新
  ↓
Git commit & push
```

## カスタマイズのポイント

### 実行頻度を変更
`.github/workflows/feed-bot.yml` の `cron` を編集

### フィードを追加・削除
`feed_bot.py` の `FEEDS` リストを編集

### 投稿先チャンネルを変更
Slack で新しい Webhook を作成し、Secrets を更新

### メッセージフォーマットを変更
`feed_bot.py` の `format_slack_message()` 関数を編集

## セキュリティ

- Webhook URL は GitHub Secrets で管理（コードに直接書かない）
- Public リポジトリでも Secrets は他人に見えない
- 定期的に Webhook URL を再生成することを推奨

## コスト

- **GitHub Actions**: 無料（Public リポジトリ）or 無料枠内（Private）
- **Slack Webhook**: 無料
- **RSS フィード**: 無料
- **合計: 0円**

## 次のステップ

1. Fork してセットアップ（SETUP_GUIDE.md 参照）
2. 自分の興味に合わせてフィードをカスタマイズ
3. 運用しながら「欲しい情報が漏れている」箇所を追加
4. AI 要約が欲しくなったら Claude API を後から追加（別料金）

## サポート

- Issues: バグ報告・機能要望
- Discussions: 使い方の質問
- Pull Requests: フィード追加などの貢献歓迎
