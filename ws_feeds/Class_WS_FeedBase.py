#!/usr/bin/env python
# coding: utf-8

import asyncio, json, websockets 
from datetime import datetime, UTC
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from abc import ABC, abstractmethod


class WSFeedBase(ABC):
    
    """
    Abstract base class for all exchange WebSocket feed adapters.
    
    This class provides a standardized framework for:
        - connection management
        - automatic reconnection handling
        - WebSocket message loop
        - symbol normalization and object mapping
    
    Subclasses are responsible only for exchange-specific logic.
    
    Required subclass implementations
    --------------------------------
    async def _subscribe(self, ws):
        Send one or more subscription messages after the WebSocket connection is established.
    
    async def _handle_message(self, msg):
        Parse incoming messages and update instrument objects via obj.update_mkt_data().
    
    @classmethod
    def complete_objects(cls, objs_list):
        Populate instrument objects with static metadata from the exchange.
    
    @classmethod
    def complete_obj(cls, obj):
        Populate a single instrument object with normalized fields.
    
    @classmethod
    def get_product_info(cls, *args, **kwargs):
        Retrieve raw product/instrument metadata from the exchange REST API.
    
    
    Optional overrides
    ------------------
    def _normalize_symbol(self, symbol):
        Normalize symbols for consistent mapping (default: uppercased).
    
    def _decode_message(self, raw):
        Decode raw WebSocket payloads (e.g., gzip, bytes, JSON).
    
    def _handle_heartbeat(self, ws, msg):
        Handle exchange-specific heartbeat messages. Return True if handled.
    
    def _handle_error(self, msg):
        Handle exchange-specific error or status messages.
    
    
    Provided functionality
    ----------------------
    - stream(): entry point that runs the feed with automatic reconnection
    - _connect(): establishes connection, calls subscribe, and starts message loop
    - _ws_loop(): processes incoming messages and dispatches to handler
    - _reconnect_loop(): retries connection with backoff based on exception type
    - _make_obj_map(): builds symbol → object lookup
    - _safe_float(): safely converts values to float
    - _ts(): returns current UTC timestamp
    
    """

    name = None     # e.g. "Coinbase"
    url  = None     # e.g. "wss://ws-feed.exchange.coinbase.com"

    RECONNECT_DELAYS = {
        ConnectionClosedOK    : 1,
        ConnectionClosedError : 2,
        Exception             : 5,
    }

    def __init__(self, objs_list):
        self.objs_list  = objs_list
        self.obj_map    = self._make_obj_map(self.objs_list)

    def _normalize_symbol(self, symbol):  
        return symbol.upper()  # override to symbol.lower() for certain venues

    def _make_obj_map(self, objs_list):
        return {self._normalize_symbol(o.pf_locator): o for o in objs_list}
        async def stream(self):
            await self._reconnect_loop(self._connect)
            
    async def stream(self):
        await self._reconnect_loop(self._connect)
    
    async def _connect(self):
        async with websockets.connect(self.url) as ws:
            await self._subscribe(ws)
            await self._ws_loop(ws)

    @abstractmethod
    async def _subscribe(self, ws):
        pass
    
    async def _ws_loop(self, ws):
        async for raw in ws:
            msg = self._decode_message(raw)
            if await self._handle_heartbeat(ws, msg):
                continue
            await self._handle_message(msg)
            
    def _decode_message(self, raw):
        return json.loads(raw)
        
    @abstractmethod
    async def _handle_message(self, msg):
        pass

    async def _handle_heartbeat(self, ws, msg):
        """Override in subclasses that require app-level heartbeat responses."""
        return False    # False = not a heartbeat, caller should continue processing

    def _handle_error(self, msg):
        """Override to add exchange-specific error/status message handling."""
        pass

    async def _reconnect_loop(self, coro_factory):
        """
        Wraps a coroutine factory in a reconnect loop with per-exception delays.
        Usage: await self._reconnect_loop(self._connect)
        """
        while True:
            try:
                await coro_factory()
            except tuple(self.RECONNECT_DELAYS.keys()) as e:
                delay = next(
                    v for k, v in self.RECONNECT_DELAYS.items() if isinstance(e, k)
                )
                print(datetime.now(), f"{self.name} WS error ({type(e).__name__}): {e}. Reconnecting in {delay}s...")
                await asyncio.sleep(delay)

    @classmethod
    @abstractmethod
    def complete_objects(cls, objs_list):
        pass
    
    @classmethod
    @abstractmethod
    def complete_obj(cls, obj):
        pass
     
    @classmethod
    @abstractmethod
    def get_product_info(cls, *args, **kwargs):
        pass
    
    @staticmethod
    def _safe_float(x):
        if x in (None, "", "null"):
            return None
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _ts():
        return datetime.now(UTC).isoformat()
 