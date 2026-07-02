import os
import requests
import json
import pandas as pd
import streamlit as pd_st # グラフやテーブル表示の補助
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

# --- 設定情報の外部読み込み ---
load_dotenv()

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_USER = os.getenv("REDMINE_ADMIN_USER", "admin")
REDMINE_PASSWORD = os.getenv("REDMINE_ADMIN_PASSWORD", "admin")

# ページの設定（ワイドモード、タイトルの設定）
st.set_page_config(page_title="AI仕分け状況ダッシュボード", layout="wide")

st.title("📊 AI自動仕分け・稼働状況ダッシュボード")
st.markdown("Redmineと連携し、AIの仕分け状況やメンバーのタスク負荷をリアルタイムに可視化します。")

# --- データ取得関数 ---
def get_redmine_issues():
    """RedmineからAIテストプロジェクトの全チケットを取得する"""
    url = f"{REDMINE_URL}/issues.json?project_id=ai-test&status_id=*"
    res = requests.get(url, auth=(REDMINE_USER, REDMINE_PASSWORD))
    if res.status_code == 200:
        return res.json().get("issues", [])
    return []

# --- データ処理と画面描画 ---
issues = get_redmine_issues()

if not issues:
    st.warning("Redmineからチケットデータを取得できませんでした。プロジェクトやチケットが存在するか確認してください。")
else:
    # データをPandasのDataFrameに変換して扱いやすくする
    data = []
    for issue in issues:
        assigned_to = issue.get("assigned_to", {}).get("name", "未割り当て")
        data.append({
            "チケットID": issue["id"],
            "件名": issue["subject"],
            "ステータス": issue["status"]["name"],
            "担当者": assigned_to,
            "更新日時": issue["updated_on"][:10] # 日付部分だけ抽出
        })
    df = pd.DataFrame(data)

    # --- 1. KPIブロック（最上部のサマリーカード） ---
    total_tickets = len(df)
    unassigned_count = len(df[df["担当者"] == "未割り当て"])
    assigned_count = total_tickets - unassigned_count

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="総チケット数", value=total_tickets)
    with col2:
        st.metric(label="AI仕分け完了", value=assigned_count, delta=f"+{assigned_count}")
    with col3:
        st.metric(label="未割り当て（滞留中）", value=unassigned_count, delta=f"-{unassigned_count}" if unassigned_count==0 else None)

    st.markdown("---")

    # --- 2. グラフエリア（2カラム配置） ---
    graph_col1, graph_col2 = st.columns(2)

    with graph_col1:
        st.subheader("👥 担当者ごとのタスク割り当て件数")
        # 担当者ごとの件数を集計（未割り当て含む）
        df_count = df["担当者"].value_counts().reset_index()
        df_count.columns = ["担当者", "件数"]
        
        # Plotlyで綺麗な横棒グラフを描画
        fig = px.bar(df_count, x="件数", y="担当者", orientation='h', 
                     color="担当者", text="件数",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(showlegend=False, height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with graph_col2:
        st.subheader("🔔 シフト・ステータス状況")
        df_status = df["ステータス"].value_counts().reset_index()
        df_status.columns = ["ステータス", "件数"]
        fig_pie = px.pie(df_status, values="件数", names="ステータス", 
                         color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # --- 3. 詳細データテーブル ---
    st.subheader("📋 リアルタイムチケット一覧")
    st.dataframe(df, use_container_width=True)

    # 右上にリフレッシュボタンを配置するための暫定処置
    if st.button("🔄 データを最新に更新"):
        st.rerun()

    # --- 最下部に追記：10秒ごとに画面を自動で最新情報に更新するマジックコード ---
    from streamlit_autorefresh import st_autorefresh
    # 10000ミリ秒（10秒）ごとにリフレッシュ、最大100回まで（カウンターのバグ防止）
    st_autorefresh(interval=10000, limit=100, key="datarefresh")