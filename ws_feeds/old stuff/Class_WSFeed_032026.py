#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#  Consider centralizing ping/pong handling where exchanges require app-level heartbeats (Huobi, KuCoin).

#  For Kraken, you might want to handle heartbeat events explicitly, like Huobi, to avoid ignoring relevant messages.


# In[ ]:


import asyncio, json, websockets, gzip, requests, uuid
import pandas as pd

from datetime import datetime, UTC
from IPython.display import display, clear_output
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from collections import defaultdict


# In[ ]:


class WSFeed:
    def __init__(self, ws_dict):
        self.ws_dict = ws_dict

        self._registry_dict = {
            "Coinbase": self.coinbase_stream,
            "Gemini": self.gemini_stream,
            "Kraken": self.kraken_stream,
            "Binance": self.binance_stream,
            "Bitfinex": self.bitfinex_stream,
            "Bybit": self.bybit_stream,
            "Huobi": self.huobi_stream,
            "KuCoin": self.kucoin_stream,
            "KuCoin-Derivs": self.kucoin_derivs_stream,
            "OKX": self.okx_stream,
        }

        self.platform_objs = defaultdict(list)
        for obj in ws_dict.values():
            self.platform_objs[obj.platform_id].append(obj)

        self.platform_ids = sorted(self.platform_objs.keys())


#----------


    async def run(self):
        tasks = []

        for platform in self.platform_ids:
            coro = self._registry_dict.get(platform)
            if coro:
                objs = self.platform_objs[platform]
                tasks.append(asyncio.create_task(coro(objs)))

        await asyncio.gather(*tasks)


#----------


    async def binance_stream(self, objs):
        streams = "/".join(f"{o.platform_symbol}@bookTicker" for o in objs)
        url = f"wss://stream.binance.com:9443/stream?streams={streams}"

        obj_map = {o.platform_symbol.upper(): o for o in objs}

        async with websockets.connect(url) as ws:
            while True:
                msg = json.loads(await ws.recv())
                data = msg["data"]

                obj = obj_map.get(data["s"])
                if not obj:
                    continue

                obj.update_mkt_data(
                    bid_price=float(data["b"]),
                    ask_price=float(data["a"]),
                    bid_size=float(data["B"]),
                    ask_size=float(data["A"]),
                )


#----------


    async def bitfinex_stream(self, objs):
        """
        objs: list of Spot objects for Bitfinex
        Each obj must have:
            - platform_symbol = e.g. "tBTCUSD"
            - update_mkt_data() method
        """
        if not objs:
            return

        url = "wss://api-pub.bitfinex.com/ws/2"

        # Build map from symbol -> object
        obj_map = {o.platform_symbol.upper(): o for o in objs}

        # Subscribe to all symbols
        for o in objs:
            sub = {
                "event": "subscribe",
                "channel": "book",
                "symbol": o.platform_symbol.upper(),
                "prec": "P0",
                "freq": "F0",
                "len": 25
            }
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps(sub))

                best_bid_map = {o.platform_symbol.upper(): None for o in objs}
                best_ask_map = {o.platform_symbol.upper(): None for o in objs}

                while True:
                    msg = json.loads(await ws.recv())

                    # Ignore non-data messages
                    if isinstance(msg, dict):
                        continue

                    if len(msg) < 2:
                        continue

                    channel_data = msg[1]
                    if channel_data == "hb":
                        continue

                    # Find the object for this channel
                    chan_id = msg[0]
                    # Lookup object by channel symbol
                    # We'll assume single-channel per ws connection for now
                    for symbol, obj in obj_map.items():
                        if msg[1] is None:
                            continue

                        data = msg[1]

                        # Snapshot case
                        if isinstance(data[0], list):
                            bids = [x for x in data if x[2] > 0]
                            asks = [x for x in data if x[2] < 0]

                            if bids:
                                p, _, a = max(bids, key=lambda x: x[0])
                                best_bid_map[symbol] = p
                                obj.update_mkt_data(bid_price=p, bid_size=a)

                            if asks:
                                p, _, a = min(asks, key=lambda x: x[0])
                                best_ask_map[symbol] = p
                                obj.update_mkt_data(ask_price=p, ask_size=abs(a))

                            continue

                        # Update case
                        price, count, amount = data
                        best_bid = best_bid_map[symbol]
                        best_ask = best_ask_map[symbol]

                        if count == 0:
                            if amount == 1 and price == best_bid:
                                best_bid_map[symbol] = None
                            if amount == -1 and price == best_ask:
                                best_ask_map[symbol] = None
                            continue

                        if amount > 0:
                            if best_bid is None or price > best_bid:
                                best_bid_map[symbol] = price
                                obj.update_mkt_data(bid_price=price, bid_size=amount)
                        else:
                            if best_ask is None or price < best_ask:
                                best_ask_map[symbol] = price
                                obj.update_mkt_data(ask_price=price, ask_size=abs(amount))


#----------


    async def bybit_stream(self, objs):
        """
        objs: list of Spot objects for Bybit
        Each obj must have:
            - platform_symbol = e.g. "BTCUSDT"
            - update_mkt_data() method
        """
        if not objs:
            return

        url = "wss://stream.bybit.com/v5/public/spot"

        # Bybit subscription args: list of topics per symbol
        topics = [f"orderbook.1.{o.platform_symbol}" for o in objs]
        sub = {"op": "subscribe", "args": topics}

        # Map symbol -> object
        obj_map = {o.platform_symbol.upper(): o for o in objs}

        async with websockets.connect(url) as ws:
            await ws.send(json.dumps(sub))

            while True:
                msg = json.loads(await ws.recv())
                data_list = msg.get("data")
                if not data_list:
                    continue

                # Bybit sends a list per message; route each to correct object
                for data in data_list:
                    topic = data.get("s") or data.get("topic")
                    if not topic:
                        continue

                    # Extract symbol from topic string
                    # topic format: "orderbook.1.BTCUSDT"
                    symbol = topic.split(".")[-1].upper()
                    obj = obj_map.get(symbol)
                    if not obj:
                        continue

                    # Update bid
                    if "b" in data and data["b"]:
                        bid_price, bid_size = map(float, data["b"][0])
                        obj.update_mkt_data(bid_price=bid_price, bid_size=bid_size)

                    # Update ask
                    if "a" in data and data["a"]:
                        ask_price, ask_size = map(float, data["a"][0])
                        obj.update_mkt_data(ask_price=ask_price, ask_size=ask_size)


#----------


    async def coinbase_stream(self, objs):       
        obj_map = {o.platform_symbol: o for o in objs}

        async with websockets.connect("wss://ws-feed.exchange.coinbase.com") as ws:
            await ws.send(json.dumps({
                "type": "subscribe",
                "channels": [{
                    "name": "ticker",
                    "product_ids": list(obj_map.keys())
                }]
            }))

            while True:
                msg = json.loads(await ws.recv())

                if msg.get("type") != "ticker":
                    continue

                obj = obj_map.get(msg["product_id"])
                if not obj:
                    continue

                obj.update_mkt_data(
                    bid_price=float(msg["best_bid"]),
                    bid_size=float(msg["best_bid_size"]),
                    ask_price=float(msg["best_ask"]),
                    ask_size=float(msg["best_ask_size"]),
                )


#----------


    async def gemini_stream(self, objs):
        """
        objs: list of Spot objects for Gemini
        Each obj must have:
            - platform_symbol = e.g. "BTCUSD"
            - update_mkt_data() method
        """
        if not objs:
            return

        # Map symbol -> object
        obj_map = {o.platform_symbol.upper(): o for o in objs}

        # Gemini allows multiple symbols via multiple connections,
        # but for now we'll connect once per venue (adjust if needed)
        for obj in objs:
            url = f"wss://api.gemini.com/v1/marketdata/{obj.platform_symbol}?top_of_book=true"
            async with websockets.connect(url) as ws:
                while True:
                    msg = json.loads(await ws.recv())
                    for event in msg.get("events", []):
                        if event.get("type") != "change":
                            continue

                        symbol = obj.platform_symbol.upper()
                        obj = obj_map.get(symbol)
                        if not obj:
                            continue

                        side = event["side"]
                        price = float(event["price"])
                        remaining = float(event["remaining"])

                        if side == "bid":
                            obj.update_mkt_data(bid_price=price, bid_size=remaining)
                        elif side == "ask":
                            obj.update_mkt_data(ask_price=price, ask_size=remaining)


#----------


    async def huobi_stream(self, objs):
        """
        objs: list of Spot objects for Huobi
        Each obj must have:
            - platform_symbol = e.g. "btcusdt"
            - update_mkt_data() method
        """
        if not objs:
            return

        url = "wss://api.huobi.pro/ws"

        # Map symbol -> object
        obj_map = {o.platform_symbol.lower(): o for o in objs}

        # Subscribe to each symbol
        sub_list = [
            {"sub": f"market.{o.platform_symbol.lower()}.bbo", "id": f"spot_bbo_{o.platform_symbol}"}
            for o in objs
        ]

        while True:  # reconnect loop
            try:
                async with websockets.connect(url, ping_interval=None) as ws:
                    # Send all subscriptions
                    for sub in sub_list:
                        await ws.send(json.dumps(sub))

                    while True:
                        raw = await ws.recv()
                        msg = json.loads(gzip.decompress(raw))

                        # Heartbeat
                        if "ping" in msg:
                            await ws.send(json.dumps({"pong": msg["ping"]}))
                            continue

                        tick = msg.get("tick")
                        if not tick:
                            continue

                        # Find the symbol from subscription id
                        sub_id = msg.get("ch", "")
                        # format: market.btcusdt.bbo
                        symbol = sub_id.split(".")[1].lower()
                        obj = obj_map.get(symbol)
                        if not obj:
                            continue

                        # Update market data
                        obj.update_mkt_data(
                            bid_price=tick["bid"],
                            bid_size=tick["bidSize"],
                            ask_price=tick["ask"],
                            ask_size=tick["askSize"],
                        )

            except ConnectionClosedOK:
                print("Huobi WS closed normally, reconnecting...")
                await asyncio.sleep(1)
            except ConnectionClosedError as e:
                print("Huobi WS connection error:", e)
                await asyncio.sleep(2)
            except Exception as e:
                print("Huobi WS unexpected error:", e)
                await asyncio.sleep(5)


#----------


    async def kraken_stream(self, objs):
        """
        objs: list of Spot objects for Kraken
        Each obj must have:
            - platform_symbol = e.g. "XBT/USD"
            - update_mkt_data() method
        """
        if not objs:
            return

        url = "wss://ws.kraken.com"

        # Map symbol -> object
        obj_map = {o.platform_symbol.upper(): o for o in objs}

        # Subscribe to all symbols
        subs = {
            "event": "subscribe",
            "pair": [o.platform_symbol.upper() for o in objs],
            "subscription": {"name": "book", "depth": 10},  # top-of-book
        }

        async with websockets.connect(url) as ws:
            await ws.send(json.dumps(subs))

            while True:
                msg = json.loads(await ws.recv())
                #print("KRAKEN RAW:", msg)   # temporary debug

                # Handle system / subscription messages instead of ignoring them
                if isinstance(msg, dict):
                    if msg.get("event") == "subscriptionStatus":
                        pair = msg.get("pair")
                        status = msg.get("status")
                        if status != "subscribed":
                            print(f"Kraken subscription error for {pair}: {msg}")
                    continue

                if not isinstance(msg, list) or len(msg) < 4:
                    continue

                data = msg[1]
                pair = msg[-1]  # symbol name at end of message
                obj = obj_map.get(pair.upper())
                if not obj:
                    continue

                # Snapshot keys
                if 'bs' in data and data['bs']:
                    bid_price, bid_size = map(float, data['bs'][0][:2])
                    obj.update_mkt_data(bid_price=bid_price, bid_size=bid_size)

                if 'as' in data and data['as']:
                    ask_price, ask_size = map(float, data['as'][0][:2])
                    obj.update_mkt_data(ask_price=ask_price, ask_size=ask_size)

                # Update bid
                if 'b' in data and data['b']:
                    bid_price, bid_size = map(float, data['b'][0][:2])
                    obj.update_mkt_data(bid_price=bid_price, bid_size=bid_size)

                # Update ask
                if 'a' in data and data['a']:
                    ask_price, ask_size = map(float, data['a'][0][:2])
                    obj.update_mkt_data(ask_price=ask_price, ask_size=ask_size)


#----------


    async def kraken_derivs_stream(self, objs):
        """
        objs: list of Futures/Perp objects for Kraken
        Each obj must have:
            - platform_symbol = e.g. "PI_XBTUSD" (perp) or "FI_XBTUSD_230630" (future)
            - update_mkt_data() method
        """
        if not objs:
            return

        url = "wss://futures.kraken.com/ws/v1"

        # Map symbol -> object
        obj_map = {o.platform_symbol.upper(): o for o in objs}

        # Subscribe to ticker for all symbols
        sub = {
            "event": "subscribe",
            "feed": "ticker",
            "product_ids": list(obj_map.keys())
        }

        async with websockets.connect(url) as ws:
            await ws.send(json.dumps(sub))

            while True:
                msg = json.loads(await ws.recv())

                # Skip non-ticker messages
                if msg.get("feed") != "ticker":
                    continue

                symbol = msg.get("product_id", "").upper()
                obj = obj_map.get(symbol)
                if not obj:
                    continue

                # Update market data
                obj.update_mkt_data(
                    bid_price=float(msg["bid"]),
                    bid_size=float(msg["bid_size"]),
                    ask_price=float(msg["ask"]),
                    ask_size=float(msg["ask_size"]),
                )


#----------


    async def kucoin_stream(self, objs):
        await self._kucoin_ws_loop(
            objs,
            bullet_url="https://api.kucoin.com/api/v1/bullet-public",
            topic_prefix="/market/ticker:",
            name="KuCoin",
        )


    async def kucoin_derivs_stream(self, objs):
        await self._kucoin_ws_loop(
            objs,
            bullet_url="https://api-futures.kucoin.com/api/v1/bullet-public",
            topic_prefix="/contractMarket/ticker:",
            name="KuCoin Derivs",
        )


    async def _kucoin_ws_loop(self, objs, *, bullet_url, topic_prefix, name,):
        if not objs:
            return

        # Map symbol -> object
        obj_map = {o.platform_symbol.upper(): o for o in objs}

        while True:  # reconnect loop
            try:
                r = requests.post(bullet_url, timeout=5)
                r.raise_for_status()
                data = r.json()["data"]

                token = data["token"]
                endpoint = data["instanceServers"][0]["endpoint"]
                ws_url = f"{endpoint}?token={token}"

                async with websockets.connect(ws_url, ping_interval=None) as ws:

                    # Subscribe to all symbols
                    sub = {
                        "id": str(uuid.uuid4()),
                        "type": "subscribe",
                        "topic": topic_prefix + ",".join(obj_map.keys()),
                        "response": True
                    }
                    await ws.send(json.dumps(sub))

                    while True:
                        msg = json.loads(await ws.recv())

                        if msg.get("type") != "message":
                            continue

                        topic = msg.get('topic').split(":")
                        spot_or_fut = topic[0]
                        symbol = topic[1]

                        data = msg.get("data")

                        # Route update to the correct object
                        obj = obj_map.get(symbol)
                        if not obj:
                            continue

                        if spot_or_fut == "/market/ticker":
                            bidName = "bestBid"
                            askName = "bestAsk"

                        else:
                            bidName = "bestBidPrice"
                            askName = "bestAskPrice"

                        obj.update_mkt_data(
                            bid_price=float(data[bidName]),
                            bid_size=float(data["bestBidSize"]),
                            ask_price=float(data[askName]),
                            ask_size=float(data["bestAskSize"])
                        )

            except ConnectionClosedOK:
                print(f"{name} WS closed normally, reconnecting...")
                await asyncio.sleep(1)
            except ConnectionClosedError as e:
                print(f"{name} WS connection error:", e)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"{name} WS unexpected error:", e)
                await asyncio.sleep(5)


#----------


    async def okx_stream(self, objs):
        """
        Unified OKX stream for spot, futures, and perpetuals.
        Each obj must have:
            - platform_symbol (e.g. "BTC-USDT", "BTC-USD-230624", "BTC-USDT-SWAP")
            - inst_type: "SPOT", "FUTURES", or "SWAP"
            - update_mkt_data() method
        """
        if not objs:
            return

        url = "wss://ws.okx.com:8443/ws/v5/public"

        # Map symbol -> object
        obj_map = {o.platform_symbol.upper(): o for o in objs}

        # Build subscription args
        sub_args = [
            {
                "channel": "books5",
                "instId": o.platform_symbol.upper(),
                "instType": o.platform_type.upper()  # SPOT, FUTURES, SWAP
            }
            for o in objs
        ]
        sub = {"op": "subscribe", "args": sub_args}

        async with websockets.connect(url) as ws:
            await ws.send(json.dumps(sub))

            while True:
                try:
                    msg = json.loads(await ws.recv())
                    data_list = msg.get("data")
                    if not data_list:
                        continue

                    for book in data_list:
                        symbol = book.get("instId", "").upper()
                        obj = obj_map.get(symbol)
                        if not obj:
                            continue

                        bids = book.get("bids", [])
                        asks = book.get("asks", [])

                        if bids:
                            bid_price, bid_size = map(float, bids[0][:2])
                            obj.update_mkt_data(bid_price=bid_price, bid_size=bid_size)

                        if asks:
                            ask_price, ask_size = map(float, asks[0][:2])
                            obj.update_mkt_data(ask_price=ask_price, ask_size=ask_size)

                except ConnectionClosedOK:
                    print("OKX WS closed normally, reconnecting...")
                    await asyncio.sleep(1)
                    return await self.okx_stream(objs)
                except ConnectionClosedError as e:
                    print("OKX WS connection error:", e)
                    await asyncio.sleep(2)
                    return await self.okx_stream(objs)
                except Exception as e:
                    print("OKX WS unexpected error:", e)
                    await asyncio.sleep(5)
                    return await self.okx_stream(objs)

