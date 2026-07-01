import os
import requests
import json
from dotenv import load_dotenv

# --- 設定情報の外部読み込み ---
load_dotenv()

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "admin")

def create_ticket(subject, description):
    """新規の未割り当てチケット（ステータス: 新規(1)）を作成する"""
    url = f"{REDMINE_URL}/issues.json"
    
    data = {
        "issue": {
            "project_id": "ai-test",     # 対象プロジェクト
            "tracker_id": 1,             # バグ
            "status_id": 1,              # 新規
            "priority_id": 2,            # 通常
            "subject": subject,
            "description": description
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    res = requests.post(
        url,
        headers=headers,
        data=json.dumps(data),
        auth=(REDMINE_USER, REDMINE_PASSWORD)
    )
    
    if res.status_code == 201:
        print(f"  ✅ チケット作成成功: 「{subject}」")
    else:
        print(f"  ❌ チケット作成失敗: {res.status_code}")
        print(f"  エラー詳細: {res.text}")

def main():
    print("--- Redmine テストデータ自動投入スクリプト 起動 ---")
    
    # 投入するテストデータ（3つの異なる専門領域）
    test_tickets = [
        {
            "subject": "画面のボタンのデザインが崩れている",
            "description": "お世話になります。Google Chromeでログイン画面を開いた際、ログインボタンの右端が切れて表示されてしまいます。CSSの調整をお願いできますでしょうか。"
        },
        {
            "subject": "APIのレスポンスが500エラーになる",
            "description": "スマホアプリからユーザー情報を取得するAPI（/api/v1/users）を呼び出した際、サーバー側で500 Internal Server Errorが発生しています。ログの確認と修正をお願いします。"
        },
        {
            "subject": "ステージング環境のDBの接続が瞬断する",
            "description": "本日14時頃より、ステージング環境のアプリケーションからDBへの接続確認の際に、数分おきに接続瞬断エラーが多発しています。コネクションプールの設定等の確認をお願いします。"
        }
    ]
    
    for ticket in test_tickets:
        create_ticket(ticket["subject"], ticket["description"])
    
    print("\nすべてのテストデータの投入が完了しました！")

if __name__ == "__main__":
    main()