

import asyncio

from numpy import size

from ib_insync import IB, Contract, ComboLeg, LimitOrder, MarketOrder
from datetime import datetime


class IBKR_IB:
    def __init__(self, host='127.0.0.1', port=7496):
        self.host = host
        self.port = port
        self.clientId = int(datetime.now().strftime("%H%M%S"))

        self.ib = IB()
        self.ticker_dict = {}  # created in stream_contract
        self.trades_by_order_id = {}  # created in place_limit_order
        self.obj_by_order_id = {}  # created in place_limit_order

    async def create_simple_contract(self, obj):
        obj.ibkr_contract = await self.contract_by_conId(int(obj.pf_locator))
        obj.ibkr_details = (await self.ib.reqContractDetailsAsync(obj.ibkr_contract))[0]

    async def contract_by_conId(self, conid):
        contract = Contract(conId=int(conid))
        await self.ib.qualifyContractsAsync(contract)
        return contract

    async def create_bag_contract(self, spread_obj):
        leg1 = ComboLeg()
        leg1.conId = int(spread_obj.far_obj.ibkr_contract.conId)
        leg1.ratio = 1
        leg1.action = 'BUY'
        leg1.exchange = spread_obj.far_obj.ibkr_contract.exchange

        leg2 = ComboLeg()
        leg2.conId = int(spread_obj.near_obj.ibkr_contract.conId)
        leg2.ratio = 1
        leg2.action = 'SELL'
        leg2.exchange = spread_obj.near_obj.ibkr_contract.exchange

        bag = Contract()
        bag.symbol = spread_obj.far_obj.ibkr_contract.symbol
        bag.secType = 'BAG'
        bag.currency = spread_obj.far_obj.ibkr_contract.currency
        bag.exchange = 'SMART'#near_obj.ibkr_contract.exchange
        bag.comboLegs = [leg1, leg2]

        spread_obj.ibkr_contract = bag        
            
    @classmethod
    async def complete_obj(cls, obj):
        obj.pf_symbol    = obj.ibkr_contract.localSymbol
        obj.pf_number    = obj.ibkr_contract.conId
        obj.pf_prod_type = obj.ibkr_contract.secType
        
        obj.numerator_currency   = obj.my_row.top_currency
        obj.denominator_currency = obj.my_row.base_currency
        obj.quote_currency       = None
        obj.settlement_currency  = None

        obj.scalar_order_size         = obj._safe_float(getattr(obj.ibkr_contract, 'multiplier'), 1.0)
        obj.scalar_price_raw_to_order = obj._safe_float(getattr(obj.ibkr_details, 'priceMagnifier'), 1.0)
        
        obj.complete_obj()
        
    async def connect(self):
        if not self.ib.isConnected():
            await self.ib.connectAsync(
                host=self.host,
                port=self.port,
                clientId=self.clientId
            )
        #print("Next Order ID:", self.ib.client.getReqId())
        return self.ib.isConnected()

    async def start_streams(self, dict_or_list):
        if isinstance(dict_or_list, dict):
            objs = list(dict_or_list.values())
        else:
            objs = dict_or_list

        for obj in objs:
            await self.stream_contract(obj, self.tick_handler)
            
    async def stream_contract(self, obj, handler):
        if obj.ibkr_contract.secType == 'BAG':
            ticker = self.ib.reqMktData(obj.ibkr_contract, "233", False, False)
        else:
            ticker = self.ib.reqMktData(obj.ibkr_contract, "", False, False)       
        
        ticker.updateEvent += handler
        self.ticker_dict[ticker] = obj
        
        return ticker
        
    def tick_handler(self, ticker):
        '''
        IBKRClient.tick_handler is a synchronous method used as an event callback, 
        which works fine with ib_insync's internal event loop, but worth noting — 
        if you ever add latency-sensitive logic there it needs to stay non-blocking.

        '''
#        print(ticker, '\n')

        obj = self.ticker_dict.get(ticker)
        if obj is None:
            return
        
        if obj.need_close_data and ticker.close is not None:
            obj.update_mkt_data(
                bid_price=ticker.bid,
                ask_price=ticker.ask,
                bid_size=ticker.bidSize,
                ask_size=ticker.askSize
            )
            
            obj.on_close_data(
                close_price=ticker.close
            )
                
        elif ticker.bid is not None and ticker.ask is not None:
            obj.on_mkt_data(
                bid_price=ticker.bid,
                ask_price=ticker.ask,
                bid_size=ticker.bidSize,
                ask_size=ticker.askSize
            )
           
    def order_handler(self, order):
        key = (
            order.order.clientId,
            order.order.orderId
            )
        
        obj = self.obj_by_order_id.get(key)
        if obj is None:
            return

        strategy = getattr(obj, "strategy", None)
        if strategy is not None and getattr(obj, "strat_on_trade_exec", False):
            asyncio.create_task(strategy.on_trade_exec(obj, order))
            
    def place_market_order(self, obj=None, side=None, size=None):
        contract = obj.ibkr_contract

        order = MarketOrder(
            action=side,
            totalQuantity=size,
            tif="DAY",
        )

        my_order = self.ib.placeOrder(contract, order)
        my_order.statusEvent += self.order_handler

        key = (
            my_order.order.clientId,
            my_order.order.orderId
        )

        self.trades_by_order_id[key] = my_order
        self.obj_by_order_id[key] = obj

        return my_order.order.orderId

    def modify_to_market_order(self, order_id=None, obj=None, side=None, size=None):
        key = (self.clientId, order_id)
        trade = self.trades_by_order_id.get(key)

        if trade is None:
            raise ValueError(f"Order {order_id} not found")
    
        trade.order.orderType = "MKT"
        trade.order.totalQuantity = size
        trade.order.side = side

        # Important: market orders should not keep a limit price
        trade.order.lmtPrice = None
    
        self.ib.placeOrder(obj.ibkr_contract, trade.order)
    
        return order_id
    
    def place_limit_order(self, obj=None, side=None, price=None, size=None):
        contract = obj.ibkr_contract

        order = LimitOrder(
            action=side,
            totalQuantity=size,
            lmtPrice=price,
            tif="DAY",
        )

        my_order = self.ib.placeOrder(contract, order)
        my_order.statusEvent += self.order_handler
        
        key = (
            my_order.order.clientId,
            my_order.order.orderId
            )
        
        self.trades_by_order_id[key] = my_order
        self.obj_by_order_id[key] = obj

        return my_order.order.orderId

    def modify_limit_order(self, order_id=None, obj=None, price=None, size=None):
        key = (self.clientId, order_id)
        trade = self.trades_by_order_id.get(key)

        if trade is None:
            raise ValueError(f"Order {order_id} not found")
    
        trade.order.lmtPrice = price
        trade.order.totalQuantity = size
    
        self.ib.placeOrder(obj.ibkr_contract, trade.order)
    
        return order_id

    

