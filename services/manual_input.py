from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ManualPrices:
    outbound_fare: int
    return_fare: int
    baggage_fee: int
    seat_fee: int
    hotel_fee: int
    booking_url: str
    hotel_url: str
    notes: str = ""

    @property
    def total_price(self) -> int:
        return self.outbound_fare + self.return_fare + self.baggage_fee + self.seat_fee + self.hotel_fee


def normalize_manual_prices(
    outbound_fare: int,
    return_fare: int,
    baggage_fee: int,
    seat_fee: int,
    hotel_fee: int,
    booking_url: str,
    hotel_url: str,
    notes: str = "",
) -> ManualPrices:
    return ManualPrices(
        outbound_fare=max(outbound_fare, 0),
        return_fare=max(return_fare, 0),
        baggage_fee=max(baggage_fee, 0),
        seat_fee=max(seat_fee, 0),
        hotel_fee=max(hotel_fee, 0),
        booking_url=booking_url.strip(),
        hotel_url=hotel_url.strip(),
        notes=notes.strip(),
    )
