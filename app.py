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
    duration_raw = st.text_input("時間（分）", value="", placeholder="半角数字で入力")

    # 5. 場所と備考
    location = st.text_input("場所")
    memo = st.text_area("備考")

    submitted = st.form_submit_button("スプレッドシートに保存")

# --- 保存処理 ---
if submitted:
    # バリデーション：時間は数字のみか確認（開始時間のチェックは削除しました）
    if duration_raw and not duration_raw.isdigit():
        st.error("「時間」には半角数字のみを入力してください。")
    else:
        try:
            # --- 年と月でシートを指定（例：2025年2月） ---
            target_sheet_name = f"{selected_date.year}年{selected_date.month}月"
            
            try:
                sheet = workbook.worksheet(target_sheet_name)
            except gspread.WorksheetNotFound:
                st.error(f"エラー: シート『{target_sheet_name}』が見つかりません。スプレッドシートのタブ名を『{target_sheet_name}』に変更または作成してください。")
                st.stop()
            # ---------------------------------------

            # データの整形
            formatted_date = selected_date.strftime("%-m/%-d")
            duration_value = int(duration_raw) if duration_raw else ""
            
            study_time = ""
            rest_time = ""
            if category == "休む":
                rest_time = duration_value
            else:
                study_time = duration_value

            # 書き込む行の作成
            row = [
                formatted_date,
                weekday_str,
                category,
                start_time_raw, # ここに「朝」などの文字もそのまま入ります
                study_time,
                rest_time,
                location,
                memo
            ]
            
            # 保存
            # USER_ENTERED なので「09:00」は時刻、「朝」は文字列として自動判定されます
            sheet.append_row(row, value_input_option="USER_ENTERED")
            
            st.success(f"『{target_sheet_name}』シートに保存完了しました！")
            st.balloons()

        except Exception as e:
            st.error(f"保存失敗: {e}")