import streamlit as st
import gspread
from google.oauth2.service_account import Credentials # ライブラリを変更
import datetime

# --- スプレッドシート接続設定 (Secrets対応版) ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# st.secrets から認証情報を取得
conf = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(conf, scopes=scope)
client = gspread.authorize(creds)

SPREADSHEET_NAME = "学習時間"

try:
    workbook = client.open(SPREADSHEET_NAME)
except Exception as e:
    st.error(f"エラー: スプレッドシート『{SPREADSHEET_NAME}』が見つかりません。")
    # 実際のエラーメッセージを画面に出すように一時的に変更
    st.error(f"詳細エラー: {e}")

# --- 日本時間(JST)を取得する設定 ---
JST = timezone(timedelta(hours=+9), 'JST')
now_jst = datetime.datetime.now(JST)

# --- アプリ画面構成 ---
st.title("📚 学習記録入力")

with st.form("input_form"):
    selected_date = st.date_input("日付", now_jst)
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_str = weekdays[selected_date.weekday()]

    category = st.selectbox("分野", ["英語", "IT", "バイナリー", "読書", "ジャーナリング", "副業", "その他", "休む"])
    start_time_raw = st.text_input("開始時間", value="", placeholder="例: 09:00, 朝 など")
    duration_raw = st.text_input("時間（分）", value="", placeholder="半角数字")
    location = st.text_input("場所")
    memo = st.text_area("備考")

    submitted = st.form_submit_button("スプレッドシートに保存")

# --- 保存処理 ---
if submitted:
    if duration_raw and not duration_raw.isdigit():
        st.error("「時間」には半角数字のみを入力してください。")
    else:
        try:
            # 年月でシートを指定（例：2026年2月）
            target_sheet_name = f"{selected_date.year}年{selected_date.month}月"
            
            try:
                sheet = workbook.worksheet(target_sheet_name)
            except gspread.WorksheetNotFound:
                st.error(f"エラー: シート『{target_sheet_name}』が見つかりません。")
                st.stop()

            # --- 修正ポイント：A列の最終行を特定する ---
            # A列（日付列）のすべての値を取得
            col_a_values = sheet.col_values(1)
            # 次に書き込むべき行番号（現在のデータ数 + 1）
            next_row = len(col_a_values) + 1
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

            # 保存するデータのリスト（A列からH列まで）
            row = [
                formatted_date, weekday_str, category, start_time_raw,
                study_time, rest_time, location, memo
            ]
            
            # --- 修正ポイント：範囲を指定して更新する ---
            # 例: "A15:H15" のような範囲を作成
            range_to_update = f"A{next_row}:H{next_row}"
            # updateメソッドで、特定した行にデータを書き込む
            sheet.update(range_name=range_to_update, values=[row], value_input_option="USER_ENTERED")
            # ------------------------------------------
            
            st.success(f"『{target_sheet_name}』の {next_row} 行目に保存しました！")
            st.balloons()

        except Exception as e:
            st.error(f"保存失敗: {e}")
