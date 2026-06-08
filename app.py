import streamlit as st
import gspread
from google.oauth2.service_account import Credentials # ライブラリを変更
from datetime import datetime, timezone, timedelta

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
now_jst = datetime.now(JST)

# --- 開始時間・所要時間のpills→入力欄への自動反映 ---
def on_time_pill_change():
    val = st.session_state.get('time_pill')
    if val is not None:
        st.session_state['start_time_input'] = val

def on_start_time_change():
    st.session_state['time_pill'] = None

def on_duration_pill_change():
    val = st.session_state.get('duration_pill')
    if val is not None:
        st.session_state['duration_input'] = val

def on_duration_change():
    st.session_state['duration_pill'] = None

# --- リセット処理（日付以外を初期状態に戻す） ---
def reset_form():
    st.session_state['category_pill']      = "読書"
    st.session_state['time_pill']          = None
    st.session_state['start_time_input']   = ""
    st.session_state['duration_pill']      = None
    st.session_state['duration_input']     = ""
    st.session_state['location_pill']      = None
    st.session_state['location_other']     = ""
    st.session_state['input_output_pill']  = None
    st.session_state['memo_input']         = ""

# --- セッション初期化 ---
for key, default in [
    ('start_time_input', ""),
    ('duration_input',   ""),
    ('location_other',   ""),
    ('memo_input',       ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- アプリ画面構成 ---
st.title("📚 学習記録入力")

selected_date = st.date_input("日付", now_jst)
weekdays = ["月", "火", "水", "木", "金", "土", "日"]
weekday_str = weekdays[selected_date.weekday()]

category = st.pills(
    "分野",
    ["読書", "瞑想", "バイナリー", "IT", "ジャーナリング", "その他", "休む"],
    default="読書",
    key="category_pill"
)

st.pills("開始時間", ["朝", "昼", "夕方", "夜"],
         key="time_pill",
         on_change=on_time_pill_change)
start_time_raw = st.text_input("開始時間_input",
                                key="start_time_input",
                                on_change=on_start_time_change,
                                placeholder="カスタム入力（例: 09:00）",
                                label_visibility="collapsed")

st.pills("時間（分）", ["5", "10", "15", "20", "25", "30"],
         key="duration_pill",
         on_change=on_duration_pill_change)
duration_raw = st.text_input("時間（分）_input",
                              key="duration_input",
                              on_change=on_duration_change,
                              placeholder="半角数字（カスタム入力）",
                              label_visibility="collapsed")

# 場所の選択（その他は自由記入）
location_choice = st.pills("場所", ["//", "家", "外", "スタバ", "マクド", "cafe", "その他"],
                            key="location_pill")
location = ""
if location_choice == "その他":
    location = st.text_input("場所（自由記入）",
                              key="location_other",
                              placeholder="場所を入力してください")
elif location_choice:
    location = location_choice

input_output = st.pills("種別", ["-", "In", "Out"], key="input_output_pill")

memo = st.text_area("備考", key="memo_input")

# --- ボタン行：保存（左・大）＋ リセット（右・小） ---
col_save, col_reset = st.columns([3, 1])

with col_reset:
    st.button("🔄 リセット", on_click=reset_form, use_container_width=True)

with col_save:
    save_clicked = st.button("スプレッドシートに保存", type="primary", use_container_width=True)

# --- 保存処理 ---
if save_clicked:
    if duration_raw and not duration_raw.isdigit():
        st.error("「時間」には半角数字のみを入力してください。")
    else:
        try:
            target_sheet_name = f"{selected_date.year}年{selected_date.month}月"

            try:
                sheet = workbook.worksheet(target_sheet_name)
            except gspread.WorksheetNotFound:
                st.error(f"エラー: シート『{target_sheet_name}』が見つかりません。")
                st.stop()

            col_a_values = sheet.col_values(1)
            next_row = len(col_a_values) + 1

            formatted_date = selected_date.strftime("%-m/%-d")
            duration_value = int(duration_raw) if duration_raw else ""

            study_time = ""
            rest_time = ""
            if category == "休む":
                rest_time = duration_value
            else:
                study_time = duration_value

            # A〜I列: 日付, 曜日, 分野, 開始時間, 学習時間, 休憩時間, 場所, 種別, 備考
            row = [
                formatted_date, weekday_str, category, start_time_raw,
                study_time, rest_time, location, input_output or "", memo
            ]

            range_to_update = f"A{next_row}:I{next_row}"
            sheet.update(range_name=range_to_update, values=[row], value_input_option="USER_ENTERED")

            st.success(f"『{target_sheet_name}』の {next_row} 行目に保存しました！")
            st.balloons()

        except Exception as e:
            st.error(f"保存失敗: {e}")
