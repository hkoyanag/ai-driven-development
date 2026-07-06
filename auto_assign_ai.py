import os
import requests
import json
import time
import re
from datetime import datetime
from dotenv import load_dotenv
# パッケージ化されたAI工場モジュールをインポート
from ai_modules import ai_factory

load_dotenv()

# Redmine基本設定
REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "password")
ENV_STAGE = os.getenv("ENV_STAGE", "Dev")

# .env から運行モード、巡回インターバル、API負荷回避用ウェイト、プロジェクトIDを動的にロード
AI_EXEC_MODE = os.getenv("AI_EXEC_MODE", "Manual")
AI_CHECK_INTERVAL = int(os.getenv("AI_CHECK_INTERVAL", "5"))
AI_RATE_LIMIT_SLEEP = int(os.getenv("AI_RATE_LIMIT_SLEEP", "12"))
REDMINE_PROJECT_ID = os.getenv("REDMINE_PROJECT_ID", "ai-test")

AUTH = (REDMINE_USER, REDMINE_PASSWORD)

def load_current_members():
    """要員スケジュールマスタ (members.json) をロードする"""
    if os.path.exists("members.json"):
        with open("members.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def normalize_name(name_str):
    """名前から全角・半角スペースや改行などの空白文字を完全に排除して正規化する"""
    if not name_str:
        return ""
    return re.sub(r'[\s\u3000]+', '', str(name_str))

def is_member_active_on_date(member, check_date_str):
    """
    対象日にメンバーが稼働可能か（参画期間内かつ各種休暇日でないか）を厳格に判定する
    """
    try:
        check_date = datetime.strptime(check_date_str, "%Y-%m-%d")
        
        # 1. 契約参画・離脱期間のチェック
        join_date = datetime.strptime(member["join_date"], "%Y-%m-%d")
        exit_date = datetime.strptime(member["exit_date"], "%Y-%m-%d")
        if not (join_date <= check_date <= exit_date):
            return False
            
        # 2. 定例固定曜日休みのチェック (0=月曜日, 6=日曜日)
        weekday = check_date.weekday()
        fixed_holidays = member.get("fixed_holidays", [])
        if weekday in fixed_holidays:
            return False
            
        # 3. 突発・特定日休みのチェック ("YYYY-MM-DD"形式の配列)
        specific_holidays = member.get("specific_holidays", [])
        if check_date_str in specific_holidays:
            return False
            
        return True
    except Exception:
        return False

def find_best_member_with_ai(subject, description, due_date_str, current_members) -> str:
    """
    指定されたAIプロバイダを使用してチケットの最適なアサイン先を判定する。
    キー未設定時、またはAPIエラー時は、即座に内製キーワードマッチングへ安全にフォールバックする。
    """
    main_provider_name = os.getenv("ACTIVE_AI_PROVIDER", "Groq").strip()
    
    # 基準日（チケットの締切日等）においてアクティブ（休暇外・期間内）なメンバーを抽出
    active_candidates = [m for m in current_members if is_member_active_on_date(m, due_date_str)]
    
    # セーフティガード：アクティブな候補者が1人もいない場合、無駄なAPI通信をせずにPMへ自動エスカレーション
    if not active_candidates:
        print("⚠️ 該当期間にアクティブな要員がマスタに存在しません。自動的にPMへ割り当てます。")
        for m in current_members:
            if "pm" in m.get("role", "").lower() or "マネージャー" in m.get("role", ""):
                return m["name"]
        return current_members[0]["name"] if current_members else "小栁 明"

    print(f"[{main_provider_name}] によるAIアサイン判定を実行中...")
    
    # APIキーの存在有無を静的にチェック
    main_key_env_var = f"{main_provider_name.upper()}_API_KEY"
    main_api_key = os.getenv(main_key_env_var, "")
    
    # キーが未設定、またはダミー値の場合は通信をスキップして即フォールバックへ
    if not main_api_key or "dummy" in main_api_key.lower() or "your_" in main_api_key.lower():
        print(f"⚠️ {main_provider_name} の有効なAPIキーが設定されていないため、AI通信をスキップします。")
        raise ValueError(f"Valid API key for {main_provider_name} is missing.")
        
    # Groq等のJSON modeの制約を完全に突破する、システム指示を内包した厳密なプロンプトの組み立て
    prompt = f"""
    You are an expert software project manager. Analyze the following Redmine ticket and select the best candidate from the active candidates list based on their role and skills.
    
    [Ticket Information]
    - Subject: {subject}
    - Description: {description}
    - Assignment Date: {due_date_str}

    [Active Candidates List]
    {json.dumps(active_candidates, ensure_ascii=False, indent=2)}

    [Output Constraint]
    You must output a single, valid JSON object containing exactly one key 'assigned_name' like below. Do not output any conversational prose, commentary, or markdown code block.
    {{"assigned_name": "Exact Name of the Selected Member"}}
    """

    try:
        # 工場クラスから動的にAIプロバイダをインスタンス化
        ai_engine = ai_factory.AIFactory.get_provider()
        response_json_str = ai_engine.ask_assignment(prompt)
        
        # 💡 マークダウンパーサーとの干渉を防ぐため、バッククォート文字列を動的に生成して除去
        backticks = "`" * 3
        if backticks in response_json_str:
            response_json_str = response_json_str.replace(f"{backticks}json", "").replace(backticks, "").strip()
            
        result = json.loads(response_json_str)
        if "assigned_name" in result and result["assigned_name"]:
            return result["assigned_name"]
        raise ValueError("AIからのレスポンスに 'assigned_name' が含まれていません。")
        
    except Exception as e:
        print(f"❌ メインAI ({main_provider_name}) でのエラーまたは制限到達を検知: {e}")
        print("🔒 安全のため、プログラム内製の『静的キーワード判定ロジック』を実行します...")
        
        # 内製フォールバック：件名と本文から技術キーワードを抽出し、メンバーのスキルと部分一致比較
        norm_desc = (subject + description).lower()
        for m in active_candidates:
            skills = m.get("skills", "").lower()
            for skill_word in [s.strip() for s in skills.split(",") if s.strip()]:
                if skill_word in norm_desc:
                    return m["name"]
                    
        # 適任者がいなければ、アクティブなPMへ自動迂回
        for m in active_candidates:
            if "pm" in m.get("role", "").lower() or "マネージャー" in m.get("role", ""):
                return m["name"]
                
        # 最終手段としてアクティブメンバーの先頭名
        return active_candidates[0]["name"]

def get_user_id_by_name(name, redmine_users):
    """メンバー氏名からRedmine上のユーザーIDを完全一致で特定する（スペースの有無を無効化）"""
    norm_target = normalize_name(name)
    for user in redmine_users:
        last = user.get('lastname', '')
        first = user.get('firstname', '')
        # 「姓＋名」および「名＋姓」の空白を除去して完全一致判定
        if normalize_name(f"{last}{first}") == norm_target or normalize_name(f"{first}{last}") == norm_target:
            return user["id"]
    return None

def process_all_issues():
    """未割り当てチケットを検出し、最適なアサイン先へ仕分けを行うメイン処理"""
    try:
        # Redmineからユーザー一覧を一括取得
        user_res = requests.get(f"{REDMINE_URL}/users.json?limit=100", auth=AUTH, timeout=15)
        redmine_users = user_res.json().get("users", []) if user_res.status_code == 200 else []
    except Exception as e:
        print(f"⚠️ ユーザーマスタの取得に失敗しました: {e}")
        return

    # 未割り当てのオープンチケットの一覧を取得
    url = f"{REDMINE_URL}/issues.json?project_id={REDMINE_PROJECT_ID}&status_id=open&limit=100"
    try:
        res = requests.get(url, auth=AUTH, timeout=5)
        if res.status_code != 200:
            return
            
        all_issues = res.json().get("issues", [])
        # 担当者が None (未割り当て) のものだけを抽出
        issues = [i for i in all_issues if i.get("assigned_to") is None]
        
        if not issues:
            return
            
        current_members = load_current_members()
        print(f"🔥 {len(issues)} 件の未割り当てチケットを検出しました。動的AI仕分けを行います。")
        
        for issue in issues:
            issue_id = issue["id"]
            subject = issue["subject"]
            description = issue.get("description", "")
            # チケットに期限がなければ今日の日付を基準日とする
            due_date_str = issue.get("due_date") or datetime.now().strftime("%Y-%m-%d")
            
            print(f"\n--- 📦 チケット #{issue_id} の仕分け開始 ---")
            final_assignee_name = find_best_member_with_ai(subject, description, due_date_str, current_members)
            print(f"  🎯 判定結果: 【{final_assignee_name}】 に決定")
            
            # 決定した人名からRedmine上の数値IDを特定
            user_id = get_user_id_by_name(final_assignee_name, redmine_users)
            if not user_id:
                print(f"  ❌ エラー: Redmine上にユーザー 【{final_assignee_name}】 が見つかりません。フォールバック処理を続行。")
                continue
                
            # チケットの担当者フィールドを自動更新
            update_url = f"{REDMINE_URL}/issues/{issue_id}.json"
            payload = {"issue": {"assigned_to_id": user_id}}
            requests.put(update_url, auth=AUTH, json=payload, timeout=5)
            
            # 大量リクエスト時のAPIレートリミット(429)を回避するための自動スリープ
            if ENV_STAGE in ["Dev", "QA"]:
                time.sleep(AI_RATE_LIMIT_SLEEP)
                
        # 1周のスキャンが終わるごとに追加のクールダウンを挿入
        if ENV_STAGE in ["Dev", "QA"]:
            print(f"\n☕ APIの連続制限を回避するため、{AI_RATE_LIMIT_SLEEP}秒間のクールダウンに入ります...")
            time.sleep(AI_RATE_LIMIT_SLEEP)

    except Exception as e:
        print(f"⚠️ 実行エラー: {e}")

if __name__ == "__main__":
    print(f"🤖 [共通パッケージ仕様] 完全汎用型AI自動仕分けエンジン 起動")
    print(f"  🔧 運行モード: {AI_EXEC_MODE} (インターバル: {AI_CHECK_INTERVAL}秒)")
    
    # 運行モードに応じた監視ループの実行
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