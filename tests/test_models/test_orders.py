from __future__ import annotations

import pytest

from bayse_markets.models.order import Order, PlacedOrder, PlaceOrderResponse

# Captured from a live CLOB placement on 2026-07-29. Note `outcome` holds a UUID
# and `type` holds the SIDE here, while the read route below spells the same
# outcome as `outcomeId` and puts the order type in `type`. The two routes really
# do disagree; the models are what reconcile them.
LIVE_PLACE_RESPONSE = {
    "engine": "CLOB",
    "clobOrder": {
        "id": "d5cfd1b2-e445-4fa1-b949-06baf62bb21f",
        "marketId": "a0922e06-a65a-46cb-95dc-96f3270a7bad",
        "userId": "00000000-0000-0000-0000-0000000000ff",
        "outcome": "25d84c55-f0fa-4b5d-a928-5ee67557d1a8",
        "orderType": "LIMIT",
        "type": "BUY",
        "side": "BUY",
        "amount": 100,
        "quantity": 99.99,
        "price": 0.01,
        "size": 99.99,
        "filledSize": 0,
        "remainingSize": 99.99,
        "status": "open",
        "fee": 0,
        "postOnly": True,
        "stpMode": "SKIP",
        "createdAt": "2026-07-28T23:42:38Z",
        "updatedAt": "2026-07-28T23:42:38Z",
    },
}

# Captured from GET /v1/pm/orders/{id} for that same order.
LIVE_GET_RESPONSE = {
    "id": "d5cfd1b2-e445-4fa1-b949-06baf62bb21f",
    "marketId": "a0922e06-a65a-46cb-95dc-96f3270a7bad",
    "outcomeLabel": "Up",
    "outcomeId": "25d84c55-f0fa-4b5d-a928-5ee67557d1a8",
    "side": "BUY",
    "type": "LIMIT",
    "stpMode": "SKIP",
    "status": "cancelled",
    "amount": 100,
    "price": 0.01,
    "size": 99.99,
    "filledSize": 0,
    "remainingSize": 99.99,
    "currency": "NGN",
    "createdAt": "2026-07-28T23:42:38Z",
    "updatedAt": "2026-07-28T23:42:38Z",
}


class TestOutcomeIdNaming:
    """`outcome` held a UUID on both models. Both are now `outcome_id`."""

    def test_order_parses_outcome_id_from_read_route(self) -> None:
        order = Order.model_validate(LIVE_GET_RESPONSE)

        assert order.outcome_id == "25d84c55-f0fa-4b5d-a928-5ee67557d1a8"

    def test_placed_order_parses_outcome_id_from_write_route(self) -> None:
        placed = PlacedOrder.model_validate(LIVE_PLACE_RESPONSE["clobOrder"])

        assert placed.outcome_id == "25d84c55-f0fa-4b5d-a928-5ee67557d1a8"

    def test_both_routes_agree_on_the_outcome_despite_different_wire_keys(self) -> None:
        order = Order.model_validate(LIVE_GET_RESPONSE)
        placed = PlacedOrder.model_validate(LIVE_PLACE_RESPONSE["clobOrder"])

        assert order.outcome_id == placed.outcome_id

    def test_place_response_selects_clob_order(self) -> None:
        parsed = PlaceOrderResponse.model_validate(LIVE_PLACE_RESPONSE)

        assert parsed.order is not None
        assert parsed.order.outcome_id == "25d84c55-f0fa-4b5d-a928-5ee67557d1a8"

    def test_outcome_attribute_is_gone(self) -> None:
        """Renamed outright in 0.2.0 — no deprecation shim."""
        order = Order.model_validate(LIVE_GET_RESPONSE)

        with pytest.raises(AttributeError):
            _ = order.outcome

    def test_wire_format_dump_is_unchanged_by_the_rename(self) -> None:
        """by_alias dumps still round-trip to the API's spelling."""
        order = Order.model_validate(LIVE_GET_RESPONSE)

        dumped = order.model_dump(by_alias=True)

        assert dumped["outcomeId"] == "25d84c55-f0fa-4b5d-a928-5ee67557d1a8"
        assert "outcome" not in dumped

    def test_unaliased_dump_uses_the_new_field_name(self) -> None:
        """This key DID change in 0.2.0 — it is called out in the changelog."""
        order = Order.model_validate(LIVE_GET_RESPONSE)

        dumped = order.model_dump()

        assert dumped["outcome_id"] == "25d84c55-f0fa-4b5d-a928-5ee67557d1a8"
        assert "outcome" not in dumped

    def test_models_can_be_built_by_field_name(self) -> None:
        placed = PlacedOrder(id="x", outcome_id="abc")

        assert placed.outcome_id == "abc"
