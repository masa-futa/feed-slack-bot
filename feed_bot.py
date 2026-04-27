#!/usr/bin/env python3
"""
RSS → Slack Bot (GitHub Actions 版)
完全版: 全カテゴリ対応 + 2チャンネル対応
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

# チャンネルID（環境変数から取得、デフォルトは mobile-dev）
CHANNEL_MOBILE = os.environ.get("SLACK_CHANNEL_MOBILE", "")  # モバイル開発用
CHANNEL_DIGEST = os.environ.get("SLACK_CHANNEL_DIGEST", "")  # デザイン・AI・ツール用

# 監視する RSS/Atom フィード
FEEDS = [
    # ============================================
    # 📱 モバイル開発系（#mobile-dev に投稿）
    # ============================================
    
    # Flutter/Dart 系
    ("Flutter Releases", "https://github.com/flutter/flutter/releases.atom", "flutter", "🚀", "mobile"),
    ("Dart SDK Releases", "https://github.com/dart-lang/sdk/releases.atom", "flutter", "🎯", "mobile"),
    ("Flutter Blog", "https://medium.com/feed/flutter", "flutter", "📝", "mobile"),
    
    # Swift/iOS 系
    ("Swift.org Blog", "https://www.swift.org/atom.xml", "swift", "⚡️", "mobile"),
    ("Apple Developer News", "https://developer.apple.com/news/rss/news.rss", "swift", "🍎", "mobile"),
    ("Hacking with Swift", "https://www.hackingwithswift.com/articles/rss", "swift", "💻", "mobile"),
    ("SwiftLee", "https://www.avanderlee.com/feed/", "swift", "🎨", "mobile"),
    ("Swift by Sundell", "https://www.swiftbysundell.com/feed/", "swift", "💡", "mobile"),
    ("NSHipster", "https://nshipster.com/feed.xml", "swift", "🔍", "mobile"),
    ("Donny Wals", "https://www.donnywals.com/feed/", "swift", "📚", "mobile"),
    ("iOS Dev Weekly", "https://iosdevweekly.com/issues.rss", "swift", "📰", "mobile"),
    
    # Android/Kotlin 系
    ("Android Developers Blog", "https://android-developers.googleblog.com/feeds/posts/default", "android", "🤖", "mobile"),
    ("Kotlin Blog", "https://blog.jetbrains.com/kotlin/feed/", "android", "💡", "mobile"),
    ("Android Weekly", "https://androidweekly.net/rss", "android", "📰", "mobile"),
    ("Joe Birch", "https://joebirch.co/feed/", "android", "🎯", "mobile"),
    ("Styling Android", "https://blog.stylingandroid.com/feed/", "android", "🎨", "mobile"),
    
    # ============================================
    # 🎨 デザイン・AI・ツール系（#dev-digest に投稿）
    # ============================================
    
    # Design & UX
    ("Nielsen Norman Group", "https://www.nngroup.com/feed/rss/", "design", "🧪", "digest"),
    ("Smashing Magazine", "https://www.smashingmagazine.com/feed/", "design", "🎨", "digest"),
    ("A List Apart", "https://alistapart.com/main/feed/", "design", "📐", "digest"),
    ("UX Collective", "https://uxdesign.cc/feed", "design", "💡", "digest"),
    ("Figma Blog", "https://www.figma.com/blog/rss/", "design", "🔷", "digest"),
    ("Laws of UX", "https://lawsofux.com/rss.xml", "design", "⚖️", "digest"),
    
    # AI & ML
    ("OpenAI Blog", "https://openai.com/blog/rss/", "ai", "🧠", "digest"),
    ("Anthropic News", "https://www.anthropic.com/news/rss", "ai", "🤖", "digest"),
    ("Google AI Blog", "https://blog.research.google/feeds/posts/default", "ai", "🔬", "digest"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "ai", "🤗", "digest"),
    ("Simon Willison", "https://simonwillison.net/atom/everything/", "ai", "📝", "digest"),
    
    # Dev Tools & Services
    ("GitHub Blog", "https://github.blog/feed/", "tools", "⚙️", "digest"),
    ("GitLab Blog", "https://about.gitlab.com/atom.xml", "tools", "🦊", "digest"),
    ("Notion Blog", "https://www.notion.so/blog/rss", "tools", "📓", "digest"),
    ("Linear Blog", "https://linear.app/blog/rss.xml", "tools", "📊", "digest"),
    ("Vercel Blog", "https://vercel.com/blog/rss.xml", "tools", "▲", "digest"),
    ("Railway Blog", "https://blog.railway.app/rss.xml", "tools", "🚂", "digest"),
]

SEEN_FILE = Path("seen_entries.json")
INITIAL_HOURS = 48

# カテゴリ情報（表示用）
CATEGORIES = {
    "flutter": {"name": "Flutter & Dart", "emoji": "📦"},
    "swift": {"name": "Swift & iOS", "emoji": "🍎"},
    "android": {"name": "Android & Kotlin", "emoji": "🤖"},
    "design": {"name": "Design & UX", "emoji": "🎨"},
    "ai": {"name": "AI & ML", "emoji": "🧠"},
    "tools": {"name": "Dev Tools", "emoji": "⚙️"},
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
    """Slack に投稿（Bot Token 使用）"""
    if not BOT_TOKEN:
        print("❌ エラー: SLACK_BOT_TOKEN が設定されていません")
        return None
    
    if not channel_id:
        print("❌ エラー: チャンネルIDが設定されていません")
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
    """1つのフィードをチェックして新着を返す"""
    print(f"📡 チェック中: {feed_name}")
    
    try:
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            print(f"  ⚠️  フィード解析エラー")
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
            print(f"  ✅ {len(new_entries)} 件の新着")
        
        return new_entries
        
    except Exception as e:
        print(f"  ⚠️  エラー: {e}")
        return []

def post_category_with_thread(category_key, entries, channel_id):
    """カテゴリの親メッセージを投稿し、詳細をスレッドに"""
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
                "text": f"*{count} 件*の新着情報をキャッチ！\n💬 スレッドで詳細をチェック"
            }
        }
    ]
    
    print(f"\n📤 投稿中: {cat_info['name']} ({count}件)")
    
    thread_ts = post_to_slack(
        channel_id,
        text=f"{cat_info['name']} ({count}件の新着)",
        blocks=parent_blocks
    )
    
    if not thread_ts:
        print(f"  ❌ 親メッセージの投稿失敗")
        return
    
    print(f"  ✅ 親メッセージ投稿完了 (ts: {thread_ts})")
    
    for idx, item in enumerate(entries, 1):
        entry = item["entry"]
        title = entry.title if hasattr(entry, 'title') else "タイトルなし"
        link = entry.link if hasattr(entry, 'link') else ""
        
        exciting_title = make_title_exciting(title)
        
        thread_result = post_to_slack(
            channel_id,
            text=f"{item['emoji']} {exciting_title}\n{link}",
            thread_ts=thread_ts
        )
        
        if thread_result:
            print(f"  └─ ✅ [{idx}/{count}] {title[:40]}...")
        else:
            print(f"  └─ ❌ [{idx}/{count}] 投稿失敗")
    
    print(f"  🎉 カテゴリ完了")

def main():
    print(f"\n{'='*60}")
    print(f"🤖 RSS Feed Bot 起動（全カテゴリ版）")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*60}\n")
    
    if not BOT_TOKEN:
        print("❌ エラー: SLACK_BOT_TOKEN 環境変数が設定されていません")
        return
    
    seen_entries = load_seen_entries()
    is_first_run = len(seen_entries) == 0
    
    if is_first_run:
        print(f"🎉 初回実行: 過去 {INITIAL_HOURS} 時間分のみ通知します\n")
    
    # カテゴリごと・チャンネルごとに新着を収集
    mobile_entries = defaultdict(list)  # mobile チャンネル用
    digest_entries = defaultdict(list)  # digest チャンネル用
    
    for feed_name, feed_url, category, emoji, channel in FEEDS:
        new_items = check_feed(feed_name, feed_url, category, emoji, channel, seen_entries, is_first_run)
        
        for item in new_items:
            if channel == "mobile":
                mobile_entries[category].append(item)
            else:
                digest_entries[category].append(item)
            seen_entries[item["entry_id"]] = True
    
    # モバイル開発チャンネルに投稿
    if CHANNEL_MOBILE:
        print(f"\n{'='*60}")
        print(f"📱 モバイル開発チャンネルに投稿")
        print(f"{'='*60}")
        for category_key in ["flutter", "swift", "android"]:
            entries = mobile_entries[category_key]
            if entries:
                post_category_with_thread(category_key, entries, CHANNEL_MOBILE)
    
    # デザイン・AI・ツールチャンネルに投稿
    if CHANNEL_DIGEST:
        print(f"\n{'='*60}")
        print(f"🎨 開発周辺チャンネルに投稿")
        print(f"{'='*60}")
        for category_key in ["design", "ai", "tools"]:
            entries = digest_entries[category_key]
            if entries:
                post_category_with_thread(category_key, entries, CHANNEL_DIGEST)
    
    # 既読情報を保存
    save_seen_entries(seen_entries)
    
    total_new = sum(len(entries) for entries in mobile_entries.values()) + \
                sum(len(entries) for entries in digest_entries.values())
    
    print(f"\n{'='*60}")
    print(f"✨ 完了: {total_new} 件の新着記事を投稿しました")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
