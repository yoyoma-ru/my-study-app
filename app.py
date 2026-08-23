import streamlit as st
import gspread
from google.oauth2.service_account import Credentials # ライブラリを変更
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta

# --- スプレッドシート・カレンダー接続設定 (Secrets対応版) ---
SPREADSHEET_NAME = "学習時間"

# 認証情報とスプレッドシート接続はキャッシュ（操作のたびの再接続を避けて高速化）。
# gspread(requests)は接続が切れても自動で張り直すので、キャッシュしても問題ない。
@st.cache_resource
def get_credentials():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/calendar',  # カレンダー連携用
    ]
    conf = st.secrets["gcp_service_account"]
    return Credentials.from_service_account_info(conf, scopes=scope)

@st.cache_resource
def get_workbook():
    client = gspread.authorize(get_credentials())
    return client.open(SPREADSHEET_NAME)

# カレンダー(googleapiclient/httplib2)はキャッシュした接続がアイドル切断されると
# 最初の登録で [Errno 32] Broken pipe になる。保存のたびに新しい接続で作り直し、
# さらに接続切れに備えて最大2回試行する。
def insert_calendar_event(event):
    last_err = None
    for _ in range(2):
        try:
            service = build('calendar', 'v3', credentials=get_credentials(), cache_discovery=False)
            service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
            return
        except Exception as e:
            last_err = e
    raise last_err

try:
    workbook = get_workbook()
except Exception as e:
    st.error(f"エラー: スプレッドシート『{SPREADSHEET_NAME}』が見つかりません。")
    st.error(f"詳細エラー: {e}")
    st.stop()

# 登録先カレンダーID（＝ユーザーのGmailアドレス）。service accountに共有しておくこと
CALENDAR_ID = st.secrets["user_calendar_id"]

# --- 日本時間(JST)を取得する設定 ---
JST = timezone(timedelta(hours=+9), 'JST')
now_jst = datetime.now(JST)

# --- 開始時刻の自動計算（終了時刻 − 所要時間）---
def recompute_start():
    end_dt = st.session_state.get('end_time_dt')
    dur = st.session_state.get('duration_input', '')
    if end_dt and dur and dur.isdigit():
        st.session_state['start_time_input'] = (end_dt - timedelta(minutes=int(dur))).strftime("%H:%M")

# 「現在時刻」ボタン：今のJSTを終了時刻として取り込み、開始時刻を再計算
def set_now():
    st.session_state['end_time_dt'] = datetime.now(JST)
    recompute_start()

# 所要時間pills→入力欄へ反映し、開始時刻を再計算
def on_duration_pill_change():
    val = st.session_state.get('duration_pill')
    if val is not None:
        st.session_state['duration_input'] = val
    recompute_start()

# 所要時間の手入力変更時：pill選択を解除し、開始時刻を再計算
def on_duration_change():
    st.session_state['duration_pill'] = None
    recompute_start()

# --- リセット処理（日付以外を初期状態に戻す） ---
def reset_form():
    st.session_state['category_pill']      = "バイナリー"
    st.session_state['duration_pill']      = None
    st.session_state['duration_input']     = ""
    st.session_state['start_time_input']   = ""
    st.session_state['location_pill']      = "//"
    st.session_state['location_other']     = ""
    st.session_state['input_output_pill']  = None
    st.session_state['memo_input']         = ""
    st.session_state['end_time_dt']        = datetime.now(JST)
    recompute_start()

# --- クイック入力プリセット（よく登録する項目をまとめて入力）---
def apply_preset(category, duration, location, input_output, memo):
    st.session_state['category_pill']      = category
    st.session_state['duration_pill']      = duration or None   # 未指定はpill選択なし
    st.session_state['duration_input']     = duration
    st.session_state['start_time_input']   = ""                 # 一旦クリア（durationがあれば再計算）
    st.session_state['location_pill']      = location
    st.session_state['location_other']     = ""
    st.session_state['input_output_pill']  = input_output
    st.session_state['memo_input']         = memo
    st.session_state['end_time_dt']        = datetime.now(JST)  # 開始時刻を現在時刻基準に
    recompute_start()

def preset_meditation():
    apply_preset("瞑想", "5", "家", "-", "呼吸")

def preset_workout():
    apply_preset("休む", "15", "//", "-", "筋トレ")

def preset_journal():
    apply_preset("ジャーナリング", "5", "//", "Out", "日記")

def preset_reading():
    apply_preset("読書", "", "//", "In", "")

# --- セッション初期化 ---
for key, default in [
    ('start_time_input', ""),
    ('duration_input',   ""),
    ('location_pill',    "//"),
    ('location_other',   ""),
    ('memo_input',       ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ページ表示時に現在時刻を終了時刻として取り込む
if 'end_time_dt' not in st.session_state:
    st.session_state['end_time_dt'] = now_jst
    recompute_start()

# --- アプリ画面構成 ---
st.subheader("📚 学習記録入力")

selected_date = st.date_input("日付", now_jst)
weekdays = ["月", "火", "水", "木", "金", "土", "日"]
weekday_str = weekdays[selected_date.weekday()]

# リセット＋クイック入力プリセット（1行に並べる）
col_reset, col_med, col_workout, col_journal, col_reading = st.columns(5)
with col_reset:
    st.button("🔄 リセット", on_click=reset_form, use_container_width=True)
with col_med:
    st.button("🧘 瞑想", on_click=preset_meditation, use_container_width=True)
with col_workout:
    st.button("💪 筋トレ", on_click=preset_workout, use_container_width=True)
with col_journal:
    st.button("📔 朝日記", on_click=preset_journal, use_container_width=True)
with col_reading:
    st.button("📖 読書", on_click=preset_reading, use_container_width=True)

category = st.pills(
    "分野",
    ["バイナリー", "読書", "IT", "ジャーナリング", "英語", "その他", "瞑想", "休む"],
    default="読書",
    key="category_pill"
)

# 開始時間（現在時刻ボタンで自動計算、HH:MM手入力で上書きも可）
st.markdown("**開始時間**")
col_now, col_start = st.columns([1, 2])
with col_now:
    st.button("🕐 現在時刻", on_click=set_now, use_container_width=True)
with col_start:
    start_time_raw = st.text_input("開始時間",
                                    key="start_time_input",
                                    placeholder="例: 09:00",
                                    label_visibility="collapsed")

# 所要時間（pills + カスタム入力）
st.pills("時間（分）",
         ["3", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60"],
         key="duration_pill",
         on_change=on_duration_pill_change)
duration_raw = st.text_input("時間（分）_input",
                              key="duration_input",
                              on_change=on_duration_change,
                              placeholder="半角数字（カスタム入力）",
                              label_visibility="collapsed")

# カレンダー登録のプレビュー（常に1行表示し、入力に応じて文字だけ更新する）
_start_disp = st.session_state.get('start_time_input', '')
_dur_disp = st.session_state.get('duration_input', '')
_preview = "🟡 カレンダー登録: 開始時間と時間を入力すると表示されます"
if _start_disp and _dur_disp.isdigit():
    try:
        _s = datetime.strptime(_start_disp, "%H:%M")
        _e = _s + timedelta(minutes=int(_dur_disp))
        _preview = f"🟡 カレンダー登録: {_start_disp} 〜 {_e.strftime('%H:%M')}（{_dur_disp}分）"
    except ValueError:
        _preview = "⚠️ 開始時間は HH:MM 形式で入力するとカレンダーに登録されます"
st.caption(_preview)

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

memo = st.text_input("備考", key="memo_input")

# --- 保存ボタン ---
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
                sheet = None
                st.error(f"エラー: シート『{target_sheet_name}』が見つかりません。")

            if sheet is not None:
                formatted_date = selected_date.strftime("%-m/%-d")
                duration_value = int(duration_raw) if duration_raw else ""

                status = st.empty()
                lines = []
                abort = False  # カレンダー登録に失敗したらスプレッドシートに書かず中断（二重登録防止）

                # --- 先にGoogleカレンダー登録を試みる（失敗＝保存全体を中止）---
                if duration_value and start_time_raw:
                    try:
                        t = datetime.strptime(start_time_raw, "%H:%M").time()
                    except ValueError:
                        t = None

                    if t is None:
                        lines.append("📅 開始時間が HH:MM 形式でないため、カレンダー登録はスキップしました。")
                    else:
                        start_dt = datetime(selected_date.year, selected_date.month, selected_date.day,
                                            t.hour, t.minute, tzinfo=JST)
                        end_dt = start_dt + timedelta(minutes=duration_value)
                        event = {
                            # タイトルは分野＋所要時間（開始時刻はカレンダー側で表示されるため含めない。例: IT（30分））
                            "summary": f"{category or '学習'}（{duration_value}分）",
                            "location": location,                    # 予定の「場所」欄
                            "description": f"種別: {input_output or '-'}\n備考: {memo}",
                            # 休む・瞑想=緑(バジル/10)、それ以外=黄(バナナ/5)
                            "colorId": "10" if category in ("休む", "瞑想") else "5",
                            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Tokyo"},
                            "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Tokyo"},
                        }
                        try:
                            insert_calendar_event(event)  # 新しい接続で登録（+リトライ）
                            lines.append(f"📅 カレンダーに登録しました（{start_dt.strftime('%H:%M')}〜{end_dt.strftime('%H:%M')}）")
                        except Exception as cal_err:
                            abort = True
                            status.error(
                                "📅 カレンダー登録に失敗したため、保存を中止しました"
                                "（スプレッドシートにも書き込んでいません）。もう一度お試しください。  \n"
                                f"詳細: {cal_err}"
                            )
                else:
                    lines.append("📅 開始時間または所要時間が未入力のため、カレンダー登録はスキップしました。")

                # --- カレンダーが成功 or スキップのときだけスプレッドシートに保存 ---
                if not abort:
                    col_a_values = sheet.col_values(1)
                    next_row = len(col_a_values) + 1

                    study_time = ""
                    rest_time = ""
                    if category in ("休む", "瞑想"):
                        rest_time = duration_value
                    else:
                        study_time = duration_value

                    # A〜I列: 日付, 曜日, 分野, 開始時間, 学習時間, 休憩時間, 場所, 種別, 備考
                    row = [
                        formatted_date, weekday_str, category, start_time_raw,
                        study_time, rest_time, location, input_output or "", memo
                    ]
                    sheet.update(range_name=f"A{next_row}:I{next_row}",
                                 values=[row], value_input_option="USER_ENTERED")

                    # 保存結果は単一のプレースホルダにまとめて表示（行を増やさず文字だけ更新）
                    lines.insert(0, f"✅ 『{target_sheet_name}』の {next_row} 行目に保存しました！")
                    status.success("  \n".join(lines))
                    st.balloons()

        except Exception as e:
            st.error(f"保存失敗: {e}")
