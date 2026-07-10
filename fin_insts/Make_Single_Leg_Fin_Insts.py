
from input_output.Class_InputOutput import InputOutput
io = InputOutput()

from fin_insts.tradable.Class_FI_Equity import Equity
from fin_insts.tradable.Class_FI_Future import Future
from fin_insts.tradable.Class_FI_Option import Option
from fin_insts.tradable.Class_FI_Spot   import Spot


def get_db_df():

    wb_name  = '2026 Fin Inst Database.xlsx'
    ws_name  = 'Static Data Table'
    tbl_name = 'static_data_table'

    wb, ws = io.set_xw_book_and_sheet(wb_name, ws_name)
    
    db_df = io.get_xw_df(ws, tbl_name, table=True)
    # print(db_df)

    return db_df


def make_single_leg_fin_insts(df):
    rows = df[df['my_prod_type'] == 'spot']
    s_objs = [Spot(row) for row in rows.itertuples(index=False)]

    rows = df[df['my_prod_type'] == 'equity']
    e_objs = [Equity(row) for row in rows.itertuples(index=False)]

    rows = df[df['my_prod_type'] == 'future']
    f_objs = [Future(row) for row in rows.itertuples(index=False)]

    rows = df[df['my_prod_type'] == 'option']
    o_objs = [Option(row) for row in rows.itertuples(index=False)]

    objs_list = s_objs + e_objs + f_objs + o_objs
    
    return objs_list
 


def get_db_df_and_make_single_leg_fin_insts(df):
    db_df = get_db_df()
    # print(db_df)

    df = df.merge(db_df, how='left', on=['my_fi_name', 'my_pf_name'])
    # print(df)

    return make_single_leg_fin_insts(df)


