"""Order types and placeholders for the Bayse prediction market.

The full order schema will be locked down as the API is explored.
For now, use ``client.place_order(event_id, market_id, body=...)``
with a raw dict until the typed models are confirmed.
"""

from bayse_markets.orders.models import LimitOrder, MarketOrder, OrderRequest

__all__ = [
    "OrderRequest",
    "LimitOrder",
    "MarketOrder",
]
