import os
import requests
import json
import time
import re
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Redmine・Gemini基本設定
REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "password")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ENV_STAGE = os.getenv("ENV_STAGE", "Dev")

# 🌟 .env から運行モード、インターバル、モデル、ウェイト、プロジェクトIDを動的に取得
AI_EXEC_MODE = os.getenv("AI_EXEC_MODE", "Manual")
AI_CHECK_INTERVAL = int(os.getenv("AI_CHECK_INTERVAL", "5"))
AI_RATE_LIMIT_SLEEP = int(os.getenv("AI_RATE_LIMIT_SLEEP", "12"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
REDMINE_PROJECT_ID = os.getenv("REDMINE_PROJECT_ID", "ai-test")

AUTH = (REDMINE_USER, REDMINE_PASSWORD)
genai.configure(api_key=GEMINI_API_KEY)

def load_current_members():
    if os.path.exists("members.json"):
        with open("members.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def normalize_name(name_str):
    if not name_str:
        return ""
    return re.sub(r'\s+', '', str(name_str))

def is_member_active_on_date(member, check_date_str):
    try:
        check_date = datetime.strptime(check_date_str, "%Y-%m-%d")
        join_date = datetime.strptime(member["join_date"], "%Y-%m-%d")
        exit_date = datetime.strptime(member["exit_date"], "%Y-%m-%d")
        return join_date <= check_date <= exit_date
    except Exception:
        return False

def find_best_member_with_ai(subject, description, due_date_str, members):
    # チケット期日時点でアクティブなメンバーのみを抽出
    active_members = [m for m in members if is_member_active_on_date(m, due_date_str)]
    
    pm_member = next((m for m in members if "PM" in m.get("role", "").upper() or "管理" in m.get("role", "")), None)
    pm_name = pm_member["name"] if pm_member else (members[0]["name"] if members else "管理者")
    
    if not active_members:
        print(f"  ⚠️ 警告: 対象期日 {due_date_str} にアクティブなメンバーがいません。PM【{pm_name}】へ迂回します。")
        return pm_name

    # 🌟 本日の日付を取得
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_weekday = datetime.now().weekday() # 0=月, 6=日

    # 🌟 メンバーの期間と休暇情報をAIに渡すテキストへ含めるように強化！
    members_profile_text = ""
    for m in active_members:
        # 定例休暇の曜日変換
        weekdays_list = ["月", "火", "水", "木", "金", "土", "日"]
        fixed_holidays_js = ", ".join([weekdays_list[idx] for idx in m.get("fixed_holidays", [])])
        specific_holidays_js = ", ".join(m.get("specific_holidays", []))

        members_profile_text += (
            f"- 氏名: {m['name']}\n"
            f"  役割: {m['role']}\n"
            f"  スキル: {m.get('skills', '未設定')}\n"
            f"  参画期間: {m['join_date']} 〜 {m['exit_date']}\n"
            f"  毎週の定例休み: {fixed_holidays_js if fixed_holidays_js else 'なし'}\n"
            f"  突発・特定日休み: {specific_holidays_js if specific_holidays_js else 'なし'}\n\n"
        )

    text_to_analyze = f"【件名】: {subject}\n【本文】: {description}\n【チケット期日】: {due_date_str}"
    
    prompt = f"""
    あなたはIT開発プロジェクトの高度なリソースマネージャーです。
    タスク情報（件名・本文・期日）を分析し、現在プロジェクトに参画している以下の「メンバー候補」の中から、スキルと役割が最も適合する1名を厳密に選定してアサインしてください。
    
    【本日の日付】
    {today_str} (曜日のインデックス: {current_weekday})
    
    【参画中のメンバー候補】
    {members_profile_text}
    
    【アサインの厳格ルール】
    1. 【最重要・最優先】本日（{today_str}）が、各メンバーの「参画期間」の範囲外である場合、そのメンバーは絶対にアサインしないでください（過去に離脱した人、未来に参加する人は除外）。
    2. 【最重要】本日（{today_str}）が、メンバーの「突発・特定日休み」の日付と完全に一致している場合、そのメンバーは本日稼働できないため、絶対にアサインしないでください。
    3. 技術スタック（ネットワーク、DB、画面、フロント、API、バックエンド等）と、稼働可能なメンバーの「役割」「スキル」の一致度を見て選定してください。
    4. ルール1, 2により適任者が不在、または本日稼働できるメンバーが誰もいない場合は、責任持ってタスクを引き受けるプロジェクトマネージャー（PM）の【{pm_name}】をアサインしてください。
    
    【対象チケット】
    {text_to_analyze}
    
    【出力フォーマット】
    必ず以下のJSON形式のみで回答してください。余計な解説文は一切含めないでください。
    {{"assigned_name": "選定したメンバーの氏名"}}
    """
    
    try:
        # 🌟 使用するモデルを設定ファイルから動的にバインド
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        result_json = json.loads(response.text.strip())
        assigned_name = result_json.get("assigned_name", "").strip()
        
        norm_assigned = normalize_name(assigned_name)
        if norm_assigned == normalize_name(pm_name):
            return pm_name
            
        for m in active_members:
            if norm_assigned == normalize_name(m["name"]):
                return m["name"]
    except Exception as e:
        print(f"  ⚠️ Gemini解析フォールバック（APIエラー等による救済措置）を実行します: {e}")
        
    combined_text = (subject + " " + description).lower()
    best_member = None
    max_score = 0
    
    for m in active_members:
        score = 0
        keywords = [k.strip().lower() for k in (m.get("skills", "") + "," + m.get("role", "")).split(",") if k.strip()]
        for kw in keywords:
            if kw in combined_text:
                score += 1
        if score > max_score:
            max_score = score
            best_member = m
            
    if best_member and max_score > 0:
        return best_member["name"]
        
    return pm_name

def get_user_id_by_name(name, redmine_users):
    norm_target = normalize_name(name)
    for user in redmine_users:
        last = user.get('lastname', '')
        first = user.get('firstname', '')
        if normalize_name(f"{last}{first}") == norm_target or normalize_name(f"{first}{last}") == norm_target:
            return user["id"]
    return None

def process_all_issues():
    """未割り当てチケットをスキャンして仕分ける主処理"""
    try:
        user_res = requests.get(f"{REDMINE_URL}/users.json?limit=100", auth=AUTH, timeout=15)
        redmine_users = user_res.json().get("users", []) if user_res.status_code == 200 else []
    except Exception as e:
        print(f"⚠️ ユーザーマスタの取得に失敗しました: {e}")
        return

    url = f"{REDMINE_URL}/issues.json?project_id={REDMINE_PROJECT_ID}&status_id=open&limit=100"
    try:
        res = requests.get(url, auth=AUTH, timeout=5)
        if res.status_code != 200:
            return
            
        all_issues = res.json().get("issues", [])
        issues = [i for i in all_issues if i.get("assigned_to") is None]
        
        if not issues:
            return
            
        current_members = load_current_members()
        print(f"🔥 {len(issues)} 件の未割り当てチケットを検出しました。動的AI仕分けを行います。")
        
        for issue in issues:
            issue_id = issue["id"]
            subject = issue["subject"]
            description = issue.get("description", "")
            due_date_str = issue.get("due_date") or datetime.now().strftime("%Y-%m-%d")
            
            print(f"\n--- 📦 チケット #{issue_id} の仕分け開始 ---")
            final_assignee_name = find_best_member_with_ai(subject, description, due_date_str, current_members)
            print(f"  🎯 AI判定結果: 【{final_assignee_name}】 さんに決定")
            
            user_id = get_user_id_by_name(final_assignee_name, redmine_users)
            if not user_id:
                print(f"  ❌ エラー: Redmine上にユーザー 【{final_assignee_name}】 が見つかりません。")
                continue
                
            update_url = f"{REDMINE_URL}/issues/{issue_id}.json"
            payload = {"issue": {"assigned_to_id": user_id}}
            requests.put(update_url, auth=AUTH, json=payload, timeout=5)
            
            # 🌟 チケットを1件処理するごとに、指定された安全マージン（12秒）を「必ず」挟む
            if ENV_STAGE in ["Dev", "QA"]:
                time.sleep(AI_RATE_LIMIT_SLEEP)
                
        # 🌟 1周の仕分け（塊）がすべて終わった後も、APIの負荷を逃がすために追加で12秒完全に休ませる
        if ENV_STAGE in ["Dev", "QA"]:
            print(f"  ☕ APIの連続制限を回避するため、{AI_RATE_LIMIT_SLEEP}秒間のクールダウンに入ります...")
            time.sleep(AI_RATE_LIMIT_SLEEP)

    except Exception as e:
        print(f"⚠️ 実行エラー: {e}")

if __name__ == "__main__":
    print(f"🤖 [共通パッケージ仕様] 完全汎用型AI自動仕分けエンジン 起動")
    print(f"  🔧 運行モード: {AI_EXEC_MODE} (インターバル: {AI_CHECK_INTERVAL}秒)")
    
    # 🌟 .env の AI_EXEC_MODE に基づいて自律監視モードを完全稼働
    if AI_EXEC_MODE == "Auto":
        print("🔄 自律巡回監視ループを開始します。停止するには Ctrl+C を押してください。")
        while True:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 未割り当てチケットの走査を開始...")
            process_all_issues()
            time.sleep(AI_CHECK_INTERVAL)
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 単発スキャンを実行します...")
        process_all_issues()
        print("✨ 単発スキャンが完了しました。")