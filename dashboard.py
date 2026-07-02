import os
import requests
import json
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

# --- 設定情報の外部読み込み ---
load_dotenv()

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "admin")
ENV_STAGE = os.getenv("ENV_STAGE", "Dev")
AI_EXEC_MODE = os.getenv("AI_EXEC_MODE", "Manual")

# 10秒ごとに画面を自動で最新情報に更新
st_autorefresh(interval=10000, limit=100, key="datarefresh")

# ページの設定
st.set_page_config(page_title="チーム稼働状況ダッシュボード", layout="wide")

# --- 📁 サイドバーのレイアウト設計 ---
with st.sidebar:
    st.header("⚙️ システム運行ステータス")
    st.markdown(f"**現在の環境**: `{ENV_STAGE}`")
    
    if AI_EXEC_MODE == "Auto":
        interval_sec = os.getenv("AI_CHECK_INTERVAL", "5")
        st.success("🤖 AI仕分け: 常時自動監視中")
        st.markdown(f"裏側でAIエンジンが **【 {interval_sec} 秒おき 】** にRedmineを常時巡回監視しています。")
    else:
        st.info("⏰ AI仕分け: 定期バッチ運行")

# --- メイン画面のタイトル表示 ---
stage_badge = f"🛠️ {ENV_STAGE}" if ENV_STAGE in ["Dev", "QA"] else f"🚀 {ENV_STAGE}"
st.title(f"📊 稼働状況ダッシュボード ({stage_badge})")
st.markdown("Redmineとリアルタイムに連携し、チームのタスク負荷やプロジェクトの消化状況を可視化します。")

# --- データ取得関数 ---
def get_redmine_issues():
    # 15件以上の表示に対応するため、取得件数上限を100に設定
    url = f"{REDMINE_URL}/issues.json?project_id=ai-test&status_id=*&limit=100"
    try:
        res = requests.get(url, auth=(REDMINE_USER, REDMINE_PASSWORD), timeout=5)
        if res.status_code == 200:
            return res.json().get("issues", [])
    except Exception as e:
        st.error(f"Redmine通信エラー: {e}")
    return []

def format_iso_to_datetime(iso_str):
    """ISO 8601形式の文字列 (2026-07-02T15:30:00Z) を YYYY/MM/DD HH:MM:SS に変換する"""
    if not iso_str:
        return "未設定"
    try:
        # タイムゾーンの'Z'やオフセットを考慮してパース
        clean_str = iso_str.replace("Z", "")
        if "." in clean_str:
            clean_str = clean_str.split(".")[0]
        dt = datetime.fromisoformat(clean_str)
        return dt.strftime("%Y/%m/%d %H:%M:%S")
    except Exception:
        return iso_str[:19].replace("-", "/").replace("T", " ")

# --- データ処理と画面描画 ---
issues = get_redmine_issues()

if not issues:
    st.warning("Redmineからチケットデータを取得できませんでした。")
else:
    today_str = datetime.now().strftime("%Y-%m-%d")

    data = []
    for issue in issues:
        # 🌟 担当者名の日本表記化 (姓 名) への組み替えロジック
        assigned_user = issue.get("assigned_to", {})
        if assigned_user:
            # APIから取得できる場合は姓と名を個別抽出して結合、なければnameを使用
            user_id = assigned_user.get("id")
            # 通常のAPIレスポンスのname属性から英語順をパースして並び替えるセーフティ
            raw_name = assigned_user.get("name", "未割り当て")
            if " " in raw_name and raw_name != "未割り当て":
                # Redmineのデフォルト「名 姓」を「姓 名」にひっくり返すガード
                parts = raw_name.split(" ")
                if len(parts) == 2:
                    # アルファベット表記などの混在も考慮しつつ、今回のテストデータ用に最適化
                    # 通常、Redmineの表示が「健太 高橋」になっていれば parts[1]=高橋, parts[0]=健太
                    assigned_to = f"{parts[1]} {parts[0]}"
                else:
                    assigned_to = raw_name
            else:
                assigned_to = raw_name
        else:
            assigned_to = "未割り当て"

        due_date = issue.get("due_date", None)
        if due_date:
            due_date = due_date.replace("-", "/")

        data.append({
            "チケットID": issue["id"],
            "件名": issue["subject"],
            "ステータス": issue["status"]["name"],
            "担当者": assigned_to,
            "作成日": format_iso_to_datetime(issue["created_on"]), # 🌟 日時フォーマット化
            "更新日": format_iso_to_datetime(issue["updated_on"]), # 🌟 日時フォーマット化
            "期日": due_date if due_date else "未設定"
        })
    df = pd.DataFrame(data)

    # 🌟 左端のナンバリング（Pandasのインデックス）を1から開始にする
    df.index = df.index + 1

    # --- 各種ビジネス指標の算出ロジック ---
    total_tickets = len(df)
    # 本日発生数は日付部分だけでマッチング
    today_prefix = datetime.now().strftime("%Y/%m/%d")
    today_created_count = len(df[df["作成日"].str.startswith(today_prefix)])
    active_tasks_df = df[~df["ステータス"].isin(["終了", "Closed"])]
    remaining_tasks_count = len(active_tasks_df)
    
    overdue_count = 0
    for _, row in active_tasks_df.iterrows():
        val = row["期日"]
        if val and val != "未設定":
            clean_today = today_prefix
            if val.replace("/", "-") < datetime.now().strftime("%Y-%m-%d"):
                overdue_count += 1

    closed_count = total_tickets - remaining_tasks_count
    completion_rate = round((closed_count / total_tickets) * 100, 1) if total_tickets > 0 else 0.0

    # --- KPI表示エリア ---
    st.subheader("📈 チーム稼働・プロジェクト進捗指標")
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    with b_col1:
        st.metric(label="🌟 本日発生（新規）", value=f"{today_created_count} 件")
    with b_col2:
        st.metric(label="🔥 現在の残タスク数", value=f"{remaining_tasks_count} 件")
    with b_col3:
        st.metric(label="👨‍💼 全体消化率", value=f"{completion_rate} %")
    with b_col4:
        st.metric(label="⚠️ 期限超過（遅延）", value=f"{overdue_count} 件", 
                  delta="要フォロー！" if overdue_count > 0 else None, delta_color="inverse" if overdue_count > 0 else "normal")

    if ENV_STAGE in ["Dev", "QA"]:
        st.markdown("---")
        st.subheader("⚙️ AI自動仕分けデバッグ指標（開発者向け）")
        unassigned_count = len(df[df["担当者"] == "未割り当て"])
        assigned_count = total_tickets - unassigned_count
        
        d_col1, d_col2, d_col3 = st.columns(3)
        with d_col1:
            st.metric(label="総チケット数", value=total_tickets)
        with d_col2:
            st.metric(label="AI仕分け完了", value=assigned_count)
        with d_col3:
            st.metric(label="未割り当て（滞留）", value=unassigned_count,
                      delta="滞留あり" if unassigned_count > 0 else "クリア！", delta_color="normal" if unassigned_count == 0 else "inverse")

    st.markdown("---")

    # --- グラフエリア ---
    graph_col1, graph_col2 = st.columns(2)
    with graph_col1:
        st.subheader("👥 担当者ごとのタスク負荷（残タスク件数）")
        if remaining_tasks_count > 0:
            df_count = active_tasks_df["担当者"].value_counts().reset_index()
            df_count.columns = ["担当者", "残件数"]
            fig = px.bar(df_count, x="残件数", y="担当者", orientation='h', 
                         color="担当者", text="残件数",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(showlegend=False, height=320, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("🎉 現在、対応が必要な残タスクはありません！")

    with graph_col2:
        st.subheader("🔔 タスクステータス内訳")
        df_status = df["ステータス"].value_counts().reset_index()
        df_status.columns = ["ステータス", "件数"]
        fig_pie = px.pie(df_status, values="件数", names="ステータス", 
                         color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 リアルタイムチケット一覧")
    st.dataframe(df, use_container_width=True)