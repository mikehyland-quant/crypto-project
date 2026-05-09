#!/usr/bin/env python
# coding: utf-8

#import asyncio

from strategies.Strategy_Parent import Strategy


class Strategy_ImproveOneTick:

    def __init__(self, trader, obj, side, limit_price, size):
        self.trader = trader
        self.obj = obj
        self.side = side.upper()          # "BUY" or "SELL"
        self.limit_price = limit_price
        self.size = size

        self.order_id = None
        self.my_working_price = None

    def calc_target_price(self):
        bid = self.obj.unit_data.get("bid_price")
        ask = self.obj.unit_data.get("ask_price")
        tick = self.obj.minTick

        if self.side == "BUY":
            if bid is None:
                return None

            target = bid + tick
            target = min(target, self.limit_price)

            # round down for bid
            return self.obj.round_price_to_tick(target, side="BUY")

        elif self.side == "SELL":
            if ask is None:
                return None

            target = ask - tick
            target = max(target, self.limit_price)

            # round up for ask
            return self.obj.round_price_to_tick(target, side="SELL")

        else:
            raise ValueError(f"Invalid side: {self.side}")

    def should_improve(self, target_price):
        if self.my_working_price is None:
            return True

        if self.side == "BUY":
            return target_price > self.my_working_price

        if self.side == "SELL":
            return target_price < self.my_working_price

    async def update_mkt_data(self):
        target_price = self.calc_target_price()

        if target_price is None:
            return

        # No order yet: place one
        if self.order_id is None:
            self.order_id = self.trader.place_limit_order(
                obj=self.obj,
                side=self.side,
                price=target_price,
                size=self.size,
            )
            self.my_working_price = target_price
            return

        # Existing order: only improve, never worsen
        if not self.should_improve(target_price):
            return

        await self.trader.cancel_order(self.order_id)

        self.order_id = self.trader.place_limit_order(
            obj=self.obj,
            side=self.side,
            price=target_price,
            size=self.size,
        )

        self.my_working_price = target_price

        