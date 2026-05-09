#!/usr/bin/env python
# coding: utf-8

import gzip
import json
import pandas as pd
import requests

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class HuobiFeed(WSFeedBase):
    """
    Huobi / HTX spot public market data feed.

    Notes
    -----
    - Uses spot websocket BBO topic: market.{symbol}.bbo
    - Huobi websocket payloads are gzip-compressed.
    - Symbols are lowercase, e.g. btcusdt.
    """

    name = "Huobi"
    url = "wss://api.huobi.pro/ws"

    def _normalize_symbol(self, symbol):
        return str(symbol).lower() if symbol else symbol

    async def _subscribe(self, ws):
        for sym in self.obj_map:
            await ws.send(json.dumps({
                "sub": f"market.{sym}.bbo",
                "id": f"spot_bbo_{sym}",
            }))

    def _decode_message(self, raw):
        if isinstance(raw, (bytes, bytearray)):
            return json.loads(gzip.decompress(raw).decode("utf-8"))
        return json.loads(raw)

    async def _handle_message(self, msg):
        tick = msg.get("tick")
        if not tick:
            self._handle_error(msg)
            return

        channel = msg.get("ch", "")
        parts = channel.split(".")
        if len(parts) < 3:
            return

        symbol = parts[1].lower()
        obj = self.obj_map.get(symbol)
        if not obj:
            return

        obj.update_mkt_data(
            bid_price=self._safe_float(tick.get("bid")),
            bid_size=self._safe_float(tick.get("bidSize")),
            ask_price=self._safe_float(tick.get("ask")),
            ask_size=self._safe_float(tick.get("askSize")),
        )

    async def _handle_heartbeat(self, ws, msg):
        if "ping" in msg:
            await ws.send(json.dumps({"pong": msg["ping"]}))
            return True
        return False

    def _handle_error(self, msg):
        if isinstance(msg, dict) and msg.get("status") == "ok":
            return
        # Uncomment for debugging unexpected messages.
        # print(f"{self.name} status: {msg}")
        return

    @classmethod
    def complete_objects(cls, objs_list):
        locators = [obj.pf_locator.lower() for obj in objs_list]
        df, _ = cls.get_product_info(product_ids=locators)
    
        row_map = {
            str(row["symbol"]).lower(): row
            for _, row in df.iterrows()
        }
    
        for obj in objs_list:
            obj.fi_row = row_map.get(obj.pf_locator.lower())
            cls.complete_obj(obj)
        
    @classmethod
    def complete_obj(cls, obj):
        obj.pf_symbol = obj.fi_row["symbol"]
        obj.pf_number = None
        obj.pf_prod_type = None
        
        obj.numerator_currency = obj.fi_row["quote-currency"].upper()
        obj.denominator_currency = obj.fi_row["base-currency"].upper()
        obj.quote_currency = None
        obj.settlement_currency = None

    @classmethod
    def get_product_info(cls, product_ids=None):
        """
        Fetch Huobi spot symbol metadata.

        Parameters
        ----------
        product_ids : list[str] or None
            Lowercase symbols like ["btcusdt", "ethusdt"].
            If None, fetch all symbols.
        """
        r = requests.get("https://api.huobi.pro/v1/common/symbols", timeout=10)
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("data", [])

        if product_ids is not None:
            wanted = {sym.lower() for sym in product_ids}
            rows = [row for row in rows if row.get("symbol", "").lower() in wanted]

        return pd.DataFrame(rows), payload