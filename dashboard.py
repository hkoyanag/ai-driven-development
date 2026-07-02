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
ENV_STAGE = os.getenv("ENV_STAGE", "Dev") # デフォルトはDev

# 10秒ごとに画面を自動で最新情報に更新（コンテナ環境でのリアルタイム同期用）
st_autorefresh(interval=10000, limit=100, key="datarefresh")

# ページの設定
st.set_page_config(page_title="チーム稼働状況ダッシュボード", layout="wide")

# タイトル表示（ステージに応じてバッジを切り替え）
stage_badge = f"🛠️ {ENV_STAGE} モード" if ENV_STAGE in ["Dev", "QA"] else f"🚀 {ENV_STAGE} モード"
st.title(f"📊 稼働状況状況ダッシュボード ({stage_badge})")
st.markdown("Redmineとリアルタイムに連携し、チームのタスク負荷やプロジェクトの消化状況を可視化します。")

# --- データ取得関数 ---
def get_redmine_issues():
    """RedmineからAIテストプロジェクトの全チケットを取得する"""
    url = f"{REDMINE_URL}/issues.json?project_id=ai-test&status_id=*"
    try:
        res = requests.get(url, auth=(REDMINE_USER, REDMINE_PASSWORD), timeout=5)
        if res.status_code == 200:
            return res.json().get("issues", [])
    except Exception as e:
        st.error(f"Redmine通信エラー: {e}")
    return []

# --- データ処理と画面描画 ---
issues = get_redmine_issues()

if not issues:
    st.warning("Redmineからチケットデータを取得できませんでした。プロジェクトやチケットが存在するか確認してください。")
else:
    # 今日の日付（ダッシュボードが動いている当日の日付、デモ用に現在日付を自動取得）
    today_str = datetime.now().strftime("%Y-%m-%d")

    data = []
    for issue in issues:
        assigned_to = issue.get("assigned_to", {}).get("name", "未割り当て")
        due_date = issue.get("due_date", "未設定")
        
        data.append({
            "チケットID": issue["id"],
            "件名": issue["subject"],
            "ステータス": issue["status"]["name"],
            "担当者": assigned_to,
            "作成日": issue["created_on"][:10],
            "更新日": issue["updated_on"][:10],
            "期日": due_date
        })
    df = pd.DataFrame(data)

    # --- 📐 各種ビジネス指標の算出ロジック ---
    total_tickets = len(df)
    
    # 1. 本日発生（作成日が今日のもの）
    today_created_count = len(df[df["作成日"] == today_str])
    
    # 2. 現在の残タスク（ステータスが「終了」または「Closed」以外のもの）
    active_tasks_df = df[~df["ステータス"].isin(["終了", "Closed"])]
    remaining_tasks_count = len(active_tasks_df)
    
    # 3. 期限切れ（残タスクのうち、期日が今日より過去のもの。未設定は除く）
    overdue_count = 0
    for _, row in active_tasks_df.iterrows():
        # 期日が存在し、かつNoneでもなく、文字列の比較ができる場合のみ判定
        if row["期日"] and row["期日"] != "未設定" and pd.notna(row["期日"]):
            if row["期日"] < today_str:
                overdue_count += 1

    # 4. 上司向け消化率（終了件数 / 総件数）
    closed_count = total_tickets - remaining_tasks_count
    completion_rate = round((closed_count / total_tickets) * 100, 1) if total_tickets > 0 else 0.0

    # --- 🗂️ KPI表示エリアの条件分岐 ---
    
    # 【A段】ビジネス・マネジメント向けKPI（常時表示）
    st.subheader("📈 チーム稼働・プロジェクト進捗指標")
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    with b_col1:
        st.metric(label="🌟 本日発生（新規）", value=f"{today_created_count} 件")
    with b_col2:
        st.metric(label="🔥 現在の残タスク数", value=f"{remaining_tasks_count} 件")
    with b_col3:
        st.metric(label="👨‍💼 全体消化率", value=f"{completion_rate} %")
    with b_col4:
        # 期限切れがあれば赤文字風に警告（Streamlitのdeltaを活用）
        st.metric(label="⚠️ 期限超過（遅延）", value=f"{overdue_count} 件", 
                  delta="要フォロー！" if overdue_count > 0 else None, delta_color="inverse" if overdue_count > 0 else "normal")

    # 【B段】AIデバッグ用KPI（Dev, QAモードの時だけ追加で表示）
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

    # --- 📊 グラフエリア（2カラム配置） ---
    graph_col1, graph_col2 = st.columns(2)

    with graph_col1:
        st.subheader("👥 担当者ごとのタスク負荷（残タスク件数）")
        # 残タスクのみを集計してグラフ化（上司やチームが今対応すべき量を見せるため）
        if remaining_tasks_count > 0:
            df_count = active_tasks_df["担当者"].value_counts().reset_index()
            df_count.columns = ["担当者", "残件数"]
            
            fig = px.bar(df_count, x="残件数", y="担当者", orientation='h', 
                         color="担当者", text="残件数",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(showlegend=False, height=300, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("🎉 現在、対応が必要な残タスクはありません！")

    with graph_col2:
        st.subheader("🔔 タスクステータス内訳")
        df_status = df["ステータス"].value_counts().reset_index()
        df_status.columns = ["ステータス", "件数"]
        fig_pie = px.pie(df_status, values="件数", names="ステータス", 
                         color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # --- 📋 詳細データテーブル ---
    st.subheader("📋 リアルタイムチケット一覧")
    st.dataframe(df, use_container_width=True)