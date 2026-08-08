
import pandas as pd

from stat_arb_prep import stat_arb_prep
from stat_arb_analysis import stat_arb_analysis
from stat_arb_comp_stats import stat_arb_comp_stats


# ============================================================
# USER INPUT
# ============================================================

etf_group = "real_estate"

suffix = "2026"

moving_average_window = 20

comm_per_share = 0.005

dollar_constant = 100_000


# ============================================================
# CHOOSE DATES
# ============================================================

dates_dict = {"2025" : ["2025-01-02", "2025-12-15"],
              "2026" : ["2026-01-02", "2026-07-31"]}

dates_list = dates_dict[suffix]

start_date = pd.Timestamp(dates_list[0])
end_date = pd.Timestamp(dates_list[1])


# ============================================================
# CHOOSE ETFs
# ============================================================

etf_group_dict = {"agg"         : ['SCHZ', 'SPAB', 'IUSB', 'BND', 'AGG'],
                  "ca_munis"    : ['CMF', 'VTEC'],
                  "converts"    : ['CWB', 'ICVT'],
                  "corps"       : ['SPBO', 'USIG', 'VTC', 'CORP'],
                  "em_mkts"     : ['VWOB', 'EMB'],
                  "faln_angls"  : ['FALN', 'ANGL'],
                  "hi_yld"      : ['SPHY', 'SCYB', 'HYLB', 'USHY', 'HYG', 'JNK'],
                  "intl_agg"    : ['BNDX', 'IAGG'],
                  "intl_tsy"    : ['BWX', 'IGOV'],
                  "lt_corps"    : ['SPLB', 'IGLB', 'VCLT'],
                  "lt_tsy"      : ['SPTL', 'SCHQ', 'VGLT'],
                  "lt_tsy2"     : ['SPTL', 'SCHQ', 'VGLT', 'TLT'],                    
                  "mortgages"   : ['SPMB', 'VMBS', 'MBB'],
                  "munis"       : ['TFI', 'VTEB', 'MUB'],
                  "prefs"       : ['PFFD', 'PFF'],
                  "real_estate" : ['SCHH', 'USRT']}

sorted_etf_list = etf_group_dict[etf_group]
anchor_etf = sorted_etf_list[-1]


# ============================================================
# CHOOSE LIMITS
# ============================================================

small_limits = [0.0001, 0.0010, 0.0001]
big_limits   = [0.0005, 0.0050, 0.0005]

limit_dict = {"agg"         : small_limits,
              "ca_munis"    : big_limits,
              "converts"    : big_limits,
              "corps"       : small_limits,
              "em_mkts"     : small_limits,
              "faln_angls"  : big_limits,
              "hi_yld"      : small_limits,
              "intl_agg"    : small_limits,
              "intl_tsy"    : small_limits,
              "lt_corps"    : small_limits,
              "lt_tsy"      : small_limits,
              "lt_tsy2"     : small_limits,                    
              "mortgages"   : big_limits,
              "munis"       : big_limits,
              "prefs"       : big_limits,
              "real_estate" : small_limits}

limit_list = limit_dict[etf_group]


# ============================================================
# START PROGRAM
# ============================================================

print()

df= stat_arb_prep(suffix=suffix,
                  start_date=start_date,
                  end_date=end_date,
                  moving_avg_window=20,
                  comm_per_share=0.005,
                  sorted_etf_list=sorted_etf_list,
                  anchor_etf=anchor_etf)

print("finished stat_arb_prep")

stat_arb_analysis(df=df,
                  etf_group=etf_group, 
                  suffix=suffix,
                  sorted_etf_list=sorted_etf_list,
                  anchor_etf=anchor_etf,
                  moving_avg_window=20,
                  comm_per_share=0.005,
                  dollar_constant=100_000,
                  limit_list=limit_list)

print("finished stat_arb_analysis")

stat_arb_comp_stats(etf_group=etf_group, 
                    suffix=suffix,
                    moving_avg_window=20)

print("finished stat_arb_comp_stats")
print()
