# 詳細セットアップガイド

このガイドでは、初めて GitHub Actions を使う方でも迷わないように、画像付きで手順を説明します。

---

## 前提知識

### GitHub Actions とは？

GitHub 上で自動実行されるプログラムです。「毎日決まった時間に実行」などの設定が可能で、無料枠内なら料金はかかりません。

### このBotの動作イメージ

```
毎日朝8時（日本時間）
  ↓
GitHub Actions が自動起動
  ↓
feed_bot.py が実行される
  ↓
RSS フィードを取得
  ↓
新着記事があれば Slack に投稿
  ↓
seen_entries.json を更新して Git にコミット
  ↓
完了（次の実行まで待機）
```

---

## ステップ1: GitHub アカウントの準備

### 1.1 アカウントがない場合

https://github.com/signup から無料アカウントを作成

### 1.2 このリポジトリを Fork

1. このリポジトリのページで右上の **Fork** ボタンをクリック
2. 「Create fork」をクリック
3. 自分のアカウントにコピーが作成されます

---

## ステップ2: Slack の準備

### 2.1 Slack Workspace の確認

- 自分が管理者権限を持つ Workspace が必要です
- ない場合は無料で作成できます: https://slack.com/get-started

### 2.2 Incoming Webhook の作成（詳細版）

#### a) Slack App を作成

1. https://api.slack.com/apps にアクセス
2. 右上の「Create New App」をクリック
3. **「From scratch」** を選択（テンプレートは使わない）
4. 以下を入力:
   - **App Name**: `Feed Bot`（任意の名前）
   - **Pick a workspace**: 投稿先の Workspace を選択
5. 「Create App」をクリック

#### b) Incoming Webhooks を有効化

1. 左メニューの「Features」→「Incoming Webhooks」をクリック
2. 右上のトグルを **On** に切り替え
3. ページ下部の「Add New Webhook to Workspace」をクリック
4. 投稿先チャンネルを選択（例: `#tech-news`）
   - なければ先に Slack で作成しておく
5. 「許可する」をクリック

#### c) Webhook URL をコピー

1. 「Webhook URL」という項目が表示されます
2. URL をクリップボードにコピー
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```
3. **この URL は秘密情報です！** GitHub の Public リポジトリには直接書かないこと

---

## ステップ3: GitHub の Secrets 設定

### 3.1 Secrets とは？

パスワードや API キーを安全に保存する機能です。Public リポジトリでも他人には見えません。

### 3.2 Webhook URL を登録

1. Fork した自分のリポジトリに移動
2. 上部タブの **Settings** をクリック（リポジトリの設定）
3. 左メニューの **Secrets and variables** → **Actions** をクリック
4. 「New repository secret」ボタンをクリック
5. 以下を入力:
   - **Name**: `SLACK_WEBHOOK_URL`（この名前は変更しないこと）
   - **Secret**: ステップ2でコピーした Webhook URL を貼り付け
6. 「Add secret」をクリック

### 3.3 確認

- Secrets のリストに `SLACK_WEBHOOK_URL` が表示されていれば OK
- 値は `***` で隠されます（正常）

---

## ステップ4: GitHub Actions の権限設定

### 4.1 Write 権限の付与

既読管理ファイル（`seen_entries.json`）を自動更新するため、Actions に書き込み権限が必要です。

1. リポジトリの **Settings** をクリック
2. 左メニューの **Actions** → **General** をクリック
3. 下部の「Workflow permissions」セクションを確認
4. **「Read and write permissions」** を選択
5. 「Save」をクリック

---

## ステップ5: 初回実行（テスト）

### 5.1 手動実行

1. リポジトリの **Actions** タブをクリック
2. 左メニューから「RSS Feed to Slack」を選択
3. 右上の「Run workflow」ボタンをクリック
4. ドロップダウンで「Run workflow」をもう一度クリック

### 5.2 実行ログの確認

1. 数秒後、ワークフローが開始されます
2. 表示されたワークフロー名をクリック
3. 「fetch-and-post」ジョブをクリック
4. ログが表示されます:
   ```
   📡 チェック中: Flutter Releases
     ✅ Flutter 3.41.0
   📡 チェック中: Swift.org Blog
     ✅ Swift 6.2 Released
   ...
   ✨ 完了: 15 件の新着記事を投稿しました
   ```

### 5.3 Slack で確認

- 指定したチャンネルに記事が投稿されていれば成功 🎉
- 初回は過去48時間分がまとめて投稿されます

---

## ステップ6: 自動実行の確認

### 6.1 スケジュール

- デフォルト: **毎日 朝8時（日本時間）**
- 変更したい場合は後述のカスタマイズを参照

### 6.2 動作確認

- 翌日の朝8時以降に Actions タブを確認
- 自動実行されていれば成功

### 6.3 通知設定（オプション）

GitHub から実行失敗の通知を受け取りたい場合:

1. 自分のプロフィール → **Settings**
2. **Notifications** → **Actions**
3. 通知方法を選択（Email / Web）

---

## カスタマイズ

### 実行時刻を変更

`.github/workflows/feed-bot.yml` を編集:

```yaml
schedule:
  - cron: '0 23 * * *'  # この行を変更
```

cron 記法の読み方:
```
分 時 日 月 曜日
0  23 *  *  *    ← UTC で 23時（日本時間 8時）
```

**よく使う設定**:

| 日本時間 | cron 設定 |
|---------|-----------|
| 朝6時   | `0 21 * * *` |
| 朝8時   | `0 23 * * *` |
| 昼12時  | `0 3 * * *` |
| 夕方18時 | `0 9 * * *` |
| 夜21時  | `0 12 * * *` |

**1日2回実行したい場合**:

```yaml
schedule:
  - cron: '0 23 * * *'  # 朝8時
  - cron: '0 9 * * *'   # 夕方18時
```

### フィードを追加・削除

`feed_bot.py` の `FEEDS` リストを編集:

```python
FEEDS = [
    # この形式で追加
    ("表示名", "フィードURL", "絵文字"),
    
    # 例: Flutter Community を追加
    ("Flutter Community", "https://medium.com/feed/flutter-community", "🔵"),
    
    # 不要なものは削除またはコメントアウト
    # ("iOS Dev Weekly", "https://iosdevweekly.com/issues.rss", "📰"),
]
```

**フィード URL の探し方**:

1. ブログのフッターや About ページで「RSS」「Feed」を探す
2. よくある URL パターン:
   - `/feed/`
   - `/rss/`
   - `/atom.xml`
   - `/feed.xml`
3. ブラウザで開いて XML が表示されれば OK

**絵文字の使い分け**:

- `🔵` Flutter/Dart 関連
- `🍎` iOS/Swift 関連
- `📰` ニュース・キュレーション
- `⚙️` ツール・ライブラリ
- 自由に変更可能

### 初回取得範囲の変更

`feed_bot.py` の設定:

```python
INITIAL_HOURS = 48  # 初回は過去48時間分
```

- 値を増やす → 初回により多くの記事が投稿される
- 値を減らす → 初回の投稿が少なくなる
- `0` にすると初回も新着のみ

---

## トラブルシューティング

### Q1. Actions が実行されない

**確認1**: Actions が有効か確認
- Settings → Actions → General
- 「Allow all actions and reusable workflows」が選択されているか

**確認2**: cron 設定の時刻
- 最初の実行は設定した時刻まで待つ必要がある
- 手動実行で動作確認する

### Q2. Slack に投稿されない

**確認1**: Webhook URL が正しいか
- Secrets に登録した URL を再確認
- Slack App が無効化されていないか

**確認2**: チャンネルが存在するか
- Webhook 作成時に選んだチャンネルが削除されていないか

**確認3**: Actions のログを確認
- `⚠️ Slack 投稿エラー` というメッセージがあれば URL が間違っている

### Q3. 同じ記事が何度も投稿される

**原因**: `seen_entries.json` の更新に失敗している

**解決**:
1. Settings → Actions → General
2. Workflow permissions を「Read and write permissions」に変更
3. 次回実行時から正常になる

### Q4. フィードが取得できない

**確認1**: URL が正しいか
- ブラウザで URL を開いて XML が表示されるか

**確認2**: サイトがダウンしていないか
- Actions のログで「フィード取得エラー」が出ている場合
- 時間をおいて再度実行

**確認3**: フィードが廃止されていないか
- 古いブログは RSS を停止している場合がある
- FEEDS リストから削除

### Q5. 実行時間が長い・タイムアウトする

**原因**: フィード数が多すぎる

**解決**:
- 本当に必要なフィードだけに絞る
- 更新頻度の低いフィードは削除

---

## セキュリティに関する注意

### ✅ やってはいけないこと

- Webhook URL をコードに直接書く
- Webhook URL を GitHub Issues/PR に貼り付ける
- リポジトリを Public にして Secrets を使わない

### ✅ 推奨事項

- Secrets を使う（必須）
- 定期的に Webhook URL を再生成
- 不要になった Slack App は削除

---

## さらに学ぶには

### GitHub Actions の公式ドキュメント

https://docs.github.com/ja/actions

### cron 記法の練習

https://crontab.guru/

### RSS フィードの探し方

- 提供した `feed_sources.md` を参照
- Feedly などの RSS リーダーで探す

---

## サポート

問題が解決しない場合:

1. GitHub の Issues で質問
2. Actions のログ全体をコピーして添付
3. どのステップで詰まったかを明記

---

お疲れさまでした！これで完全無料の情報収集 Bot が完成です 🎉
