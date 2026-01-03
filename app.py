import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# --- スプレッドシート接続設定 ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# シート名を「学習時間」に変更
SHEET_NAME = "学習時間" 

try:
    sheet = client.open(SHEET_NAME).sheet1
except Exception as e:
    st.error(f"エラー: スプレッドシート『{SHEET_NAME}』が見つからないか、共有設定がされていません。")

# --- アプリ画面構成 ---
st.title("📚 学習記録入力")

with st.form("input_form"):
    # 1. 日付と曜日
    selected_date = st.date_input("日付", datetime.now())
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_str = weekdays[selected_date.weekday()]

    # 2. 分野
    category = st.selectbox("分野", ["英語", "IT", "バイナリー", "読書", "ジャーナリング", "その他", "休む"])

    # 3. 開始時間（初期状態を空に設定）
    # placeholder を使うことで入力例を表示しつつ、最初は空欄にします
    start_time_raw = st.text_input("開始時間 (記入例 09:00)", value="", placeholder="未入力なら空白")

    # 4. 時間（勉強または休む）
    duration_raw = st.text_input("時間（分）", value="", placeholder="半角数字で入力")

    # 5. 場所と備考
    location = st.text_input("場所")
    memo = st.text_area("備考")

    submitted = st.form_submit_button("スプレッドシートに保存")

# --- 保存処理 ---
if submitted:
    # バリデーション：時間は数字のみか確認
    if duration_raw and not duration_raw.isdigit():
        st.error("「時間」には半角数字のみを入力してください。")
    elif start_time_raw and not re.match(r"^\d{1,2}:\d{2}$", start_time_raw):
        st.error("「開始時間」は 09:00 のような形式（半角）で入力してください。")
    else:
        try:
            formatted_date = selected_date.strftime("%-m/%-d")
            
            # --- ここが修正ポイント ---
            # 入力された文字を数値(int)に変換。空の場合はNone（または空文字）にする
            duration_value = int(duration_raw) if duration_raw else ""
            
            study_time = ""
            rest_time = ""
            if category == "休む":
                rest_time = duration_value  # 数値として代入
            else:
                study_time = duration_value # 数値として代入
            # --------------------------

            row = [
                formatted_date,
                weekday_str,
                category,
                start_time_raw,
                study_time,
                rest_time,
                location,
                memo
            ]
            
            # 数字を数字として書き込む設定
            sheet.append_row(row, value_input_option="RAW")
            st.success("保存完了しました！")
            st.balloons()
        except Exception as e:
            st.error(f"保存失敗: {e}")