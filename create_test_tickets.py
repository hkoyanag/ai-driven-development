import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "password")
AUTH = (REDMINE_USER, REDMINE_PASSWORD)

# 🌟 .env からプロジェクトID、各種デフォルトIDを動的ロード
REDMINE_PROJECT_ID = os.getenv("REDMINE_PROJECT_ID", "ai-test")
TRACKER_ID = int(os.getenv("REDMINE_DEFAULT_TRACKER_ID", "1"))
STATUS_ID = int(os.getenv("REDMINE_DEFAULT_STATUS_ID", "1"))
PRIORITY_ID = int(os.getenv("REDMINE_DEFAULT_PRIORITY_ID", "2"))

def clear_existing_issues():
    print("🧹 既存の検証用チケットをクレンジング中...")
    url = f"{REDMINE_URL}/issues.json?project_id={REDMINE_PROJECT_ID}&status_id=*"
    try:
        res = requests.get(url, auth=AUTH, timeout=5)
        if res.status_code == 200:
            issues = res.json().get("issues", [])
            for issue in issues:
                del_url = f"{REDMINE_URL}/issues/{issue['id']}.json"
                requests.delete(del_url, auth=AUTH, timeout=5)
            print(f"✅ 既存の {len(issues)} 件のチケットを削除し、環境をクリーンにしました。")
    except Exception as e:
        print(f"⚠️ クレンジング中にエラーが発生しました: {e}")

def create_rich_test_tickets():
    print("🚀 バリエーション豊かな検証用データ（15件）をRedmineへ投入します...")
    
    today = datetime.now()
    three_days_ago = today - timedelta(days=3)
    five_days_ago = today - timedelta(days=5)
    
    test_tickets = [
        # --- 【インフラ】セクター ---
        {"subject": "【インフラ】ネットワーク疎通テストとセキュリティグループの見直し", "desc": "ステージング環境から外部APIセクターへの疎通テストが一部遮断されているため、SGの設定変更をお願いします。", "start": today, "due": (today + timedelta(days=2))},
        {"subject": "【インフラ】本本ステージング環境のDBの接続が瞬断する", "desc": "1時間に数回、コネクションプールが枯渇するような挙動があり瞬断が発生しています。ログの調査を要請。", "start": today, "due": today},
        {"subject": "【インフラ】死活監視アラートの閾値チューニング（CPU高負荷対策）", "desc": "夜間のバッチ処理中にCPU使用率が95%を超え、アラートが誤検知されています。閾値を98%へ緩和してください。", "start": today, "due": (today + timedelta(days=5))},
        {"subject": "【インフラ】SSL証明書の更新作業とWebサーバー再起動の計画策定", "desc": "来月末に期限を迎えるSSL/TLS証明書の入れ替え手順書の作成および本番反映のスケジュール調整。", "start": five_days_ago, "due": (today - timedelta(days=2))},
        {"subject": "【インフラ】検証用Dockerコンテナのディスク容量逼迫による不要ログの削除", "desc": "/var/lib/docker/containers 内のログが肥大化しディスクを圧迫しています。ローテーション設定を導入してください。", "start": today, "due": None},

        # --- 【フロントエンド】セクター ---
        {"subject": "【フロント】画面のボタンのデザインが崩れている箇所の微調整", "desc": "スマホ表示（iPhone14/SE）の際、ヘッダー内の「ログイン」ボタンがメニューバーの下に隠れてクリックできません。", "start": today, "due": (today + timedelta(days=1))},
        {"subject": "【フロント】マイページのお気に入り一覧画面における画像読み込みの高速化", "desc": "画像コンポーネントに Lazy Loading（遅延読み込み）を適用し、初期表示のレンダリング速度を改善してください。", "start": today, "due": (today + timedelta(days=4))},
        {"subject": "【フロント】レスポンシブ対応：入稿フォームのテキストエリア幅調整", "desc": "iPad Pro（横画面）の時だけ、入力フォームの右端が5pxほど見切れてしまう不具合のCSS修正。", "start": today, "due": (today + timedelta(days=3))},
        {"subject": "【フロント】ダークモード切り替え時のテキスト視認性向上とカラーコード修正", "desc": "ダークモードにした際、特定のリンクテキストが濃い青のままになり背景と同化して読めない不具合。", "start": three_days_ago, "due": (today - timedelta(days=1))},
        {"subject": "【フロント】新規機能：FAQページのハンバーガーメニュー開閉アニメーション追加", "desc": "アコーディオンがパッと切り替わるのを、0.3秒かけてフワッと開閉するスムーズなアニメーションに変更。", "start": today, "due": None},

        # --- 【バックエンド】セクター ---
        {"subject": "【バックエンド】APIのレスポンスが稀に500エラーになる不具合", "desc": "特定のユーザーIDでログインし、決済履歴を取得しようとするとヌルポ（NullPointerException）で500エラーが返ります。", "start": today, "due": (today + timedelta(days=2))},
        {"subject": "【バックエンド】CSVエクスポート機能のメモリリーク調査と一括処理のバッチ化", "desc": "1万件以上のユーザーデータを一度に出力しようとすると、Out of Memoryでプロセスがクラッシュします。", "start": today, "due": (today + timedelta(days=6))},
        {"subject": "【バックエンド】認証トークン（JWT）の有効期限延長およびリフレッシュトークンロジック実装", "desc": "セキュリティ強化に伴い、アクセストークンの有効期限を15分に短縮し、リフレッシュトークンによる再認可を実装。", "start": today, "due": (today + timedelta(days=7))},
        {"subject": "【バックエンド】新規ユーザー登録時のバリデーションに特殊文字の弾き処理を追加", "desc": "ユーザー名に絵文字や特定の記号が含まれている場合、DB挿入時に文字化けする問題のバリデーション強化。", "start": today, "due": (today + timedelta(days=1))},
        {"subject": "【バックエンド】大量アクセス時のダッシュボード集計SQLのインデックス最適化", "desc": "検索時のJOIN処理が非常に重く、スロークエリログに記録されています。複合インデックスを貼って速度改善してください。", "start": today, "due": None}
    ]

    for i, t in enumerate(test_tickets, 1):
        url = f"{REDMINE_URL}/issues.json"
        start_str = t["start"].strftime("%Y-%m-%d")
        due_str = t["due"].strftime("%Y-%m-%d") if t["due"] else None
        
        payload = {
            "issue": {
                "project_id": REDMINE_PROJECT_ID,
                "tracker_id": TRACKER_ID,
                "status_id": STATUS_ID,
                "priority_id": PRIORITY_ID,
                "subject": t["subject"],
                "description": t["desc"],
                "start_date": start_str
            }
        }
        if due_str:
            payload["issue"]["due_date"] = due_str

        res = requests.post(url, auth=AUTH, json=payload, timeout=5)
        if res.status_code == 201:
            print(f"  [{i}/15] 投入成功: {t['subject']}")
        else:
            print(f"  ❌ [{i}/15] 投入失敗: {res.text}")

    print("\n✨ 15件の検証データの初期セットアップが完了しました！")

if __name__ == "__main__":
    clear_existing_issues()
    print("-" * 50)
    create_rich_test_tickets()