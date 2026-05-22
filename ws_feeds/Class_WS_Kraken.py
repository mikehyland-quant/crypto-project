#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import asyncio
from datetime import datetime
import json
import pandas as pd
import websockets

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class KrakenSpotFeed(WSFeedBase):

    name = "Kraken"
    url  = "wss://ws.kraken.com/v2"

    async def _subscribe(self, ws):
        symbols = [obj.pf_locator for obj in self.objs_list]
        await ws.send(json.dumps({
            "method": "subscribe",
            "params": {
                "channel": "ticker",
                "symbol": symbols,
                "event_trigger": "bbo",
                "snapshot": True,
            }
        }))

    async def _handle_message(self, msg):
        if "method" in msg:
            if msg.get("success") is False:
                self._handle_error(msg)
            return
    
        if msg.get("channel") != "ticker":
            return
    
        data = msg.get("data", [])
        if not data:
            return
    
        for ticker in data:
            symbol = ticker.get("symbol")
            obj = self.obj_map.get(self._normalize_symbol(symbol))
            if not obj:
                continue
    
            obj.update_mkt_data(
                bid_price=self._safe_float(ticker.get("bid")),
                bid_size=self._safe_float(ticker.get("bid_qty")),
                ask_price=self._safe_float(ticker.get("ask")),
                ask_size=self._safe_float(ticker.get("ask_qty")),
            )

    def _handle_error(self, msg):
        err = msg.get("error") or msg
        print(datetime.now(), f"{self.name} error: {err}")

    @classmethod
    def complete_objects(cls, objs_list):
        locators_list = [obj.pf_locator.upper() for obj in objs_list]
        df_pairs, df_assets = cls.get_product_info(product_ids=locators_list)

        row_map = {
            str(row["symbol"]).upper(): row
            for _, row in df_pairs.iterrows()
        }

        asset_map = {
            str(row["id"]).upper(): row
            for _, row in df_assets.iterrows()
        } if not df_assets.empty and "id" in df_assets.columns else {}

        for obj in objs_list:
            obj.fi_row = row_map.get(obj.pf_locator.upper())
            obj.asset_map = asset_map
            cls.complete_obj(obj)

    @classmethod
    def complete_obj(cls, obj):
        obj.pf_symbol    = obj.fi_row.get("symbol")
        obj.pf_number    = None
        obj.pf_prod_type = None

        obj.numerator_currency   = obj.fi_row.get("quote")
        obj.denominator_currency = obj.fi_row.get("base")
        obj.quote_currency       = None
        obj.settlement_currency  = None

        obj.complete_obj()

        '''
        # Kraken instrument metadata
        obj.tick_size            = row.get("price_increment")
        obj.price_increment      = row.get("price_increment")
        obj.price_precision      = row.get("price_precision")
        obj.qty_increment        = row.get("qty_increment")
        obj.qty_min              = row.get("qty_min")
        obj.qty_precision        = row.get("qty_precision")
        obj.cost_min             = row.get("cost_min")
        obj.cost_precision       = row.get("cost_precision")
        obj.status               = row.get("status")
        obj.marginable           = row.get("marginable")
        obj.margin_initial       = row.get("margin_initial")
        obj.position_limit_long  = row.get("position_limit_long")
        obj.position_limit_short = row.get("position_limit_short")
        obj.has_index            = row.get("has_index")

        # Optional asset-level metadata
        base_asset = obj.asset_map.get(str(row.get("base", "")).upper(), {})
        quote_asset = obj.asset_map.get(str(row.get("quote", "")).upper(), {})

        obj.base_asset_precision       = base_asset.get("precision")
        obj.base_asset_display_prec    = base_asset.get("precision_display")
        obj.quote_asset_precision      = quote_asset.get("precision")
        obj.quote_asset_display_prec   = quote_asset.get("precision_display")
        '''
        
    @classmethod
    # usage:  df, _ = await module.KrakenSpotFeed._get_product_info_ws()
    async def _get_product_info_ws(cls, product_ids=None):
        """
        One-shot product info pull using Kraken WS v2 instrument channel.
        Subscribes, reads the first snapshot, returns, disconnects.
        """
        wanted = None
        if product_ids is not None:
            wanted = {str(x).upper() for x in product_ids}

        async with websockets.connect(cls.url) as ws:
            await ws.send(json.dumps({
                "method": "subscribe",
                "params": {
                    "channel": "instrument",
                    "snapshot": True,
                    "include_tokenized_assets": False,
                }
            }))

            while True:
                msg = json.loads(await ws.recv())

                if "method" in msg:
                    if msg.get("success") is False:
                        raise RuntimeError(msg.get("error", msg))
                    continue

                if msg.get("channel") != "instrument":
                    continue

                if msg.get("type") != "snapshot":
                    continue

                data = msg.get("data", {})
                pairs = data.get("pairs", [])
                assets = data.get("assets", [])

                df_pairs = pd.DataFrame(pairs)
                df_assets = pd.DataFrame(assets)

                if not df_pairs.empty and wanted is not None:
                    df_pairs = df_pairs[
                        df_pairs["symbol"].str.upper().isin(wanted)
                    ].reset_index(drop=True)

                return df_pairs, df_assets

    @classmethod
    def get_product_info(cls, product_ids=None):
        """
        Sync wrapper for the one-shot WS instrument snapshot.
        Works well with your existing asyncio.to_thread(...) pattern.
        """
        return asyncio.run(cls._get_product_info_ws(product_ids=product_ids))

