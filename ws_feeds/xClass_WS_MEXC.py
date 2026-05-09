'''
This doesn't work yet
It requires more complicated download sofware
'''

#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python
# coding: utf-8

import json
import pandas as pd
#import PushDataV3ApiWrapper_pb2
import requests

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class MEXCFeed(WSFeedBase):
    name = "MEXC"
    url = "wss://wbs-api.mexc.com/ws"
    rest_url = "https://api.mexc.com/api/v3/exchangeInfo"

    def _normalize_symbol(self, symbol):
        return str(symbol).upper() if symbol else symbol

    async def _subscribe(self, ws):
        for sym in self.obj_map:
            payload = {
                "method": "SUBSCRIPTION",
                "params": [f"spot@public.aggre.bookTicker.v3.api.pb@100ms@{sym}"],
            }
            print("MEXC subscribe:", payload)
            await ws.send(json.dumps(payload))

    def _decode_message(self, raw):
        if isinstance(raw, (bytes, bytearray)):
            msg = PushDataV3ApiWrapper_pb2.PushDataV3ApiWrapper()
            msg.ParseFromString(raw)
    
            # convert to plain dict-like structure your handler can use
            out = {
                "channel": msg.channel,
                "symbol": msg.symbol,
            }
    
            if msg.HasField("publicbookticker"):
                out["publicbookticker"] = {
                    "bidprice": msg.publicbookticker.bidprice,
                    "bidquantity": msg.publicbookticker.bidquantity,
                    "askprice": msg.publicbookticker.askprice,
                    "askquantity": msg.publicbookticker.askquantity,
                }
    
            return out
        return json.loads(raw)
    
    async def _handle_message(self, msg):
        channel = msg.get("channel", "")
        if "bookTicker" not in channel:
            self._handle_error(msg)
            return
    
        symbol = self._normalize_symbol(msg.get("symbol"))
        book = msg.get("publicbookticker", {})
        if not symbol or not book:
            return
    
        obj = self.obj_map.get(symbol)
        if not obj:
            return
    
        obj.update_mkt_data(
            bid_price=self._safe_float(book.get("bidprice")),
            bid_size=self._safe_float(book.get("bidquantity")),
            ask_price=self._safe_float(book.get("askprice")),
            ask_size=self._safe_float(book.get("askquantity")),
        )
        
    def _handle_error(self, msg):
        code = msg.get("code")
        if code not in (None, 0):
            print(f"{self.name} error: {msg}")

    @classmethod
    def complete_objects(cls, objs_list):
        locators = [str(obj.pf_locator).upper() for obj in objs_list]
        df, _ = cls.get_product_info(product_ids=locators)

        row_map = {
            str(row["symbol"]).upper(): row
            for _, row in df.iterrows()
        }

        for obj in objs_list:
            obj.fi_row = row_map.get(str(obj.pf_locator).upper())
            cls.complete_obj(obj)

    @classmethod
    def complete_obj(cls, obj):
        if obj.fi_row is None:
            return

        row = obj.fi_row

        obj.numerator_currency = row.get("quoteAsset")
        obj.denominator_currency = row.get("baseAsset")
        obj.quote_currency = None
        obj.settlement_currency = None

        obj.pf_symbol = row.get("symbol")
        obj.pf_number = None
        obj.pf_prod_type = None

    @classmethod
    def get_product_info(cls, product_ids=None):
        r = requests.get(cls.rest_url, timeout=10)
        r.raise_for_status()

        payload = r.json()
        rows = payload.get("symbols", [])
        df = pd.DataFrame(rows)

        if product_ids is not None and not df.empty:
            wanted = {str(x).upper() for x in product_ids}
            df = df[df["symbol"].str.upper().isin(wanted)].reset_index(drop=True)

        return df, payload

