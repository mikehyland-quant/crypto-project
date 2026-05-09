#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from fin_insts.tradable.Class_FI_Equity import Equity
from fin_insts.tradable.Class_FI_Future import Future
#from fin_insts.tradable.Class_FI_Option import Option
from fin_insts.tradable.Class_FI_Spot import Spot


# In[1]:


def make_single_leg_fin_insts(df):   
    rows = df[df['my_prod_type'] == 'spot']
    s_objs = [Spot(row) for row in rows.itertuples(index=False)]

    rows = df[df['my_prod_type'] == 'equity']
    e_objs = [Equity(row) for row in rows.itertuples(index=False)]

    rows = df[df['my_prod_type'] == 'future']
    f_objs = [Future(row) for row in rows.itertuples(index=False)]

    #rows = merged_df[merged_df['my_prod_type'] == 'option']
    #o_objs = [Option(row) for row in rows.itertuples(index=False)]

    objs_list = s_objs + e_objs + f_objs # + o_objs
    
    return objs_list