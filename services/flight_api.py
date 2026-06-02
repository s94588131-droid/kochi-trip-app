from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import os


JETSTAR_SEARCH_URL = "https://www.jetstar.com/jp/ja/home"


@dataclass(frozen=True)
class FlightQuote:
    outbound_fare: int
    return_fare: int
    baggage_fee: int
    seat_fee: int
    booking_url: str
    source: str

    @property
    def total(self) -> int:
        return self.outbound_fare + self.return_fare + self.baggage_fee + self.seat_fee


BAGGAGE_FEES = {
    "機内持ち込み7kgのみ": 0,
    "機内持ち込み追加あり": 3000,
    "受託手荷物20kgあり": 5200,
}

SEAT_FEES = {
    "なし": 0,
    "標準席": 800,
    "前方席": 1200,
    "足元広め席": 2200,
}


class FlightApiClient:
    """Adapter boundary for replacing mock quotes with a real provider such as Duffel."""

    def __init__(self, api_token: str | None = None, use_mock: bool = True) -> None:
        self.api_token = api_token or os.getenv("DUFFEL_API_TOKEN")
        self.use_mock = use_mock or not self.api_token

    def search_round_trip(
        self,
        departure_date: date,
        return_date: date,
        baggage_plan: str,
        seat_plan: str,
    ) -> FlightQuote:
        if self.use_mock:
            return self._mock_search(departure_date, return_date, baggage_plan, seat_plan)
        return self._duffel_search_placeholder(departure_date, return_date, baggage_plan, seat_plan)

    def _mock_search(
        self,
        departure_date: date,
        return_date: date,
        baggage_plan: str,
        seat_plan: str,
    ) -> FlightQuote:
        outbound_fare = _mock_fare(departure_date, "outbound")
        return_fare = _mock_fare(return_date, "return")
        return FlightQuote(
            outbound_fare=outbound_fare,
            return_fare=return_fare,
            baggage_fee=BAGGAGE_FEES.get(baggage_plan, 0),
            seat_fee=SEAT_FEES.get(seat_plan, 0),
            booking_url=JETSTAR_SEARCH_URL,
            source="mock_flight",
        )

    def _duffel_search_placeholder(
        self,
        departure_date: date,
        return_date: date,
        baggage_plan: str,
        seat_plan: str,
    ) -> FlightQuote:
        raise NotImplementedError(
            "Duffel API connection is intentionally left as an adapter point. "
            "Set use_mock=True or implement offer request/selection here."
        )


def build_playwright_search_plan(departure_date: date, return_date: date) -> dict[str, str]:
    return {
        "url": JETSTAR_SEARCH_URL,
        "origin": "NRT",
        "destination": "KCZ",
        "departure_date": departure_date.isoformat(),
        "return_date": return_date.isoformat(),
        "note": "半自動化する場合は、Playwrightで公式サイトを開いて検索条件の入力補助だけを行います。",
    }


def _mock_fare(travel_date: date, direction: str) -> int:
    day_factor = int(datetime.combine(travel_date, datetime.min.time()).strftime("%j"))
    weekday_factor = 2500 if travel_date.weekday() in (4, 5, 6) else 800
    direction_factor = 700 if direction == "return" else 0
    seasonal_factor = 3500 if travel_date.month in (3, 4, 8, 12) else 0
    return 6990 + (day_factor % 9) * 420 + weekday_factor + direction_factor + seasonal_factor
