import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "password")

# 🌟 .env からプロジェクトIDをロード
REDMINE_PROJECT_ID = os.getenv("REDMINE_PROJECT_ID", "ai-test")

AUTH = (REDMINE_USER, REDMINE_PASSWORD)
HEADERS = {"Content-Type": "application/json"}

def setup_all():
    print("🚀 --- [Day 3 最終完全版] 全員2025/4/1参画マスタ生成を開始します ---")
    
    today = datetime.now()
    half_year_later = today + timedelta(days=180)
    
    # 🌟 全員の参画開始日を「2025-04-01」に美しく統一
    users_to_create = [
        {"login": "sato", "firstname": "隆", "lastname": "佐藤", "mail": "sato@example.com", "skills": "Network, DB, Security", "fixed_join": "2025-04-01", "fixed_exit": "2026-07-02"}, # 昨日期限切れ
        {"login": "suzuki", "firstname": "美咲", "lastname": "鈴木", "mail": "suzuki@example.com", "skills": "React, CSS, HTML5", "fixed_join": "2025-04-01"},
        {"login": "takahashi", "firstname": "健太", "lastname": "高橋", "mail": "takahashi@example.com", "skills": "Python, FastAPI, API Design", "fixed_join": "2025-04-01"},
        {"login": "koyanagi", "firstname": "明", "lastname": "小栁", "mail": "koyanagi@example.com", "skills": "PM, Management, Emergency", "fixed_join": "2025-04-01"}
    ]
    
    roles_meta = {
        "sato": {"role": "インフラ・DB担当", "fixed_holidays": [2], "specific_holidays": ["2026-07-08"]},
        "suzuki": {"role": "フロントエンド担当", "fixed_holidays": [3], "specific_holidays": ["2026-07-09"]},
        "takahashi": {"role": "バックエンド・API担当", "fixed_holidays": [4], "specific_holidays": ["2026-07-03"]}, # 本日お休み
        "koyanagi": {"role": "PM・その他緊急担当", "fixed_holidays": [5, 6], "specific_holidays": []}
    }

    created_members = []
    for u in users_to_create:
        data = {"user": {"login": u["login"], "firstname": u["firstname"], "lastname": u["lastname"], "mail": u["mail"], "password": "password123"}}
        res = requests.post(f"{REDMINE_URL}/users.json", auth=AUTH, headers=HEADERS, json=data)
        
        user_id = None
        if res.status_code == 201:
            user_id = res.json()["user"]["id"]
            print(f"  ✅ ユーザー生成: {u['lastname']} (ID: {user_id})")
        else:
            user_info = requests.get(f"{REDMINE_URL}/users.json?name={u['login']}", auth=AUTH, headers=HEADERS)
            if user_info.status_code == 200 and user_info.json().get("users"):
                user_id = user_info.json()["users"][0]["id"]
                print(f"  ℹ️ 既存ユーザー: {u['login']} (ID: {user_id})")

        if user_id:
            login = u["login"]
            m_join = u["fixed_join"]
            m_exit = u.get("fixed_exit", half_year_later.strftime("%Y-%m-%d"))
            
            created_members.append({
                "id": user_id, 
                "login": login, 
                "name": f"{u['lastname']} {u['firstname']}",
                "role": roles_meta[login]["role"],
                "skills": u["skills"],
                "join_date": m_join,
                "exit_date": m_exit,
                "fixed_holidays": roles_meta[login]["fixed_holidays"], 
                "specific_holidays": roles_meta[login]["specific_holidays"]
            })
            
    with open("members.json", "w", encoding="utf-8") as f:
        json.dump(created_members, f, indent=2, ensure_ascii=False)
    
    # プロジェクト作成
    proj_data = {"project": {"name": "AI駆動開発検証", "identifier": REDMINE_PROJECT_ID}}
    requests.post(f"{REDMINE_URL}/projects.json", auth=AUTH, headers=HEADERS, json=proj_data)
    
    for m in created_members:
        requests.post(f"{REDMINE_URL}/projects/{REDMINE_PROJECT_ID}/memberships.json", auth=AUTH, headers=HEADERS, json={"membership": {"user_id": m["id"], "role_ids": [4]}})

    print("✨ マスタセットアップ完了！")

if __name__ == "__main__":
    setup_all()