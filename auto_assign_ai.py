import os
import requests
import json
import time
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. 設定情報・環境変数の読み込み ---
load_dotenv()

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "admin")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ENV_STAGE = os.getenv("ENV_STAGE", "Dev")
AI_EXEC_MODE = os.getenv("AI_EXEC_MODE", "Manual")

try:
    AI_CHECK_INTERVAL = int(os.getenv("AI_CHECK_INTERVAL", "5"))
except ValueError:
    AI_CHECK_INTERVAL = 5

AUTH = (REDMINE_USER, REDMINE_PASSWORD)
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. メンバー・シフト情報の定義 ---
# 🌟 小栁さんの指定をシステム上の表記「小栁 明」に統一
MEMBERS_DATA = {
    "佐藤 隆": {"role": "インフラ", "is_holiday_today": False},
    "高橋 健太": {"role": "バックエンド", "is_holiday_today": True},
    "鈴木 美咲": {"role": "フロントエンド", "is_holiday_today": False},
    "小栁 明": {"role": "PM", "is_holiday_today": False}
}
PM_NAME = "小栁 明"

# --- 3. ロジック関数群 ---

def select_best_assignee(ai_analysis_role):
    """AIの判定した領域とシフト情報を照合し、最適な担当者を決定する"""
    candidate = None
    for name, info in MEMBERS_DATA.items():
        if info["role"] == ai_analysis_role and name != PM_NAME:
            candidate = name
            break
            
    if not candidate:
        return PM_NAME
        
    if MEMBERS_DATA[candidate]["is_holiday_today"]:
        print(f"  ℹ️ シフト確認: 領域適任者の【{candidate}】は本日休暇です。PM【{PM_NAME}】へ迂回します。")
        return PM_NAME
        
    print(f"  ℹ️ シフト確認: 【{candidate}】は本日稼働日のため、アサインを確定します。")
    return candidate

def get_user_id_by_name(name):
    """Redmine内から氏名をもとにユーザーIDを取得する（姓名逆転対応の完全版）"""
    url = f"{REDMINE_URL}/users.json"
    try:
        res = requests.get(url, auth=AUTH, timeout=5)
        if res.status_code == 200:
            for user in res.json().get("users", []):
                last = user.get('lastname', '')
                first = user.get('firstname', '')
                
                # パターンA（姓 名）と パターンB（名 姓）の両方を作成
                fullname_pattern_a = f"{last} {first}".strip()
                fullname_pattern_b = f"{first} {last}".strip()
                
                # どちらか一方でも探している名前に一致すればOK
                if name in [fullname_pattern_a, fullname_pattern_b]:
                    return user["id"]
                    
        print(f"  ⚠️ 警告: ユーザー【{name}】がRedmineに見つかりません。")
    except Exception as e:
        print(f"  ⚠️ ユーザーID取得エラー: {e}")
    return None

def analyze_issue_with_ai(subject, description):
    """Gemini 2.5 Flash を用いてチケットの専門領域を確実に3択で判定する"""
    text_to_analyze = f"【件名】: {subject}\n【本文】: {description}"
    
    prompt = f"""
    あなたはIT開発チームの優秀なプロジェクトマネージャーです。
    提供されたチケットの情報（件名・本文）を読み、以下の「3つのいずれの領域」に該当するかを厳密に判定してください。
    
    【判定ルール】
    1. 「DB」「接続瞬断」「サーバー」「ネットワーク」「セキュリティ」などの単語やインフラ基盤に関する内容は必ず「インフラ」と判定してください。
    2. 「API」「500エラー」「バックエンド」「処理」「ロジック」などの単語やサーバーサイドプログラムに関する内容は必ず「バックエンド」と判定してください。
    3. 「フロント」「画面」「UI」「デザイン」「ボタン」「ボタンの調整」などの単語や画面表示に関する内容は必ず「フロントエンド」と判定してください。
    
    【ターゲットチケット】
    {text_to_analyze}
    
    【出力フォーマット】
    JSON形式でのみ出力してください。```json などの装飾マークは一切不要です。
    {{"role": "インフラ" または "バックエンド" または "フロントエンド"}}
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        result_json = json.loads(response.text.strip())
        ai_role = result_json.get("role", "").strip()
        if ai_role in ["インフラ", "バックエンド", "フロントエンド"]:
            return ai_role
    except Exception as e:
        pass
        
    lower_subject = subject.lower()
    if any(k in lower_subject for k in ["フロント", "デザイン", "画面", "ボタン"]):
        return "フロントエンド"
    elif any(k in lower_subject for k in ["api", "500", "バックエンド", "エラー"]):
        return "バックエンド"
    return "インフラ"

def run_auto_assign():
    """未割り当てチケットを抽出し、AI仕分けとRedmine更新を実行するメイン関数"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 未割り当てチケットをチェック中...")
    url = f"{REDMINE_URL}/issues.json?project_id=ai-test&status_id=open&limit=100"
    
    try:
        res = requests.get(url, auth=AUTH, timeout=5)
        if res.status_code != 200:
            return
            
        all_issues = res.json().get("issues", [])
        issues = [i for i in all_issues if i.get("assigned_to") is None]
        
        if not issues:
            print("✨ 現在、未割り当ての滞留チケットはありません。")
            return
            
        print(f"🔥 {len(issues)} 件の未割り当てチケットを検出しました。仕分けを開始します。")
        
        for issue in issues:
            issue_id = issue["id"]
            subject = issue["subject"]
            description = issue.get("description", "")
            
            print(f"\n--- 📦 チケット #{issue_id}: [{subject}] の仕分け開始 ---")
            ai_role = analyze_issue_with_ai(subject, description)
            print(f"  🤖 AI判定結果: 専門領域 = 【{ai_role}】")
            
            final_assignee_name = select_best_assignee(ai_role)
            user_id = get_user_id_by_name(final_assignee_name)
            if not user_id:
                print(f"  ❌ エラー: ユーザー【{final_assignee_name}】のIDを見つけられませんでした。")
                continue
                
            update_url = f"{REDMINE_URL}/issues/{issue_id}.json"
            payload = {"issue": {"assigned_to_id": user_id}}
            
            update_res = requests.put(update_url, auth=AUTH, json=payload, timeout=5)
            if update_res.status_code in [200, 204]:
                print(f"  🎯 成功: チケット #{issue_id} を 【{final_assignee_name}】 にアサインしました！")
                
            if ENV_STAGE in ["Dev", "QA"]:
                print("  ⏳ [Devモード制限回避] 3秒間スリープします...")
                time.sleep(3)
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ チケットの一括仕分けが完了しました。\n")
    except Exception as e:
        print(f"⚠️ 想定外の例外が発生しました: {e}")

if __name__ == "__main__":
    print(f"🤖 AI自動仕分けエンジン 起動 (環境: {ENV_STAGE} / 運行モード: {AI_EXEC_MODE})")
    if AI_EXEC_MODE == "Auto":
        try:
            while True:
                run_auto_assign()
                time.sleep(AI_CHECK_INTERVAL)
        except KeyboardInterrupt:
            print("\n🛑 常時自動監視モードを安全に停止しました。")
    else:
        run_auto_assign()