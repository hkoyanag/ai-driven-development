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

# .env からプロジェクトID、各種デフォルトIDを動的ロード
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

def create_timeline_test_tickets():
    print("🚀 時系列検証用データ（7/4, 7/5, 7/6 各4件・計12件）を投入します...")
    
    # 2026年7月6日（本日）を基準に動的計算
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    
    # テストシナリオに沿った12件のチケット定義
    test_tickets = [
        # --- 📅 7/6 (本日作成・本日締切セクター：4件) ---
        {"subject": "【インフラ】7/6 本日のネットワーク疎通エラー対応", "desc": "ステージング環境のSG見直し要請。", "start": today, "due": today},
        {"subject": "【フロント】7/6 本日のログイン画面ボタンデザイン崩れ修正", "desc": "スマホ表示でボタンが見切れる不具合のCSS調整。", "start": today, "due": today},
        {"subject": "【バックエンド】7/6 本日のAPIレスポンス500エラー調査", "desc": "ヌルポによる決済履歴取得失敗のバグ修正。", "start": today, "due": today},
        {"subject": "【インフラ】7/6 本日のDockerコンテナ容量逼迫にともなうログローテーション", "desc": "ディスク逼迫対策のための即時対応。", "start": today, "due": today},

        # --- 📅 7/5 (昨日作成・昨日〜本日締切セクター：4件) ---
        {"subject": "【インフラ】7/5 昨日から発生しているSSL証明書の更新計画策定", "desc": "来期の入れ替え手順書の作成調整。", "start": yesterday, "due": today},
        {"subject": "【フロント】7/5 昨日起票のお気に入り一覧画面レンダリング高速化", "desc": "Lazy Loading適用のフロントエンド改善。", "start": yesterday, "due": today},
        {"subject": "【バックエンド】7/5 昨日からのCSVエクスポート機能メモリリーク調査", "desc": "大量出力時のクラッシュ対策バッチ化。", "start": yesterday, "due": today},
        {"subject": "【フロント】7/5 昨日起票のレスポンシブ幅のCSSバグ修正", "desc": "iPad表示時の見切れ対応。", "start": yesterday, "due": today},

        # --- 📅 7/4 (一昨日作成・すでに期日超過セクター：4件) ---
        # ⚠️ もともとの仕様なら「昨日まで（7/5）」のチケットを割り当てするため、ここは処理対象外になる想定
        {"subject": "【インフラ】7/4 過去分の死活監視アラート閾値チューニング", "desc": "古い夜間バッチの高負荷アラート誤検知対策。", "start": two_days_ago, "due": yesterday - timedelta(days=1)},
        {"subject": "【フロント】7/4 過去分のダークモードテキスト視認性向上", "desc": "背景と同化しているカラーコードの修正。", "start": two_days_ago, "due": yesterday - timedelta(days=1)},
        {"subject": "【バックエンド】7/4 過去分のJWT認証トークン有効期限変更ロジック", "desc": "リフレッシュトークンの古い実装見直し。", "start": two_days_ago, "due": yesterday - timedelta(days=1)},
        {"subject": "【バックエンド】7/4 過去分の新規ユーザー登録バリデーション強化", "desc": "特殊文字挿入時の文字化け不具合の修正。", "start": two_days_ago, "due": yesterday - timedelta(days=1)}
    ]

    for i, t in enumerate(test_tickets, 1):
        url = f"{REDMINE_URL}/issues.json"
        start_str = t["start"].strftime("%Y-%m-%d")
        due_str = t["due"].strftime("%Y-%m-%d")
        
        payload = {
            "issue": {
                "project_id": REDMINE_PROJECT_ID,
                "tracker_id": TRACKER_ID,
                "status_id": STATUS_ID,
                "priority_id": PRIORITY_ID,
                "subject": t["subject"],
                "description": t["desc"],
                "start_date": start_str,
                "due_date": due_str
            }
        }

        res = requests.post(url, auth=AUTH, json=payload, timeout=5)
        if res.status_code == 201:
            print(f"  [{i}/12] 投入成功: {t['subject']} (期日: {due_str})")
        else:
            print(f"  ❌ [{i}/12] 投入失敗: {res.text}")

    print("\n✨ 時系列シミュレーションデータ（計12件）のクリーンセットアップが完了しました！")

if __name__ == "__main__":
    clear_existing_issues()
    print("-" * 50)
    create_timeline_test_tickets()