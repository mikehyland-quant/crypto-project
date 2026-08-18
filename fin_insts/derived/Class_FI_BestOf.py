
from fin_insts.derived.Class_FI_Subscriber import Subscriber


import asyncio
import numpy as np
import pandas as pd


class BestOf(Subscriber):
    '''
    for either mode, create class:
        bestof = BestOf(
            my_name="BTC venues",
            objs_list=objs_list,
            attr_tuples=[
                ("mkt_bid", "max"),
                ("mkt_ask", "min"),
            ],
            mode="auto",
        )

    for timer mode:
        for obj in bo_obj_list:     #these are the bestOf objects
            tasks.append(asyncio.create_task(obj.run_timer())) 
            

    for auto mode:
        will be triggered by underlying objects at subscriber.update_unit_data() at end of mkt_data_update()
    '''
 
    consensus_attr_list = [
        'my_pf_name',
        'numerator_currency',
        'denominator_currency',
        'pf_prod_type'
                        ]


    def __init__(self, 
                 my_name, 
                 objs_list, 
                 attr_tuples, 
                 mode="timer", 
                 update_interval=1.0,
                 ranked_list=False):


        super().__init__()


        self.objs_list = objs_list
        self.mode = mode.lower() 
        self.update_interval = update_interval  

        self.ranked_list = ranked_list          
        
        self.my_prod_type = 'best_of'
        self.my_fi_name = 'b/o ' + my_name
        
        for attr in self.consensus_attr_list:
            setattr(self, attr, self._consensus_attr(attr))
         
        self.mkt_attr_tuples = attr_tuples
        for attr, agg_name in self.mkt_attr_tuples:
            setattr(self, attr, None)
            setattr(self, attr + '_name', None)

        self._running = False
        
        # Market-update mode
        if self.mode == "auto":
            for obj in self.objs_list:
                obj.subscribers.append(self)


    def _consensus_attr(self, attr_name):
        values = {getattr(obj, attr_name, None) for obj in self.objs_list}
        return values.pop() if len(values) == 1 else "multi"


    async def run_timer(self):  # if self.mode == 'timer'
        self._running = True
        while self._running:
            self.update_best_of()
            #strat.on_best_of_update()
            await asyncio.sleep(self.update_interval)


    def stop_timer(self):  # if self.mode == 'timer'
        self._running = False


    def update_subscriber_data(self, obj):  # if self.mode == 'auto'
        if self.ranked_list:
            self.update_best_of_ranked()
        else:
            self.update_best_of_best_only()
            
        for subscriber in self.subscribers:
            subscriber.update_subscriber_data()
        

    def update_best_of_ranked(self):
        for attr, agg_fn in self.mkt_attr_tuples:

            candidates = [
                (getattr(obj, attr), obj)
                for obj in self.objs_list
                if not pd.isna(getattr(obj, attr, np.nan))
            ]

            ranked = sorted(
                candidates,
                key=lambda x: x[0],
                reverse=agg_fn is max
            )

            setattr(self, attr + "_ranked_amts_list", [amt for amt, obj in ranked])
            setattr(self, attr + "_ranked_objs_list", [obj for amt, obj in ranked])  


    def update_best_of_best_only(self):
        for attr, agg_fn in self.mkt_attr_tuples:

            candidates = []

            for obj in self.objs_list:
                val = getattr(obj, attr, np.nan)

                if not pd.isna(val):                    
                    candidates.append((val, obj))

            if not candidates:
                best_amt = None
                best_obj = None

            else:
                best_amt = agg_fn(val for val, obj in candidates)

                best_obj = [
                    obj for val, obj in candidates if val == best_amt
                ][0]

            setattr(self, attr, best_amt)
            setattr(self, attr + '_obj', best_obj)  
            
