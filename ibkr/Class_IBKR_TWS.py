#!/usr/bin/env python
# coding: utf-8

# In[1]:


#imports
from datetime import datetime
import time

#from IBKR
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract, ComboLeg
from ibapi.tag_value import TagValue
from ibapi.order import *


# In[5]:


class IBKR_TWS(EWrapper, EClient):     
       
    
    def __init__(self):
        EWrapper.__init__(self)
        EClient.__init__(self, self)


    def get_ibkr_channel(self):    
        channel = int(datetime.now().strftime("%H%M%S"))
        print('Connection number is', channel, "\n")
        return channel   
        
    
    def connect_to_ibkr(self, port, channel):
        self.connect("127.0.0.1", int(port), int(channel))
#        time.sleep(2) 
    
    
    def nextValidId(self, orderNum):
        super().nextValidId(orderNum)
        print("\n")
        print("Successful API client connection confirmed -> Next OrderId = ", orderNum, '\n') 
        self.next_order_id = orderNum

        
    def makeSimpleContract(self, conId, exch=None):
        obj                              = Contract()    
        obj.conId                        = conId
#        obj.exchange                     = exch
        return obj
    
    
    def makeComplexContract(self, sym, fiList1, fiList2):
        obj                              = Contract()
        obj.conId                        = "" # this is for use by IBKR - BAGs don't get conIds
        obj.secType                      = 'BAG'    
        obj.symbol                       = sym  
        obj.exchange                     = "SMART" #fiList1[0].contract_dict["exchange"]     
        obj.currency                     = "USD"
        
        obj.comboLegs                    = []
        for fiList in [fiList1, fiList2]:
            leg                          = ComboLeg()
            leg.conId                    = int(fiList[0])
            leg.exchange                 = fiList[1]    
            leg.ratio                    = int(fiList[2])     
            leg.action                   = fiList[3]            
            obj.comboLegs.append(leg)   
            
        return obj

    
    def makeOptionContract(self, symbol, secType, expiry, strike, option_type, exchange):
        obj                              = Contract()
        obj.symbol                       = symbol
        obj.secType                      = secType
        obj.exchange                     = exchange
        obj.lastTradeDateOrContractMonth = expiry
        obj.strike                       = strike
        obj.right                        = option_type  # "C" for call, "P" for put
        obj.currency                     = "USD"        
        #obj.multiplier                   = "100"  # Standard for stock options
        
        return obj


