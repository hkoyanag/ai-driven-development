import streamlit as st
import pandas as pd
import json
import os
import requests
import re
import plotly.express as px
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

st.set_page_config(page_title="AI-Driven Development Dashboard", layout="wide")

REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
# 🔑 パスワード認証からAPIキー認証へ変更
REDMINE_API_KEY = os.getenv("REDMINE_API_KEY", "")
HEADERS = {
    "X-Redmine-API-Key": REDMINE_API_KEY,
    "Content-Type": "application/json"
}

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

def load_members():
    if os.path.exists("members.json"):
        with open("members.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_members(members):
    with open("members.json", "w", encoding="utf-8") as f:
        json.dump(members, f, indent=2, ensure_ascii=False)

def match_member_name(redmine_name, json_members):
    if not redmine_name:
        return "未割り当て"
    norm_redmine = re.sub(r'\s+', '', str(redmine_name))
    for m in json_members:
        if re.sub(r'\s+', '', m["name"]) == norm_redmine:
            return m["name"]
    return redmine_name

tab1, tab2 = st.tabs(["📊 稼働状況ダッシュボード", "👥 メンバー管理・要員計画"])

members = load_members()

with tab1:
    st.title("📊 稼働状況ダッシュボード (🛠️ パッケージ汎用版)")
    st.caption("Redmineから取得した担当者名の表記揺れを自動補正し、正確なリアルタイム負荷を表示します。")
    
    if members:
        today_str = datetime.now().strftime("%Y-%m-%d")
        active_display_members = [m for m in members if m["join_date"] <= today_str <= m["exit_date"]]
        
        if active_display_members:
            cols = st.columns(len(active_display_members))
            for i, m in enumerate(active_display_members):
                with cols[i]:
                    st.metric(label=m["name"], value=m["role"], delta=f"参画期間: {m['join_date']} 〜 {m['exit_date']}")
    
    st.markdown("---")
    
    try:
        # 🛠️ auth=AUTH から headers=HEADERS に変更
        res = requests.get(f"{REDMINE_URL}/issues.json?project_id=ai-test&status_id=*&limit=100", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            issues = res.json().get("issues", [])
            
            if issues:
                df_issues = pd.DataFrame(issues)
                
                total_tickets = len(issues)
                closed_count = 0
                open_count = 0
                unassigned_count = 0
                overdue_count = 0
                
                today_str = datetime.now().strftime("%Y-%m-%d")
                assignee_list = []
                status_list = []
                
                for idx, row in df_issues.iterrows():
                    status_obj = row.get("status", {})
                    status_name = status_obj.get("name", "新規")
                    
                    if status_name in ["終了", "クローズ", "Closed", "Resolved"]:
                        closed_count += 1
                        status_list.append("終了")
                    else:
                        open_count += 1
                        status_list.append("新規")
                        
                        due_date = row.get("due_date")
                        if isinstance(due_date, str) and due_date < today_str:
                            overdue_count += 1
                    
                    assignee = row.get("assigned_to")
                    if isinstance(assignee, dict):
                        raw_name = assignee.get("name")
                        assignee_list.append(match_member_name(raw_name, members))
                    else:
                        unassigned_count += 1
                        assignee_list.append("未割り当て")
                
                completion_rate = round((closed_count / total_tickets) * 100, 1) if total_tickets > 0 else 0.0
                
                st.subheader("📈 チーム稼働・プロジェクト進捗指標")
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                m_col1.metric(label="🌟 総チケット数", value=f"{total_tickets} 件")
                m_col2.metric(label="🔥 現在の残タスク数", value=f"{open_count} 件")
                m_col3.metric(label="🧸 進捗率", value=f"{completion_rate} %")
                m_col4.metric(label="⚠️ 期限超過", value=f"{overdue_count} 件")
                
                st.markdown("---")
                
                g_col1, g_col2 = st.columns(2)
                
                with g_col1:
                    st.subheader("👥 担当者ごとのタスク負荷 (残タスク数)")
                    df_open_issues = df_issues[~df_issues['status'].apply(lambda x: x.get('name', '') in ["終了", "クローズ", "Closed", "Resolved"])]
                    
                    open_assignees = []
                    for idx, row in df_open_issues.iterrows():
                        assignee = row.get("assigned_to")
                        if isinstance(assignee, dict):
                            open_assignees.append(match_member_name(assignee.get("name"), members))
                        else:
                            open_assignees.append("未割り当て")
                    
                    if open_assignees:
                        df_counts = pd.Series(open_assignees).value_counts().reset_index()
                        df_counts.columns = ["担当者", "残タスク件数"]
                        
                        fig_bar = px.bar(
                            df_counts,
                            x="残タスク件数",
                            y="担当者",
                            orientation="h",
                            color="担当者",
                            color_discrete_sequence=px.colors.qualitative.Pastel
                        )
                        fig_bar.update_layout(
                            showlegend=False,
                            height=350,
                            margin=dict(l=20, r=20, t=10, b=10),
                            yaxis={'categoryorder': 'total ascending'}
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
                    else:
                        st.info("現在、残タスクはありません。")
                
                with g_col2:
                    st.subheader("🔔 タスクステータス内訳")
                    df_status = pd.DataFrame({"ステータス": status_list})
                    df_status_counts = df_status["ステータス"].value_counts().reset_index()
                    df_status_counts.columns = ["ステータス", "件数"]
                    
                    fig_pie = px.pie(
                        df_status_counts,
                        names="ステータス",
                        values="件数",
                        color="ステータス",
                        color_discrete_map={"新規": "#5dade2", "終了": "#e74c3c"}
                    )
                    fig_pie.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=10))
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                df_all_counts = pd.Series(assignee_list).value_counts().reset_index()
                df_all_counts.columns = ["担当者", "総チケット件数"]
                st.table(df_all_counts)
                
            else:
                st.info("現在、プロジェクト内にチケットはありません。")
        else:
            # 🛠️ 認証失敗などのエラーを画面に通知する親切設計を追加
            st.error(f"Redmineからのデータ取得に失敗しました。Status Code: {res.status_code}")
    except Exception as e:
        st.error(f"Redmineデータの集計中にエラーが発生しました: {e}")

# --- dashboard.py の最下部付近を以下に差し替え ---
with tab2:
    st.header("👥 プロジェクト要員管理 ＆ 休暇計画")
    
    with st.expander("➕ 新規メンバーの追加 / 既存情報・休暇の修正"):
        member_names = [m["name"] for m in members]
        target_name = st.selectbox("編集するメンバーを選択", ["(新規追加)"] + member_names)
        target_data = next((m for m in members if m["name"] == target_name), None)
        
        with st.form("member_form"):
            name = st.text_input("氏名", value=target_data["name"] if target_data else "")
            login = st.text_input("ログインID", value=target_data["login"] if target_data else "")
            role = st.text_input("担当領域 / 役割", value=target_data["role"] if target_data else "")
            skills = st.text_area("保有スキル (カンマ区切り)", value=target_data.get("skills", "") if target_data else "")
            
            col_a, col_b = st.columns(2)
            with col_a:
                join_date = st.date_input("参画日", value=datetime.strptime(target_data["join_date"], "%Y-%m-%d") if target_data else datetime.now())
            with col_b:
                exit_date = st.date_input("離脱予定日", value=datetime.strptime(target_data["exit_date"], "%Y-%m-%d") if target_data else datetime.now())
            
            st.markdown("**📅 休暇スケジュール設定**")
            current_fixed = target_data.get("fixed_holidays", []) if target_data else []
            fixed_labels = [WEEKDAYS[d] for d in current_fixed if d < 7]
            selected_fixed_labels = st.multiselect("定例曜日休暇 (毎週休む曜日)", WEEKDAYS, default=fixed_labels)
            fixed_indices = [WEEKDAYS.index(lbl) for lbl in selected_fixed_labels]
            
            current_specific = ", ".join(target_data.get("specific_holidays", [])) if target_data else ""
            specific_input = st.text_input("特定日休暇 (カンマ区切り、例: 2026-07-03, 2026-07-15)", value=current_specific)
            specific_list = [d.strip() for d in specific_input.split(",") if re.match(r'^\d{4}-\d{2}-\d{2}$', d.strip())]
            
            submit = st.form_submit_button("保存する")
            if submit:
                new_member = {
                    "id": target_data["id"] if target_data else 99,
                    "login": login, "name": name, "role": role, "skills": skills,
                    "join_date": join_date.strftime("%Y-%m-%d"), "exit_date": exit_date.strftime("%Y-%m-%d"),
                    "fixed_holidays": fixed_indices,
                    "specific_holidays": specific_list
                }
                if target_data:
                    members = [new_member if m["name"] == target_name else m for m in members]
                else:
                    members.append(new_member)
                save_members(members)
                st.success(f"{name} さんの情報を更新しました！")
                st.rerun()

    st.subheader("📋 現在のプロジェクトメンバー一覧 (休暇計画含む)")
    if members:
        display_rows = []
        for m in members:
            # 💡 もし万が一 fixed_holidays が数値単体や null だった場合も想定して、リスト内包表記を安全に
            fh_list = m.get("fixed_holidays", [])
            if not isinstance(fh_list, list):
                fh_list = []
            fixed_str = ", ".join([WEEKDAYS[idx] for idx in fh_list if isinstance(idx, int) and idx < 7]) if fh_list else "なし"
            
            sh_list = m.get("specific_holidays", [])
            specific_str = ", ".join(sh_list) if isinstance(sh_list, list) and sh_list else "なし"
            
            display_rows.append({
                "氏名": str(m.get("name", "未登録")),
                "役割": str(m.get("role", "未登録")),
                "参画日": str(m.get("join_date", "未登録")),
                "離脱予定日": str(m.get("exit_date", "未登録")),
                "定例曜日休暇": str(fixed_str),
                "特定日休暇": str(specific_str),
                "保有スキル": str(m.get("skills", "未登録")) # 💡str() で囲んで完全な文字列へ固定
            })
        st.table(pd.DataFrame(display_rows))