#!/usr/bin/env python
# coding: utf-8

from datetime import datetime
import json
import pandas as pd
import requests

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class BybitFeed(WSFeedBase):
    name = "Bybit"
    url = "wss://stream.bybit.com/v5/public/spot"

    async def _subscribe(self, ws):
        topics = [f"orderbook.1.{symbol}" for symbol in self.obj_map]
        await ws.send(json.dumps({
            "op": "subscribe",
            "args": topics,
        }))

    async def _handle_message(self, msg):
        topic = msg.get("topic", "")

        if not topic.startswith("orderbook.1."):
            if msg.get("op") == "subscribe" or msg.get("type") == "snapshot":
                return
            self._handle_error(msg)
            return

        data = msg.get("data", {})
        symbol = topic.split(".")[-1]
        obj = self.obj_map.get(symbol)
        if not obj:
            return

        bids = data.get("b", [])
        asks = data.get("a", [])

        bid_price = bid_size = ask_price = ask_size = None

        if bids:
            bid_price = self._safe_float(bids[0][0])
            bid_size = self._safe_float(bids[0][1])

        if asks:
            ask_price = self._safe_float(asks[0][0])
            ask_size = self._safe_float(asks[0][1])

        obj.update_mkt_data(
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
        )

    def _handle_error(self, msg):
        if msg.get("success") is False:
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
        obj.pf_symbol = obj.fi_row["symbol"]
        obj.pf_number = None
        obj.pf_prod_type = obj.fi_row["category"]

        obj.numerator_currency = getattr(obj.fi_row, "quoteCoin", None)
        obj.denominator_currency = getattr(obj.fi_row, "baseCoin", None)
        obj.quote_currency = None
        obj.settlement_currency = getattr(obj.fi_row, "settleCoin", None)

        obj.complete_obj()

    '''
    # raw exchange metadata you probably care about
            obj.tick_size        = row.get("tickSize")
            obj.min_order_qty    = row.get("minOrderQty")
            obj.max_order_qty    = row.get("maxOrderQty")
            obj.qty_step         = row.get("qtyStep")
            obj.min_order_amt    = row.get("minOrderAmt")
            obj.max_limit_qty    = row.get("maxLimitOrderQty")
            obj.max_market_qty   = row.get("maxMarketOrderQty")
            obj.min_notional     = row.get("minNotionalValue")
            obj.launch_time      = row.get("launchTime")
            obj.delivery_time    = row.get("deliveryTime")
            obj.status           = row.get("status")
    '''

    @classmethod
    def get_product_info(
        cls,
        category="spot",
        product_ids=None,
        symbol=None,
        status=None,
        base_coin=None,
        limit=None,
        cursor=None,
    ):
        """
        Pull Bybit instruments into a DataFrame.

        Parameters
        ----------
        category : str
            One of: "spot", "linear", "inverse", "option"

        product_ids : list[str] or None
            Example: ["BTCUSDT", "ETHUSDT"]

        symbol : str or None
            Single symbol filter.

        status : str or None
            Examples: "Trading", "PreLaunch", "Settling", "Delivering", "Closed"

        base_coin : str or None
            For linear / inverse / option.

        limit : int or None
            Spot ignores pagination. Others may paginate.

        cursor : str or None
            Pagination cursor.
        """
        base_url = "https://api.bybit.com/v5/market/instruments-info"

        params = {
            "category" : category
                }

        if symbol is not None:
            params["symbol"] = symbol

        if status is not None:
            params["status"] = status

        if base_coin is not None:
            params["baseCoin"] = base_coin

        if limit is not None and category != "spot":
            params["limit"] = limit

        if cursor is not None and category != "spot":
            params["cursor"] = cursor

        r = requests.get(base_url, params=params, timeout=10)
        r.raise_for_status()

        payload = r.json()
        result = payload.get("result", {})
        rows = result.get("list", [])

        df = pd.DataFrame(rows)

        if not df.empty:
            price_cols = pd.json_normalize(df["priceFilter"]).add_prefix("priceFilter.")
            lot_cols = pd.json_normalize(df["lotSizeFilter"]).add_prefix("lotSizeFilter.")

            df = df.drop(columns=[c for c in ["priceFilter", "lotSizeFilter", "riskParameters"] if c in df.columns])
            df = pd.concat([df.reset_index(drop=True), price_cols, lot_cols], axis=1)

            df["category"] = category

            if product_ids is not None:
                wanted = {str(x).upper() for x in product_ids}
                df = df[df["symbol"].str.upper().isin(wanted)].reset_index(drop=True)

        return df, result.get("nextPageCursor", "")
        