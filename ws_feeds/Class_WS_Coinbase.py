#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from datetime import datetime
import json
import pandas as pd
import requests

from ws_feeds.Class_WS_FeedBase import WSFeedBase


# In[ ]:


class CoinbaseFeed(WSFeedBase):

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

        '''

# In[ ]:


class CoinbaseFeedFCM(WSFeedBase):
    name = "Coinbase Derivatives"
    url = "wss://advanced-trade-ws.coinbase.com"

    async def stream(self):
        await self._reconnect_loop(self._connect)

    async def _connect(self):
        async with websockets.connect(
            self.url,
            ping_interval=20,
            ping_timeout=20,
            max_size=None,
        ) as ws:
            self.ws = ws
            await self._subscribe_all()

            async for raw in ws:
                msg = json.loads(raw)
                self._handle_message(msg)

    async def _subscribe_all(self):
        product_ids = list(self.obj_map.keys())
        if not product_ids:
            raise ValueError("No Coinbase derivatives product_ids found")

        await self._send_subscribe("heartbeats")
        await self._send_subscribe("level2", product_ids)
        await self._send_subscribe("ticker", product_ids)
        await self._send_subscribe("market_trades", product_ids)

    def _update_obj_bid_ask(self, product_id, bid_px=None, bid_sz=None, ask_px=None, ask_sz=None, ts=None):
        ts = ts or self._ts()
        obj = self.obj_map.get(product_id.upper())
        if not obj:
            return
        obj.update_mkt_data(
            **{k: v for k, v in {
                "bid_price": bid_px,
                "bid_size": bid_sz,
                "ask_price": ask_px,
                "ask_size": ask_sz,
                "timestamp": ts,
            }.items() if v is not None}
        )

    def complete_obj(self, obj):
         pass

    def get_product_info(
                        self,
                        prod_type=None,
                        expire_type=None,
                        expire_status=None,
                        product_ids=None,
                        get_all_products=None,
                        limit=None,
                        cursor=None,
                        ):
        CoinbaseFeedFCM.get_product_info(
                                        self,
                                        prod_type=None,
                                        expire_type=None,
                                        expire_status=None,
                                        product_ids=None,
                                        get_all_products=None,
                                        limit=None,
                                        cursor=None,
                                        )

        '''
