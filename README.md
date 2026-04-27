# RSS Feed to Slack Bot

Flutter/Dart と Swift/iOS の最新情報を自動で Slack に投稿する Bot です。

GitHub Actions で **完全無料** で運用できます（1日1回実行）。

---

## 🎯 特徴

- ✅ **完全無料**: GitHub Actions の無料枠内で動作
- ✅ **AI 不要**: RSS 取得のみなので Claude API など不要
- ✅ **ノイズなし**: 既読管理で同じ記事を何度も通知しない
- ✅ **カスタマイズ可能**: フィード追加・削除が簡単
- ✅ **1日1回**: 朝8時（JST）にまとめて配信

---

## 📡 デフォルトで監視しているソース

### Flutter/Dart 系
- Flutter 公式リリース
- Dart SDK リリース
- Flutter 公式ブログ (Medium)

### Swift/iOS 系
- Swift.org 公式ブログ
- Apple Developer News
- Hacking with Swift
- SwiftLee
- Swift by Sundell
- NSHipster
- Donny Wals
- iOS Dev Weekly

---

## 🚀 セットアップ（10分）

### 1. このリポジトリを Fork

右上の「Fork」ボタンをクリック

### 2. Slack の Incoming Webhook を作成

1. https://api.slack.com/apps にアクセス
2. 「Create New App」→「From scratch」
3. App Name: 例えば「Feed Bot」
4. Workspace を選択
5. 左メニュー「Incoming Webhooks」をクリック
6. 「Activate Incoming Webhooks」を **On**
7. 「Add New Webhook to Workspace」をクリック
8. 投稿先チャンネル（例: `#tech-news`）を選択
9. 表示された Webhook URL をコピー
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```

### 3. GitHub の Secrets に Webhook URL を登録

1. Fork した自分のリポジトリに移動
2. **Settings** → **Secrets and variables** → **Actions** をクリック
3. 「New repository secret」をクリック
4. 以下を入力:
   - **Name**: `SLACK_WEBHOOK_URL`
   - **Secret**: ステップ2でコピーした Webhook URL
5. 「Add secret」をクリック

### 4. 動作確認

#### 手動実行でテスト

1. リポジトリの **Actions** タブを開く
2. 左メニューから「RSS Feed to Slack」を選択
3. 右上の「Run workflow」→「Run workflow」をクリック
4. 数十秒後、Slack にメッセージが届けば成功 🎉

#### 自動実行の確認

- **毎日 朝8時（JST）** に自動実行されます
- 初回は過去48時間分の記事が投稿されます
- 2回目以降は新着のみ投稿されます

---

## ⚙️ カスタマイズ

### 実行時刻を変更

`.github/workflows/feed-bot.yml` の `cron` を編集:

```yaml
schedule:
  - cron: '0 23 * * *'  # UTC 23:00 = JST 8:00
```

| 日本時間 | UTC (cron) |
|---------|-----------|
| 6:00    | `0 21 * * *` |
| 8:00    | `0 23 * * *` |
| 12:00   | `0 3 * * *` |
| 18:00   | `0 9 * * *` |
| 21:00   | `0 12 * * *` |

### フィードを追加・削除

`feed_bot.py` の `FEEDS` リストを編集:

```python
FEEDS = [
    # 新しいフィードを追加
    ("ブログ名", "https://example.com/feed.xml", "🔵"),
    
    # 不要なフィードはコメントアウトまたは削除
    # ("Flutter Blog", "https://medium.com/feed/flutter", "🔵"),
]
```

絵文字の意味:
- `🔵` Flutter/Dart 系
- `🍎` Swift/iOS 系
- `📰` ニュース・キュレーション系

### 複数の Slack チャンネルに投稿

1チャンネルごとに Webhook URL が必要です。

**方法1**: リポジトリを複数作る（推奨）
- `feed-bot-flutter` → `#flutter-news`
- `feed-bot-ios` → `#ios-news`

**方法2**: スクリプトを拡張
- Secrets に複数の URL を登録
- カテゴリごとに投稿先を切り替える実装を追加

---

## 📊 コスト

| 項目 | 費用 |
|-----|------|
| GitHub Actions | **無料** (Public リポジトリ) |
| Slack Webhook | **無料** |
| RSS フィード | **無料** |
| **合計** | **0円** |

**Private リポジトリの場合**:
- 無料枠: 月 2000分
- この Bot の実行時間: 1回 約30秒
- 1日1回なら 月15分 → 無料枠内 ✅

---

## 🔧 トラブルシューティング

### Slack に投稿されない

1. Actions タブでエラーログを確認
2. Webhook URL が正しいか確認
3. Slack App が無効化されていないか確認

### 同じ記事が何度も投稿される

`seen_entries.json` が Git にコミットされているか確認:
```bash
git log --oneline | grep "Update seen entries"
```

表示されない場合、Actions の権限を確認:
- **Settings** → **Actions** → **General**
- **Workflow permissions** を「Read and write permissions」に変更

### フィードが取得できない

- RSS/Atom URL が正しいか確認
- ブラウザで URL を開いて XML が表示されるか確認
- サイトが一時的にダウンしている可能性

---

## 📝 ライセンス

MIT License

---

## 🙏 参考記事

この Bot は以下の記事からインスパイアされました:

- [Claude Codeで日常のタスクを45個自動化した東大院生の全記録](https://zenn.dev/shunya_sudo/articles/claude-code-45-automation-tasks)

---

## 🤝 コントリビューション

- フィード追加の PR 歓迎
- Issue でバグ報告・機能要望も歓迎
