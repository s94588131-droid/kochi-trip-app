from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os


HOTEL_NAME = "ベストプライスホテル高知"
HOTEL_SEARCH_URL = "https://travel.rakuten.co.jp/"


@dataclass(frozen=True)
class HotelQuote:
    hotel_name: str
    nights: int
    guests: int
    total_price: int
    hotel_url: str
    source: str


class HotelApiClient:
    """Adapter boundary for Rakuten Travel, Booking.com Demand API, or another hotel API."""

    def __init__(self, api_key: str | None = None, use_mock: bool = True) -> None:
        self.api_key = api_key or os.getenv("RAKUTEN_TRAVEL_APP_ID") or os.getenv("BOOKING_COM_API_KEY")
        self.use_mock = use_mock or not self.api_key

    def search_stay(self, checkin_date: date, checkout_date: date, guests: int) -> HotelQuote:
        nights = max((checkout_date - checkin_date).days, 0)
        if self.use_mock:
            return self._mock_search(checkin_date, nights, guests)
        return self._provider_search_placeholder(checkin_date, checkout_date, guests)

    def _mock_search(self, checkin_date: date, nights: int, guests: int) -> HotelQuote:
        base_per_night = 6200
        weekend_fee = 1200 if checkin_date.weekday() in (4, 5) else 0
        seasonal_fee = 1800 if checkin_date.month in (3, 4, 8, 12) else 0
        total = (base_per_night + weekend_fee + seasonal_fee) * max(nights, 1) * max(guests, 1)
        return HotelQuote(
            hotel_name=HOTEL_NAME,
            nights=max(nights, 1),
            guests=guests,
            total_price=total,
            hotel_url=HOTEL_SEARCH_URL,
            source="mock_hotel",
        )

    def _provider_search_placeholder(self, checkin_date: date, checkout_date: date, guests: int) -> HotelQuote:
        raise NotImplementedError(
            "Hotel API connection is intentionally left as an adapter point. "
            "Set use_mock=True or implement provider-specific hotel lookup here."
        )
