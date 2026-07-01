import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

# --- 設定情報の外部読み込み ---
load_dotenv()

# 環境ステージの取得（指定がない場合は安全のため Prod 扱いとする）
ENV_STAGE = os.getenv("ENV_STAGE", "Prod")

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "admin")
REDMINE_API_KEY = os.getenv("REDMINE_API_KEY")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("エラー: GEMINI_API_KEY が設定されていません。")

# Geminiクライアントの初期化
client = genai.Client(api_key=GEMINI_API_KEY)

def load_members():
    with open("members.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_unassigned_tickets():
    url = f"{REDMINE_URL}/issues.json?project_id=ai-test&status_id=1&assigned_to_id=!*"
    res = requests.get(url, auth=(REDMINE_USER, REDMINE_PASSWORD))
    return res.json().get("issues", []) if res.status_code == 200 else []

def ask_ai_for_assignee(ticket, members):
    prompt = f"""
あなたは優秀なITヘルプデスクの仕分け担当リーダーです。
以下の【チケット内容】を分析し、提供された【メンバーリスト】の中から、そのタスクの専門領域に最も合致する最適な担当者を1名選考してください。

【チケット内容】
・件名: {ticket['subject']}
・本文: {ticket.get('description', 'なし')}

【メンバーリスト】
{json.dumps(members, ensure_ascii=False, indent=2)}

【選考ルール】
1. チケットの課題とメンバーの「role」をマッチングさせてください。
2. 必ず1名だけ選出してください。

【出力フォーマット】
必ず以下のJSONフォーマットのみで返答してください。
{{
  "login": "選出したメンバーのlogin名",
  "reason": "そのメンバーを選んだ理由（1文で簡潔に）"
}}
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)
    except ClientError as ce:
        error_msg = str(ce)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print("  ⚠️ Gemini APIの無料枠制限（429）に達しました。このチケットのAI解析をスキップします。")
            return None
        else:
            print(f"  ❌ Gemini APIエラー: {ce}")
            return None
    except Exception as e:
        print(f"  ❌ 解析エラー: {e}")
        return None

def is_member_available(member):
    today_str = "2026-07-01"
    weekday = 3 # 水曜日
    if today_str in member.get("specific_holidays", []): return False
    if weekday in member.get("fixed_holidays", []): return False
    return True

def update_ticket_assignee(ticket_id, user_id):
    url = f"{REDMINE_URL}/issues/{ticket_id}.json"
    try:
        target_user_id = int(user_id)
    except Exception:
        target_user_id = user_id
        
    data = {"issue": {"assigned_to_id": target_user_id}}
    headers = {"Content-Type": "application/json"}
    
    res = requests.put(
        url, 
        headers=headers, 
        data=json.dumps(data),
        auth=(REDMINE_USER, REDMINE_PASSWORD)
    )
    
    if res.status_code in [200, 204]:
        return True
    else:
        print(f"  ❌ Redmine更新失敗 (ステータスコード: {res.status_code})")
        print(f"  ❌ エラー詳細: {res.text}")
        return False

def main():
    print(f"--- AI自動仕分け・シフト考慮システム 起動（ステージ: {ENV_STAGE}） ---")
    tickets = get_unassigned_tickets()
    members = load_members()
    
    print(f"未割り当てのチケットが {len(tickets)} 件見つかりました。\n")
    
    for ticket in tickets:
        print(f"📄 チケットID {ticket['id']}: 「{ticket['subject']}」を分析中...")
        
        ai_result = ask_ai_for_assignee(ticket, members)
        if not ai_result:
            continue
            
        primary_login = ai_result["login"]
        reason = ai_result["reason"]
        print(f"  🤖 AIの一次判定: {primary_login} ({reason})")
        
        selected_member = next((m for m in members if m["login"] == primary_login), None)
        
        if selected_member:
            if is_member_available(selected_member):
                print(f"  ✅ シフト確認: {selected_member['name']} さんは本日稼働可能です。")
                if update_ticket_assignee(ticket['id'], selected_member['id']):
                    print(f"  🎯 Redmine更新成功: 担当者を「{selected_member['name']}」に設定しました。")
            else:
                print(f"  ⚠️ シフト確認: {selected_member['name']} さんは本日お休みです！")
                pm_member = next((m for m in members if m["login"] == "koyanagi"), None)
                print(f"  🔀 迂回ロジック作動: PMの「{pm_member['name']}」へチケットをエスカレーションします。")
                if update_ticket_assignee(ticket['id'], pm_member['id']):
                    print(f"  🎯 Redmine更新成功: 担当者をPM「{pm_member['name']}」に代理設定しました。")
        
        # 【重要】Dev（開発環境）の場合のみ、レートリミット回避のために3秒待機する
        if ENV_STAGE == "Dev":
            time.sleep(3)
            
        print("-" * 50)

if __name__ == "__main__":
    main()