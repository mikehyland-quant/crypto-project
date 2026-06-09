
import asyncio

import numpy as np

from datetime import datetime

from ib_insync import IB, Contract, ComboLeg, LimitOrder, MarketOrder

class IBKR_IB:
    SAFE_TO_MODIFY = {"Submitted", "PreSubmitted"}


    def __init__(self, host='127.0.0.1', port=7496):
        self.host = host
        self.port = port
        self.clientId = int(datetime.now().strftime("%H%M%S"))

        self.ib = IB()
        self.ticker_dict = {}  # created in stream_contract
        self.obj_by_order_handler = {}  # created in place_limit_order


    async def contract_by_conId(self, conid):
        contract = Contract(conId=int(conid))
        await self.ib.qualifyContractsAsync(contract)
        return contract
    
    
    async def create_simple_contract(self, obj):
        #print(obj.my_fi_name)
        obj.ibkr_contract = await self.contract_by_conId(int(obj.pf_locator))
        obj.ibkr_details = (await self.ib.reqContractDetailsAsync(obj.ibkr_contract))[0]

 
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

        obj.scalar_price_raw_to_mkt  = obj._safe_float(getattr(obj.ibkr_details, 'priceMagnifier'), 1.0)

        obj.scalar_size_unit_per_mkt = obj._safe_float(getattr(obj.ibkr_contract, 'multiplier'), 1.0)
        obj.scalar_size_mkt_per_unit = 1 / obj.scalar_size_unit_per_mkt
        
        obj.min_tick       = obj._safe_float(getattr(obj.ibkr_details, 'minTick'), 1.0)
        obj.min_size       = obj._safe_float(getattr(obj.ibkr_details,  'minSize'), 1.0)
        obj.size_increment = obj._safe_float(getattr(obj.ibkr_details,  'sizeIncrement'), 1.0)
        
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

        #print(ticker, '\n')
        
        return ticker
         

    def tick_handler(self, ticker):
        '''
        IBKRClient.tick_handler is a synchronous method used as an event callback, 
        which works fine with ib_insync's internal event loop, but worth noting — 
        if you ever add latency-sensitive logic there it needs to stay non-blocking.

        '''
        #print(ticker, '\n')

        obj = self.ticker_dict.get(ticker)
        if obj is None:
            return
        
        if obj.need_close_data and ticker.close is not None and not np.isnan(ticker.close):
            x = obj.update_mkt_data(
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
           

    def order_handler(self, trade):
        #print(trade, '\n')
        
        obj = self.obj_by_order_handler.get(trade.order)
        if obj is None:
            return

        strategy = getattr(obj, "strategy", None)
        if strategy is not None and getattr(obj, "strat_on_trade_exec", False):
            asyncio.create_task(strategy.on_trade_exec(obj, trade))


    def place_market_order(self, obj=None, size=None, buy_sell=None):
        order = MarketOrder(
            action=buy_sell,
            totalQuantity=size,
            tif="DAY",
        )

        #print(order, '\n')

        trade = self.ib.placeOrder(obj.ibkr_contract, order)
        trade.statusEvent += self.order_handler

        self.obj_by_order_handler[order] = obj
        
        #print(trade, '\n')

        return trade
    

    def place_limit_order(self, obj=None, size=None, buy_sell=None, price=None):
        order = LimitOrder(
            action=buy_sell,
            totalQuantity=size,
            lmtPrice=price,
            tif="DAY",
        )

        #print(order, '\n')

        trade = self.ib.placeOrder(obj.ibkr_contract, order)
        trade.statusEvent += self.order_handler

        self.obj_by_order_handler[order] = obj

        #print(trade, '\n')

        return trade
 

    def modify_to_market_order(self, obj=None, size=None, buy_sell=None, trade=None):
        if trade is None:
            raise ValueError(f"Trade not found")

        if trade.orderStatus.status not in self.SAFE_TO_MODIFY:
            #raise ValueError(f"Order {trade.order.orderId} is not in a modifiable state")
            return

        trade.order.orderType = "MKT"

        # Important: market orders should not keep a limit price
        trade.order.lmtPrice = None

        trade.order.totalQuantity = size
        trade.order.action = buy_sell
    
        self.ib.placeOrder(obj.ibkr_contract, trade.order)

        #print(trade.order, '\n')
    
        return trade 
    

    def modify_limit_order(self, obj=None, size=None, buy_sell=None, trade=None, price=None):
        if trade is None:
            raise ValueError(f"Trade not found")
    
        if trade.orderStatus.status not in self.SAFE_TO_MODIFY:
            #raise ValueError(f"Order {trade.order.orderId} is not in a modifiable state")
            return

        trade.order.lmtPrice = price
        trade.order.totalQuantity = size
        trade.order.action = buy_sell

        self.ib.placeOrder(obj.ibkr_contract, trade.order)

        #print(trade.order, '\n')
    
        return trade


    def cancel_trade(self, trade):
        if trade is None:
            return

        status = trade.orderStatus.status

        if status in {"Cancelled", "Filled", "Inactive"}:
            return

        self.ib.cancelOrder(trade.order)


    '''
    this is the old code.  needs to be updatedd.
    
    def get_position_size(self, account, contract, position, avgCost):
        super().position(account, contract, position, avgCost)

        objList = [obj for key, obj in self.ibkrDictID.items() if obj.ibkr_contractID == contract.conId]
        if len(objList) == 1:
            obj = objList[0]
            obj.current_position = position
    '''

