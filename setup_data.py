import os
import requests
import json
from dotenv import load_dotenv

# .envファイルから環境変数をロード
load_dotenv()

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "password")

# APIアクセスキーの手動転記を廃止し、安全な基本認証(Basic Auth)で全自動化
AUTH = (REDMINE_USER, REDMINE_PASSWORD)
HEADERS = {"Content-Type": "application/json"}

def setup_all():
    print("🚀 --- [最終確定版] 初期マスタデータ＆プロジェクト自動生成を開始します ---")
    
    # 15件のテストデータを完璧に受け止める4人のユーザー定義
    users_to_create = [
        {"login": "sato", "firstname": "隆", "lastname": "佐藤", "mail": "sato@example.com"},
        {"login": "suzuki", "firstname": "美咲", "lastname": "鈴木", "mail": "suzuki@example.com"},
        {"login": "takahashi", "firstname": "健太", "lastname": "高橋", "mail": "takahashi@example.com"},
        {"login": "koyanagi", "firstname": "明", "lastname": "小栁", "mail": "koyanagi@example.com"}
    ]
    roles_meta = {
        "sato": {"role": "インフラ・DB担当", "fixed_holidays": [2], "specific_holidays": ["2026-07-08"]},
        "suzuki": {"role": "フロントエンド担当", "fixed_holidays": [3], "specific_holidays": ["2026-07-09"]},
        "takahashi": {"role": "バックエンド・API担当", "fixed_holidays": [4], "specific_holidays": ["2026-07-03"]},
        "koyanagi": {"role": "PM・その他緊急担当", "fixed_holidays": [5, 6], "specific_holidays": []}
    }

    # ==========================================
    # 👥 1. 4人のユーザーアカウント作成
    # ==========================================
    print("👥 --- ユーザーのアカウント生成を開始します ---")
    created_members = []
    for u in users_to_create:
        data = {
            "user": {
                "login": u["login"], 
                "firstname": u["firstname"], 
                "lastname": u["lastname"], 
                "mail": u["mail"], 
                "password": "password123"
            }
        }
        res = requests.post(f"{REDMINE_URL}/users.json", auth=AUTH, headers=HEADERS, json=data)
        
        if res.status_code == 201:
            user_id = res.json()["user"]["id"]
            print(f"  ✅ ユーザー生成成功: {u['lastname']} {u['firstname']} (ID: {user_id})")
        else:
            # 既に存在する場合は競合を避けてIDを逆引き取得（再実行時のセーフティ）
            user_info = requests.get(f"{REDMINE_URL}/users.json?name={u['login']}", auth=AUTH, headers=HEADERS)
            if user_info.status_code == 200 and user_info.json().get("users"):
                user_id = user_info.json()["users"][0]["id"]
                print(f"  ℹ️ ユーザーは既に存在します: {u['login']} (ID: {user_id})")
            else:
                print(f"  ❌ ユーザー登録失敗: {u['login']} - {res.text}")
                continue

        login = u["login"]
        created_members.append({
            "id": user_id, "login": login, "name": f"{u['lastname']} {u['firstname']}",
            "role": roles_meta[login]["role"], "fixed_holidays": roles_meta[login]["fixed_holidays"], "specific_holidays": roles_meta[login]["specific_holidays"]
        })
            
    if created_members:
        # AIエンジンおよびダッシュボードが参照する「メンバーマスタ」をローカルに出力
        with open("members.json", "w", encoding="utf-8") as f:
            json.dump(created_members, f, indent=2, ensure_ascii=False)
        print("  → members.json の出力を完了しました。")

    # ==========================================
    # 📦 2. 検証用プロジェクト (ai-test) の作成
    # ==========================================
    print("\n📦 --- プロジェクトの自動生成を開始します ---")
    proj_data = {
        "project": {
            "name": "AI駆動開発検証",
            "identifier": "ai-test",
            "description": "Gemini 2.5 Flash による自動チケット仕分けのデモ検証プロジェクトです。"
        }
    }
    proj_res = requests.post(f"{REDMINE_URL}/projects.json", auth=AUTH, headers=HEADERS, json=proj_data)
    if proj_res.status_code == 201:
        print("  ✅ プロジェクト [ai-test] の作成に成功しました！")
    else:
        print(f"  ℹ️ プロジェクトは既に存在するか、作成をスキップしました。")

    # ==========================================
    # 🔗 3. ユーザーをプロジェクトへ「開発者」として紐付け
    # ==========================================
    print("\n🔗 --- ユーザーのプロジェクトへの所属紐付けを行います ---")
    for member in created_members:
        # 初期データのロードコマンドを実行しているため、ロールIDは「4（開発者）」で固定連携
        member_data = {"membership": {"user_id": member["id"], "role_ids": [4]}}
        m_res = requests.post(f"{REDMINE_URL}/projects/ai-test/memberships.json", auth=AUTH, headers=HEADERS, json=member_data)
        if m_res.status_code == 201:
            print(f"  ✅ {member['name']} をプロジェクト 'ai-test' に紐付けました。")
        else:
            print(f"  ❌ {member['name']} の紐付けに失敗: {m_res.text}")

    print("\n✨ すべての初期化マスタセットアップが正常に完了しました！")

if __name__ == "__main__":
    setup_all()