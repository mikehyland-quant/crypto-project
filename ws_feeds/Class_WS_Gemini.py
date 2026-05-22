#!/usr/bin/env python
# coding: utf-8

# In[ ]:

import asyncio
import json
import pandas as pd
import requests
import websockets

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class GeminiFeed(WSFeedBase):
    """
    Gemini requires one connection per symbol, so this adapter overrides
    stream() and runs one per-symbol WebSocket task concurrently.
    """

    name = "Gemini"
    url = None  # Gemini uses one WS URL per symbol

    async def _subscribe(self, ws):
        pass

    async def _handle_message(self, msg):
        pass
        
    @staticmethod
    def _normalize_symbol(symbol):
        return symbol.lower() if symbol else symbol

    @classmethod
    def _symbol_url(cls, symbol):
        symbol = cls._normalize_symbol(symbol)
        return f"wss://api.gemini.com/v1/marketdata/{symbol}?top_of_book=true"

    async def stream(self):
        await asyncio.gather(*(self._stream_symbol(obj) for obj in self.objs_list))

    async def _stream_symbol(self, obj):
        await self._reconnect_loop(lambda: self._connect_symbol(obj))

    async def _connect_symbol(self, obj):
        url = self._symbol_url(obj.pf_locator)

        async with websockets.connect(url) as ws:
            async for raw in ws:
                msg = self._decode_message(raw)

                if await self._handle_heartbeat(ws, msg):
                    continue

                events = msg.get("events", [])
                if not events:
                    self._handle_error(msg)
                    continue

                for event in events:
                    if event.get("type") != "change":
                        continue

                    side = event.get("side")
                    price = self._safe_float(event.get("price"))
                    remaining = self._safe_float(event.get("remaining"))

                    if side == "bid":
                        obj.update_mkt_data(bid_price=price, bid_size=remaining)
                    elif side == "ask":
                        obj.update_mkt_data(ask_price=price, ask_size=remaining)

    def _handle_error(self, msg):
        return

    @classmethod
    def complete_objects(cls, objs_list):
        locators = [cls._normalize_symbol(obj.pf_locator) for obj in objs_list]
        df, _ = cls.get_product_info(product_ids=locators)

        row_map = {
            cls._normalize_symbol(row.symbol): row
            for row in df.itertuples(index=False)
        }

        for obj in objs_list:
            obj.fi_row = row_map.get(cls._normalize_symbol(obj.pf_locator))
            cls.complete_obj(obj)
    
    @classmethod
    def complete_obj(cls, obj):
        obj.pf_symbol = obj.fi_row.symbol
        obj.pf_number = None
        obj.pf_prod_type = obj.fi_row.product_type

        obj.numerator_currency = obj.fi_row.quote_currency
        obj.denominator_currency = obj.fi_row.base_currency
        obj.quote_currency = None
        obj.settlement_currency = None

        obj.complete_obj()

    @classmethod
    def get_product_info(cls, product_ids=None):
        """
        Fetch Gemini product metadata.

        Parameters
        ----------
        product_ids : list[str] or None
            Symbols such as ["btcusd", "ethusd"].
            If None, all available Gemini symbols are fetched first.

        Returns
        -------
        tuple[pd.DataFrame, None]
            DataFrame of symbol details and placeholder None for consistency
            with the rest of your framework.
        """

        base = "https://api.gemini.com"

        if product_ids is None:
            r = requests.get(f"{base}/v1/symbols", timeout=10)
            r.raise_for_status()
            product_ids = r.json()

        rows = []
        for symbol in product_ids:
            symbol = cls._normalize_symbol(symbol)
            r = requests.get(f"{base}/v1/symbols/details/{symbol}", timeout=10)
            r.raise_for_status()
            row = r.json()
            row["symbol"] = symbol
            rows.append(row)

        return pd.DataFrame(rows), None


