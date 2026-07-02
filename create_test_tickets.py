import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- 設定情報の外部読み込み ---
load_dotenv()

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "admin")
PROJECT_ID = "ai-test"

AUTH = (REDMINE_USER, REDMINE_PASSWORD)

def delete_all_current_issues():
    """1. 過去の古いテストチケットを根こそぎ全削除する機能"""
    print("🧹 過去のテストチケットをクレンジング中...")
    # 全ステータス(*)のチケットを取得
    url = f"{REDMINE_URL}/issues.json?project_id={PROJECT_ID}&status_id=*&limit=100"
    res = requests.get(url, auth=AUTH)
    
    if res.status_code == 200:
        issues = res.json().get("issues", [])
        if not issues:
            print("✨ 削除対象の古いチケットはありません。クリーンな状態です。")
            return
        
        for issue in issues:
            issue_id = issue["id"]
            del_url = f"{REDMINE_URL}/issues/{issue_id}.json"
            del_res = requests.delete(del_url, auth=AUTH)
            if del_res.status_code == 200:
                print(f"  🗑️ チケット #{issue_id} を削除しました。")
        print("✅ 過去データの全削除が完了しました！")
    else:
        print("⚠️ 過去チケットの取得に失敗しました。プロジェクトが存在するか確認してください。")

def create_rich_test_tickets():
    """2. マネジメント向けダッシュボードを彩る、多彩なバリエーションのチケットを自動生成"""
    print("\n🚀 デモ用のバリエーション豊かなテストデータを投入します...")
    
    # 日付の計算（今日、昨日、3日前）
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    three_days_ago_str = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    # デモ用のドラマチックなデータバリエーション定義
    test_tickets = [
        # --- Aパターン: 本日発生・未割り当て（AI自動仕分けエンジンに今すぐ喰わせるターゲット） ---
        {
            "subject": "【インフラ】本番ステージング環境のDBの接続が瞬断する",
            "description": "本日朝から、数回接続エラーを検知しました。解析をお願いします。",
            "status_id": 1, # 新規
            "due_date": today_str
        },
        {
            "subject": "【バックエンド】APIのレスポンスが稀に500エラーになる不具合",
            "description": "ユーザー情報の更新処理で、500Internal Server Errorが発生しています。",
            "status_id": 1, # 新規
            "due_date": None
        },
        
        # --- Bパターン: すでに終了しているタスク（「消化率」をきれいに上昇させるための実績データ） ---
        {
            "subject": "【フロント】画面のボタンのデザインが崩れている箇所の微調整",
            "description": "昨日の夕方に報告のあったUI崩れを修正してください。",
            "status_id": 3, # 終了 (Redmineの標準ID:3)
            "due_date": yesterday_str
        },
        
        # --- Cパターン: 期限超過（上司向けアラート「⚠️要フォロー！」を発動させるための遅延データ） ---
        {
            "subject": "【インフラ】ネットワーク疎通テストとセキュリティグループの見直し",
            "description": "3日前に対応完了予定だったタスクですが、詰まっています。",
            "status_id": 2, # 進行中
            "due_date": three_days_ago_str # 3日前（期限切れ！）
        }
    ]

    for item in test_tickets:
        payload = {
            "issue": {
                "project_id": PROJECT_ID,
                "subject": item["subject"],
                "description": item["description"],
                "status_id": item["status_id"]
            }
        }
        
        # 🌟 期日が設定されている場合は、Redmineの開始日整合性エラーを完全に回避する処理
        if item["due_date"]:
            payload["issue"]["due_date"] = item["due_date"]
            
            # 期日（YYYY-MM-DD）の1日前を開始日として自動計算してセット
            due_dt = datetime.strptime(item["due_date"], "%Y-%m-%d")
            start_dt = due_dt - timedelta(days=1)
            payload["issue"]["start_date"] = start_dt.strftime("%Y-%m-%d")

        url = f"{REDMINE_URL}/issues.json"
        res = requests.post(url, auth=AUTH, json=payload)
        
        if res.status_code == 201:
            new_id = res.json()["issue"]["id"]
            status_name = "新規" if item["status_id"] == 1 else ("進行中" if item["status_id"] == 2 else "終了")
            print(f"  ➕ チケット作成成功! -> #{new_id} [{status_name}] (期日: {item['due_date'] or '未設定'})")
        else:
            print(f"  ❌ 作成失敗: {res.text}")

    print("\n🎉 すべてのテストデータの作成が完了しました！")

if __name__ == "__main__":
    # 1. まず過去分をきれいに消し去る
    delete_all_current_issues()
    # 2. 次にバリエーション豊かなデータを流し込む
    create_rich_test_tickets()