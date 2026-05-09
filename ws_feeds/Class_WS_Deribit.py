#!/usr/bin/env python
# coding: utf-8

from datetime import datetime
import json
import requests
import pandas as pd

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class DeribitFeed(WSFeedBase):
    name = "Deribit"
    url = "wss://www.deribit.com/ws/api/v2"
    rest_url = "https://www.deribit.com/api/v2"

    async def _subscribe(self, ws):
        channels = [
            f"ticker.{obj.pf_locator}.100ms"
            for obj in self.objs_list
        ]

        sub_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "public/subscribe",
            "params": {"channels": channels},
        }

        await ws.send(json.dumps(sub_msg))

    async def _handle_message(self, msg):
        if msg.get("method") != "subscription":
            if "error" in msg:
                self._handle_error(msg)
            return

        params = msg.get("params", {})
        channel = params.get("channel", "")
        data = params.get("data", {})

        parts = channel.split(".")
        if len(parts) < 3:
            return

        symbol = ".".join(parts[1:-1]).upper()
        obj = self.obj_map.get(symbol)
        if not obj:
            return

        update_kwargs = {}

        best_bid = data.get("best_bid_price")
        best_ask = data.get("best_ask_price")
        best_bid_amount = data.get("best_bid_amount")
        best_ask_amount = data.get("best_ask_amount")

        if best_bid is not None:
            update_kwargs["bid_price"] = float(best_bid)
        if best_ask is not None:
            update_kwargs["ask_price"] = float(best_ask)
        if best_bid_amount is not None:
            update_kwargs["bid_size"] = float(best_bid_amount)
        if best_ask_amount is not None:
            update_kwargs["ask_size"] = float(best_ask_amount)

        if update_kwargs:
            obj.update_mkt_data(**update_kwargs)

    def _handle_error(self, msg):
        if "error" in msg:
            print(datetime.now(), f"{self.name} error: {msg['error']}")

    @classmethod
    def complete_objects(cls, objs_list):
        for obj in objs_list:
            df, _ = cls.get_product_info(instrument_name=obj.pf_locator)
            obj.fi_row = next(df.itertuples(index=False), None)
            cls.complete_obj(obj)

    @classmethod
    def complete_obj(cls, obj):
        obj.pf_symbol = obj.fi_row.instrument_name
        obj.pf_number = obj.fi_row.instrument_id
        obj.pf_prod_type = obj.fi_row.kind

        obj.numerator_currency = obj.fi_row.counter_currency
        obj.denominator_currency = obj.fi_row.base_currency
        obj.quote_currency = obj.fi_row.quote_currency
        obj.settlement_currency = (getattr(obj.fi_row, "settlement_currency", None))

        '''
        #obj.fi_row.tick_size
        #obj.fi_row.contract_size
        #obj.fi_row.min_trade_amount
        
        
        if self.my_prod_type in ['future', 'option']:
            self.settlement_days_dict['expiry'] = None #([{convert obj.fi_row.expiration_timestamp  
                                                    #or obj.fi_row.expiration_datetime }])

        if self.my_prod_type == 'option':
            self.strike = obj.fi_row.strike
            self.option_right = obj.fi_row.option_type
            self.underlying = None
        '''
        
    @classmethod
    def get_product_info(cls, instrument_name=None, currency="BTC", kind=None, expired=None):
        """
        Pull Deribit instruments into a DataFrame.

        Parameters
        ----------
        instrument_name : str or None
            For a single instrument, e.g. "BTC_USDC", "BTC-29MAY26",
            "BTC-13APR26-64000-C".

        currency : str
            For grouped queries, examples: "BTC", "ETH", "SOL", "USDC", "USDT", or "any".

        kind : str or None
            Examples: "future", "option", "spot", "future_combo", "option_combo".

        expired : bool
            False = active instruments
            True = recently expired instruments
        """
        if instrument_name is not None:
            endpoint = "/public/get_instrument"
            params = {
                "instrument_name": instrument_name,
            }
        else:
            endpoint = "/public/get_instruments"
            params = {
                "currency": currency,
                "expired": expired,
            }
            if kind is not None:
                params["kind"] = kind

        r = requests.get(cls.rest_url + endpoint, params=params, timeout=10)
        r.raise_for_status()

        payload = r.json()
        if "result" not in payload:
            raise ValueError(f"Unexpected response: {payload}")

        result = payload["result"]

        if isinstance(result, dict):
            df = pd.DataFrame([result])
        else:
            df = pd.DataFrame(result)

        return df, None


