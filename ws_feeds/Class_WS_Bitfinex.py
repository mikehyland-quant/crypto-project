#!/usr/bin/env python
# coding: utf-8

from datetime import datetime
import json
import pandas as pd
import requests

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class BitfinexFeed(WSFeedBase):
    name = "Bitfinex"
    url = "wss://api-pub.bitfinex.com/ws/2"

    def _normalize_symbol(self, symbol):
        return str(symbol) if symbol else symbol
        
    def _make_obj_map(self, objs_list):
        return {self._normalize_symbol(o.pf_locator): o for o in objs_list}

    async def _subscribe(self, ws):
        self.best_bid_map = {key: None for key in self.obj_map}
        self.best_ask_map = {key: None for key in self.obj_map}
        self.chan_map = {}

        for key in self.obj_map:
            await ws.send(json.dumps({
                "event": "subscribe",
                "channel": "book",
                "symbol": key,
                "prec": "P0",
                "freq": "F0",
                "len": 25,
            }))

    async def _handle_message(self, msg):
        if isinstance(msg, dict):
            event = msg.get("event")
            if event == "subscribed" and msg.get("channel") == "book":
                chan_id = msg.get("chanId")
                symbol = self._normalize_symbol(msg.get("symbol"))
                if chan_id is not None and symbol is not None:
                    self.chan_map[chan_id] = symbol
                return

            if event in {"info", "conf"}:
                return

            self._handle_error(msg)
            return

        if not isinstance(msg, list) or len(msg) < 2:
            return

        chan_id = msg[0]
        data = msg[1]

        if data == "hb":
            return

        symbol = self.chan_map.get(chan_id)
        if not symbol:
            return

        obj = self.obj_map.get(symbol)
        if not obj or data is None:
            return

        # snapshot
        if isinstance(data, list) and data and isinstance(data[0], list):
            bids = [x for x in data if len(x) >= 3 and x[2] > 0]
            asks = [x for x in data if len(x) >= 3 and x[2] < 0]

            bid_price = bid_size = ask_price = ask_size = None

            if bids:
                best_bid = max(bids, key=lambda x: x[0])
                bid_price = self._safe_float(best_bid[0])
                bid_size = self._safe_float(best_bid[2])
                self.best_bid_map[symbol] = bid_price

            if asks:
                best_ask = min(asks, key=lambda x: x[0])
                ask_price = self._safe_float(best_ask[0])
                ask_size = self._safe_float(abs(best_ask[2]))
                self.best_ask_map[symbol] = ask_price

            obj.update_mkt_data(
                bid_price=bid_price,
                bid_size=bid_size,
                ask_price=ask_price,
                ask_size=ask_size,
            )
            return

        # incremental update: [PRICE, COUNT, AMOUNT]
        if not isinstance(data, list) or len(data) < 3:
            return

        price = self._safe_float(data[0])
        count = int(data[1])
        amount = self._safe_float(data[2])

        best_bid = self.best_bid_map[symbol]
        best_ask = self.best_ask_map[symbol]

        if count == 0:
            if amount == 1 and price == best_bid:
                self.best_bid_map[symbol] = None
            elif amount == -1 and price == best_ask:
                self.best_ask_map[symbol] = None
            return

        if amount > 0:
            if best_bid is None or price >= best_bid:
                self.best_bid_map[symbol] = price
                obj.update_mkt_data(
                    bid_price=price,
                    bid_size=amount,
                )
        else:
            if best_ask is None or price <= best_ask:
                self.best_ask_map[symbol] = price
                obj.update_mkt_data(
                    ask_price=price,
                    ask_size=abs(amount),
                )

    def _handle_error(self, msg):
        event = msg.get("event")
        if event == "error":
            print(datetime.now(), f"{self.name} error: {msg.get('msg')}")
        elif event not in {"info", "conf"}:
            print(datetime.now(), f"{self.name} status: {msg}")

    @classmethod
    def complete_objects(cls, objs_list):
        locators_list = [obj.pf_locator for obj in objs_list]
        df, _ = cls.get_product_info(product_ids=locators_list)

        row_map = {
            row.pf_locator : row
            for row in df.itertuples(index=False)
                }

        for obj in objs_list:
            obj.fi_row = row_map.get(obj.pf_locator)
            cls.complete_obj(obj)

    @classmethod
    def complete_obj(cls, obj):
        obj.pf_symbol = obj.fi_row.symbol
        obj.pf_number = None
        obj.pf_prod_type = None
        
        obj.numerator_currency   = obj.my_row.top_currency 
        obj.denominator_currency = obj.my_row.base_currency
        obj.quote_currency       = None
        obj.settlement_currency  = None

    @classmethod
    def get_product_info(cls, product_ids=None, pair_type="exchange"):
        url = f"https://api-pub.bitfinex.com/v2/conf/pub:info:pair"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        payload = r.json()

        rows = payload[0]

        BITFINEX_PAIR_INFO_COLS = [
            "unknown_0",
            "unknown_1",
            "unknown_2",
            "min_order_size",
            "max_order_size",
            "unknown_5",
            "unknown_6",
            "unknown_7",
            "initial_margin",
            "maintenance_margin",
            "unknown_10",
            "unknown_11",
        ]
        
        df = pd.DataFrame(
                            [[symbol, *info] for symbol, info in rows],
                            columns=["symbol", *BITFINEX_PAIR_INFO_COLS]
                        )

        df['pf_locator'] = 't' + df['symbol']

        if product_ids is not None:
            wanted = {x for x in product_ids}
            df = df[df["pf_locator"].isin(wanted)].reset_index(drop=True)

        return df, None

        