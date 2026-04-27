# Slack 情報収集 Bot 用ソースカタログ
## Flutter / Dart / Swift / iOS

> **最終更新**: 2026-04-27
> **設計方針**: 公式 > GitHub API > 良質な個人ブログ > その他コミュニティ
> **凡例**: ⭐ 必須 / ◯ 推奨 / △ 興味があれば

---

## 🟦 Flutter / Dart 系

### A. 公式リリース・アナウンスメント (即時通知すべき)

| 優先度 | ソース | URL | 種別 | 推奨頻度 |
|---|---|---|---|---|
| ⭐ | Flutter releases (GitHub) | `https://github.com/flutter/flutter/releases.atom` | Atom | 30分 |
| ⭐ | Dart SDK releases (GitHub) | `https://github.com/dart-lang/sdk/releases.atom` | Atom | 30分 |
| ⭐ | Flutter Engine releases | `https://github.com/flutter/engine/releases.atom` | Atom | 1時間 |
| ⭐ | flutter-announce (Google Group) | `https://groups.google.com/g/flutter-announce/feed/atom_v1_0_msgs.xml` | Atom | 1時間 |
| ⭐ | Dart Announce (Google Group) | `https://groups.google.com/g/announce/feed/atom_v1_0_msgs.xml` | Atom | 1時間 |
| ⭐ | 公式 Flutter ブログ (Medium) | `https://medium.com/feed/flutter` | RSS | 6時間 |
| ◯ | Dart 公式ブログ (Medium) | `https://medium.com/feed/dartlang` | RSS | 6時間 |
| ◯ | Flutter Releases ダッシュボード | `https://flutterreleases.com/` (RSS あり) | RSS | 1時間 |

### B. GitHub - PR/Issue 監視 (バージョンに何が入るか追跡)

GitHub Search API を使う想定。基本クエリは `is:pr is:merged repo:flutter/flutter` を起点にラベル/マイルストーンで絞る。

| 優先度 | 監視対象 | クエリ例 | 推奨頻度 |
|---|---|---|---|
| ⭐ | Flutter フレームワークの直近マージ PR | `repo:flutter/flutter is:pr is:merged sort:updated-desc` | 6時間 |
| ⭐ | 次バージョンのマイルストーン | `repo:flutter/flutter is:pr milestone:"3.42"` (バージョンは適宜) | 1日1回 |
| ◯ | iOS/macOS 関連 PR | `repo:flutter/flutter is:pr is:merged label:"platform-ios"` | 6時間 |
| ◯ | Breaking change ラベル | `repo:flutter/flutter is:issue is:closed label:"severe: API break"` | 1日1回 |
| △ | Hot reload / DevTools の変更 | `repo:flutter/flutter is:pr is:merged label:"d: api docs"` | 1日1回 |

> **Tip**: マージされた PR の本文には通常、対象マイルストーン（≒ 入るバージョン）が記載されている。GitHub API の `pull` エンドポイントから `milestone.title` を取得すると確実。

### C. pub.dev - パッケージ更新監視

| 優先度 | ソース | URL | 用途 |
|---|---|---|---|
| ◯ | pub.dev Atom (パッケージ別) | `https://pub.dev/feed.atom` | 全体 |
| ◯ | パッケージ個別 changelog | `https://pub.dev/packages/<name>/changelog` を fetch | 自分が依存するパッケージ |

### D. コミュニティ・キュレーション系

| 優先度 | ソース | URL | 特徴 |
|---|---|---|---|
| ⭐ | Code with Andrea | `https://codewithandrea.com/rss.xml` | GDE。実装重視で質が高い |
| ◯ | Flutter Community (Medium) | `https://medium.com/feed/flutter-community` | コミュニティ寄稿 |
| ◯ | Resocoder | `https://resocoder.com/feed/` | アーキテクチャ系 |
| ◯ | Flutter Awesome | `https://flutterawesome.com/rss.xml` | 新規パッケージ・サンプル |
| △ | Codemagic blog | `https://blog.codemagic.io/rss/` | CI/CD 視点 |

---

## 🟥 Swift / iOS 系

### A. 公式リリース・アナウンスメント (即時通知すべき)

| 優先度 | ソース | URL | 備考 |
|---|---|---|---|
| ⭐ | Swift.org ブログ | `https://www.swift.org/atom.xml` | 言語アップデートの一次ソース |
| ⭐ | Apple Developer News | `https://developer.apple.com/news/rss/news.rss` | β/正式リリース、ガイドライン変更 |
| ⭐ | Swift releases (GitHub) | `https://github.com/swiftlang/swift/releases.atom` | コンパイラリリース |
| ⭐ | Apple Newsroom | `https://www.apple.com/newsroom/rss-feed.rss` | 製品発表・WWDC告知 |
| ⭐ | Apple Security Releases | `https://developer.apple.com/news/releases/rss/releases.rss` | OS/Xcode β含むリリース履歴 |
| ◯ | Apple Security Blog | `https://security.apple.com/blog/rss/` | セキュリティ詳細 |

### B. Swift Evolution 監視 (言語仕様の変化)

これが Swift のキモ。Proposal の状態変化が言語の未来を予告する。

| 優先度 | 監視対象 | 方法 | 頻度 |
|---|---|---|---|
| ⭐ | Swift Evolution proposals | `https://github.com/swiftlang/swift-evolution` のコミット監視 | 1日2回 |
| ⭐ | Accepted proposals | `data.swift.org/swift-evolution/proposals` JSON を取得して状態差分検出 | 1日1回 |
| ⭐ | Swift Forums - Evolution | `https://forums.swift.org/c/evolution/18.rss` | 6時間 |
| ◯ | Swift Forums - Announcements | `https://forums.swift.org/c/announcements/6.rss` | 1時間 |

> **Tip**: Swift Evolution の proposal は GitHub 上で `proposals/NNNN-*.md` のファイル名と冒頭メタ情報（`Status: Accepted` など）で管理されている。新規ファイル追加と Status 行の差分を取れば、新規提案・状態変化を完全に追える。

### C. SwiftUI / フレームワーク系の公式ドキュメント

| 優先度 | ソース | URL | 用途 |
|---|---|---|---|
| ◯ | Apple Developer Documentation Updates | (RSS なし、API Differences ページを定期 fetch) | API 差分検出 |
| ◯ | Xcode リリースノート | `https://developer.apple.com/documentation/xcode-release-notes` を定期 fetch | β情報 |

### D. 良質な個人ブログ（必須レベル）

iOS は公式が薄いのでブログ依存度が高い。以下は10年以上続いている信頼ソース。

| 優先度 | ブログ | URL | 著者・特徴 |
|---|---|---|---|
| ⭐ | Hacking with Swift | `https://www.hackingwithswift.com/articles/rss` | Paul Hudson。最新OS対応が早い |
| ⭐ | Swift by Sundell | `https://www.swiftbysundell.com/feed/` | John Sundell。深い設計論 |
| ⭐ | SwiftLee | `https://www.avanderlee.com/feed/` | Antoine van der Lee。Concurrency に強い |
| ⭐ | NSHipster | `https://nshipster.com/feed.xml` | Mattt Thompson。隠れたAPI詳説 |
| ⭐ | Donny Wals | `https://www.donnywals.com/feed/` | 並行性・SwiftUI |
| ⭐ | Point-Free | `https://www.pointfree.co/blog/rss.xml` | 関数型 / TCA |
| ⭐ | iOS Dev Weekly | `https://iosdevweekly.com/issues.rss` | Dave Verwer。週刊キュレーション |
| ◯ | Mike Ash (NSBlog) | `https://www.mikeash.com/pyblog/rss.py` | 低レイヤ |
| ◯ | Ole Begemann | `https://oleb.net/blog/atom.xml` | 言語仕様の深い考察 |
| ◯ | SwiftRocks | `https://swiftrocks.com/rss.xml` | Bruno Rocha |
| ◯ | Jacob's Tech Tavern | `https://jacobbartlett.substack.com/feed` | 実務話 |
| ◯ | Matt Massicotte | `https://www.massicotte.org/feed.xml` | Concurrency の第一人者 |
| ◯ | Cocoa with Love | `https://www.cocoawithlove.com/atom.xml` | Matt Gallagher。アーキテクチャ |
| ◯ | Michael Tsai | `https://mjtsai.com/blog/feed/` | Apple ニュースまとめ |
| △ | The.Swift.Dev | `https://theswiftdev.com/rss.xml` | Tibor Bodecs |
| △ | Swift with Vincent | `https://www.swiftwithvincent.com/rss` | 短い実践ネタ |
| △ | Kodeco (旧 Ray Wenderlich) | `https://www.kodeco.com/feed.xml` | 入門〜中級 |
| △ | AppCoda | `https://feeds.feedburner.com/appcoda` | チュートリアル |

### E. ニュースレター / キュレーション

| 優先度 | ソース | URL | 配信 |
|---|---|---|---|
| ⭐ | iOS Dev Weekly | `https://iosdevweekly.com/issues.rss` | 毎週金曜 |
| ◯ | Indie iOS Focus Weekly | (メール購読推奨) | 毎週 |
| ◯ | iOS Goodies | `https://ios-goodies.com/rss` | 毎週 |
| ◯ | iOS Feeds (アグリゲータ) | `https://iosfeeds.com/` | 800+ ソース集約 |

### F. WWDC / 季節性の高いソース

WWDC（毎年6月）前後だけ重み付けを上げる運用が良い。

| ソース | URL | 期間 |
|---|---|---|
| WWDC By Sundell | `https://wwdcbysundell.com/feed/` | 6-7月のみ重要 |
| WWDC Notes | `https://wwdcnotes.com/` (RSSなし) | 6-7月 |
| Apple Developer Videos | `https://developer.apple.com/videos/all-videos/?q=` | β含む |

---

## 🟩 横断的・関連技術

| 優先度 | ソース | URL | 用途 |
|---|---|---|---|
| ◯ | Hacker News - Swift | `https://hnrss.org/newest?q=swift+ios&points=50` | コミュニティの注目 |
| ◯ | Hacker News - Flutter | `https://hnrss.org/newest?q=flutter+dart&points=50` | 同上 |
| ◯ | Reddit r/iOSProgramming | `https://www.reddit.com/r/iOSProgramming/.rss` | 議論 |
| ◯ | Reddit r/FlutterDev | `https://www.reddit.com/r/FlutterDev/.rss` | 議論 |
| △ | Stack Overflow タグ | `https://stackoverflow.com/feeds/tag?tagnames=swift` | 質問動向 |

---

## 推奨 Slack チャンネル設計

```
#flutter-releases    ⭐ 公式リリース系（A 優先度⭐すべて）
#flutter-prs         ◯ GitHub PR/Issue 監視（B）
#flutter-articles    ◯ コミュニティブログ（D）日次ダイジェスト

#ios-releases        ⭐ Apple/Swift 公式リリース（A 優先度⭐すべて）
#ios-evolution       ⭐ Swift Evolution 状態変化（B）
#ios-articles-daily  ◯ 良質ブログ日次ダイジェスト（D）
#ios-weekly          ◯ iOS Dev Weekly など週次（E）

#dev-news-hn         △ HN/Reddit 横断（任意）
```

---

## 実装上の注意

**1. Medium の RSS は不安定**
Medium はたまに RSS を止めるので、`@username/feed` 形式で複数パターンを試せるようにしておく。

**2. Google Groups の RSS**
`flutter-announce` などの Google Groups は Atom フィードがあるが、購読数によっては取得制限がある。フォールバックとして週1回の Web fetch を用意。

**3. GitHub Releases.atom は削除に注意**
プレリリースが多いリポジトリでは `?per_page=10` のような細かい制御ができないので、Python 側でタグの prefix（例: `v3.41`）でフィルタリングする。

**4. ノイズ削減のキー**
- 公式リリースは「stable のみ通知、β/dev はオプトイン」
- ブログ系は1日1回ダイジェストにまとめる（即時通知は集中力を奪う）
- AI 要約は文字数で判定（短い記事はそのまま、長い記事だけ要約）

**5. 優先度⭐だけでまず始める**
全部入れると最初から疲れる。⭐印（Flutter 8件 + iOS 16件 = 24件）でまず1ヶ月運用し、欲しい情報が漏れている箇所を◯から足す。

---

## 次のステップ候補

1. このリストから最初に試す10件程度を選び、最小コードで取得して Slack に流す
2. OPML ファイルに変換して RSS リーダーにも併用できるようにする
3. GitHub API トークンを発行して PR 監視部分を実装する
4. AI 要約レイヤーを後から足す（最初はタイトル＋リンクだけで十分価値がある）
