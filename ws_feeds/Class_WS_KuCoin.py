#!/usr/bin/env python
# coding: utf-8

import asyncio
import contextlib
from datetime import datetime
import json
import pandas as pd
import requests
import websockets

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class KuCoinSpotFeed(WSFeedBase):
    name = "KuCoin"
    url = None  # KuCoin requires a tokenized WS URL from bullet-public
    token_url = "https://api.kucoin.com/api/v1/bullet-public"
    symbols_url = "https://api.kucoin.com/api/v2/symbols"

    async def _subscribe(self, ws):
        pass

    async def _handle_message(self, msg):
        pass
    
    async def stream(self):
        await self._reconnect_loop(self._connect)

    @classmethod
    def _get_ws_token(cls):
        """
        Get public websocket token + server list for KuCoin spot.
        """
        r = requests.post(cls.token_url, timeout=10)
        r.raise_for_status()

        payload = r.json()
        data = payload.get("data", {})
        token = data.get("token")
        servers = data.get("instanceServers", [])

        if not token or not servers:
            raise RuntimeError(f"{cls.name} token response missing token/server list: {payload}")

        server = servers[0]
        endpoint = server["endpoint"]
        ping_interval_ms = int(server.get("pingInterval", 18000))
        ping_timeout_ms = int(server.get("pingTimeout", 10000))

        return endpoint, token, ping_interval_ms, ping_timeout_ms

    async def _ping_loop(self, ws, ping_interval_ms):
        """
        KuCoin expects application-level ping messages using the cadence
        returned by the bullet-public endpoint.
        """
        interval = max(ping_interval_ms / 1000.0, 1.0)

        while True:
            await asyncio.sleep(interval)
            await ws.send(json.dumps({
                "id": str(int(asyncio.get_running_loop().time() * 1000)),
                "type": "ping",
            }))

    async def _connect(self):
        endpoint, token, ping_interval_ms, _ = self._get_ws_token()
        ws_url = f"{endpoint}?token={token}"

        symbols = [obj.pf_locator.upper() for obj in self.objs_list]
        if not symbols:
            return

        topic = f"/spotMarket/level1:{','.join(symbols)}"

        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None) as ws:
            ping_task = asyncio.create_task(self._ping_loop(ws, ping_interval_ms))

            try:
                await ws.send(json.dumps({
                    "id": "spot-level1-sub",
                    "type": "subscribe",
                    "topic": topic,
                    "response": True,
                }))

                async for raw in ws:
                    msg = self._decode_message(raw)

                    msg_type = msg.get("type")

                    if msg_type in {"welcome", "ack", "pong"}:
                        continue

                    if msg_type == "error":
                        self._handle_error(msg)
                        continue

                    if msg_type != "message":
                        continue

                    topic = msg.get("topic", "")
                    if not topic.startswith("/spotMarket/level1:"):
                        continue

                    symbol = topic.split(":")[-1]

                    data = msg.get("data", {})
                    bids = data.get("bids", [])
                    asks = data.get("asks", [])

                    if len(bids) < 2 or len(asks) < 2:
                        continue

                    obj = self.obj_map.get(symbol)
                    if not obj:
                        continue

                    obj.update_mkt_data(
                        bid_price=self._safe_float(bids[0]),
                        bid_size=self._safe_float(bids[1]),
                        ask_price=self._safe_float(asks[0]),
                        ask_size=self._safe_float(asks[1]),
                    )
            finally:
                ping_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await ping_task

    def _handle_error(self, msg):
        print(datetime.now(), f"{self.name} error: {msg}")

    @classmethod
    def complete_objects(cls, objs_list):
        locators_list = [obj.pf_locator.upper() for obj in objs_list]
        df, _ = cls.get_product_info(product_ids=locators_list)

        row_map = {
            str(row["symbol"]).upper(): row
            for _, row in df.iterrows()
        }

        for obj in objs_list:
            obj.fi_row = row_map.get(obj.pf_locator.upper())
            cls.complete_obj(obj)

    @classmethod
    def complete_obj(cls, obj):
        obj.pf_symbol = obj.fi_row.get("symbol")
        obj.pf_number = None
        obj.pf_prod_type = None

        obj.numerator_currency = obj.fi_row.get("quoteCurrency")
        obj.denominator_currency = obj.fi_row.get("baseCurrency")
        obj.quote_currency = obj.fi_row.get("quoteCurrency")
        obj.settlement_currency = None
        obj.fee_currency = obj.fi_row.get("feeCurrency")      # unique

        obj.complete_obj()

        '''
        # KuCoin spot symbol metadata
        obj.tick_size         = row.get("priceIncrement")
        obj.price_increment   = row.get("priceIncrement")
        obj.base_increment    = row.get("baseIncrement")
        obj.quote_increment   = row.get("quoteIncrement")
        obj.min_order_size    = row.get("baseMinSize")
        obj.max_order_size    = row.get("baseMaxSize")
        obj.min_funds         = row.get("minFunds")
        obj.enable_trading    = row.get("enableTrading")
        obj.is_margin_enabled = row.get("isMarginEnabled")
        obj.fee_currency      = row.get("feeCurrency")
        obj.market            = row.get("market")
        '''

    @classmethod
    def _get_all_symbols(cls, market=None):
        params = {}
        if market is not None:
            params["market"] = market

        r = requests.get(cls.symbols_url, params=params, timeout=10)
        r.raise_for_status()

        payload = r.json()
        rows = payload.get("data", [])
        return pd.DataFrame(rows), payload

    @classmethod
    def _get_symbol_detail(cls, symbol):
        url = f"{cls.symbols_url}/{symbol}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        payload = r.json()
        row = payload.get("data", {})
        return row, payload

    @classmethod
    def get_product_info(cls, product_ids=None, market=None):
        """
        Product metadata for KuCoin spot.

        If product_ids is None:
            use GET /api/v2/symbols
        If product_ids is provided:
            call GET /api/v2/symbols/{symbol} for each requested symbol
            so you get the same detailed per-symbol shape consistently.
        """
        if product_ids is None:
            return cls._get_all_symbols(market=market)

        rows = []
        for symbol in product_ids:
            row, _ = cls._get_symbol_detail(symbol)
            if row:
                rows.append(row)

        return pd.DataFrame(rows), {}

