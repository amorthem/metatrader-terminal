"""Tests for trading endpoints (order execution).

These tests place real orders on a demo account. They require:
- MT5 terminal connected to a demo broker
- Algo trading enabled
- Sufficient demo balance
"""
import pytest
import time


DEMO_SYMBOL = "EURUSD"
DEMO_VOLUME = 0.01


@pytest.fixture(scope="module")
def ensure_symbol_selected(client):
    """Ensure test symbol is in Market Watch."""
    client.post(f"/api/v1/symbols/select/{DEMO_SYMBOL}")


def test_order_check(client, ensure_symbol_selected):
    r = client.get(f"/api/v1/trading/order_check/{DEMO_SYMBOL}")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data


def test_order_check_unknown_symbol(client):
    r = client.get("/api/v1/trading/order_check/FAKESYMBOL")
    assert r.status_code == 404


def test_send_buy_order(client, ensure_symbol_selected):
    """Place a BUY order, verify it appears in positions, then close it."""
    # Get current price for SL
    tick = client.get(f"/api/v1/symbols/ticks/{DEMO_SYMBOL}").json()
    sl = round(tick["bid"] - 0.01, 5)

    r = client.post("/api/v1/trading/order", json={
        "symbol": DEMO_SYMBOL,
        "volume": DEMO_VOLUME,
        "order_type": "BUY",
        "sl": sl,
        "type_filling": "FOK",
    })
    assert r.status_code == 201, f"Order failed: {r.json()}"
    data = r.json()
    assert data["success"] is True

    # Verify position exists
    time.sleep(1)
    positions = client.get("/api/v1/positions/").json()
    tickets = [p["ticket"] for p in positions]
    order_ticket = data["trade"]["transaction_broker_id"]
    # The position ticket may differ from order ticket, check by symbol
    symbols = [p["symbol"] for p in positions]
    assert DEMO_SYMBOL in symbols

    # Close the position
    if positions:
        pos = next((p for p in positions if p["symbol"] == DEMO_SYMBOL), None)
        if pos:
            close_r = client.post("/api/v1/positions/close", params={
                "ticket": pos["ticket"],
                "type_filling": "FOK",
            })
            assert close_r.status_code == 200


def test_send_sell_order(client, ensure_symbol_selected):
    """Place a SELL order and close it."""
    tick = client.get(f"/api/v1/symbols/ticks/{DEMO_SYMBOL}").json()
    sl = round(tick["ask"] + 0.01, 5)

    r = client.post("/api/v1/trading/order", json={
        "symbol": DEMO_SYMBOL,
        "volume": DEMO_VOLUME,
        "order_type": "SELL",
        "sl": sl,
        "type_filling": "FOK",
    })
    assert r.status_code == 201, f"Order failed: {r.json()}"
    assert r.json()["success"] is True

    # Close
    time.sleep(1)
    positions = client.get("/api/v1/positions/").json()
    pos = next((p for p in positions if p["symbol"] == DEMO_SYMBOL), None)
    if pos:
        client.post("/api/v1/positions/close", params={
            "ticket": pos["ticket"],
            "type_filling": "FOK",
        })


def test_send_order_with_tp(client, ensure_symbol_selected):
    """Place order with take profit."""
    tick = client.get(f"/api/v1/symbols/ticks/{DEMO_SYMBOL}").json()
    sl = round(tick["bid"] - 0.01, 5)
    tp = round(tick["ask"] + 0.01, 5)

    r = client.post("/api/v1/trading/order", json={
        "symbol": DEMO_SYMBOL,
        "volume": DEMO_VOLUME,
        "order_type": "BUY",
        "sl": sl,
        "tp": tp,
        "type_filling": "FOK",
    })
    assert r.status_code == 201
    assert r.json()["success"] is True

    # Cleanup
    time.sleep(1)
    positions = client.get("/api/v1/positions/").json()
    pos = next((p for p in positions if p["symbol"] == DEMO_SYMBOL), None)
    if pos:
        client.post("/api/v1/positions/close", params={
            "ticket": pos["ticket"],
            "type_filling": "FOK",
        })


def test_send_order_invalid_type(client):
    r = client.post("/api/v1/trading/order", json={
        "symbol": DEMO_SYMBOL,
        "volume": DEMO_VOLUME,
        "order_type": "INVALID",
        "sl": 1.0,
    })
    assert r.status_code == 422


def test_modify_sl_tp(client, ensure_symbol_selected):
    """Place an order, modify SL/TP, then close."""
    tick = client.get(f"/api/v1/symbols/ticks/{DEMO_SYMBOL}").json()
    sl = round(tick["bid"] - 0.01, 5)

    # Open position
    r = client.post("/api/v1/trading/order", json={
        "symbol": DEMO_SYMBOL,
        "volume": DEMO_VOLUME,
        "order_type": "BUY",
        "sl": sl,
        "type_filling": "FOK",
    })
    assert r.status_code == 201
    trade_id = r.json()["trade"]["id"]

    time.sleep(1)

    # Modify SL/TP
    new_sl = round(tick["bid"] - 0.02, 5)
    new_tp = round(tick["ask"] + 0.02, 5)
    mod_r = client.post("/api/v1/trading/modify-sl-tp", params={"trade_id": trade_id}, json={
        "ticket": 0,  # not used by endpoint, trade_id is the param
        "sl": new_sl,
        "tp": new_tp,
    })
    assert mod_r.status_code == 200

    # Cleanup
    positions = client.get("/api/v1/positions/").json()
    pos = next((p for p in positions if p["symbol"] == DEMO_SYMBOL), None)
    if pos:
        client.post("/api/v1/positions/close", params={
            "ticket": pos["ticket"],
            "type_filling": "FOK",
        })
