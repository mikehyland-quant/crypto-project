#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python
# coding: utf-8

from datetime import datetime
import json
import pandas as pd
import requests

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class PhemexFeed(WSFeedBase):
    name = "Phemex"
    url = "wss://ws.phemex.com"
    rest_url = "https://api.phemex.com/public/products"

    def _normalize_symbol(self, symbol):
        if not symbol:
            return symbol
        s = str(symbol)
        if s.startswith("s"):
            return "s" + s[1:].upper()
        return s.upper()

    async def _subscribe(self, ws):
        for i, symbol in enumerate(self.obj_map.keys(), start=1):
            payload = {
                "id": i,
                "method": "orderbook.subscribe",
                "params": [symbol],
            }
            await ws.send(json.dumps(payload))
        
    async def _handle_message(self, msg):
        symbol = self._normalize_symbol(msg.get("symbol"))
        if not symbol:
            self._handle_error(msg)
            return
    
        obj = self.obj_map.get(symbol)
        if not obj:
            return
    
        book = msg.get("book", {})
        bids = book.get("bids", [])
        asks = book.get("asks", [])
    
        kwargs = {}
        if bids:
            kwargs["bid_price"] = self._safe_float(bids[0][0]) / 1e8
            kwargs["bid_size"]  = self._safe_float(bids[0][1])
        if asks:
            kwargs["ask_price"] = self._safe_float(asks[0][0]) / 1e8
            kwargs["ask_size"]  = self._safe_float(asks[0][1])
    
        if kwargs:
            obj.update_mkt_data(**kwargs)
            
    def _handle_error(self, msg):
        if isinstance(msg, dict) and msg.get("error") is not None:
            print(datetime.now(), f"{self.name} error: {msg}")

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
        obj.pf_symbol = obj.fi_row.get("symbol")
        obj.pf_number = None
        obj.pf_prod_type = obj.fi_row.get("type")

        obj.numerator_currency = obj.fi_row.get("quoteCurrency")
        obj.denominator_currency = obj.fi_row.get("baseCurrency")
        obj.quote_currency = None
        obj.settlement_currency = obj.fi_row.get("settleCurrency")
        
    @classmethod
    def get_product_info(cls, product_ids=None):
        r = requests.get(cls.rest_url, timeout=10)
        r.raise_for_status()
    
        payload = r.json()
    
        if isinstance(payload, list):
            products = payload
    
        elif isinstance(payload, dict):
            data = payload.get("data", [])
    
            if isinstance(data, dict):
                products = data.get("products", []) or payload.get("products", [])
            elif isinstance(data, list):
                products = data
            else:
                products = payload.get("products", [])
    
        else:
            products = []
    
        rows = []
    
        for row in products:
            if not isinstance(row, dict):
                continue
    
            symbol = row.get("symbol") or row.get("symbolName")
            if not symbol:
                continue

            rows.append(row)
    
        df = pd.DataFrame(products)
            #rows)
    
        if product_ids is not None and not df.empty:
            wanted = {str(x).upper() for x in product_ids}
            df = df[df["symbol"].str.upper().isin(wanted)].reset_index(drop=True)
    
        return df, payload