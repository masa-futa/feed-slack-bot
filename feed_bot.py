#!/usr/bin/env python3
"""
RSS → Slack Bot (GitHub Actions 版)
7チャンネル構成 + リッチフォーマット:
  - release_* カテゴリ → リリースカード（アクセント + 要約 + 相対日時）
  - それ以外           → コンパクトリスト（タイトル + 要約 + ソース + 相対日時）
"""

import feedparser
import requests
import json
import os
import re
import html as html_lib
from datetime import datetime, timedelta, timezone
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
# CHANNEL_RESEARCH = os.environ.get("SLACK_CHANNEL_RESEARCH", "")

SUMMARY_MAX_CHARS = 100   # 要約の最大文字数

# ==================== タイトルフィルタ ====================

AI_CODING_TITLE_BLACKLIST = [
    "deprecat", "retired", "removal", "removed from", "end of life", "eol", "sunset",
    "廃止", "削除",
    "outage", "incident", "degraded", "post-mortem", "postmortem", "障害",
    "pricing", "price increase", "billing change", "値上げ", "料金改定",
    "benchmark", "leaderboard", "model card", "research preview", "paper:", "arxiv",
    "case study", "partner", "transformation partners", "customer story", "事例紹介",
]

DESIGN_PRODUCT_TITLE_BLACKLIST = [
    "we're hiring", "we are hiring", "now hiring", "join our team", "career", "採用",
    "award", "awards", "winner", "shortlist", "nominees", "受賞",
    "webinar", "conference", "summit", "meetup", "live event",
    "case study", "customer story", "success story", "事例紹介",
    "promotion", "promo code", "discount", "セール",
    "sponsored", "advertisement",
]

ZENN_TITLE_BLACKLIST = [
    "入門", "はじめて", "はじめての", "初心者", "初めて", "初学者",
    "for beginners", "getting started", "quick start", "quickstart",
    "基礎", "基本", "とは？", "とは ", "って何",
    "やってみた", "してみた", "使ってみた", "試してみた", "触ってみた",
    "作ってみた", "書いてみた", "調べてみた",
    "まとめてみた", "比較してみた", "まとめました",
    "週報", "日報", "振り返り", "ふりかえり", "アドベントカレンダー",
    "自己紹介", "学習記録", "勉強記録", "転職", "未経験",
]

DESIGN_PRODUCT_CATEGORIES = (
    "design_mobile", "design_ec", "design_tools", "design_a11y", "design_system"
)

ZENN_FEED_URLS = {
    "https://zenn.dev/topics/flutter/feed",
    "https://zenn.dev/topics/swift/feed",
    "https://zenn.dev/topics/android/feed",
    "https://zenn.dev/topics/claudecode/feed",
    "https://zenn.dev/topics/cursor/feed",
    "https://zenn.dev/topics/githubcopilot/feed",
}


def is_blocked_by_blacklist(title: str, category: str, is_zenn: bool = False) -> bool:
    if not title:
        return False
    lowered = title.lower()
    if category == "ai_coding":
        if any(kw in lowered for kw in AI_CODING_TITLE_BLACKLIST):
            return True
    if category in DESIGN_PRODUCT_CATEGORIES:
        if any(kw in lowered for kw in DESIGN_PRODUCT_TITLE_BLACKLIST):
            return True
    if is_zenn:
        if any(kw in lowered for kw in ZENN_TITLE_BLACKLIST):
            return True
    return False


# ==================== Codemagic タグルーティング ====================

CODEMAGIC_TAG_ROUTING = [
    (["flutter"],                                                "mobile", "flutter",  "🔩"),
    (["dart"],                                                   "mobile", "flutter",  "🔩"),
    (["react-native", "react native", "ionic", "xamarin"],       "mobile", "android",  "🔩"),
    (["android", "kotlin", "jetpack", "compose", "google play"], "mobile", "android",  "🔩"),
    (["ios", "swift", "xcode", "testflight", "app store"],       "mobile", "swift",    "🔩"),
]
CODEMAGIC_DEFAULT_CHANNEL  = "tools"
CODEMAGIC_DEFAULT_CATEGORY = "tools_vcs"
CODEMAGIC_DEFAULT_EMOJI    = "🔩"


def route_codemagic_entry(entry):
    tags = {t.get("term", "").lower() for t in entry.get("tags", [])}
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    for tag_list, channel, category, emoji in CODEMAGIC_TAG_ROUTING:
        if any(t in tags or t in text for t in tag_list):
            return channel, category, emoji
    return CODEMAGIC_DEFAULT_CHANNEL, CODEMAGIC_DEFAULT_CATEGORY, CODEMAGIC_DEFAULT_EMOJI


# ==================== フォーマットユーティリティ ====================

def clean_html(raw: str) -> str:
    """HTML タグと余分な空白を除去してプレーンテキストに変換"""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_summary(entry, max_chars: int = SUMMARY_MAX_CHARS) -> str:
    """RSS エントリから要約テキストを生成（最大 max_chars 文字）"""
    raw = (
        getattr(entry, "summary", "")
        or getattr(entry, "description", "")
        or ""
    )
    text = clean_html(raw)
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    # 文字数でカット、単語途中にならないよう調整
    cut = text[:max_chars]
    # 日本語混在を考慮: スペースか句読点で切れるなら手前で切る
    for sep in [" ", "。", "、", "，", "."]:
        idx = cut.rfind(sep)
        if idx > max_chars * 0.7:
            cut = cut[:idx]
            break
    return cut.rstrip(" ,.:;") + "…"


def relative_time(entry) -> str:
    """エントリの公開日時を「N時間前」「昨日」などの相対表現で返す"""
    pub = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        pub = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

    if pub is None:
        return ""

    now = datetime.now(timezone.utc)
    diff = now - pub
    secs = diff.total_seconds()

    if secs < 0:
        return "たった今"
    if secs < 3600:
        m = max(1, int(secs // 60))
        return f"{m}分前"
    if secs < 86400:
        h = int(secs // 3600)
        return f"{h}時間前"
    if secs < 86400 * 2:
        return "昨日"
    if secs < 86400 * 7:
        d = int(secs // 86400)
        return f"{d}日前"
    if secs < 86400 * 30:
        w = int(secs // (86400 * 7))
        return f"{w}週間前"
    m = int(secs // (86400 * 30))
    return f"{m}ヶ月前"


def make_title_exciting(title: str) -> str:
    """タイトルに感情的な装飾を付与"""
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


# ==================== カテゴリ別アクセントカラー ====================
# Slack の Block Kit には color サイドバーがあるので活用

CATEGORY_COLORS = {
    # Mobile
    "flutter":        "#0175C2",
    "swift":          "#FA7343",
    "android":        "#3DDC84",
    "release_mobile": "#00BFA5",
    # Design
    "design_thought": "#7C4DFF",
    "design_graphic": "#FF6E40",
    "design_typo":    "#795548",
    "design_web":     "#039BE5",
    "design_mobile":  "#1976D2",
    "design_ec":      "#E64A19",
    "design_tools":   "#F57C00",
    "design_a11y":    "#388E3C",
    "design_system":  "#512DA8",
    # AI
    "ai_coding":      "#6750A4",
    "release_ai":     "#FF6B6B",
    # Tools
    "tools_vcs":      "#24292E",
    "tools_pm":       "#0052CC",
    "tools_infra":    "#FF9900",
    "tools_dev":      "#007ACC",
}

RELEASE_CATEGORIES = {"release_mobile", "release_ai"}


# ==================== Slack 投稿 ====================

def post_to_slack(channel_id, text=None, blocks=None, attachments=None, thread_ts=None):
    if not BOT_TOKEN or not channel_id:
        return None
    payload = {"channel": channel_id, "unfurl_links": False, "unfurl_media": False}
    if text:
        payload["text"] = text
    if blocks:
        payload["blocks"] = blocks
    if attachments:
        payload["attachments"] = attachments
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


def build_release_attachment(item: dict) -> dict:
    """
    リリース記事用アタッチメント（カラーサイドバー付きカード）
    Slack の legacy attachments を使うことで左側のカラーバーが出る
    """
    entry    = item["entry"]
    category = item["category"]
    emoji    = item["emoji"]
    title    = make_title_exciting(getattr(entry, "title", "タイトルなし"))
    link     = getattr(entry, "link", "")
    summary  = make_summary(entry)
    rel_time = relative_time(entry)
    color    = CATEGORY_COLORS.get(category, "#888888")

    # フッター: ソース名 + 相対時刻
    feed_name = item.get("feed_name", "")
    footer_parts = [p for p in [feed_name, rel_time] if p]
    footer = "  ·  ".join(footer_parts)

    text_parts = [f"*<{link}|{title}>*"]
    if summary:
        text_parts.append(summary)

    return {
        "color":       color,
        "text":        "\n".join(text_parts),
        "footer":      footer,
        "footer_icon": "https://slack-imgs.com/?c=1&o1=ro&url=https%3A%2F%2Fgithub.com%2Ffavicon.ico",
        "mrkdwn_in":   ["text"],
    }


def build_compact_list_blocks(items: list, category: str) -> list:
    """
    Tips・ブログ記事用コンパクトリストのブロック群を返す。
    記事を mrkdwn のセクションとして並べる。
    """
    color = CATEGORY_COLORS.get(category, "#888888")
    lines = []

    for item in items:
        entry    = item["entry"]
        emoji    = item["emoji"]
        title    = make_title_exciting(getattr(entry, "title", "タイトルなし"))
        link     = getattr(entry, "link", "")
        summary  = make_summary(entry)
        rel_time = relative_time(entry)
        feed_name = item.get("feed_name", "")

        meta_parts = [p for p in [feed_name, rel_time] if p]
        meta = "  ·  ".join(meta_parts)

        line = f"{emoji}  *<{link}|{title}>*"
        if summary:
            line += f"\n{summary}"
        if meta:
            line += f"\n_{meta}_"
        lines.append(line)

    # 1つの attachment にリストをまとめる（カラーバー付き）
    return [{
        "color":     color,
        "text":      "\n\n".join(lines),
        "mrkdwn_in": ["text"],
    }]


def post_category_with_thread(category_key, items, channel_id, categories_meta):
    """
    カテゴリの親メッセージを投稿し、スレッドに記事を流す。
    release カテゴリ → 1記事ごとにカードとしてスレッドへ
    その他         → まとめてコンパクトリストとしてスレッドへ（5件ごとに分割）
    """
    if not items:
        return

    cat      = categories_meta[category_key]
    count    = len(items)
    is_release = category_key in RELEASE_CATEGORIES

    # 親メッセージ
    parent_blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{cat['emoji']} {cat['name']}", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{count} 件* の新着情報　💬 スレッドで詳細をチェック"},
        },
    ]

    print(f"\n  📤 {cat['name']} ({count}件) [{'リリースカード' if is_release else 'コンパクトリスト'}]")
    thread_ts = post_to_slack(channel_id, text=f"{cat['name']} ({count}件)", blocks=parent_blocks)
    if not thread_ts:
        return

    if is_release:
        # リリースカード: 1記事ごとに attachment で投稿
        for item in items:
            title = make_title_exciting(getattr(item["entry"], "title", ""))
            post_to_slack(
                channel_id,
                text=title,
                attachments=[build_release_attachment(item)],
                thread_ts=thread_ts,
            )
    else:
        # コンパクトリスト: 5件ごとにまとめて投稿（Slack のブロック制限対策）
        chunk_size = 5
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            attachments = build_compact_list_blocks(chunk, category_key)
            post_to_slack(
                channel_id,
                text=f"{cat['name']} {i+1}〜{i+len(chunk)}件",
                attachments=attachments,
                thread_ts=thread_ts,
            )


# ==================== フィード定義 ====================

FEEDS = [
    # ============================================================
    # 📱 モバイル ブログ・Tips (#mobile-dev)
    # ============================================================
    ("Flutter Blog",              "https://medium.com/feed/flutter",                                       "flutter", "📝", "mobile"),
    ("Flutter Community",         "https://medium.com/feed/flutter-community",                             "flutter", "💎", "mobile"),
    ("Code with Andrea",          "https://codewithandrea.com/rss.xml",                                    "flutter", "🎓", "mobile"),
    ("FlutterDev Reddit",         "https://www.reddit.com/r/FlutterDev/.rss",                              "flutter", "🔧", "mobile"),
    ("Very Good Ventures Blog",   "https://verygood.ventures/blog-category/tech/rss.xml",                  "flutter", "🏗️", "mobile"),
    ("Zenn: Flutter",             "https://zenn.dev/topics/flutter/feed",                                  "flutter", "🇯🇵", "mobile"),
    ("Hacking with Swift",        "https://www.hackingwithswift.com/articles/rss",                         "swift",   "💻", "mobile"),
    ("SwiftLee",                  "https://www.avanderlee.com/feed/",                                      "swift",   "🎨", "mobile"),
    ("Swift by Sundell",          "https://www.swiftbysundell.com/feed/",                                  "swift",   "💡", "mobile"),
    ("NSHipster",                 "https://nshipster.com/feed.xml",                                        "swift",   "🔍", "mobile"),
    ("Donny Wals",                "https://www.donnywals.com/feed/",                                       "swift",   "📚", "mobile"),
    ("Point-Free",                "https://www.pointfree.co/blog/rss.xml",                                 "swift",   "🎯", "mobile"),
    ("Swift with Vincent",        "https://www.swiftwithvincent.com/blog/rss.xml",                         "swift",   "🛠️", "mobile"),
    ("iOS Dev Weekly",            "https://iosdevweekly.com/issues.rss",                                   "swift",   "📰", "mobile"),
    ("Zenn: Swift",               "https://zenn.dev/topics/swift/feed",                                    "swift",   "🇯🇵", "mobile"),
    ("Android Weekly",            "https://androidweekly.net/rss",                                         "android", "📰", "mobile"),
    ("ProAndroidDev",             "https://proandroiddev.com/feed",                                         "android", "⭐", "mobile"),
    ("Joe Birch",                 "https://joebirch.co/feed/",                                              "android", "🎯", "mobile"),
    ("Styling Android",           "https://blog.stylingandroid.com/feed/",                                  "android", "🎨", "mobile"),
    ("Pushing Pixels",            "https://pushing-pixels.org/feed",                                        "android", "✨", "mobile"),
    ("Philipp Lackner",           "https://pl-coding.com/feed/",                                            "android", "📝", "mobile"),
    ("Chris Banes",               "https://chris.banes.dev/rss.xml",                                        "android", "🏗️", "mobile"),
    ("Zenn: Android",             "https://zenn.dev/topics/android/feed",                                   "android", "🇯🇵", "mobile"),
    ("Codemagic Blog",            "https://blog.codemagic.io/index.xml",                                    "_codemagic", "🔩", "_codemagic", "codemagic"),

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
    # 💻 AI Coding Tips (#ai-coding-tools)
    # ============================================================
    ("Zenn: Claude Code",         "https://zenn.dev/topics/claudecode/feed",                              "ai_coding", "📘", "ai"),
    ("Zenn: Cursor",              "https://zenn.dev/topics/cursor/feed",                                  "ai_coding", "📗", "ai"),
    ("Zenn: GitHub Copilot",      "https://zenn.dev/topics/githubcopilot/feed",                           "ai_coding", "📕", "ai"),
    ("Simon Willison",            "https://simonwillison.net/atom/everything/",                           "ai_coding", "🧵", "ai"),
    ("OpenAI News",               "https://openai.com/news/rss.xml",                                     "ai_coding", "🟢", "ai"),

    # ============================================================
    # ⚡ AI 公式リリース (#ai-releases)
    # ============================================================
    ("Claude Code Releases",      "https://github.com/anthropics/claude-code/releases.atom",             "release_ai", "🤖", "ai_releases"),
    ("OpenAI Codex Releases",     "https://github.com/openai/codex/releases.atom",                       "release_ai", "🛠️", "ai_releases"),
    ("Gemini CLI Releases",       "https://github.com/google-gemini/gemini-cli/releases.atom",           "release_ai", "✨", "ai_releases"),
    ("GitHub Copilot Changelog",  "https://github.blog/changelog/label/copilot/feed/",                   "release_ai", "🐙", "ai_releases"),

    # ============================================================
    # 🔬 [将来用] 研究論文系 (無効化中)
    # ============================================================
    # ("OpenAI Blog",     "https://openai.com/blog/rss/",                      "ai_research", "🧠", "research"),
    # ("Anthropic News",  "https://www.anthropic.com/news/rss",                "ai_research", "🤖", "research"),
    # ("Google AI Blog",  "https://blog.research.google/feeds/posts/default",  "ai_research", "🔬", "research"),
    # ("Hugging Face",    "https://huggingface.co/blog/feed.xml",              "ai_research", "🤗", "research"),
    # ("Meta AI",         "https://ai.meta.com/blog/rss/",                     "ai_research", "🦾", "research"),
    # ("DeepMind",        "https://deepmind.google/blog/rss.xml",              "ai_research", "🎯", "research"),
    # ("Stability AI",    "https://stability.ai/news/rss",                     "ai_research", "🔵", "research"),
    # ("Mistral AI",      "https://mistral.ai/news/rss/",                      "ai_research", "⚡️", "research"),
    # ("LangChain Blog",  "https://blog.langchain.dev/rss/",                   "ai_tools",    "🛠️", "research"),
    # ("LlamaIndex",      "https://www.llamaindex.ai/blog/rss.xml",            "ai_tools",    "🔗", "research"),
    # ("The Batch",       "https://www.deeplearning.ai/the-batch/feed/",       "ai_news",     "🎙️", "research"),
    # ("Papers with Code","https://paperswithcode.com/feed.xml",               "ai_news",     "🔍", "research"),

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
    "flutter":        {"name": "Flutter & Dart",                       "emoji": "📦"},
    "swift":          {"name": "Swift & iOS",                          "emoji": "🍎"},
    "android":        {"name": "Android & Kotlin",                     "emoji": "🤖"},
    "release_mobile": {"name": "公式リリース",                          "emoji": "🚀"},
    "design_thought": {"name": "UI/UX 思想・論考",                      "emoji": "💭"},
    "design_graphic": {"name": "Graphic & Visual",                     "emoji": "🖼️"},
    "design_typo":    {"name": "Typography",                           "emoji": "📝"},
    "design_web":     {"name": "Web Design",                           "emoji": "🌐"},
    "design_mobile":  {"name": "モバイルアプリ設計",                    "emoji": "📱"},
    "design_ec":      {"name": "EC/コマース UX",                        "emoji": "🛒"},
    "design_tools":   {"name": "Figma / Adobe ツール情報",              "emoji": "🛠️"},
    "design_a11y":    {"name": "HCD・アクセシビリティ",                  "emoji": "♿"},
    "design_system":  {"name": "プロダクトデザイン・デザインシステム",  "emoji": "🧩"},
    "ai_coding":      {"name": "AI Coding Tips・実践記事",             "emoji": "💻"},
    "release_ai":     {"name": "公式リリース",                          "emoji": "⚡"},
    "ai_research":    {"name": "AI Research",                          "emoji": "🧠"},
    "ai_tools":       {"name": "AI Tools",                             "emoji": "🛠️"},
    "ai_news":        {"name": "AI News",                              "emoji": "📰"},
    "tools_vcs":      {"name": "Version Control & CI/CD",              "emoji": "⚙️"},
    "tools_pm":       {"name": "Project Management",                   "emoji": "📊"},
    "tools_infra":    {"name": "Hosting & Infrastructure",             "emoji": "☁️"},
    "tools_dev":      {"name": "Developer Tools",                      "emoji": "🔧"},
}

CHANNEL_CATEGORIES = {
    "mobile":          ["flutter", "swift", "android"],
    "mobile_releases": ["release_mobile"],
    "design":          ["design_thought", "design_graphic", "design_typo", "design_web"],
    "design_product":  ["design_mobile", "design_ec", "design_tools", "design_a11y", "design_system"],
    "ai":              ["ai_coding"],
    "ai_releases":     ["release_ai"],
    "tools":           ["tools_vcs", "tools_pm", "tools_infra", "tools_dev"],
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


def check_feed(feed_name, feed_url, category, emoji, channel, seen_entries,
               is_first_run, is_zenn=False, is_codemagic=False):
    print(f"📡 {feed_name}")
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            return []

        new_entries = []
        cutoff  = datetime.now() - timedelta(hours=INITIAL_HOURS) if is_first_run else None
        filtered = 0

        for entry in feed.entries[:15]:
            entry_id = getattr(entry, "link", None) or getattr(entry, "title", "")
            if entry_id in seen_entries:
                continue

            if is_first_run and cutoff:
                if parse_entry_date(entry) < cutoff:
                    seen_entries[entry_id] = True
                    continue

            title = getattr(entry, "title", "")

            if is_codemagic:
                resolved_channel, resolved_category, resolved_emoji = route_codemagic_entry(entry)
            else:
                resolved_channel  = channel
                resolved_category = category
                resolved_emoji    = emoji

            if is_blocked_by_blacklist(title, resolved_category, is_zenn=is_zenn):
                seen_entries[entry_id] = True
                filtered += 1
                continue

            new_entries.append({
                "feed_name": feed_name,
                "entry":     entry,
                "emoji":     resolved_emoji,
                "category":  resolved_category,
                "channel":   resolved_channel,
                "entry_id":  entry_id,
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


def main():
    print(f"\n{'='*60}")
    print(f"🤖 RSS Feed Bot (7ch + リッチフォーマット)")
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

    for feed_def in FEEDS:
        feed_name, feed_url, category, emoji, channel = feed_def[:5]
        handler = feed_def[5] if len(feed_def) > 5 else None

        is_codemagic = (handler == "codemagic")
        is_zenn      = (feed_url in ZENN_FEED_URLS)

        if not is_codemagic and channel not in channel_data:
            continue

        new_items = check_feed(
            feed_name, feed_url, category, emoji, channel,
            seen_entries, is_first_run,
            is_zenn=is_zenn, is_codemagic=is_codemagic,
        )

        for item in new_items:
            dest = item["channel"]
            cat  = item["category"]
            if dest in channel_data:
                channel_data[dest][cat].append(item)
            seen_entries[item["entry_id"]] = True

    channels = [
        ("mobile",          CHANNEL_MOBILE,          "📱 モバイル開発 (Tips)"),
        ("mobile_releases", CHANNEL_MOBILE_RELEASES, "🚀 モバイル 公式リリース"),
        ("design",          CHANNEL_DESIGN,          "🎨 デザイン (思想・網羅)"),
        ("design_product",  CHANNEL_DESIGN_PRODUCT,  "🛍️ デザイン (実務)"),
        ("ai",              CHANNEL_AI,              "💻 AI Coding Tips"),
        ("ai_releases",     CHANNEL_AI_RELEASES,     "⚡ AI 公式リリース"),
        ("tools",           CHANNEL_TOOLS,           "⚙️ ツール・サービス"),
        # ("research",      CHANNEL_RESEARCH,         "🔬 AI 研究・論文"),
    ]

    total_new = 0
    for channel_key, channel_id, channel_name in channels:
        if not channel_id:
            continue
        print(f"\n{'='*60}")
        print(f"{channel_name}")
        print(f"{'='*60}")
        for cat_key in CHANNEL_CATEGORIES.get(channel_key, []):
            items = channel_data[channel_key][cat_key]
            if items:
                post_category_with_thread(cat_key, items, channel_id, CATEGORIES)
                total_new += len(items)

    save_seen_entries(seen_entries)
    print(f"\n{'='*60}")
    print(f"✨ 完了: {total_new} 件の新着記事を投稿")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
