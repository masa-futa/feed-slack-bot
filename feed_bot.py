#!/usr/bin/env python3
"""
RSS → Slack Bot (GitHub Actions 版)

GitHub Actions で動作させる場合:
1. リポジトリの Settings → Secrets and variables → Actions
2. New repository secret で SLACK_WEBHOOK_URL を登録
3. .github/workflows/feed-bot.yml が自動実行される

ローカルでテストする場合:
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
python feed_bot.py
"""

import feedparser
import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ==================== 設定 ====================

# Slack Webhook URL (環境変数から取得)
WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# 監視する RSS/Atom フィード
FEEDS = [
    # Flutter 系 - 公式リリース
    ("Flutter Releases", "https://github.com/flutter/flutter/releases.atom", "🔵"),
    ("Dart SDK Releases", "https://github.com/dart-lang/sdk/releases.atom", "🔵"),
    ("Flutter Blog", "https://medium.com/feed/flutter", "🔵"),
    
    # Swift/iOS 系 - 公式
    ("Swift.org Blog", "https://www.swift.org/atom.xml", "🍎"),
    ("Apple Developer News", "https://developer.apple.com/news/rss/news.rss", "🍎"),
    
    # Swift/iOS 系 - 良質ブログ
    ("Hacking with Swift", "https://www.hackingwithswift.com/articles/rss", "🍎"),
    ("SwiftLee", "https://www.avanderlee.com/feed/", "🍎"),
    ("Swift by Sundell", "https://www.swiftbysundell.com/feed/", "🍎"),
    ("NSHipster", "https://nshipster.com/feed.xml", "🍎"),
    ("Donny Wals", "https://www.donnywals.com/feed/", "🍎"),
    
    # 週次キュレーション
    ("iOS Dev Weekly", "https://iosdevweekly.com/issues.rss", "📰"),
]

# 既読管理ファイル（Git で管理される）
SEEN_FILE = Path("seen_entries.json")

# 初回実行時に過去何時間分まで遡るか
INITIAL_HOURS = 48

# ==================== コア処理 ====================

def load_seen_entries():
    """既読エントリを読み込む"""
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️  既読ファイルが破損しています。新規作成します。")
            return {}
    return {}

def save_seen_entries(seen):
    """既読エントリを保存"""
    with open(SEEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def parse_entry_date(entry):
    """エントリの日付をパース"""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    return datetime.now()

def format_slack_message(feed_name, entry, emoji):
    """Slack メッセージを整形"""
    title = entry.title if hasattr(entry, 'title') else "タイトルなし"
    link = entry.link if hasattr(entry, 'link') else ""
    
    # 説明文（あれば先頭150文字）
    summary = ""
    if hasattr(entry, 'summary'):
        # HTML タグを簡易除去
        import re
        clean_summary = re.sub('<[^<]+?>', '', entry.summary)
        summary = clean_summary[:150].replace('\n', ' ').strip()
        if len(clean_summary) > 150:
            summary += "..."
    
    # 日付
    entry_date = parse_entry_date(entry)
    date_str = entry_date.strftime("%Y-%m-%d")
    
    # Slack Block Kit 形式
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{feed_name}*\n<{link}|{title}>"
            }
        }
    ]
    
    if summary:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{date_str} • {summary}"
                }
            ]
        })
    else:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": date_str
                }
            ]
        })
    
    return {"blocks": blocks}

def send_to_slack(message):
    """Slack に投稿"""
    if not WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URL が設定されていません")
        return False
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=message,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if response.status_code != 200:
            print(f"⚠️  Slack 投稿エラー: {response.status_code}")
            return False
        return True
    except Exception as e:
        print(f"⚠️  Slack 投稿失敗: {e}")
        return False

def check_feed(feed_name, feed_url, emoji, seen_entries, is_first_run):
    """1つのフィードをチェック"""
    print(f"📡 チェック中: {feed_name}")
    
    try:
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            print(f"  ⚠️  フィード解析エラー")
            return 0
        
        new_count = 0
        cutoff_time = datetime.now() - timedelta(hours=INITIAL_HOURS) if is_first_run else None
        
        # 新しいエントリから順に処理（最大10件まで）
        for entry in feed.entries[:10]:
            # ユニークIDを生成
            entry_id = entry.link if hasattr(entry, 'link') else entry.title
            
            # 既読チェック
            if entry_id in seen_entries:
                continue
            
            # 初回実行時は古い記事をスキップ
            if is_first_run and cutoff_time:
                entry_date = parse_entry_date(entry)
                if entry_date < cutoff_time:
                    seen_entries[entry_id] = True
                    continue
            
            # Slack に投稿
            message = format_slack_message(feed_name, entry, emoji)
            if send_to_slack(message):
                seen_entries[entry_id] = True
                new_count += 1
                print(f"  ✅ {entry.title[:50]}...")
            else:
                print(f"  ❌ 投稿失敗: {entry.title[:50]}...")
        
        return new_count
        
    except Exception as e:
        print(f"  ⚠️  エラー: {e}")
        return 0

def send_daily_summary(total_new):
    """日次サマリーを投稿"""
    now = datetime.now()
    
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 本日のフィードまとめ ({now.strftime('%Y-%m-%d')})"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• 新着記事: *{total_new}* 件\n• 監視フィード: *{len(FEEDS)}* 個"
                }
            }
        ]
    }
    
    send_to_slack(message)

def main():
    """メイン処理"""
    print(f"\n{'='*60}")
    print(f"🤖 RSS Feed Bot 起動 (GitHub Actions)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*60}\n")
    
    # Webhook URL チェック
    if not WEBHOOK_URL:
        print("❌ エラー: SLACK_WEBHOOK_URL 環境変数が設定されていません")
        print("   GitHub の Settings → Secrets で設定してください")
        return
    
    # 既読情報を読み込み
    seen_entries = load_seen_entries()
    is_first_run = len(seen_entries) == 0
    
    if is_first_run:
        print(f"🎉 初回実行: 過去 {INITIAL_HOURS} 時間分のみ通知します\n")
    
    # 各フィードをチェック
    total_new = 0
    for feed_name, feed_url, emoji in FEEDS:
        new_count = check_feed(feed_name, feed_url, emoji, seen_entries, is_first_run)
        total_new += new_count
    
    # 既読情報を保存
    save_seen_entries(seen_entries)
    
    # 日次サマリーを投稿（新着がある場合のみ）
    if total_new > 0:
        send_daily_summary(total_new)
    
    print(f"\n{'='*60}")
    print(f"✨ 完了: {total_new} 件の新着記事を投稿しました")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
