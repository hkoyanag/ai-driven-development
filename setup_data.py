import requests
import json

REDMINE_URL = "http://localhost:3000"
API_KEY = "82bcf964ed56fa3e0d41459115f3c8808be4aae8"

headers = {
    "X-Redmine-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def create_users():
    print("--- ユーザーの作成と members.json の更新を開始します ---")
    created_members = []
    users_to_create = [
        {"login": "sato", "firstname": "隆", "lastname": "佐藤", "mail": "sato@example.com"},
        {"login": "suzuki", "firstname": "美咲", "lastname": "鈴木", "mail": "suzuki@example.com"},
        {"login": "takahashi", "firstname": "健太", "lastname": "高橋", "mail": "takahashi@example.com"},
        {"login": "koyanagi", "firstname": "明", "lastname": "小栁", "mail": "koyanagi@example.com"}
    ]
    roles = {
        "sato": {"role": "インフラ・DB担当", "fixed_holidays": [2], "specific_holidays": ["2026-07-08"]},
        "suzuki": {"role": "フロントエンド担当", "fixed_holidays": [3], "specific_holidays": ["2026-07-09"]},
        "takahashi": {"role": "バックエンド・API担当", "fixed_holidays": [4], "specific_holidays": ["2026-07-03"]},
        "koyanagi": {"role": "PM・その他緊急担当", "fixed_holidays": [5, 6], "specific_holidays": []}
    }

    for u in users_to_create:
        data = {"user": {"login": u["login"], "firstname": u["firstname"], "lastname": u["lastname"], "mail": u["mail"], "password": "password123"}}
        res = requests.post(f"{REDMINE_URL}/users.json", headers=headers, json=data)
        if res.status_code == 201:
            user_id = res.json()["user"]["id"]
            print(f"成功: {u['lastname']} {u['firstname']} (ID: {user_id})")
            login = u["login"]
            created_members.append({
                "id": user_id, "login": login, "name": f"{u['lastname']} {u['firstname']}",
                "role": roles[login]["role"], "fixed_holidays": roles[login]["fixed_holidays"], "specific_holidays": roles[login]["specific_holidays"]
            })
        else:
            # 既に存在する場合はRedmineからIDを検索して取得し、members.jsonを正しく構成する
            user_info = requests.get(f"{REDMINE_URL}/users.json?name={u['login']}", headers=headers)
            if user_info.status_code == 200 and user_info.json().get("users"):
                user_id = user_info.json()["users"][0]["id"]
                login = u["login"]
                created_members.append({
                    "id": user_id, "login": login, "name": f"{u['lastname']} {u['firstname']}",
                    "role": roles[login]["role"], "fixed_holidays": roles[login]["fixed_holidays"], "specific_holidays": roles[login]["specific_holidays"]
                })
            print(f"既存ユーザーのため登録スキップ（members.json 用のIDは取得完了）: {u['login']}")
            
    if created_members:
        with open("members.json", "w", encoding="utf-8") as f:
            json.dump(created_members, f, indent=2, ensure_ascii=False)
        print("→ members.json を最新の状態に更新しました。")

if __name__ == "__main__":
    create_users()