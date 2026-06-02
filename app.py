from __future__ import annotations

from datetime import date, timedelta
import os

import streamlit as st
from dotenv import load_dotenv

from database import (
    get_best_check,
    get_previous_check,
    get_rankings,
    get_settings,
    init_db,
    list_price_checks,
    now_iso,
    save_price_check,
    upsert_setting,
)
from services.flight_api import BAGGAGE_FEES, SEAT_FEES, FlightApiClient, build_playwright_search_plan
from services.hotel_api import HOTEL_NAME, HotelApiClient
from services.manual_input import normalize_manual_prices
from services.notifier import send_discord_notification, send_email_notification, should_notify


load_dotenv()

DB_PATH = os.getenv("DATABASE_PATH", "travel_prices.sqlite3")
init_db(DB_PATH)

st.set_page_config(
    page_title="Jetstar NRT-KCZ 旅行費用チェック",
    page_icon="✈️",
    layout="wide",
)


def yen(value: int | float | None) -> str:
    if value is None:
        return "-"
    return f"{int(value):,}円"


def signed_yen(value: int | None) -> str:
    if value is None:
        return "-"
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value:,}円"


def save_and_report(record: dict) -> int:
    saved_id = save_price_check(record, DB_PATH)
    st.session_state["last_record"] = record | {"id": saved_id}
    return saved_id


settings = get_settings(DB_PATH)

st.title("Jetstar NRT-KCZ 旅行費用チェック")
st.caption("成田空港から高知空港へ来る友人向けの、個人利用ローカルWebアプリです。")

search_tab, result_tab, history_tab, ranking_tab, settings_tab = st.tabs(
    ["検索条件入力", "価格結果", "履歴", "最安ランキング", "設定"]
)

with search_tab:
    st.subheader("検索条件")
    mode = st.radio("価格取得モード", ["モックAPI", "手動入力"], horizontal=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        departure_date = st.date_input("出発日", value=date.today() + timedelta(days=14))
    with col2:
        return_date = st.date_input("帰宅日", value=date.today() + timedelta(days=16))
    with col3:
        guests = st.number_input("宿泊人数", min_value=1, max_value=6, value=1, step=1)

    col4, col5 = st.columns(2)
    with col4:
        baggage_plan = st.selectbox("手荷物プラン", list(BAGGAGE_FEES.keys()))
    with col5:
        seat_plan = st.selectbox("座席指定", list(SEAT_FEES.keys()))

    if return_date <= departure_date:
        st.warning("帰宅日は出発日より後の日付にしてください。")

    manual_prices = None
    if mode == "手動入力":
        st.divider()
        st.subheader("手動価格")
        m1, m2, m3 = st.columns(3)
        with m1:
            manual_outbound = st.number_input("往路の最安運賃", min_value=0, value=9500, step=100)
            manual_return = st.number_input("復路の最安運賃", min_value=0, value=9900, step=100)
        with m2:
            manual_baggage = st.number_input("手荷物オプション込み価格", min_value=0, value=BAGGAGE_FEES[baggage_plan], step=100)
            manual_seat = st.number_input("座席指定込み価格", min_value=0, value=SEAT_FEES[seat_plan], step=100)
        with m3:
            manual_hotel = st.number_input("ホテル宿泊料金", min_value=0, value=12400, step=100)
        manual_booking_url = st.text_input("航空券予約ページ", value="https://www.jetstar.com/jp/ja/home")
        manual_hotel_url = st.text_input("ホテル予約ページ", value="https://travel.rakuten.co.jp/")
        manual_notes = st.text_area("メモ", placeholder="公式サイトで確認した条件など")
        manual_prices = normalize_manual_prices(
            manual_outbound,
            manual_return,
            manual_baggage,
            manual_seat,
            manual_hotel,
            manual_booking_url,
            manual_hotel_url,
            manual_notes,
        )

    threshold = int(settings.get("notify_threshold", "0") or 0)
    notify_channel = settings.get("notify_channel", "なし") or "なし"

    if st.button("価格をチェックして保存", type="primary", disabled=return_date <= departure_date):
        previous = get_previous_check(
            departure_date.isoformat(),
            return_date.isoformat(),
            int(guests),
            baggage_plan,
            seat_plan,
            DB_PATH,
        )
        best = get_best_check(DB_PATH)

        if mode == "手動入力" and manual_prices:
            total_price = manual_prices.total_price
            record = {
                "checked_at": now_iso(),
                "departure_date": departure_date.isoformat(),
                "return_date": return_date.isoformat(),
                "guests": int(guests),
                "baggage_plan": baggage_plan,
                "seat_plan": seat_plan,
                "outbound_fare": manual_prices.outbound_fare,
                "return_fare": manual_prices.return_fare,
                "baggage_fee": manual_prices.baggage_fee,
                "seat_fee": manual_prices.seat_fee,
                "hotel_fee": manual_prices.hotel_fee,
                "total_price": total_price,
                "booking_url": manual_prices.booking_url,
                "hotel_url": manual_prices.hotel_url,
                "source": "manual",
                "notes": manual_prices.notes,
            }
        else:
            flight_client = FlightApiClient(use_mock=True)
            hotel_client = HotelApiClient(use_mock=True)
            flight = flight_client.search_round_trip(departure_date, return_date, baggage_plan, seat_plan)
            hotel = hotel_client.search_stay(departure_date, return_date, int(guests))
            total_price = flight.total + hotel.total_price
            record = {
                "checked_at": now_iso(),
                "departure_date": departure_date.isoformat(),
                "return_date": return_date.isoformat(),
                "guests": int(guests),
                "baggage_plan": baggage_plan,
                "seat_plan": seat_plan,
                "outbound_fare": flight.outbound_fare,
                "return_fare": flight.return_fare,
                "baggage_fee": flight.baggage_fee,
                "seat_fee": flight.seat_fee,
                "hotel_fee": hotel.total_price,
                "total_price": total_price,
                "booking_url": flight.booking_url,
                "hotel_url": hotel.hotel_url,
                "source": f"{flight.source}+{hotel.source}",
                "notes": f"{HOTEL_NAME} / {hotel.nights}泊",
            }

        record["previous_diff"] = None if previous is None else total_price - int(previous["total_price"])
        record["best_diff"] = None if best is None else total_price - int(best["total_price"])
        save_and_report(record)

        summary = (
            f"{departure_date.isoformat()} - {return_date.isoformat()} / "
            f"合計 {yen(total_price)} / 前回差額 {signed_yen(record['previous_diff'])}"
        )
        if should_notify(total_price, threshold):
            if notify_channel == "Discord":
                result = send_discord_notification(total_price, summary)
                st.info(result.message)
            elif notify_channel == "メール":
                result = send_email_notification(total_price, summary)
                st.info(result.message)

        st.success("価格チェックを保存しました。価格結果タブで確認できます。")

    with st.expander("半自動モードの設計メモ"):
        plan = build_playwright_search_plan(departure_date, return_date)
        st.json(plan)

with result_tab:
    st.subheader("価格結果")
    record = st.session_state.get("last_record")
    if not record:
        latest = list_price_checks(1, DB_PATH)
        record = latest[0] if latest else None

    if not record:
        st.info("まだ価格チェックがありません。検索条件入力画面からチェックしてください。")
    else:
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("往路の最安運賃", yen(record["outbound_fare"]))
        r2.metric("復路の最安運賃", yen(record["return_fare"]))
        r3.metric("手荷物オプション込み価格", yen(record["baggage_fee"]))
        r4.metric("座席指定込み価格", yen(record["seat_fee"]))

        r5, r6, r7 = st.columns(3)
        r5.metric("ホテル宿泊料金", yen(record["hotel_fee"]))
        r6.metric("航空券＋ホテル合計", yen(record["total_price"]))
        r7.metric("前回チェック時との差額", signed_yen(record.get("previous_diff")))

        best_diff = record.get("best_diff")
        if best_diff is None:
            st.info("過去最安との比較: 初回または比較対象がありません。")
        elif best_diff == 0:
            st.success("過去最安と同額です。")
        elif best_diff > 0:
            st.warning(f"過去最安より {yen(best_diff)} 高いです。")
        else:
            st.success(f"過去最安を {yen(abs(best_diff))} 更新しました。")

        link_col1, link_col2 = st.columns(2)
        link_col1.link_button("Jetstar予約ページを開く", record["booking_url"])
        link_col2.link_button("ホテル予約ページを開く", record["hotel_url"])
        st.caption("表示価格は参考価格です。予約前に必ずJetstar公式サイトおよびホテル予約サイトで最終確認してください。")

with history_tab:
    st.subheader("履歴")
    rows = list_price_checks(100, DB_PATH)
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("履歴はまだありません。")

with ranking_tab:
    st.subheader("最安ランキング")
    rows = get_rankings(30, DB_PATH)
    if rows:
        st.dataframe(
            [
                {
                    "順位": idx + 1,
                    "合計": yen(row["total_price"]),
                    "出発日": row["departure_date"],
                    "帰宅日": row["return_date"],
                    "手荷物": row["baggage_plan"],
                    "座席": row["seat_plan"],
                    "確認日時": row["checked_at"],
                }
                for idx, row in enumerate(rows)
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("ランキングはまだありません。")

with settings_tab:
    st.subheader("設定")
    current_threshold = int(settings.get("notify_threshold", "0") or 0)
    current_channel = settings.get("notify_channel", "なし") or "なし"
    new_threshold = st.number_input("指定金額以下になったら通知", min_value=0, value=current_threshold, step=1000)
    new_channel = st.selectbox("通知方法", ["なし", "Discord", "メール"], index=["なし", "Discord", "メール"].index(current_channel))
    st.text_input("Discord Webhook URL", value=os.getenv("DISCORD_WEBHOOK_URL", ""), type="password", disabled=True)
    st.caption(".env に DISCORD_WEBHOOK_URL または SMTP設定を保存してください。画面上では秘密情報を保存しません。")

    if st.button("設定を保存"):
        upsert_setting("notify_threshold", str(int(new_threshold)), DB_PATH)
        upsert_setting("notify_channel", new_channel, DB_PATH)
        st.success("設定を保存しました。")
