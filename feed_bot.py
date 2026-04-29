#!/usr/bin/env python3
"""
RSS → Slack Bot (GitHub Actions 版)
7チャンネル構成:
  mobile-dev        : モバイル ブログ・Tips
  mobile-releases   : モバイル 公式リリースのみ
  design-trends     : デザイン 思想・論考
  design-product    : デザイン モバイル/EC 実務
  ai-coding-tools   : AI コーディング Tips・実践記事
  ai-releases       : AI コーディングツール 公式リリースのみ
  dev-tools-services: インフラ / CI/CD / PM
  (将来) ai-research: LLM 研究・論文
"""

import feedparser
import requests
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ==================== 設定 ====================
BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

CHANNEL_MOBILE          = os.environ.get("SLACK_CHANNEL_MOBILE", "")
CHANNEL_MOBILE_RELEASES = os.environ.get("SLACK_CHANNEL_MOBILE_RELEASES", "")
CHANNEL_DESIGN          = os.environ.get("SLACK_CHANNEL_DESIGN", "")
CHANNEL_DESIGN_PRODUCT  = os.environ.get("SLACK_CHANNEL_DESIGN_PRODUCT", "")
CHANNEL_AI              = os.environ.get("SLACK_CHANNEL_AI", "")
CHANNEL_AI_RELEASES     = os.environ.get("SLACK_CHANNEL_AI_RELEASES", "")
CHANNEL_TOOLS           = os.environ.get("SLACK_CHANNEL_TOOLS", "")
# 将来用
# CHANNEL_RESEARCH = os.environ.get("SLACK_CHANNEL_RESEARCH", "")

# ==================== タイトルフィルタ ====================
# ai_coding カテゴリ: 「機能追加・使い方」以外のノイズを弾く
AI_CODING_TITLE_BLACKLIST = [
    "deprecat", "retired", "removal", "removed from", "end of life", "eol", "sunset",
    "廃止", "削除",
    "outage", "incident", "degraded", "post-mortem", "postmortem", "障害",
    "pricing", "price increase", "billing change", "値上げ", "料金改定",
    "benchmark", "leaderboard", "model card", "research preview", "paper:", "arxiv",
    "case study", "partner", "transformation partners", "customer story", "事例紹介",
]

# design_product 系カテゴリ: モバイル/EC 実務からノイズを弾く
DESIGN_PRODUCT_TITLE_BLACKLIST = [
    "we're hiring", "we are hiring", "now hiring", "join our team", "career", "採用",
    "award", "awards", "winner", "shortlist", "nominees", "受賞",
    "webinar", "conference", "summit", "meetup", "live event",
    "case study", "customer story", "success story", "事例紹介",
    "promotion", "promo code", "discount", "セール",
    "sponsored", "advertisement", "ad placement",
]

DESIGN_PRODUCT_CATEGORIES = (
    "design_mobile", "design_ec", "design_tools", "design_a11y", "design_system"
)


def is_blocked_by_blacklist(title: str, category: str) -> bool:
    if not title:
        return False
    lowered = title.lower()
    if category == "ai_coding":
        return any(kw in lowered for kw in AI_CODING_TITLE_BLACKLIST)
    if category in DESIGN_PRODUCT_CATEGORIES:
        return any(kw in lowered for kw in DESIGN_PRODUCT_TITLE_BLACKLIST)
    return False


# ==================== フィード定義 ====================
# (フィード名, URL, カテゴリ, 絵文字, 投稿先チャンネルキー)
FEEDS = [

    # ============================================================
    # 📱 モバイル開発 ブログ・Tips (#mobile-dev)
    # ============================================================
    # Flutter/Dart — リリースは mobile_releases へ移動済み
    ("Flutter Blog",              "https://medium.com/feed/flutter",                                       "flutter", "📝", "mobile"),
    ("Flutter Community",         "https://medium.com/feed/flutter-community",                             "flutter", "💎", "mobile"),
    ("Code with Andrea",          "https://codewithandrea.com/rss.xml",                                    "flutter", "🎓", "mobile"),
    ("FlutterDev Reddit",         "https://www.reddit.com/r/FlutterDev/.rss",                              "flutter", "🔧", "mobile"),
    ("Codemagic Blog",            "https://blog.codemagic.io/index.xml",                                   "flutter", "🔩", "mobile"),
    ("Very Good Ventures Blog",   "https://verygood.ventures/blog-category/tech/rss.xml",                  "flutter", "🏗️", "mobile"),
    ("Zenn: Flutter",             "https://zenn.dev/topics/flutter/feed",                                  "flutter", "🇯🇵", "mobile"),

    # Swift/iOS — リリースは mobile_releases へ移動済み
    ("Hacking with Swift",        "https://www.hackingwithswift.com/articles/rss",                         "swift", "💻", "mobile"),
    ("SwiftLee",                  "https://www.avanderlee.com/feed/",                                      "swift", "🎨", "mobile"),
    ("Swift by Sundell",          "https://www.swiftbysundell.com/feed/",                                  "swift", "💡", "mobile"),
    ("NSHipster",                 "https://nshipster.com/feed.xml",                                        "swift", "🔍", "mobile"),
    ("Donny Wals",                "https://www.donnywals.com/feed/",                                       "swift", "📚", "mobile"),
    ("Point-Free",                "https://www.pointfree.co/blog/rss.xml",                                 "swift", "🎯", "mobile"),
    ("Swift with Vincent",        "https://www.swiftwithvincent.com/blog/rss.xml",                         "swift", "🛠️", "mobile"),
    ("iOS Dev Weekly",            "https://iosdevweekly.com/issues.rss",                                   "swift", "📰", "mobile"),
    ("Zenn: Swift",               "https://zenn.dev/topics/swift/feed",                                    "swift", "🇯🇵", "mobile"),

    # Android/Kotlin — リリースは mobile_releases へ移動済み
    ("Android Weekly",            "https://androidweekly.net/rss",                                         "android", "📰", "mobile"),
    ("ProAndroidDev",             "https://proandroiddev.com/feed",                                         "android", "⭐", "mobile"),
    ("Joe Birch",                 "https://joebirch.co/feed/",                                              "android", "🎯", "mobile"),
    ("Styling Android",           "https://blog.stylingandroid.com/feed/",                                  "android", "🎨", "mobile"),
    ("Pushing Pixels",            "https://pushing-pixels.org/feed",                                        "android", "✨", "mobile"),
    ("Philipp Lackner",           "https://pl-coding.com/feed/",                                            "android", "📝", "mobile"),
    ("Chris Banes",               "https://chris.banes.dev/rss.xml",                                        "android", "🏗️", "mobile"),

    # ============================================================
    # 🚀 モバイル 公式リリース (#mobile-releases)
    # ============================================================
    ("Flutter Releases",          "https://github.com/flutter/flutter/releases.atom",                      "release_mobile", "🚀", "mobile_releases"),
    ("Dart SDK Releases",         "https://github.com/dart-lang/sdk/releases.atom",                        "release_mobile", "🎯", "mobile_releases"),
    ("Swift.org Blog",            "https://www.swift.org/atom.xml",                                        "release_mobile", "⚡️", "mobile_releases"),
    ("Apple Developer News",      "https://developer.apple.com/news/rss/news.rss",                         "release_mobile", "🍎", "mobile_releases"),
    ("Android Developers Blog",   "https://android-developers.googleblog.com/feeds/posts/default",         "release_mobile", "🤖", "mobile_releases"),
    ("Kotlin Blog",               "https://blog.jetbrains.com/kotlin/feed/",                               "release_mobile", "💡", "mobile_releases"),
    ("Compose Releases",          "https://github.com/JetBrains/compose-multiplatform/releases.atom",      "release_mobile", "🔷", "mobile_releases"),

    # ============================================================
    # 🎨 デザイン 思想・論考 (#design-trends)
    # ============================================================
    ("A List Apart",              "https://alistapart.com/main/feed/",                                     "design_thought", "📐", "design"),
    ("UX Collective",             "https://uxdesign.cc/feed",                                              "design_thought", "💡", "design"),
    ("Smashing Magazine",         "https://www.smashingmagazine.com/feed/",                                "design_thought", "🎨", "design"),
    ("IxDF",                      "https://www.interaction-design.org/literature/rss",                     "design_thought", "📊", "design"),
    ("Creative Bloq",             "https://www.creativebloq.com/feed",                                     "design_graphic", "🎨", "design"),
    ("Designmodo",                "https://designmodo.com/feed/",                                          "design_graphic", "🌈", "design"),
    ("Abduzeedo",                 "https://abduzeedo.com/rss.xml",                                         "design_graphic", "💫", "design"),
    ("Awwwards",                  "https://www.awwwards.com/blog/feed/",                                   "design_graphic", "💎", "design"),
    ("Typewolf",                  "https://www.typewolf.com/feed",                                         "design_typo",    "📝", "design"),
    ("Fonts In Use",              "https://fontsinuse.com/rss",                                            "design_typo",    "✍️", "design"),
    ("I Love Typography",         "https://ilovetypography.com/feed/",                                     "design_typo",    "🔤", "design"),
    ("CSS-Tricks",                "https://css-tricks.com/feed/",                                          "design_web",     "🌐", "design"),
    ("Codrops",                   "https://tympanus.net/codrops/feed/",                                    "design_web",     "🎯", "design"),
    ("Web Designer Depot",        "https://www.webdesignerdepot.com/feed/",                                "design_web",     "🚀", "design"),

    # ============================================================
    # 🛍️ デザイン プロダクト実務 (#design-product)
    # ============================================================
    ("Material Design Blog",      "https://material.io/feed.xml",                                         "design_mobile",  "📱", "design_product"),
    ("Apple Developer News",      "https://developer.apple.com/news/rss/news.rss",                        "design_mobile",  "🍎", "design_product"),
    ("Android Developers Blog",   "https://android-developers.googleblog.com/feeds/posts/default",        "design_mobile",  "🤖", "design_product"),
    ("Baymard Institute",         "https://baymard.com/blog/rss",                                         "design_ec",      "🛒", "design_product"),
    ("Figma Blog",                "https://www.figma.com/blog/rss/",                                      "design_tools",   "🔷", "design_product"),
    ("Adobe Create",              "https://blog.adobe.com/en/topics/creativity/feed",                     "design_tools",   "🖼️", "design_product"),
    ("Nielsen Norman Group",      "https://www.nngroup.com/feed/rss/",                                    "design_a11y",    "🧪", "design_product"),
    ("Laws of UX",                "https://lawsofux.com/rss.xml",                                         "design_a11y",    "⚖️", "design_product"),
    ("Deque Blog",                "https://www.deque.com/blog/feed/",                                     "design_a11y",    "♿", "design_product"),
    ("W3C WAI News",              "https://www.w3.org/WAI/news/feed/",                                    "design_a11y",    "🌐", "design_product"),
    ("UX Design Institute",       "https://www.uxdesigninstitute.com/blog/feed/",                         "design_system",  "🎯", "design_product"),
    ("RWD Weekly",                "https://responsivedesign.is/rss/",                                     "design_system",  "📲", "design_product"),

    # ============================================================
    # 💻 AI コーディング Tips・実践記事 (#ai-coding-tools)
    # ============================================================
    ("Zenn: Claude Code",         "https://zenn.dev/topics/claudecode/feed",                              "ai_coding", "📘", "ai"),
    ("Zenn: Cursor",              "https://zenn.dev/topics/cursor/feed",                                  "ai_coding", "📗", "ai"),
    ("Zenn: GitHub Copilot",      "https://zenn.dev/topics/githubcopilot/feed",                           "ai_coding", "📕", "ai"),
    ("Simon Willison",            "https://simonwillison.net/atom/everything/",                           "ai_coding", "🧵", "ai"),
    ("OpenAI News",               "https://openai.com/news/rss.xml",                                     "ai_coding", "🟢", "ai"),

    # ============================================================
    # ⚡ AI コーディングツール 公式リリース (#ai-releases)
    # ============================================================
    ("Claude Code Releases",      "https://github.com/anthropics/claude-code/releases.atom",             "release_ai", "🤖", "ai_releases"),
    ("OpenAI Codex Releases",     "https://github.com/openai/codex/releases.atom",                       "release_ai", "🛠️", "ai_releases"),
    ("Gemini CLI Releases",       "https://github.com/google-gemini/gemini-cli/releases.atom",           "release_ai", "✨", "ai_releases"),
    ("GitHub Copilot Changelog",  "https://github.blog/changelog/label/copilot/feed/",                   "release_ai", "🐙", "ai_releases"),

    # ============================================================
    # 🔬 [将来用] 研究論文系 (現在は無効化)
    # ============================================================
    # Secrets に SLACK_CHANNEL_RESEARCH を追加後、以下のコメントを外す
    #
    # ("OpenAI Blog",       "https://openai.com/blog/rss/",                      "ai_research", "🧠", "research"),
    # ("Anthropic News",    "https://www.anthropic.com/news/rss",                "ai_research", "🤖", "research"),
    # ("Google AI Blog",    "https://blog.research.google/feeds/posts/default",  "ai_research", "🔬", "research"),
    # ("Hugging Face",      "https://huggingface.co/blog/feed.xml",              "ai_research", "🤗", "research"),
    # ("Meta AI",           "https://ai.meta.com/blog/rss/",                     "ai_research", "🦾", "research"),
    # ("DeepMind",          "https://deepmind.google/blog/rss.xml",              "ai_research", "🎯", "research"),
    # ("Stability AI",      "https://stability.ai/news/rss",                     "ai_research", "🔵", "research"),
    # ("Mistral AI",        "https://mistral.ai/news/rss/",                      "ai_research", "⚡️", "research"),
    # ("LangChain Blog",    "https://blog.langchain.dev/rss/",                   "ai_tools",    "🛠️", "research"),
    # ("LlamaIndex",        "https://www.llamaindex.ai/blog/rss.xml",            "ai_tools",    "🔗", "research"),
    # ("Weights & Biases",  "https://wandb.ai/site/rss.xml",                     "ai_tools",    "📊", "research"),
    # ("Runway ML",         "https://runwayml.com/blog/rss/",                    "ai_tools",    "🖼️", "research"),
    # ("Replicate Blog",    "https://replicate.com/blog/rss.xml",                "ai_tools",    "🔄", "research"),
    # ("The Batch",         "https://www.deeplearning.ai/the-batch/feed/",       "ai_news",     "🎙️", "research"),
    # ("Papers with Code",  "https://paperswithcode.com/feed.xml",               "ai_news",     "🔍", "research"),
    # ("AI News",           "https://www.artificialintelligence-news.com/feed/", "ai_news",     "📰", "research"),

    # ============================================================
    # ⚙️ ツール・サービス (#dev-tools-services)
    # ============================================================
    ("GitHub Blog",               "https://github.blog/feed/",                                           "tools_vcs",   "⚙️", "tools"),
    ("GitLab Blog",               "https://about.gitlab.com/atom.xml",                                   "tools_vcs",   "🦊", "tools"),
    ("CircleCI",                  "https://circleci.com/blog/feed.xml",                                  "tools_vcs",   "🔄", "tools"),
    ("Jenkins Blog",              "https://www.jenkins.io/node/feed.xml",                                "tools_vcs",   "🚀", "tools"),
    ("Notion Blog",               "https://www.notion.so/blog/rss",                                     "tools_pm",    "📓", "tools"),
    ("Linear Blog",               "https://linear.app/blog/rss.xml",                                    "tools_pm",    "📊", "tools"),
    ("Jira Software",             "https://www.atlassian.com/blog/jira-software/feed",                  "tools_pm",    "🎯", "tools"),
    ("Slack Engineering",         "https://slack.engineering/feed/",                                     "tools_pm",    "💬", "tools"),
    ("Vercel Blog",               "https://vercel.com/blog/rss.xml",                                    "tools_infra", "▲",  "tools"),
    ("Railway Blog",              "https://blog.railway.app/rss.xml",                                   "tools_infra", "🚂", "tools"),
    ("AWS News",                  "https://aws.amazon.com/blogs/aws/feed/",                             "tools_infra", "☁️", "tools"),
    ("Azure Updates",             "https://azure.microsoft.com/en-us/updates/feed/",                    "tools_infra", "🔵", "tools"),
    ("Cloudflare Blog",           "https://blog.cloudflare.com/rss/",                                   "tools_infra", "🌐", "tools"),
    ("Docker Blog",               "https://www.docker.com/blog/feed/",                                  "tools_infra", "🐳", "tools"),
    ("VS Code Blog",              "https://code.visualstudio.com/feed.xml",                             "tools_dev",   "🎨", "tools"),
    ("JetBrains Blog",            "https://blog.jetbrains.com/feed/",                                   "tools_dev",   "🔧", "tools"),
    ("Raycast Blog",              "https://www.raycast.com/blog/rss.xml",                               "tools_dev",   "🌙", "tools"),
    ("npm Blog",                  "https://blog.npmjs.org/rss.xml",                                     "tools_dev",   "📦", "tools"),
]

SEEN_FILE = Path("seen_entries.json")
INITIAL_HOURS = 48

# ==================== カテゴリ定義 ====================
CATEGORIES = {
    # Mobile Tips
    "flutter":        {"name": "Flutter & Dart",                       "emoji": "📦"},
    "swift":          {"name": "Swift & iOS",                          "emoji": "🍎"},
    "android":        {"name": "Android & Kotlin",                     "emoji": "🤖"},
    # Mobile Releases
    "release_mobile": {"name": "公式リリース",                          "emoji": "🚀"},
    # Design (思想)
    "design_thought": {"name": "UI/UX 思想・論考",                      "emoji": "💭"},
    "design_graphic": {"name": "Graphic & Visual",                     "emoji": "🖼️"},
    "design_typo":    {"name": "Typography",                           "emoji": "📝"},
    "design_web":     {"name": "Web Design",                           "emoji": "🌐"},
    # Design (実務)
    "design_mobile":  {"name": "モバイルアプリ設計",                    "emoji": "📱"},
    "design_ec":      {"name": "EC/コマース UX",                        "emoji": "🛒"},
    "design_tools":   {"name": "Figma / Adobe ツール情報",              "emoji": "🛠️"},
    "design_a11y":    {"name": "HCD・アクセシビリティ",                  "emoji": "♿"},
    "design_system":  {"name": "プロダクトデザイン・デザインシステム",  "emoji": "🧩"},
    # AI Tips
    "ai_coding":      {"name": "AI Coding Tips・実践記事",             "emoji": "💻"},
    # AI Releases
    "release_ai":     {"name": "公式リリース",                          "emoji": "⚡"},
    # AI Research (将来用)
    "ai_research":    {"name": "AI Research",                          "emoji": "🧠"},
    "ai_tools":       {"name": "AI Tools",                             "emoji": "🛠️"},
    "ai_news":        {"name": "AI News",                              "emoji": "📰"},
    # Tools
    "tools_vcs":      {"name": "Version Control & CI/CD",              "emoji": "⚙️"},
    "tools_pm":       {"name": "Project Management",                   "emoji": "📊"},
    "tools_infra":    {"name": "Hosting & Infrastructure",             "emoji": "☁️"},
    "tools_dev":      {"name": "Developer Tools",                      "emoji": "🔧"},
}

# ==================== チャンネル → カテゴリ ====================
CHANNEL_CATEGORIES = {
    "mobile":          ["flutter", "swift", "android"],
    "mobile_releases": ["release_mobile"],
    "design":          ["design_thought", "design_graphic", "design_typo", "design_web"],
    "design_product":  ["design_mobile", "design_ec", "design_tools", "design_a11y", "design_system"],
    "ai":              ["ai_coding"],
    "ai_releases":     ["release_ai"],
    "tools":           ["tools_vcs", "tools_pm", "tools_infra", "tools_dev"],
    # 将来用
    # "research":      ["ai_research", "ai_tools", "ai_news"],
}


# ==================== コア処理 ====================
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
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    return datetime.now()


def make_title_exciting(title):
    t = title or ""
    low = t.lower()
    if any(w in low for w in ["release", "released", "available", "launches"]):
        ver = re.search(r"\d+\.\d+(?:\.\d+)?", t)
        return f"v{ver.group()} がリリース！🎉" if ver else f"{t} 🎉"
    if any(w in low for w in ["beta", "preview", "rc", "alpha"]):
        return f"{t} ⚡️"
    if any(w in low for w in ["update", "new", "introducing", "announce"]):
        return f"{t} ✨"
    if any(w in low for w in ["fix", "hotfix", "patch"]):
        return f"{t} 🔧"
    return t


def post_to_slack(channel_id, text=None, blocks=None, thread_ts=None):
    if not BOT_TOKEN or not channel_id:
        return None
    payload = {"channel": channel_id, "unfurl_links": False, "unfurl_media": False}
    if text:
        payload["text"] = text
    if blocks:
        payload["blocks"] = blocks
    if thread_ts:
        payload["thread_ts"] = thread_ts
    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            json=payload,
            headers={"Authorization": f"Bearer {BOT_TOKEN}", "Content-Type": "application/json"},
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            print(f"  ⚠️ Slack エラー: {data.get('error', 'unknown')}")
            return None
        return data.get("ts")
    except Exception as e:
        print(f"  ⚠️ Slack 投稿失敗: {e}")
        return None


def check_feed(feed_name, feed_url, category, emoji, channel, seen_entries, is_first_run):
    print(f"📡 {feed_name}")
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            return []

        new_entries = []
        cutoff = datetime.now() - timedelta(hours=INITIAL_HOURS) if is_first_run else None
        filtered = 0

        for entry in feed.entries[:10]:
            entry_id = getattr(entry, "link", None) or getattr(entry, "title", "")
            if entry_id in seen_entries:
                continue

            if is_first_run and cutoff:
                if parse_entry_date(entry) < cutoff:
                    seen_entries[entry_id] = True
                    continue

            title = getattr(entry, "title", "")
            if is_blocked_by_blacklist(title, category):
                seen_entries[entry_id] = True
                filtered += 1
                continue

            new_entries.append({
                "entry": entry,
                "emoji": emoji,
                "category": category,
                "entry_id": entry_id,
            })

        if new_entries:
            suffix = f" (フィルタで {filtered} 件除外)" if filtered else ""
            print(f"  ✅ {len(new_entries)} 件{suffix}")
        elif filtered:
            print(f"  🚫 フィルタで {filtered} 件除外")

        return new_entries
    except Exception as e:
        print(f"  ⚠️ エラー: {e}")
        return []


def post_category_with_thread(category_key, entries, channel_id):
    if not entries:
        return
    cat = CATEGORIES[category_key]
    count = len(entries)

    parent_blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{cat['emoji']} {cat['name']}", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{count} 件* の新着情報\n💬 スレッドで詳細をチェック"}},
    ]

    print(f"\n  📤 {cat['name']} ({count}件)")
    thread_ts = post_to_slack(channel_id, text=f"{cat['name']} ({count}件)", blocks=parent_blocks)
    if not thread_ts:
        return

    for item in entries:
        entry = item["entry"]
        title = make_title_exciting(getattr(entry, "title", "タイトルなし"))
        link = getattr(entry, "link", "")
        post_to_slack(channel_id, text=f"{item['emoji']} {title}\n{link}", thread_ts=thread_ts)


def main():
    print(f"\n{'='*60}")
    print(f"🤖 RSS Feed Bot (7チャンネル構成)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*60}\n")

    if not BOT_TOKEN:
        print("❌ SLACK_BOT_TOKEN が設定されていません")
        return

    seen_entries = load_seen_entries()
    is_first_run = len(seen_entries) == 0
    if is_first_run:
        print(f"🎉 初回実行: 過去 {INITIAL_HOURS} 時間分のみ通知\n")

    channel_data = {k: defaultdict(list) for k in CHANNEL_CATEGORIES}
    # 将来用: "research": defaultdict(list)

    for feed_name, feed_url, category, emoji, channel in FEEDS:
        if channel not in channel_data:
            continue
        new_items = check_feed(feed_name, feed_url, category, emoji, channel, seen_entries, is_first_run)
        for item in new_items:
            channel_data[channel][category].append(item)
            seen_entries[item["entry_id"]] = True

    channels = [
        ("mobile",          CHANNEL_MOBILE,          "📱 モバイル開発 (Tips)"),
        ("mobile_releases", CHANNEL_MOBILE_RELEASES, "🚀 モバイル 公式リリース"),
        ("design",          CHANNEL_DESIGN,          "🎨 デザイン (思想・網羅)"),
        ("design_product",  CHANNEL_DESIGN_PRODUCT,  "🛍️ デザイン (実務)"),
        ("ai",              CHANNEL_AI,              "💻 AI Coding Tips"),
        ("ai_releases",     CHANNEL_AI_RELEASES,     "⚡ AI 公式リリース"),
        ("tools",           CHANNEL_TOOLS,           "⚙️ ツール・サービス"),
        # ("research", CHANNEL_RESEARCH, "🔬 AI 研究・論文"),
    ]

    total_new = 0
    for channel_key, channel_id, channel_name in channels:
        if not channel_id:
            continue
        print(f"\n{'='*60}")
        print(f"{channel_name}")
        print(f"{'='*60}")
        for category in CHANNEL_CATEGORIES.get(channel_key, []):
            entries = channel_data[channel_key][category]
            if entries:
                post_category_with_thread(category, entries, channel_id)
                total_new += len(entries)

    save_seen_entries(seen_entries)
    print(f"\n{'='*60}")
    print(f"✨ 完了: {total_new} 件の新着記事を投稿")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
