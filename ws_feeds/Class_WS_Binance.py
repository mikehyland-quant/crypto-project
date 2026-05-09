#!/usr/bin/env python
# coding: utf-8

import json
from datetime import datetime
import pandas as pd
import requests
import websockets

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class BinanceSpotFeed(WSFeedBase):
    name = "Binance"
    rest_url = "https://api.binance.com/api/v3/exchangeInfo"

    @property
    def url(self):
        streams = "/".join(f"{o.pf_locator.lower()}@bookTicker" for o in self.objs_list)
        return f"wss://stream.binance.com:9443/stream?streams={streams}"

    async def _subscribe(self, ws):
        return

    async def _handle_message(self, msg):
        data = msg.get("data", {})
        symbol = data.get("s")

        obj = self.obj_map.get(symbol)
        if not obj:
            return

        obj.update_mkt_data(
            bid_price=self._safe_float(data.get("b")),
            bid_size=self._safe_float(data.get("B")),
            ask_price=self._safe_float(data.get("a")),
            ask_size=self._safe_float(data.get("A")),
        )

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
        
        obj.numerator_currency   = obj.fi_row.get("quoteAsset")
        obj.denominator_currency = obj.fi_row.get("baseAsset")
        obj.quote_currency       = None
        obj.settlement_currency  = None

        '''
        # Exchange-specific metadata
        obj.tick_size     = row.get("tickSize")
        obj.price_min     = row.get("minPrice")
        obj.price_max     = row.get("maxPrice")

        obj.qty_step      = row.get("stepSize")
        obj.min_order_qty = row.get("minQty")
        obj.max_order_qty = row.get("maxQty")

        obj.min_notional  = row.get("minNotional")

        obj.status        = row.get("status")
        obj.is_spot       = row.get("isSpotTradingAllowed")
        obj.is_margin     = row.get("isMarginTradingAllowed")
        '''

    @classmethod
    def get_product_info(cls, product_ids=None):
        """
        Pull Binance spot metadata.
    
        Returns:
            DataFrame of symbols with filters flattened
        """
        r = requests.get(cls.rest_url, timeout=10)
        r.raise_for_status()
    
        payload = r.json()
        rows = payload.get("symbols", [])
    
        df = pd.DataFrame(rows)
    
        if df.empty:
            return df, {}
    
        def extract_filter(filters_list, filter_type, key):
            for f in filters_list:
                if f.get("filterType") == filter_type:
                    return f.get(key)
            return None

        df["tickSize"] = df["filters"].apply(lambda x: extract_filter(x, "PRICE_FILTER", "tickSize"))
        df["minPrice"] = df["filters"].apply(lambda x: extract_filter(x, "PRICE_FILTER", "minPrice"))
        df["maxPrice"] = df["filters"].apply(lambda x: extract_filter(x, "PRICE_FILTER", "maxPrice"))
    
        df["stepSize"] = df["filters"].apply(lambda x: extract_filter(x, "LOT_SIZE", "stepSize"))
        df["minQty"]   = df["filters"].apply(lambda x: extract_filter(x, "LOT_SIZE", "minQty"))
        df["maxQty"]   = df["filters"].apply(lambda x: extract_filter(x, "LOT_SIZE", "maxQty"))
    
        df["minNotional"] = df["filters"].apply(lambda x: extract_filter(x, "MIN_NOTIONAL", "minNotional"))
    
        if product_ids is not None:
            wanted = {str(x).upper() for x in product_ids}
            df = df[df["symbol"].isin(wanted)].reset_index(drop=True)

        return df, payload
