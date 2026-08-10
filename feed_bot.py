#!/usr/bin/env python3
"""
RSS → Slack Bot (GitHub Actions 版) — 曜日ローテーション版

コンセプト:
- 公式リリース・報道記事は対象外。個人が一次体験から書いたものだけを拾う。
- 1日1カテゴリだけを担当させ、週1回・濃密な投稿にする。
- 曜日: 月=経営(個人の自論) / 火=モバイル / 水=AI活用術(個人の実装記事)
        木=経営(個人の自論) / 金=デザイン・文化(個人の声) / 土=読書 / 日=振り返りリマインド
- 既存の4チャンネル(mobile/design/ai/tools)をそのまま再利用。新規チャンネル不要。
"""

import feedparser
import requests
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

# ==================== 設定 ====================

BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

# チャンネルID(環境変数から取得)
CHANNEL_MOBILE = os.environ.get("SLACK_CHANNEL_MOBILE", "")
CHANNEL_DESIGN = os.environ.get("SLACK_CHANNEL_DESIGN", "")   # → デザイン・文化(個人の声)に転用
CHANNEL_AI = os.environ.get("SLACK_CHANNEL_AI", "")
CHANNEL_TOOLS = os.environ.get("SLACK_CHANNEL_TOOLS", "")     # → 経営・読書・振り返りに転用

JST = timezone(timedelta(hours=9))

# ============================================
# 曜日ローテーション設定
# Python の weekday(): 月=0, 火=1, 水=2, 木=3, 金=4, 土=5, 日=6
# ============================================
WEEKDAY_CATEGORIES = {
    0: ["management"],                                # 月: 経営・経済(個人の自論)
    1: ["flutter", "swift", "android", "mobile_rn"],  # 火: モバイル全般
    2: ["ai_practice"],                               # 水: AI活用術(個人の実装記事のみ)
    3: ["management"],                                # 木: 経営・経済(月と同カテゴリ)
    4: ["culture_design"],                             # 金: デザイン・文化(個人の声)
    5: ["culture_reading"],                            # 土: 読書
    6: [],                                             # 日: 振り返りリマインドのみ
}

WEEKDAY_NAMES_JA = ["月", "火", "水", "木", "金", "土", "日"]

SUNDAY_REMINDER = (
    "🗒️ 今週の振り返りタイム\n"
    "今週インプットした中で一番刺さったトピックを1つ選んで、"
    "「結論→根拠→打ち手」で1枚メモにまとめてみましょう。"
)

# ============================================
# RSS / Atom フィード定義
# (name, url, category, emoji, channel)
# ============================================
FEEDS = [
    # ============================================
    # 📱 モバイル開発系(火曜)
    # ============================================
    # Flutter & Dart
    ("Flutter Releases", "https://github.com/flutter/flutter/releases.atom", "flutter", "🚀", "mobile"),
    ("Dart SDK Releases", "https://github.com/dart-lang/sdk/releases.atom", "flutter", "🎯", "mobile"),
    ("Flutter Blog", "https://medium.com/feed/flutter", "flutter", "📝", "mobile"),
    ("Flutter Community", "https://medium.com/feed/flutter-community", "flutter", "💎", "mobile"),
    ("Code with Andrea", "https://codewithandrea.com/rss.xml", "flutter", "🎓", "mobile"),
    ("Riverpod Releases", "https://github.com/rrousselGit/riverpod/releases.atom", "flutter", "🔗", "mobile"),
    ("Freezed Releases", "https://github.com/rrousselGit/freezed/releases.atom", "flutter", "❄️", "mobile"),
    ("Flutter Packages", "https://github.com/flutter/packages/releases.atom", "flutter", "📦", "mobile"),

    # Swift & iOS
    ("Swift.org Blog", "https://www.swift.org/atom.xml", "swift", "⚡️", "mobile"),
    ("Apple Developer News", "https://developer.apple.com/news/rss/news.rss", "swift", "🍎", "mobile"),
    ("Hacking with Swift", "https://www.hackingwithswift.com/articles/rss", "swift", "💻", "mobile"),
    ("SwiftLee", "https://www.avanderlee.com/feed/", "swift", "🎨", "mobile"),
    ("Swift by Sundell", "https://www.swiftbysundell.com/feed/", "swift", "💡", "mobile"),
    ("NSHipster", "https://nshipster.com/feed.xml", "swift", "🔍", "mobile"),
    ("Donny Wals", "https://www.donnywals.com/feed/", "swift", "📚", "mobile"),
    ("Point-Free", "https://www.pointfree.co/blog/rss.xml", "swift", "🎯", "mobile"),
    ("Swift with Vincent", "https://www.swiftwithvincent.com/blog/rss.xml", "swift", "🛠️", "mobile"),
    ("iOS Dev Weekly", "https://iosdevweekly.com/issues.rss", "swift", "📰", "mobile"),
    ("Swift Evolution", "https://forums.swift.org/c/evolution/18.rss", "swift", "📜", "mobile"),

    # Android & Kotlin
    ("Android Developers Blog", "https://android-developers.googleblog.com/feeds/posts/default", "android", "🤖", "mobile"),
    ("Kotlin Blog", "https://blog.jetbrains.com/kotlin/feed/", "android", "💡", "mobile"),
    ("Android Weekly", "https://androidweekly.net/rss", "android", "📰", "mobile"),
    ("Joe Birch", "https://joebirch.co/feed/", "android", "🎯", "mobile"),
    ("Styling Android", "https://blog.stylingandroid.com/feed/", "android", "🎨", "mobile"),
    ("Compose Releases", "https://github.com/JetBrains/compose-multiplatform/releases.atom", "android", "🔷", "mobile"),
    ("Philipp Lackner", "https://pl-coding.com/feed/", "android", "📝", "mobile"),
    ("Chris Banes", "https://chris.banes.dev/rss.xml", "android", "🏗️", "mobile"),
    ("Android Studio Blog", "https://blog.jetbrains.com/android/feed/", "android", "🛠️", "mobile"),

    # React Native(新規)
    ("React Native Blog", "https://reactnative.dev/blog/rss.xml", "mobile_rn", "⚛️", "mobile"),

    # ============================================
    # 🧠 AI活用術(水曜)— 公式リリース情報は対象外
    # ============================================
    ("Simon Willison", "https://simonwillison.net/atom/everything/", "ai_practice", "✨", "ai"),
    ("Anthropic Engineering", "https://www.anthropic.com/engineering/rss.xml", "ai_practice", "🔧", "ai"),
    ("Medium - Claude", "https://medium.com/feed/tag/claude", "ai_practice", "🤖", "ai"),
    ("Medium - Claude Code", "https://medium.com/feed/tag/claude-code", "ai_practice", "💻", "ai"),
    ("Medium - GitHub Copilot", "https://medium.com/feed/tag/github-copilot", "ai_practice", "🐙", "ai"),
    ("Medium - Cursor", "https://medium.com/feed/tag/cursor", "ai_practice", "🖱️", "ai"),
    ("Medium - Prompt Engineering", "https://medium.com/feed/tag/prompt-engineering", "ai_practice", "✏️", "ai"),
    ("Medium - LLM", "https://medium.com/feed/tag/large-language-models", "ai_practice", "📚", "ai"),
    ("Medium - AI Agents", "https://medium.com/feed/tag/ai-agents", "ai_practice", "🕵️", "ai"),
    ("Medium - Codex", "https://medium.com/feed/tag/openai-codex", "ai_practice", "📋", "ai"),

    # ============================================
    # 💼 経営・経済(月・木)— 個人の一次体験ベースのエッセイ
    # ============================================
    ("Medium - Startup", "https://medium.com/feed/tag/startup", "management", "📝", "tools"),
    ("Medium - Entrepreneurship", "https://medium.com/feed/tag/entrepreneurship", "management", "💡", "tools"),
    ("Medium - Business Strategy", "https://medium.com/feed/tag/business-strategy", "management", "♟️", "tools"),

    # ============================================
    # 🎨 デザイン・文化(金)— 好きな書き手を直接フォロー
    # 汎用ハッシュタグではなく個人アカウントを直接指定
    # ============================================
    ("goyemon - 武内賢太", "https://note.com/ken_ta_keuchi/rss", "culture_design", "🎨", "design"),
    ("goyemon - 大西藍(yuki)", "https://note.com/yuki_goyemon/rss", "culture_design", "🏛️", "design"),
    # 気になる書き手が増えたら同じ形式で1行ずつ追加:
    # ("表示名", "https://note.com/ユーザー名/rss", "culture_design", "絵文字", "design"),

    # ============================================
    # 📚 読書(土)— 要検証
    # ============================================
    ("HONZ書評", "https://honz.jp/feed", "culture_reading", "📚", "tools"),
]

# ============================================
# Zenn API ソース定義(RSS ではなく JSON API を直接叩く)
# (display_name, topic, emoji, channel, category)
# ============================================
ZENN_SOURCES = [
    # AI活用術
    ("Zenn - Claude Code", "claudecode", "💻", "ai", "ai_practice"),
    ("Zenn - Claude", "claude", "🤖", "ai", "ai_practice"),
    ("Zenn - GitHub Copilot", "githubcopilot", "🐙", "ai", "ai_practice"),
    ("Zenn - Cursor", "cursor", "🖱️", "ai", "ai_practice"),
    ("Zenn - LLM", "llm", "📚", "ai", "ai_practice"),
    ("Zenn - Prompt Engineering", "プロンプトエンジニアリング", "✏️", "ai", "ai_practice"),
    ("Zenn - Codex", "codex", "🤖", "ai", "ai_practice"),
    ("Zenn - 生成AI", "生成ai", "🌟", "ai", "ai_practice"),

    # モバイル
    ("Zenn - Flutter", "flutter", "📱", "mobile", "flutter"),
    ("Zenn - Swift", "swift", "⚡️", "mobile", "swift"),
    ("Zenn - SwiftUI", "swiftui", "🖼️", "mobile", "swift"),
    ("Zenn - Android", "android", "🤖", "mobile", "android"),
    ("Zenn - Kotlin", "kotlin", "💜", "mobile", "android"),
]

# Zenn の LGTM 閾値(これ以上の "いいね" がついた記事のみ取得)
ZENN_LGTM_THRESHOLD = 15
# Zenn 記事の最大鮮度(これより古い記事は無視。日数)
ZENN_MAX_AGE_DAYS = 7

# ============================================
# Qiita API ソース定義
# (display_name, tag, emoji, channel, category)
# ============================================
QIITA_SOURCES = [
    ("Qiita - Flutter", "flutter", "📱", "mobile", "flutter"),
    ("Qiita - Dart", "dart", "🎯", "mobile", "flutter"),
    ("Qiita - Swift", "swift", "⚡️", "mobile", "swift"),
    ("Qiita - SwiftUI", "swiftui", "🖼️", "mobile", "swift"),
    ("Qiita - Android", "android", "🤖", "mobile", "android"),
    ("Qiita - Kotlin", "kotlin", "💜", "mobile", "android"),
    ("Qiita - Claude", "claude", "🤖", "ai", "ai_practice"),
    ("Qiita - ChatGPT", "chatgpt", "💬", "ai", "ai_practice"),
    ("Qiita - LLM", "llm", "📚", "ai", "ai_practice"),
]

QIITA_API_TOKEN = os.environ.get("QIITA_API_TOKEN", "")
QIITA_LGTM_THRESHOLD = 10
QIITA_MAX_AGE_DAYS = 7

# ============================================
# キーワードフィルタ設定(ai_practice のみ)
# ============================================
FILTER_RULES = {
    "ai_practice": {
        "mode": "include",
        "keywords": [
            "claude code", "claude", "codex", "copilot", "cursor",
            "windsurf", "cline", "aider", "continue.dev",
            "chatgpt", "gemini", "gpt-4", "gpt-5", "o1", "o3",
            "agent", "agentic", "mcp", "rag",
            "prompt engineering", "prompt", "system prompt",
            "automation", "workflow", "tutorial", "guide", "how to",
            "lesson", "tips", "best practice", "playbook",
            "subagent", "sub-agent", "multi-agent",
            "活用", "使い方", "自動化", "業務効率", "プロンプト",
        ],
        "exclude": [
            "you won't believe", "shocking", "i made $", "i earned",
            "millionaire", "10x your", "become a",
        ],
        "min_title_length": 15,
    },
    # それ以外のカテゴリは passthrough(全件通す)
}

# ============================================
# カテゴリ別投稿上限(ノイズ抑制)
# ============================================
MAX_PER_CATEGORY = {
    "ai_practice": 10,
    "management": 8,
    "culture_design": 8,
}

# ============================================
# カテゴリ表示情報
# ============================================
CATEGORIES = {
    "flutter": {"name": "Flutter & Dart", "emoji": "📦"},
    "swift": {"name": "Swift & iOS", "emoji": "🍎"},
    "android": {"name": "Android & Kotlin", "emoji": "🤖"},
    "mobile_rn": {"name": "React Native", "emoji": "⚛️"},
    "ai_practice": {"name": "AI活用術(個人の実装記事)", "emoji": "💡"},
    "management": {"name": "経営・経済(個人の視点)", "emoji": "💼"},
    "culture_design": {"name": "デザイン・文化(個人の声)", "emoji": "🎨"},
    "culture_reading": {"name": "読書", "emoji": "📚"},
}

# チャンネルごとのカテゴリ表示順(4チャンネルをそのまま再利用)
CHANNEL_CATEGORIES = {
    "mobile": ["flutter", "swift", "android", "mobile_rn"],
    "design": ["culture_design"],
    "ai": ["ai_practice"],
    "tools": ["management", "culture_reading"],
}

SEEN_FILE = Path("seen_entries.json")
INITIAL_HOURS = 48

# ==================== ユーティリティ ====================

def load_seen_entries():
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_seen_entries(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def parse_entry_date(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    return datetime.now()


def make_title_exciting(title):
    """タイトルをワクワクする表現に変換"""
    if any(word in title.lower() for word in ["release", "released", "available", "launches"]):
        version = re.search(r"\d+\.\d+(?:\.\d+)?", title)
        if version:
            return f"v{version.group()} がリリース！🎉"
        return f"{title} 🎉"
    if any(word in title.lower() for word in ["beta", "preview", "rc", "alpha"]):
        return f"{title} ⚡️"
    if any(word in title.lower() for word in ["update", "new", "introducing", "announce"]):
        return f"{title} ✨"
    if any(word in title.lower() for word in ["fix", "hotfix", "patch"]):
        return f"{title} 🔧"
    return title

# ==================== フィルタ ====================

def get_entry_text(entry):
    """エントリからフィルタ用のテキスト(title + summary)を抽出"""
    title = getattr(entry, "title", "") or ""
    summary = getattr(entry, "summary", "") or ""
    summary = re.sub(r"<[^>]+>", " ", summary)
    return f"{title} {summary}".lower()


def should_post(item):
    """カテゴリ別フィルタを適用するかどうか判定"""
    category = item["category"]
    rule = FILTER_RULES.get(category)

    if rule is None:
        return True

    mode = rule.get("mode", "passthrough")
    if mode == "passthrough":
        return True

    entry = item["entry"]
    title = getattr(entry, "title", "") or ""
    text = get_entry_text(entry)

    if len(title) < rule.get("min_title_length", 0):
        return False

    for ex in rule.get("exclude", []):
        if ex.lower() in text:
            return False

    if mode == "include":
        keywords = rule.get("keywords", [])
        if not any(kw.lower() in text for kw in keywords):
            return False

    return True

# ==================== Zenn API ====================

def fetch_zenn_articles(topic, lgtm_threshold, max_age_days, seen_entries):
    url = f"https://zenn.dev/api/articles?topicname={topic}&order=latest"
    try:
        res = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; feed-slack-bot/3.0)",
                "Accept": "application/json",
            },
        )
        if not res.ok:
            print(f"  ⚠️ Zenn API エラー: {res.status_code}")
            return []
        data = res.json()
    except Exception as e:
        print(f"  ⚠️ Zenn 取得失敗: {e}")
        return []

    articles = data.get("articles", [])
    if not articles:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    results = []

    for art in articles:
        if not art.get("published", True):
            continue
        if art.get("liked_count", 0) < lgtm_threshold:
            continue
        try:
            pub_at = datetime.fromisoformat(art["published_at"]).astimezone(timezone.utc)
            if pub_at < cutoff:
                continue
        except (KeyError, ValueError):
            continue
        if art.get("article_type") != "tech":
            continue

        link = f"https://zenn.dev{art['path']}"
        if link in seen_entries:
            continue

        results.append({
            "title": art["title"],
            "link": link,
            "liked_count": art["liked_count"],
            "emoji": art.get("emoji", "📝"),
            "published_at": art["published_at"],
        })

    return results


def check_zenn_source(display_name, topic, emoji, channel, category, seen_entries):
    print(f"📡 {display_name} (LGTM>={ZENN_LGTM_THRESHOLD})")
    articles = fetch_zenn_articles(topic, ZENN_LGTM_THRESHOLD, ZENN_MAX_AGE_DAYS, seen_entries)
    if not articles:
        return []

    print(f"  ✅ {len(articles)} 件 (人気記事)")

    items = []
    for art in articles:
        class _Entry:
            pass
        e = _Entry()
        e.title = f"{art['title']} 👍{art['liked_count']}"
        e.link = art["link"]
        items.append({
            "feed_name": display_name,
            "entry": e,
            "emoji": art["emoji"] or emoji,
            "category": category,
            "channel": channel,
            "entry_id": art["link"],
        })
    return items

# ==================== Qiita API ====================

def fetch_qiita_articles(tag, lgtm_threshold, max_age_days, seen_entries):
    url = f"https://qiita.com/api/v2/tags/{tag}/items"
    params = {"page": 1, "per_page": 20}
    headers = {"Accept": "application/json"}
    if QIITA_API_TOKEN:
        headers["Authorization"] = f"Bearer {QIITA_API_TOKEN}"

    try:
        res = requests.get(url, params=params, timeout=15, headers=headers)
        if not res.ok:
            print(f"  ⚠️ Qiita API エラー: {res.status_code}")
            return []
        articles = res.json()
    except Exception as e:
        print(f"  ⚠️ Qiita 取得失敗: {e}")
        return []

    if not articles:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    results = []

    for art in articles:
        if art.get("likes_count", 0) < lgtm_threshold:
            continue
        try:
            pub_at = datetime.fromisoformat(art["created_at"]).astimezone(timezone.utc)
            if pub_at < cutoff:
                continue
        except (KeyError, ValueError):
            continue

        link = art.get("url", "")
        if link in seen_entries:
            continue

        results.append({
            "title": art.get("title", ""),
            "link": link,
            "likes_count": art.get("likes_count", 0),
            "created_at": art.get("created_at", ""),
        })

    return results


def check_qiita_source(display_name, tag, emoji, channel, category, seen_entries):
    print(f"📡 {display_name} (LGTM>={QIITA_LGTM_THRESHOLD})")
    articles = fetch_qiita_articles(tag, QIITA_LGTM_THRESHOLD, QIITA_MAX_AGE_DAYS, seen_entries)
    if not articles:
        return []

    print(f"  ✅ {len(articles)} 件 (人気記事)")

    items = []
    for art in articles:
        class _Entry:
            pass
        e = _Entry()
        e.title = f"{art['title']} 👍{art['likes_count']}"
        e.link = art["link"]
        items.append({
            "feed_name": display_name,
            "entry": e,
            "emoji": emoji,
            "category": category,
            "channel": channel,
            "entry_id": art["link"],
        })
    return items

# ==================== Slack 投稿 ====================

def post_to_slack(channel_id, text=None, blocks=None, thread_ts=None):
    if not BOT_TOKEN or not channel_id:
        return None

    payload = {
        "channel": channel_id,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    if text:
        payload["text"] = text
    if blocks:
        payload["blocks"] = blocks
    if thread_ts:
        payload["thread_ts"] = thread_ts

    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            json=payload,
            headers={
                "Authorization": f"Bearer {BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        data = response.json()
        if not data.get("ok"):
            print(f"⚠️ Slack 投稿エラー: {data.get('error', 'unknown')}")
            return None
        return data.get("ts")
    except Exception as e:
        print(f"⚠️ Slack 投稿失敗: {e}")
        return None

# ==================== RSS ====================

def check_feed(feed_name, feed_url, category, emoji, channel, seen_entries, is_first_run):
    print(f"📡 {feed_name}")
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            return []

        new_entries = []
        cutoff_time = datetime.now() - timedelta(hours=INITIAL_HOURS) if is_first_run else None

        for entry in feed.entries[:15]:
            entry_id = entry.link if hasattr(entry, "link") else entry.title
            if entry_id in seen_entries:
                continue

            if is_first_run and cutoff_time:
                entry_date = parse_entry_date(entry)
                if entry_date < cutoff_time:
                    seen_entries[entry_id] = True
                    continue

            new_entries.append({
                "feed_name": feed_name,
                "entry": entry,
                "emoji": emoji,
                "category": category,
                "channel": channel,
                "entry_id": entry_id,
            })

        if new_entries:
            print(f"  ✅ {len(new_entries)} 件")
        return new_entries
    except Exception as e:
        print(f"  ⚠️ エラー: {e}")
        return []

# ==================== カテゴリ別投稿 ====================

def post_category_with_thread(category_key, entries, channel_id):
    """カテゴリの親メッセージとスレッド投稿"""
    if not entries:
        return

    cat_info = CATEGORIES[category_key]
    count = len(entries)

    parent_blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{cat_info['emoji']} {cat_info['name']}", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{count} 件* の新着情報\n💬 スレッドで詳細をチェック"},
        },
    ]

    print(f"\n  📤 {cat_info['name']} ({count}件)")

    thread_ts = post_to_slack(channel_id, text=f"{cat_info['name']} ({count}件)", blocks=parent_blocks)
    if not thread_ts:
        return

    for item in entries:
        entry = item["entry"]
        title = entry.title if hasattr(entry, "title") else "タイトルなし"
        link = entry.link if hasattr(entry, "link") else ""
        exciting_title = make_title_exciting(title)
        post_to_slack(channel_id, text=f"{item['emoji']} {exciting_title}\n{link}", thread_ts=thread_ts)

# ==================== メイン ====================

def main():
    print(f"\n{'='*60}")
    print("🤖 RSS Feed Bot 起動(曜日ローテーション版)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*60}\n")

    if not BOT_TOKEN:
        print("❌ SLACK_BOT_TOKEN が設定されていません")
        return

    today_jst = datetime.now(JST)
    weekday = today_jst.weekday()
    categories_today = WEEKDAY_CATEGORIES.get(weekday, [])
    print(f"📅 本日({WEEKDAY_NAMES_JA[weekday]}曜日)の担当カテゴリ: {categories_today or 'なし(振り返り日)'}\n")

    seen_entries = load_seen_entries()
    is_first_run = len(seen_entries) == 0
    if is_first_run:
        print(f"🎉 初回実行: 過去 {INITIAL_HOURS} 時間分のみ通知\n")

    channel_data = {
        "mobile": defaultdict(list),
        "design": defaultdict(list),
        "ai": defaultdict(list),
        "tools": defaultdict(list),
    }

    # ---- 1. RSS フィード収集(今日の担当カテゴリのみ) ----
    print(f"\n{'─'*60}")
    print("📡 RSS フィード収集")
    print(f"{'─'*60}")
    for feed_name, feed_url, category, emoji, channel in FEEDS:
        if category not in categories_today:
            continue
        new_items = check_feed(feed_name, feed_url, category, emoji, channel, seen_entries, is_first_run)
        for item in new_items:
            if not should_post(item):
                seen_entries[item["entry_id"]] = True
                continue
            channel_data[channel][category].append(item)
            seen_entries[item["entry_id"]] = True

    # ---- 2. Zenn API 収集(今日の担当カテゴリのみ) ----
    print(f"\n{'─'*60}")
    print("📡 Zenn API 収集")
    print(f"{'─'*60}")
    for display_name, topic, emoji, channel, category in ZENN_SOURCES:
        if category not in categories_today:
            continue
        items = check_zenn_source(display_name, topic, emoji, channel, category, seen_entries)
        for item in items:
            if category == "ai_practice" and not should_post(item):
                seen_entries[item["entry_id"]] = True
                continue
            channel_data[channel][category].append(item)
            seen_entries[item["entry_id"]] = True

    # ---- 3. Qiita API 収集(今日の担当カテゴリのみ) ----
    print(f"\n{'─'*60}")
    print("📡 Qiita API 収集")
    print(f"{'─'*60}")
    for display_name, tag, emoji, channel, category in QIITA_SOURCES:
        if category not in categories_today:
            continue
        items = check_qiita_source(display_name, tag, emoji, channel, category, seen_entries)
        for item in items:
            if category == "ai_practice" and not should_post(item):
                seen_entries[item["entry_id"]] = True
                continue
            channel_data[channel][category].append(item)
            seen_entries[item["entry_id"]] = True

    # ---- 4. カテゴリ別上限の適用 ----
    for ch_key, cat_dict in channel_data.items():
        for cat, items in cat_dict.items():
            limit = MAX_PER_CATEGORY.get(cat)
            if limit and len(items) > limit:
                def sort_key(it):
                    title = getattr(it["entry"], "title", "")
                    m = re.search(r"👍(\d+)", title)
                    return -int(m.group(1)) if m else 0
                items.sort(key=sort_key)
                cat_dict[cat] = items[:limit]
                print(f"  ✂️ {cat}: {len(items)} → {limit} 件に制限")

    # ---- 5. 各チャンネルへ投稿 ----
    channels = [
        ("mobile", CHANNEL_MOBILE, "📱 モバイル開発"),
        ("design", CHANNEL_DESIGN, "🎨 デザイン・文化"),
        ("ai", CHANNEL_AI, "🧠 AI活用術"),
        ("tools", CHANNEL_TOOLS, "💼 経営・読書"),
    ]

    total_new = 0
    for channel_key, channel_id, channel_name in channels:
        if not channel_id:
            continue
        print(f"\n{'='*60}")
        print(channel_name)
        print(f"{'='*60}")

        categories = CHANNEL_CATEGORIES[channel_key]
        for category in categories:
            entries = channel_data[channel_key][category]
            if entries:
                post_category_with_thread(category, entries, channel_id)
                total_new += len(entries)

    # ---- 6. 日曜の振り返りリマインド ----
    if weekday == 6 and CHANNEL_TOOLS:
        post_to_slack(CHANNEL_TOOLS, text=SUNDAY_REMINDER)
        print("\n🗒️ 日曜リマインドを投稿しました")

    save_seen_entries(seen_entries)

    print(f"\n{'='*60}")
    print(f"✨ 完了: {total_new} 件の新着記事を投稿")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
