#!/usr/bin/env python
# coding: utf-8

import json
import pandas as pd
import requests

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class OKXFeed(WSFeedBase):
    """
    OKX public market data feed.

    Notes
    -----
    - Uses public websocket endpoint: wss://ws.okx.com:8443/ws/v5/public
    - Uses books5 channel for top-of-book updates.
    - Symbols are typically upper-case instIds like BTC-USDT or BTC-USD-SWAP.
    - Instrument metadata comes from GET /api/v5/public/instruments.
    """

    name = "OKX"
    url = "wss://ws.okx.com:8443/ws/v5/public"

    async def _subscribe(self, ws):
        sub_args = []
        for obj in self.objs_list:
            arg = {
                "channel": "books5",
                "instId": obj.pf_locator.upper(),
#fix olatform_type on next line
                "instType": getattr(obj, "platform_type", None),
            }
            if arg["instType"] is not None:
                arg["instType"] = str(arg["instType"]).upper()
            sub_args.append({k: v for k, v in arg.items() if v is not None})

        await ws.send(json.dumps({
            "op": "subscribe",
            "args": sub_args,
        }))

    async def _handle_message(self, msg):
        if await self._handle_heartbeat(None, msg):
            return

        if isinstance(msg, dict) and msg.get("event") in {"subscribe", "unsubscribe"}:
            return

        data_list = msg.get("data")
        if not data_list:
            self._handle_error(msg)
            return

        for book in data_list:
            symbol = book.get("instId", "").upper()
            obj = self.obj_map.get(symbol)
            if not obj:
                continue

            bids = book.get("bids", [])
            asks = book.get("asks", [])

            kwargs = {}
            if bids:
                kwargs["bid_price"] = self._safe_float(bids[0][0])
                kwargs["bid_size"] = self._safe_float(bids[0][1])
            if asks:
                kwargs["ask_price"] = self._safe_float(asks[0][0])
                kwargs["ask_size"] = self._safe_float(asks[0][1])

            if kwargs:
                obj.update_mkt_data(**kwargs)

    def _handle_error(self, msg):
        if isinstance(msg, dict) and msg.get("event") in {"subscribe", "unsubscribe"}:
            return
        # Uncomment for debugging unexpected messages.
        # print(f"{self.name} status: {msg}")
        return

    @classmethod
    def complete_objects(cls, objs_list):
        locators = [obj.pf_locator.upper() for obj in objs_list]
        df, _ = cls.get_product_info(product_ids=locators)

        row_map = {
            getattr(row, "instId", "").upper(): row
            for row in df.itertuples(index=False)
        }

        for obj in objs_list:
            obj.fi_row = row_map.get(obj.pf_locator.upper())
            cls.complete_obj(obj)

    @classmethod
    def complete_obj(cls, obj):
        obj.pf_symbol = getattr(obj.fi_row, "instId", None)
        obj.pf_number = None
        obj.pf_prod_type = getattr(obj.fi_row, "instType", None)
        
        obj.numerator_currency = getattr(obj.fi_row, "quoteCcy", None)
        obj.denominator_currency = getattr(obj.fi_row, "baseCcy", None)
        obj.quote_currency = None
        obj.settlement_currency = getattr(obj.fi_row, "settleCcy", None)

        obj.complete_obj()

        '''
        obj.underlying_symbol = getattr(row, "uly", None)
        obj.instrument_family = getattr(row, "instFamily", None)
        obj.contract_type = getattr(row, "ctType", None)
        obj.contract_value = cls._safe_float(getattr(row, "ctVal", None))
        obj.contract_value_currency = getattr(row, "ctValCcy", None)
        obj.strike = cls._safe_float(getattr(row, "stk", None))
        obj.option_type = getattr(row, "optType", None)
        obj.lot_size = cls._safe_float(getattr(row, "lotSz", None))
        obj.min_size = cls._safe_float(getattr(row, "minSz", None))
        obj.tick_size = cls._safe_float(getattr(row, "tickSz", None))
        obj.state = getattr(row, "state", None)
        obj.list_time = getattr(row, "listTime", None)
        obj.expiry_time = getattr(row, "expTime", None)
        '''


    @classmethod
    def get_product_info(cls, product_ids=None, inst_type=None):
        """
        Fetch OKX instrument metadata.

        Parameters
        ----------
        product_ids : list[str] or None
            Instrument IDs like ["BTC-USDT", "BTC-USD-SWAP"].
        inst_type : str or None
            Optional OKX instType such as SPOT, SWAP, FUTURES, OPTION.
            If omitted, the method queries common instTypes and filters locally.
        """
        base = "https://www.okx.com/api/v5/public/instruments"
        inst_types = [inst_type.upper()] if inst_type else ["SPOT", "SWAP", "FUTURES"]  #, "OPTIONS"]

        wanted = {pid.upper() for pid in product_ids} if product_ids is not None else None
        rows = []

        for itype in inst_types:
            r = requests.get(base, params={"instType": itype}, timeout=10)
            r.raise_for_status()
            payload = r.json()
            data = payload.get("data", [])

            if wanted is not None:
                data = [row for row in data if row.get("instId", "").upper() in wanted]

            rows.extend(data)

        dedup = {}
        for row in rows:
            dedup[row.get("instId", "").upper()] = row

        return pd.DataFrame(dedup.values()), None
