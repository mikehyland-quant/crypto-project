#!/usr/bin/env python
# coding: utf-8

# In[1]:


#!/usr/bin/env python
# coding: utf-8

from datetime import datetime
import json
import time
import pandas as pd
import requests

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class GateFeed(WSFeedBase):
    name = "Gate"
    url = "wss://api.gateio.ws/ws/v4/"
    rest_url = "https://api.gateio.ws/api/v4/spot/currency_pairs"

    def _normalize_symbol(self, symbol):
        return str(symbol).upper() if symbol else symbol

    async def _subscribe(self, ws):
        now = int(time.time())
        for sym in self.obj_map:
            payload = {
                "time": now,
                "channel": "spot.order_book",
                "event": "subscribe",
                "payload": [sym, "5", "100ms"],
            }
            await ws.send(json.dumps(payload))
        
    async def _handle_message(self, msg):
        channel = msg.get("channel")
        event = msg.get("event")

        if channel == "spot.ping":
            return

        if channel != "spot.order_book":
            self._handle_error(msg)
            return

        if event not in {"update", "all"}:
            return

        result = msg.get("result", {})
        if not result:
            return

        symbol = self._normalize_symbol(result.get("s") or result.get("currency_pair"))
        obj = self.obj_map.get(symbol)
        if not obj:
            return

        bids = result.get("b", []) or result.get("bids", [])
        asks = result.get("a", []) or result.get("asks", [])

        kwargs = {}
        if bids:
            best_bid = bids[0]
            kwargs["bid_price"] = self._safe_float(best_bid[0])
            kwargs["bid_size"] = self._safe_float(best_bid[1])

        if asks:
            best_ask = asks[0]
            kwargs["ask_price"] = self._safe_float(best_ask[0])
            kwargs["ask_size"] = self._safe_float(best_ask[1])

        if kwargs:
            obj.update_mkt_data(**kwargs)

    def _handle_error(self, msg):
        if isinstance(msg, dict) and msg.get("event") in {"subscribe", "unsubscribe"}:
            return
        if isinstance(msg, dict) and msg.get("error") is not None:
            print(datetime.now(), f"{self.name} error: {msg}")

    @classmethod
    def complete_objects(cls, objs_list):
        locators = [str(obj.pf_locator).upper() for obj in objs_list]
        df, _ = cls.get_product_info(product_ids=locators)

        row_map = {
            str(row["id"]).upper(): row
            for _, row in df.iterrows()
        }

        for obj in objs_list:
            obj.fi_row = row_map.get(str(obj.pf_locator).upper())
            cls.complete_obj(obj)

    @classmethod
    def complete_obj(cls, obj):
        obj.pf_symbol = obj.fi_row.get("id")
        obj.pf_number = None
        obj.pf_prod_type = None

        obj.numerator_currency = obj.fi_row.get("quote")
        obj.denominator_currency = obj.fi_row.get("base")
        obj.quote_currency = None
        obj.settlement_currency = None

    @classmethod
    def get_product_info(cls, product_ids=None):
        r = requests.get(cls.rest_url, timeout=10)
        r.raise_for_status()

        rows = r.json()
        df = pd.DataFrame(rows)

        if product_ids is not None and not df.empty:
            wanted = {str(x).upper() for x in product_ids}
            df = df[df["id"].str.upper().isin(wanted)].reset_index(drop=True)

        return df, None

