#!/usr/bin/env python
# coding: utf-8

import os
import json
from datetime import datetime

from ws_feeds.Class_WS_FeedBase import WSFeedBase


class NinjaDataFeed(WSFeedBase):

    name = "NinjaTrader"

    # Optional placeholder for later REST metadata lookup.
    rest_url = os.getenv("NINJATRADER_REST_URL")

    @property
    def url(self):
        """
        NinjaTrader WebSocket URL.

        Set this outside the code, for example in Windows environment variables:

            NINJATRADER_WS_URL=wss://...

        Exact URL depends on which NinjaTrader / Tradovate API endpoint you use.
        """

        ws_url = os.getenv("NINJATRADER_WS_URL")

        if not ws_url:
            raise ValueError("Missing NINJATRADER_WS_URL environment variable")

        return ws_url

    async def _subscribe(self, ws):

        token = os.getenv("NINJATRADER_API_TOKEN")

        if not token:
            raise ValueError("Missing NINJATRADER_API_TOKEN environment variable")

        symbols = list(self.obj_map.keys())

        await ws.send(json.dumps({
            "type": "subscribe",
            "channel": "marketData",
            "symbols": symbols,
            "token": token,
        }))

    async def _handle_message(self, msg):

        if self._is_heartbeat(msg):
            return

        if self._is_error(msg):
            self._handle_error(msg)
            return

        for data in self._extract_data(msg):
            if not isinstance(data, dict):
                continue

            symbol = self._get_symbol(data)

            if not symbol:
                continue

            obj = self.obj_map.get(self._normalize_symbol(symbol))

            if not obj:
                continue

            obj.update_mkt_data(
                bid_price=self._safe_float(
                    data.get("bid")
                    or data.get("bestBid")
                    or data.get("bidPrice")
                    or data.get("best_bid")
                ),
                bid_size=self._safe_float(
                    data.get("bidSize")
                    or data.get("bestBidSize")
                    or data.get("bid_size")
                    or data.get("best_bid_size")
                ),
                ask_price=self._safe_float(
                    data.get("ask")
                    or data.get("bestAsk")
                    or data.get("askPrice")
                    or data.get("best_ask")
                ),
                ask_size=self._safe_float(
                    data.get("askSize")
                    or data.get("bestAskSize")
                    or data.get("ask_size")
                    or data.get("best_ask_size")
                ),
            )

    def _extract_data(self, msg):
        """
        Normalize possible message containers into a list of quote dictionaries.
        """

        if not isinstance(msg, dict):
            return []

        data = msg.get("data")

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return [data]

        quotes = msg.get("quotes")

        if isinstance(quotes, list):
            return quotes

        if isinstance(quotes, dict):
            return [quotes]

        return [msg]

    def _get_symbol(self, data):
        """
        Extract the symbol/instrument identifier from one quote message.
        """

        return (
            data.get("symbol")
            or data.get("instrument")
            or data.get("instrumentName")
            or data.get("contract")
            or data.get("name")
        )

    def _is_heartbeat(self, msg):
        """
        Ignore heartbeat / ping / pong messages.
        """

        if not isinstance(msg, dict):
            return False

        msg_type = str(msg.get("type", "")).lower()
        channel = str(msg.get("channel", "")).lower()
        event = str(msg.get("event", "")).lower()

        return (
            msg_type in {"heartbeat", "ping", "pong"}
            or channel == "heartbeat"
            or event in {"heartbeat", "ping", "pong"}
        )

    def _is_error(self, msg):
        """
        Detect simple error/reject messages.
        """

        if not isinstance(msg, dict):
            return False

        msg_type = str(msg.get("type", "")).lower()
        event = str(msg.get("event", "")).lower()

        return msg_type in {"error", "reject", "rejected"} or event in {
            "error",
            "reject",
            "rejected",
        }

    def _handle_error(self, msg):
        print(datetime.now(), f"{self.name} error: {msg}")

    @classmethod
    def complete_objects(cls, objs_list):
        """
        Complete all NinjaTrader objects.

        This mirrors BinanceSpotFeed.complete_objects(), but does not yet pull
        REST instrument metadata.
        """

        for obj in objs_list:
            cls.complete_obj(obj)

    @classmethod
    def complete_obj(cls, obj):
        """
        Populate normalized object fields.

        This is intentionally light until you have the exact NinjaTrader
        instrument metadata endpoint/fields.
        """

        obj.pf_symbol = obj.pf_locator
        obj.pf_number = None
        obj.pf_prod_type = getattr(obj, "my_prod_type", None)

        obj.numerator_currency = getattr(obj, "numerator_currency", None)
        obj.denominator_currency = getattr(obj, "denominator_currency", "USD")
        obj.quote_currency = getattr(obj, "quote_currency", "USD")
        obj.settlement_currency = getattr(obj, "settlement_currency", "USD")

        obj.min_tick = getattr(obj, "min_tick", None)
        obj.min_size = getattr(obj, "min_size", 1.0)
        obj.size_increment = getattr(obj, "size_increment", 1.0)

        obj.complete_obj()

    @classmethod
    def get_product_info(cls, product_ids=None):
        """
        Placeholder for future NinjaTrader instrument metadata lookup.

        Keep the same return shape as Binance:

            df, payload

        For now:
            None, {}
        """

        return None, {}