#!/usr/bin/env python
# coding: utf-8

# In[ ]:


def WorkbookDetails():

    #create dictionary to hold other info    
    WorkbookDetailsDict = {    

        #initial instruction area for program
        "Workbook Name" :                            '2026 Short Rates.xlsx',
        "Instruction Worksheet Name" :               'PYTHON',
        "Instruction Range" :                        'Table1'}

    return WorkbookDetailsDict


# In[ ]:


#IBKR imports
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *

#non-IBKR imports
import pandas as pd
import xlwings as xw
import threading
import time
from datetime import datetime

#self-written shortcuts
from Class_xlWings import *
xlw  = xlWings()

##########################################

def QuickFutureObject(symbol, exchange, contractMonth):        
    objectName = Contract()
    objectName.symbol = symbol
    objectName.secType = "FUT"
    objectName.exchange = exchange
    objectName.currency = "USD"
    objectName.lastTradeDateOrContractMonth = contractMonth
    return objectName

##########################################    


class IBKRLightOW(EWrapper, EClient):     

    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId):
        self.nextOrderId = orderId
        print("\n")
        print("Successful API client connection confirmed -> Next OrderId = ", self.nextOrderId) 

    def tickPrice(self, tickerId, field, price, attribs):
        if (0 < field < 3) or (field == 4): 
            updateLivePriceDF(self, tickerId, field, price)



# In[ ]:


def updateLivePriceDF(self, tickerId, field, amount): 
    # this function can be preceded by IBKR.tickPrice or IBKR.tickSize
    if field == 1:
        colNumber = 4
    elif field ==2:
        colNumber = 5
    elif field == 4:
        colNumber = 6        
    self.FinInstDF.iloc[int(tickerId), colNumber] = amount



# In[ ]:


def printBidAsk(inst, InstructionsDict):    
    wb = xw.Book(InstructionsDict["Workbook Name"])
    ws = wb.sheets[InstructionsDict["Output Worksheet"]]    
    ws.range(InstructionsDict["Output Cell"]).options(index = False, header=1).value = \
                                        inst.FinInstDF[['BID PRICE','ASK PRICE','LAST PRICE']]

    print(datetime.now())

    timer2 = threading.Timer(InstructionsDict["Timer Interval"], printBidAsk, [inst, InstructionsDict])
    timer2.start()



# In[ ]:


def main():

#Step 1 - create data structures and initiate variables
    WorkbookDetailsDict = WorkbookDetails()

#Step 2 - get instructions
    FixedInputsDict = xlw.getDict(WorkbookDetailsDict["Workbook Name"], 
                                  WorkbookDetailsDict["Instruction Worksheet Name"], 
                                  'Table1', True, int)

#Step 3 - create instances of necessary classes
    IBKR = IBKRLightOW() 

#Step 4 - create Financial Instrument dataframe
    IBKR.FinInstDF = xlw.getDF(FixedInputsDict["Workbook Name"],
                               FixedInputsDict["Input Worksheet"],
                               FixedInputsDict["Input Range"], True,
                               FixedInputsDict["Header Rows"], int)
    IBKR.FinInstDF['MONTH'] = IBKR.FinInstDF['MONTH'].astype(int)
    IBKR.FinInstDF['BID PRICE'] = "-"
    IBKR.FinInstDF['ASK PRICE'] = "-"
    IBKR.FinInstDF['LAST PRICE'] = "-"

#Step 5 - create asset objects       
    for i in IBKR.FinInstDF.index:
        IBKR.FinInstDF.loc[i, "OBJECT"] = QuickFutureObject(IBKR.FinInstDF.loc[i, "SYMBOL"], 
                                                            IBKR.FinInstDF.loc[i, "EXCHANGE"], 
                                                            IBKR.FinInstDF.loc[i, "MONTH"])

#Step 6 - connect to IBKR                       
    IBKR.connect("127.0.0.1", FixedInputsDict["IBKR Port"], FixedInputsDict["Client Number"])
    time.sleep(2)

#Step 7 - kickoff dataframe printing thread
    timer1 = threading.Timer(FixedInputsDict["Timer Interval"], printBidAsk, [IBKR, FixedInputsDict])
    timer1.start()

#Step 8 - request market data    
    for i in IBKR.FinInstDF.index:
        IBKR.reqMktData(i, IBKR.FinInstDF.loc[i, "OBJECT"], "", False, False, [])

#Step 9 - run and populate Excel        
    IBKR.run()   

main()

