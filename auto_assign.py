import requests
import json

# 設定情報
REDMINE_URL = "http://localhost:3000"
API_KEY = "82bcf964ed56f5a3e0d41459115f3c8808be4ae8"

headers = {
    "X-Redmine-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def get_unassigned_tickets():
    """特定のプロジェクト(ai-test)から、新規かつ未割り当てのチケットを取得する"""
    # 【修正箇所】assigned_to_id=none を assigned_to_id=!* (Redmineの未割り当て記号) に変更
    url = f"{REDMINE_URL}/issues.json?project_id=ai-test&status_id=1&assigned_to_id=!*"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("issues", [])
    else:
        print(f"エラーが発生しました（ステータスコード）: {response.status_code}")
        print(f"エラーの詳細ログ: {response.text}")
        return []

if __name__ == "__main__":
    print("--- チケット取得テストを開始します ---")
    tickets = get_unassigned_tickets()
    print(f"現在、未割り当ての新規チケットは {len(tickets)} 件です。")
    for ticket in tickets:
        print(f"--- チケットID: {ticket['id']} ---")
        print(f"件名: {ticket['subject']}")