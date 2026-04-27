#!/usr/bin/env python3
"""
RSS → Slack Bot (GitHub Actions 版)
完全版: 80フィード + 4チャンネル対応
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

# チャンネルID（環境変数から取得）
CHANNEL_MOBILE = os.environ.get("SLACK_CHANNEL_MOBILE", "")      # モバイル開発
CHANNEL_DESIGN = os.environ.get("SLACK_CHANNEL_DESIGN", "")      # デザイン
CHANNEL_AI = os.environ.get("SLACK_CHANNEL_AI", "")              # AI・ML
CHANNEL_TOOLS = os.environ.get("SLACK_CHANNEL_TOOLS", "")        # ツール・サービス

# 監視する RSS/Atom フィード (80個)
FEEDS = [
    # ============================================
    # 📱 モバイル開発系 (#mobile-dev)
    # ============================================
    
    # Flutter & Dart (6)
    ("Flutter Releases", "https://github.com/flutter/flutter/releases.atom", "flutter", "🚀", "mobile"),
    ("Dart SDK Releases", "https://github.com/dart-lang/sdk/releases.atom", "flutter", "🎯", "mobile"),
    ("Flutter Blog", "https://medium.com/feed/flutter", "flutter", "📝", "mobile"),
    ("Flutter Community", "https://medium.com/feed/flutter-community", "flutter", "💎", "mobile"),
    ("Code with Andrea", "https://codewithandrea.com/rss.xml", "flutter", "🎓", "mobile"),
    ("FlutterDev Reddit", "https://www.reddit.com/r/FlutterDev/.rss", "flutter", "🔧", "mobile"),
    
    # Swift & iOS (10)
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
    
    # Android & Kotlin (9)
    ("Android Developers Blog", "https://android-developers.googleblog.com/feeds/posts/default", "android", "🤖", "mobile"),
    ("Kotlin Blog", "https://blog.jetbrains.com/kotlin/feed/", "android", "💡", "mobile"),
    ("Android Weekly", "https://androidweekly.net/rss", "android", "📰", "mobile"),
    ("Joe Birch", "https://joebirch.co/feed/", "android", "🎯", "mobile"),
    ("Styling Android", "https://blog.stylingandroid.com/feed/", "android", "🎨", "mobile"),
    ("Compose Releases", "https://github.com/JetBrains/compose-multiplatform/releases.atom", "android", "🔷", "mobile"),
    ("Kotlin Multiplatform", "https://blog.jetbrains.com/kotlin/feed/", "android", "🌐", "mobile"),
    ("Philipp Lackner", "https://pl-coding.com/feed/", "android", "📝", "mobile"),
    ("Chris Banes", "https://chris.banes.dev/rss.xml", "android", "🏗️", "mobile"),
    
    # ============================================
    # 🎨 デザイン系 (#design-trends)
    # ============================================
    
    # UI/UX Design (8)
    ("Nielsen Norman Group", "https://www.nngroup.com/feed/rss/", "design_ux", "🧪", "design"),
    ("Smashing Magazine", "https://www.smashingmagazine.com/feed/", "design_ux", "🎨", "design"),
    ("A List Apart", "https://alistapart.com/main/feed/", "design_ux", "📐", "design"),
    ("UX Collective", "https://uxdesign.cc/feed", "design_ux", "💡", "design"),
    ("Figma Blog", "https://www.figma.com/blog/rss/", "design_ux", "🔷", "design"),
    ("Laws of UX", "https://lawsofux.com/rss.xml", "design_ux", "⚖️", "design"),
    ("UX Design Institute", "https://www.uxdesigninstitute.com/blog/feed/", "design_ux", "🎯", "design"),
    ("IxDF", "https://www.interaction-design.org/literature/rss", "design_ux", "📊", "design"),
    
    # Graphic Design (4)
    ("Adobe Create", "https://blog.adobe.com/en/topics/creativity/feed", "design_graphic", "🖼️", "design"),
    ("Creative Bloq", "https://www.creativebloq.com/feed", "design_graphic", "🎨", "design"),
    ("Designmodo", "https://designmodo.com/feed/", "design_graphic", "🌈", "design"),
    ("Abduzeedo", "https://abduzeedo.com/rss.xml", "design_graphic", "💫", "design"),
    
    # Typography (3)
    ("Typewolf", "https://www.typewolf.com/feed", "design_typo", "📝", "design"),
    ("Fonts In Use", "https://fontsinuse.com/rss", "design_typo", "✍️", "design"),
    ("I Love Typography", "https://ilovetypography.com/feed/", "design_typo", "🔤", "design"),
    
    # Web Design (5)
    ("CSS-Tricks", "https://css-tricks.com/feed/", "design_web", "🌐", "design"),
    ("Codrops", "https://tympanus.net/codrops/feed/", "design_web", "🎯", "design"),
    ("Awwwards", "https://www.awwwards.com/blog/feed/", "design_web", "💎", "design"),
    ("Web Designer Depot", "https://www.webdesignerdepot.com/feed/", "design_web", "🚀", "design"),
    ("RWD Weekly", "https://responsivedesign.is/rss/", "design_web", "📱", "design"),
    
    # ============================================
    # 🧠 AI & ML系 (#ai-ml-news)
    # ============================================
    
    # AI Companies & Research (8)
    ("OpenAI Blog", "https://openai.com/blog/rss/", "ai_research", "🧠", "ai"),
    ("Anthropic News", "https://www.anthropic.com/news/rss", "ai_research", "🤖", "ai"),
    ("Google AI Blog", "https://blog.research.google/feeds/posts/default", "ai_research", "🔬", "ai"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "ai_research", "🤗", "ai"),
    ("Meta AI", "https://ai.meta.com/blog/rss/", "ai_research", "🦾", "ai"),
    ("DeepMind", "https://deepmind.google/blog/rss.xml", "ai_research", "🎯", "ai"),
    ("Stability AI", "https://stability.ai/news/rss", "ai_research", "🔵", "ai"),
    ("Mistral AI", "https://mistral.ai/news/rss/", "ai_research", "⚡️", "ai"),
    
    # AI Tools & Platforms (5)
    ("LangChain Blog", "https://blog.langchain.dev/rss/", "ai_tools", "🛠️", "ai"),
    ("LlamaIndex", "https://www.llamaindex.ai/blog/rss.xml", "ai_tools", "🔗", "ai"),
    ("Weights & Biases", "https://wandb.ai/site/rss.xml", "ai_tools", "📊", "ai"),
    ("Runway ML", "https://runwayml.com/blog/rss/", "ai_tools", "🖼️", "ai"),
    ("Replicate Blog", "https://replicate.com/blog/rss.xml", "ai_tools", "🔄", "ai"),
    
    # AI News & Analysis (4)
    ("Simon Willison", "https://simonwillison.net/atom/everything/", "ai_news", "📝", "ai"),
    ("The Batch", "https://www.deeplearning.ai/the-batch/feed/", "ai_news", "🎙️", "ai"),
    ("Papers with Code", "https://paperswithcode.com/feed.xml", "ai_news", "🔍", "ai"),
    ("AI News", "https://www.artificialintelligence-news.com/feed/", "ai_news", "📰", "ai"),
    
    # ============================================
    # ⚙️ ツール・サービス系 (#dev-tools-services)
    # ============================================
    
    # Version Control & CI/CD (4)
    ("GitHub Blog", "https://github.blog/feed/", "tools_vcs", "⚙️", "tools"),
    ("GitLab Blog", "https://about.gitlab.com/atom.xml", "tools_vcs", "🦊", "tools"),
    ("CircleCI", "https://circleci.com/blog/feed.xml", "tools_vcs", "🔄", "tools"),
    ("Jenkins Blog", "https://www.jenkins.io/node/feed.xml", "tools_vcs", "🚀", "tools"),
    
    # Project Management (4)
    ("Notion Blog", "https://www.notion.so/blog/rss", "tools_pm", "📓", "tools"),
    ("Linear Blog", "https://linear.app/blog/rss.xml", "tools_pm", "📊", "tools"),
    ("Jira Software", "https://www.atlassian.com/blog/jira-software/feed", "tools_pm", "🎯", "tools"),
    ("Slack Engineering", "https://slack.engineering/feed/", "tools_pm", "💬", "tools"),
    
    # Hosting & Infrastructure (6)
    ("Vercel Blog", "https://vercel.com/blog/rss.xml", "tools_infra", "▲", "tools"),
    ("Railway Blog", "https://blog.railway.app/rss.xml", "tools_infra", "🚂", "tools"),
    ("AWS News", "https://aws.amazon.com/blogs/aws/feed/", "tools_infra", "☁️", "tools"),
    ("Azure Updates", "https://azure.microsoft.com/en-us/updates/feed/", "tools_infra", "🔵", "tools"),
    ("Cloudflare Blog", "https://blog.cloudflare.com/rss/", "tools_infra", "🌐", "tools"),
    ("Docker Blog", "https://www.docker.com/blog/feed/", "tools_infra", "🐳", "tools"),
    
    # Developer Tools (4)
    ("VS Code Blog", "https://code.visualstudio.com/feed.xml", "tools_dev", "🎨", "tools"),
    ("JetBrains Blog", "https://blog.jetbrains.com/feed/", "tools_dev", "🔧", "tools"),
    ("Raycast Blog", "https://www.raycast.com/blog/rss.xml", "tools_dev", "🌙", "tools"),
    ("npm Blog", "https://blog.npmjs.org/rss.xml", "tools_dev", "📦", "tools"),
]

SEEN_FILE = Path("seen_entries.json")
INITIAL_HOURS = 48

# カテゴリ情報
CATEGORIES = {
    # Mobile
    "flutter": {"name": "Flutter & Dart", "emoji": "📦"},
    "swift": {"name": "Swift & iOS", "emoji": "🍎"},
    "android": {"name": "Android & Kotlin", "emoji": "🤖"},
    # Design
    "design_ux": {"name": "UI/UX Design", "emoji": "🎨"},
    "design_graphic": {"name": "Graphic Design", "emoji": "🖼️"},
    "design_typo": {"name": "Typography", "emoji": "📝"},
    "design_web": {"name": "Web Design", "emoji": "🌐"},
    # AI
    "ai_research": {"name": "AI Research", "emoji": "🧠"},
    "ai_tools": {"name": "AI Tools", "emoji": "🛠️"},
    "ai_news": {"name": "AI News", "emoji": "📰"},
    # Tools
    "tools_vcs": {"name": "Version Control & CI/CD", "emoji": "⚙️"},
    "tools_pm": {"name": "Project Management", "emoji": "📊"},
    "tools_infra": {"name": "Hosting & Infrastructure", "emoji": "☁️"},
    "tools_dev": {"name": "Developer Tools", "emoji": "🔧"},
}

# チャンネルごとのカテゴリマッピング
CHANNEL_CATEGORIES = {
    "mobile": ["flutter", "swift", "android"],
    "design": ["design_ux", "design_graphic", "design_typo", "design_web"],
    "ai": ["ai_research", "ai_tools", "ai_news"],
    "tools": ["tools_vcs", "tools_pm", "tools_infra", "tools_dev"],
}

# ==================== コア処理 ====================

def load_seen_entries():
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_seen_entries(seen):
    with open(SEEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def parse_entry_date(entry):
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    return datetime.now()

def make_title_exciting(title):
    """タイトルをワクワクする表現に変換"""
    if any(word in title.lower() for word in ['release', 'released', 'available', 'launches']):
        version = re.search(r'\d+\.\d+(?:\.\d+)?', title)
        if version:
            return f"v{version.group()} がリリース！🎉"
        return f"{title} 🎉"
    
    if any(word in title.lower() for word in ['beta', 'preview', 'rc', 'alpha']):
        return f"{title} ⚡️"
    
    if any(word in title.lower() for word in ['update', 'new', 'introducing', 'announce']):
        return f"{title} ✨"
    
    if any(word in title.lower() for word in ['fix', 'hotfix', 'patch']):
        return f"{title} 🔧"
    
    return title

def post_to_slack(channel_id, text=None, blocks=None, thread_ts=None):
    """Slack に投稿"""
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
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        data = response.json()
        
        if not data.get("ok"):
            print(f"⚠️  Slack 投稿エラー: {data.get('error', 'unknown')}")
            return None
        
        return data.get("ts")
        
    except Exception as e:
        print(f"⚠️  Slack 投稿失敗: {e}")
        return None

def check_feed(feed_name, feed_url, category, emoji, channel, seen_entries, is_first_run):
    """1つのフィードをチェック"""
    print(f"📡 {feed_name}")
    
    try:
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            return []
        
        new_entries = []
        cutoff_time = datetime.now() - timedelta(hours=INITIAL_HOURS) if is_first_run else None
        
        for entry in feed.entries[:10]:
            entry_id = entry.link if hasattr(entry, 'link') else entry.title
            
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
                "entry_id": entry_id
            })
        
        if new_entries:
            print(f"  ✅ {len(new_entries)} 件")
        
        return new_entries
        
    except Exception as e:
        print(f"  ⚠️  エラー: {e}")
        return []

def post_category_with_thread(category_key, entries, channel_id):
    """カテゴリの親メッセージとスレッド投稿"""
    if not entries:
        return
    
    cat_info = CATEGORIES[category_key]
    count = len(entries)
    
    parent_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{cat_info['emoji']} {cat_info['name']}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{count} 件*の新着情報\n💬 スレッドで詳細をチェック"
            }
        }
    ]
    
    print(f"\n  📤 {cat_info['name']} ({count}件)")
    
    thread_ts = post_to_slack(
        channel_id,
        text=f"{cat_info['name']} ({count}件)",
        blocks=parent_blocks
    )
    
    if not thread_ts:
        return
    
    for idx, item in enumerate(entries, 1):
        entry = item["entry"]
        title = entry.title if hasattr(entry, 'title') else "タイトルなし"
        link = entry.link if hasattr(entry, 'link') else ""
        
        exciting_title = make_title_exciting(title)
        
        post_to_slack(
            channel_id,
            text=f"{item['emoji']} {exciting_title}\n{link}",
            thread_ts=thread_ts
        )

def main():
    print(f"\n{'='*60}")
    print(f"🤖 RSS Feed Bot 起動（完全版: 80フィード）")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*60}\n")
    
    if not BOT_TOKEN:
        print("❌ SLACK_BOT_TOKEN が設定されていません")
        return
    
    seen_entries = load_seen_entries()
    is_first_run = len(seen_entries) == 0
    
    if is_first_run:
        print(f"🎉 初回実行: 過去 {INITIAL_HOURS} 時間分のみ通知\n")
    
    # チャンネルごとに分類
    channel_data = {
        "mobile": defaultdict(list),
        "design": defaultdict(list),
        "ai": defaultdict(list),
        "tools": defaultdict(list),
    }
    
    for feed_name, feed_url, category, emoji, channel in FEEDS:
        new_items = check_feed(feed_name, feed_url, category, emoji, channel, seen_entries, is_first_run)
        
        for item in new_items:
            channel_data[channel][category].append(item)
            seen_entries[item["entry_id"]] = True
    
    # 各チャンネルに投稿
    channels = [
        ("mobile", CHANNEL_MOBILE, "📱 モバイル開発"),
        ("design", CHANNEL_DESIGN, "🎨 デザイン"),
        ("ai", CHANNEL_AI, "🧠 AI & ML"),
        ("tools", CHANNEL_TOOLS, "⚙️ ツール・サービス"),
    ]
    
    total_new = 0
    
    for channel_key, channel_id, channel_name in channels:
        if not channel_id:
            continue
        
        print(f"\n{'='*60}")
        print(f"{channel_name}")
        print(f"{'='*60}")
        
        categories = CHANNEL_CATEGORIES[channel_key]
        for category in categories:
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
