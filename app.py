import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
# re は今回使わなくなりましたが、インポートしたままでも問題ありません
import re

# --- スプレッドシート接続設定 ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# スプレッドシートのファイル名
SPREADSHEET_NAME = "学習時間"

try:
    workbook = client.open(SPREADSHEET_NAME)
except Exception as e:
    st.error(f"エラー: スプレッドシート『{SPREADSHEET_NAME}』が見つからないか、共有設定がされていません。")

# --- アプリ画面構成 ---
st.title("📚 学習記録入力")

with st.form("input_form"):
    # 1. 日付と曜日
    selected_date = st.date_input("日付", datetime.now())
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_str = weekdays[selected_date.weekday()]

    # 2. 分野
    category = st.selectbox("分野", ["英語", "IT", "バイナリー", "読書", "ジャーナリング", "その他", "休む"])

    # 3. 開始時間
    # 自由入力できるようにヒント（placeholder）を変更しました
    start_time_raw = st.text_input("開始時間", value="", placeholder="例: 09:00, 朝, 起床後 など")

    # 4. 時間（勉強または休む）
    duration_raw = st.text_input("時間（分）", value="",