#!/usr/bin/env python3
"""
RSS → Slack Bot (GitHub Actions 版)
完全版: 本物のスレッド機能対応
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
CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", "")

# 監視する RSS/Atom フィード
FEEDS = [
    # Flutter/Dart 系
    ("Flutter Releases", "https://github.com/flutter/flutter/releases.atom", "flutter", "🚀"),
    ("Dart SDK Releases", "https://github.com/dart-lang/sdk/releases.atom", "flutter", "🎯"),
    ("Flutter Blog", "https://medium.com/feed/flutter", "flutter", "📝"),
    
    # Swift/iOS 系 - 公式
    ("Swift.org Blog", "https://www.swift.org/atom.xml", "swift", "⚡️"),
    ("Apple Developer News", "https://developer.apple.com/news/rss/news.rss", "swift", "🍎"),
    
    # Swift/iOS 系 - コミュニティ
    ("Hacking with Swift", "https://www.hackingwithswift.com/articles/rss", "swift", "💻"),
    ("SwiftLee", "https://www.avanderlee.com/feed/", "swift", "🎨"),
    ("Swift by Sundell", "https://www.swiftbysundell.com/feed/", "swift", "💡"),
    ("NSHipster", "https://nshipster.com/feed.xml", "swift", "🔍"),
    ("Donny Wals", "https://www.donnywals.com/feed/", "swift", "📚"),
    
    # 週次キュレーション
    ("iOS Dev Weekly", "https://iosdevweekly.com/issues.rss", "weekly", "📰"),
]

SEEN_FILE = Path("seen_entries.json")
INITIAL_HOURS = 48

# カテゴリ情報
CATEGORIES = {
    "flutter": {
        "name": "Flutter & Dart Updates",
        "emoji": "📦",
    },
    "swift": {
        "name": "Swift & iOS News",
        "emoji": "🍎",
    },
    "weekly": {
        "name": "Weekly Digest",
        "emoji": "📰",
    }
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
    # リリース系
    if any(word in title.lower() for word in ['release', 'released', 'available', 'launches']):
        version = re.search(r'\d+\.\d+(?:\.\d+)?', title)
        if version:
            return f"v{version.group()} がリリース！🎉"
        return f"{title} 🎉"
    
    # ベータ・プレビュー系
    if any(word in title.lower() for word in ['beta', 'preview', 'rc', 'alpha']):
        return f"{title} ⚡️"
    
    # アップデート・新機能系
    if any(word in title.lower() for word in ['update', 'new', 'introducing', 'announce']):
        return f"{title} ✨"
    
    # 修正系
    if any(word in title.lower() for word in ['fix', 'hotfix', 'patch']):
        return f"{title} 🔧"
    
    # そのまま返す
    return title

def post_to_slack(text=None, blocks=None, thread_ts=None):
    """Slack に投稿（Bot Token 使用）"""
    if not BOT_TOKEN:
        print("❌ エラー: SLACK_BOT_TOKEN が設定されていません")
        return None
    
    if not CHANNEL_ID:
        print("❌ エラー: SLACK_CHANNEL_ID が設定されていません")
        return None
    
    payload = {
        "channel": CHANNEL_ID,
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
        
        # スレッドのタイムスタンプを返す
        return data.get("ts")
        
    except Exception as e:
        print(f"⚠️  Slack 投稿失敗: {e}")
        return None

def check_feed(feed_name, feed_url, category, emoji, seen_entries, is_first_run):
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
                "entry_id": entry_id
            })
        
        if new_entries:
            print(f"  ✅ {len(new_entries)} 件の新着")
        
        return new_entries
        
    except Exception as e:
        print(f"  ⚠️  エラー: {e}")
        return []

def post_category_with_thread(category_key, entries):
    """カテゴリの親メッセージを投稿し、詳細をスレッドに"""
    if not entries:
        return
    
    cat_info = CATEGORIES[category_key]
    count = len(entries)
    
    # 親メッセージ（カテゴリサマリー）
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
    
    # 親メッセージを投稿
    thread_ts = post_to_slack(
        text=f"{cat_info['name']} ({count}件の新着)",
        blocks=parent_blocks
    )
    
    if not thread_ts:
        print(f"  ❌ 親メッセージの投稿失敗")
        return
    
    print(f"  ✅ 親メッセージ投稿完了 (ts: {thread_ts})")
    
    # スレッドに各エントリを投稿
    for idx, item in enumerate(entries, 1):
        entry = item["entry"]
        title = entry.title if hasattr(entry, 'title') else "タイトルなし"
        link = entry.link if hasattr(entry, 'link') else ""
        
        # ワクワクするタイトル
        exciting_title = make_title_exciting(title)
        
        # スレッドに投稿
        thread_result = post_to_slack(
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
    print(f"🤖 RSS Feed Bot 起動（スレッド対応版）")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*60}\n")
    
    if not BOT_TOKEN:
        print("❌ エラー: SLACK_BOT_TOKEN 環境変数が設定されていません")
        return
    
    if not CHANNEL_ID:
        print("❌ エラー: SLACK_CHANNEL_ID 環境変数が設定されていません")
        return
    
    seen_entries = load_seen_entries()
    is_first_run = len(seen_entries) == 0
    
    if is_first_run:
        print(f"🎉 初回実行: 過去 {INITIAL_HOURS} 時間分のみ通知します\n")
    
    # カテゴリごとに新着を収集
    category_entries = defaultdict(list)
    
    for feed_name, feed_url, category, emoji in FEEDS:
        new_items = check_feed(feed_name, feed_url, category, emoji, seen_entries, is_first_run)
        
        for item in new_items:
            category_entries[category].append(item)
            seen_entries[item["entry_id"]] = True
    
    # カテゴリごとに投稿（スレッド形式）
    total_new = 0
    for category_key in ["flutter", "swift", "weekly"]:
        entries = category_entries[category_key]
        if entries:
            post_category_with_thread(category_key, entries)
            total_new += len(entries)
    
    # 既読情報を保存
    save_seen_entries(seen_entries)
    
    print(f"\n{'='*60}")
    print(f"✨ 完了: {total_new} 件の新着記事を投稿しました")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
