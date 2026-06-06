#!/usr/bin/env python
# coding: utf-8

import asyncio
from collections import defaultdict

from ws_feeds.Class_WS_Binance       import BinanceSpotFeed
from ws_feeds.Class_WS_BinanceUS     import BinanceUSFeed
from ws_feeds.Class_WS_Bitfinex      import BitfinexFeed
from ws_feeds.Class_WS_Bybit         import BybitFeed
from ws_feeds.Class_WS_Coinbase      import CoinbaseSpotFeed, CoinbaseDerivsFeed
from ws_feeds.Class_WS_Deribit       import DeribitFeed
from ws_feeds.Class_WS_Gate          import GateFeed
from ws_feeds.Class_WS_Gemini        import GeminiFeed
from ws_feeds.Class_WS_Huobi         import HuobiFeed
from ws_feeds.Class_WS_Kraken        import KrakenSpotFeed
from ws_feeds.Class_WS_KuCoin        import KuCoinSpotFeed
#from ws_feeds.Class_WS_NinjaData     import NinjaDataFeed
from ws_feeds.Class_WS_OKX           import OKXFeed
from ws_feeds.Class_WS_Phemex        import PhemexFeed
#from ws_feeds.Class_WS_MEXC          import MEXCFeed

class WSFeedManager:
    """
    Manager that groups instrument objects by venue, instantiates one feed per venue,
    and runs or completes them concurrently.
    
    Input:
        fi_objs_list : list of instrument objects
    
    Each instrument object must provide:
        - my_pf_name   : registry key for the venue/feed class
        - pf_locator   : venue-specific symbol used by the feed
        - update_mkt_data() : method used by feed adapters
    """
    
    REGISTRY = {
        "BinanceSpot"     : BinanceSpotFeed,
        #binance derivs
        "BinanceUS"       : BinanceUSFeed,
        "Bitfinex"        : BitfinexFeed,
        #bitnomial
        "Bybit"           : BybitFeed,
        "Coinbase"        : CoinbaseSpotFeed,
        "Coinbase-Derivs" : CoinbaseDerivsFeed,
        "Deribit"         : DeribitFeed,
        "Gate"            : GateFeed,
        "Gemini"          : GeminiFeed,
        "Huobi"           : HuobiFeed,
        #"Kraken-Derivs"   : KrakenDerivsFeed,
        "KrakenSpot"      : KrakenSpotFeed,
        #"KuCoin-Derivs"   : KuCoinDerivsFeed,
        "KuCoinSpot"      : KuCoinSpotFeed,
#        "MEXC"            : MEXCFeed,
#         "NT8-Data"       : NinjaDataFeed,
        "OKX"             : OKXFeed,
        "Phemex"          : PhemexFeed

#Gate, BitMEX, and MEXC  Crypto.com   Hyperliquid  PHEMEX
        
    }

    def __init__(self, fi_objs_list):
        self.objs_by_pf_dict = self._group_objects_by_platform(fi_objs_list)
        self.feeds = self._build_pf_list()


    def _group_objects_by_platform(self, list_):
        dict_ = defaultdict(list)
        for obj in list_:
            dict_[obj.my_pf_name].append(obj)
        return dict_
    
        
    def _build_pf_list(self):
        list_ = []
        for my_pf_name, fi_objs_list in sorted(self.objs_by_pf_dict.items()):
            feed_class = self.REGISTRY.get(my_pf_name)
            if feed_class is None:
                raise KeyError(f"No feed class registered for {my_pf_name}")
            list_.append(feed_class(fi_objs_list))
        return list_
    
    async def run(self):
        tasks = [asyncio.create_task(feed.stream()) for feed in self.feeds]
        await asyncio.gather(*tasks)

    
    @classmethod
    def add_feed(self, my_pf_name, feed_class):
        """Register a new exchange feed class at runtime."""
        self.REGISTRY[my_pf_name] = feed_class

    
    @property
    def active_platforms(self):
        return [feed.name for feed in self.feeds]

    
    async def complete_fi_objects(self):
        tasks = []
        for platform, objs_list in self.objs_by_pf_dict.items():
            feed_class = self.REGISTRY.get(platform)
            if feed_class is None:
                raise KeyError(f"No feed class registered for {platform}")
            tasks.append(asyncio.to_thread(feed_class.complete_objects, objs_list))
        await asyncio.gather(*tasks)
        
        