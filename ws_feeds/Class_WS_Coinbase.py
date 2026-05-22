#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from datetime import datetime
import json
import pandas as pd
import requests

from ws_feeds.Class_WS_FeedBase import WSFeedBase


# In[ ]:


class CoinbaseSpotFeed(WSFeedBase):

    name = "Coinbase"
    url  = "wss://advanced-trade-ws.coinbase.com"

    
    async def _subscribe(self, ws):
        await ws.send(json.dumps({
            "type": "subscribe",
            "product_ids": list(self.obj_map.keys()),
            "channel": "ticker",
        }))

    async def _handle_message(self, msg):
        channel = msg.get("channel")

        if channel == "heartbeats":
            return

        if channel != "ticker":
            self._handle_error(msg)
            return

        for event in msg.get("events", []):
            for ticker in event.get("tickers", []):
                product_id = ticker.get("product_id", "").upper()
                obj = self.obj_map.get(product_id)
                if not obj:
                    continue

                obj.update_mkt_data(
                    bid_price=self._safe_float(ticker.get("best_bid")),
                    bid_size=self._safe_float(ticker.get("best_bid_quantity")),
                    ask_price=self._safe_float(ticker.get("best_ask")),
                    ask_size=self._safe_float(ticker.get("best_ask_quantity")),
                )

    def _handle_error(self, msg):
        if msg.get("type") == "error":
            print(datetime.now(), f"{self.name} error: {msg.get('message')}")

    @classmethod
    def complete_objects(cls, objs_list):
        locators_list = [obj.pf_locator for obj in objs_list]
        df, _ = cls.get_product_info(product_ids=locators_list)
    
        # build lookup: product_id -> row
        row_map = {
            row.product_id: row
            for row in df.itertuples(index=False)
        }
    
        for obj in objs_list:
            obj.fi_row = row_map.get(obj.pf_locator)
            cls.complete_obj(obj)
            
    @classmethod
    def complete_obj(cls, obj):
        obj.pf_symbol    = obj.fi_row.product_id
        obj.pf_number    = None
        obj.pf_prod_type = obj.fi_row.product_type

        obj.numerator_currency   = obj.fi_row.quote_currency_id     
        obj.denominator_currency = obj.fi_row.base_currency_id
        obj.quote_currency       = None
        obj.settlement_currency  = None

        obj.complete_obj()

        '''
        #obj.fi_row.base_increment & price_increent
        #obj.fi_row.quote_increment
        #obj.fi_row.quote_min_size & base_min_size
        
        
        if self.my_prod_type in ['future', 'option']:
            self.settlement_days_dict['expiry'] = 0

        if self.my_prod_type = 'option':
            self.strike = obj.fi_row.strike
            self.option_right = obj.fi_row.option_type
            self.underlying = 
        '''

    @classmethod
    def get_product_info( 
        cls,
        prod_type=None,
        expire_type=None,
        expire_status=None,
        product_ids=None,
        get_all_products=None,
        limit=None,
        cursor=None,
                    ):
        """
        Pull Coinbase products into a DataFrame.

        Parameters
        ----------
        prod_type : str or None
            Examples: "SPOT", "FUTURE"

        expire_type : str or None
            Examples: "EXPIRING", "PERPETUAL"
            Only applies when prod_type == "FUTURE".

        expire_status : str or None
            Examples: "STATUS_UNEXPIRED", "STATUS_EXPIRED", "STATUS_ALL"

        product_ids : list[str] or None
            Example: ["BTC-USD", "ETH-USD"]

        get_all_products : bool or None
            If True, include all products, including expired futures.

        limit : int or None
            Page size.

        cursor : str or None
            Pagination cursor returned by prior call.
        """
        BASE = "https://api.coinbase.com/api/v3/brokerage/market/products"

        params = {}

        if prod_type is not None:
            params["product_type"] = prod_type

        if expire_type is not None:
            params["contract_expiry_type"] = expire_type

        if expire_status is not None:
            params["expiring_contract_status"] = expire_status

        if product_ids is not None:
            params["product_ids"] = product_ids

        if get_all_products is not None:
            params["get_all_products"] = get_all_products

        if limit is not None:
            params["limit"] = limit

        if cursor is not None:
            params["cursor"] = cursor

        r = requests.get(BASE, params=params, timeout=10)
        r.raise_for_status()

        payload = r.json()
        products = payload.get("products", [])

        return pd.DataFrame(products), payload.get("pagination", {})



# In[ ]:


class CoinbaseDerivsFeed(WSFeedBase):
    """
    Coinbase Derivatives / FCM futures feed.

    Uses same Advanced Trade websocket format as Coinbase spot,
    but defaults REST completion to FUTURE products.
    """
    
    name = "Coinbase-Derivs"
    url = "wss://advanced-trade-ws.coinbase.com"

    async def _subscribe(self, ws):
        product_ids = list(self.obj_map.keys())
        if not product_ids:
            raise ValueError("No Coinbase derivatives product_ids found")

        # heartbeats help keep quiet subscriptions alive
        await ws.send(json.dumps({
            "type": "subscribe",
            "product_ids": product_ids,
            "channel": "heartbeats",
        }))

        await ws.send(json.dumps({
            "type": "subscribe",
            "product_ids": product_ids,
            "channel": "ticker",
        }))

    @classmethod
    def complete_objects(cls, objs_list):
        locators_list = [obj.pf_locator for obj in objs_list]

        df, _ = cls.get_product_info(
            prod_type="FUTURE",
            product_ids=locators_list,
        )

        row_map = {
            row.product_id.upper(): row
            for row in df.itertuples(index=False)
        }

        for obj in objs_list:
            obj.fi_row = row_map.get(obj.pf_locator.upper())

            if obj.fi_row is None:
                raise ValueError(f"No Coinbase derivatives product found for {obj.pf_locator}")

            cls.complete_obj(obj)

    @classmethod
    def complete_obj(cls, obj):
        row = obj.fi_row

        obj.pf_symbol    = row.product_id
        obj.pf_number    = None
        obj.pf_prod_type = row.product_type

        obj.numerator_currency   = row.base_currency_id
        obj.denominator_currency = row.quote_currency_id
        obj.quote_currency       = row.quote_currency_id
        obj.settlement_currency  = getattr(row, "settlement_currency_id", None)

        obj.expiration_date = getattr(row, "future_product_details", None)

    @classmethod
    def get_product_info(
        cls,
        prod_type="FUTURE",
        expire_type=None,
        expire_status="STATUS_UNEXPIRED",
        product_ids=None,
        get_all_products=None,
        limit=None,
        cursor=None,
    ):
        return CoinbaseSpotFeed.get_product_info(
            prod_type=prod_type,
            expire_type=expire_type,
            expire_status=expire_status,
            product_ids=product_ids,
            get_all_products=get_all_products,
            limit=limit,
            cursor=cursor,
        )

        