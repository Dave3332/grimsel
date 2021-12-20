# -*- coding: utf-8 -*-
"""
Created on Tue Jan 29 08:35:09 2019

@author: user
"""

# execute primary input data building script
# import build_input_res_heating
print('####################')
print('BUILDING INPUT DATA FOR INCLUDING ENERGY EFFICIENCY AND DHW BOILERS')
print('####################')
import os
import itertools
import hashlib

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import grimsel.auxiliary.sqlutils.aux_sql_func as aql
import datetime

import seaborn as sns

from grimsel.auxiliary.aux_general import print_full
from grimsel.auxiliary.aux_general import translate_id

import config_local as conf
from grimsel.auxiliary.aux_general import expand_rows

base_dir = conf.BASE_DIR
data_path = conf.PATH_CSV
data_path_prv = conf.PATH_CSV + '_res_heating'

seed = 2

np.random.seed(seed)

db = conf.DATABASE
sc = conf.SCHEMA

#db = 'grimsel_1'
#sc = 'lp_input_ht_ee_dsm'

def append_new_rows(df, tb):

    list_col = list(aql.get_sql_cols(tb, sc, db).keys())

    aql.write_sql(df[list_col], db=db, sc=sc, tb=tb, if_exists='append')

def del_new_rows(ind, tb, df):

    del_list = df[ind].drop_duplicates()

    for i in ind:
        del_list[i] = '%s = '%i + del_list[i].astype(str)

    del_str = ' OR '.join(del_list.apply(lambda x: '(' + ' AND '.join(x) + ')', axis=1))

    exec_strg = '''
                DELETE FROM {sc}.{tb}
                WHERE {del_str}
                '''.format(tb=tb, sc=sc, del_str=del_str)
    aql.exec_sql(exec_strg, db=db)

def replace_table(df, tb):
    print('Replace table %s'%tb)
#    list_col = list(aql.get_sql_cols(tb, sc, db).keys())
    
    aql.write_sql(df, db=db, sc=sc, tb=tb, if_exists='replace')
 

def append_new_cols(df, tb):
#
    list_col = list(aql.get_sql_cols(tb, sc, db).keys())
    
    col_new = dict.fromkeys((set(df.columns.tolist()) - set(list_col)))
    for key, value in col_new.items():
        col_new[key] = 'DOUBLE PRECISION'
#    col_new = dict.fromkeys((set(list_col[0].columns.tolist()) - set(list_col)),1)
    
    aql.add_column(df_src=df,tb_tgt=[sc,tb],col_new=col_new,on_cols=list_col, db=db)
#    exec_strg = '''
#                AlTER
#                DELETE FROM {sc}.{tb}
#                WHERE {del_str}
#                '''.format(tb=tb, sc=sc, del_str=del_str)
#    aql.exec_sql(exec_strg, db=db)
#    
#    aql.write_sql(df[list_col], db=db, sc=sc, tb=tb, if_exists='append')
#
#aql.exec_sql('''
#             ALTER TABLE lp_input_archetypes.profdmnd
#            DROP CONSTRAINT profdmnd_pkey,
#            DROP CONSTRAINT profdmnd_dmnd_pf_id_fkey;
#             ''', db=db)
#aql.exec_sql('''
#             ALTER TABLE lp_input_ht.def_node
#             ALTER COLUMN nd TYPE varchar(20);
#             ''', db=db)

# %% DHW loads

dfload_arch_dhw = pd.read_csv(base_dir +  '/ee_dhw/demand/dmnd_archetypes_dhw_dec.csv')
dfload_arch_dhw['DateTime'] = dfload_arch_dhw['DateTime'].astype('datetime64[ns]')

# dfload_arch_dhw = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_dhw_dec')

dferg_arch_dhw = dfload_arch_dhw.groupby('nd_id')['erg_tot'].sum().reset_index()
dferg_arch_dhw['nd_id_new'] = dferg_arch_dhw.nd_id

dfload_arch_dhw_central = pd.read_csv(base_dir +  '/ee_dhw/demand/dmnd_archetypes_dhw_cen.csv')
# dfload_arch_dhw_central = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_dhw_cen')

dferg_arch_dhw_central = dfload_arch_dhw_central.groupby('nd_id')['erg_tot'].sum().reset_index()
dferg_arch_dhw_central['nd_id_new'] = dferg_arch_dhw_central.nd_id

# dfload_dhw_elec = pd.read_csv(os.path.join(base_dir,'../heat_dhw/dhw_el_load_night_charge.csv'),sep=';')
# dfload_dhw_elec['DateTime'] = pd.to_datetime(dfload_dhw_elec.DateTime)

# dfload_dhw_remove = pd.merge(dfload_arch_dhw,dfload_dhw_elec.drop(columns='dhw_mw'), on='DateTime' )
# dfload_dhw_remove = pd.merge(dfload_dhw_remove,dferg_arch_dhw.drop(columns='nd_id_new').rename(columns={'erg_tot':'erg_year'}),on='nd_id'
#                              ).assign(load_dhw_rem = lambda x: x.dhw_rel_load*x.erg_year)


# %% Central DHW loads
#Bau load
dfload_arch_dhw_central = pd.read_csv(base_dir +  '/ee_dhw/demand/dmnd_archetypes_dhw_cen.csv')
# dfload_arch_dhw_central = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_dhw_cen')

dfload_arch_dhw_central['erg_tot'] = dfload_arch_dhw_central.erg_tot/24 # MWh -> MW
dfload_arch_dhw_central['erg_tot_retr_1pc'] = dfload_arch_dhw_central.erg_tot # here already in MW previous line
dfload_arch_dhw_central['erg_tot_retr_2pc'] = dfload_arch_dhw_central.erg_tot # here already in MW previous line

dfload_arch_dhw_central = dfload_arch_dhw_central.set_index('DateTime')
dfload_arch_dhw_central.index = pd.to_datetime(dfload_arch_dhw_central.index)

#fossil  load
dfload_arch_dhw_central_fossil = pd.read_csv(base_dir +  '/ee_dhw/demand/dmnd_archetypes_dhw_cen_fossil.csv')
# dfload_arch_dhw_central_fossil = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_dhw_cen_fossil')

dfload_arch_dhw_central_fossil['erg_tot_fossil'] = dfload_arch_dhw_central_fossil.erg_tot/24 # MWh -> MW
dfload_arch_dhw_central_fossil['erg_tot_retr_1pc_fossil'] = dfload_arch_dhw_central_fossil.erg_tot/24 # MWh -> MW
dfload_arch_dhw_central_fossil['erg_tot_retr_2pc_fossil'] = dfload_arch_dhw_central_fossil.erg_tot/24 # MWh -> MW

dfload_arch_dhw_central_fossil = dfload_arch_dhw_central_fossil.drop(columns='erg_tot')

dfload_arch_dhw_central_fossil = dfload_arch_dhw_central_fossil.set_index('DateTime')
dfload_arch_dhw_central_fossil.index = pd.to_datetime(dfload_arch_dhw_central_fossil.index)


dfload_arch_dhw_central = dfload_arch_dhw_central.reset_index()
dfload_arch_dhw_central = pd.merge(dfload_arch_dhw_central,dfload_arch_dhw_central_fossil,on=['index','doy','nd_id'])

dfload_arch_dhw_central = dfload_arch_dhw_central.set_index('DateTime')
dfload_arch_dhw_central.index = pd.to_datetime(dfload_arch_dhw_central.index)


# %% Seperation for aw and bw heat pumps DHW central

dfload_arch_dhw_central_aw = dfload_arch_dhw_central.copy()
dfload_arch_dhw_central_aw[['erg_tot', 'erg_tot_fossil',
      'erg_tot_retr_1pc', 'erg_tot_retr_2pc', 'erg_tot_retr_1pc_fossil',
      'erg_tot_retr_2pc_fossil']] *= 0.615
dfload_arch_dhw_central_ww = dfload_arch_dhw_central.copy()
dfload_arch_dhw_central_ww[['erg_tot', 'erg_tot_fossil',
      'erg_tot_retr_1pc', 'erg_tot_retr_2pc', 'erg_tot_retr_1pc_fossil',
      'erg_tot_retr_2pc_fossil']] *= 0.385
                  


# %% EE loads

dfload_arch_ee_sfh = pd.read_csv(base_dir +  '/ee_dhw/demand/dmnd_archetypes_ee_sfh_diff.csv')
dfload_arch_ee_sfh['DateTime'] = dfload_arch_ee_sfh['DateTime'].astype('datetime64[ns]')
dfload_arch_ee_mfh = pd.read_csv(base_dir +  '/ee_dhw/demand/dmnd_archetypes_ee_mfh_diff.csv')
dfload_arch_ee_mfh['DateTime'] = dfload_arch_ee_mfh['DateTime'].astype('datetime64[ns]')

# dfload_arch_ee_sfh = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_ee_sfh_diff')
# dfload_arch_ee_mfh = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_ee_mfh_diff')

dfload_arch_ee = pd.concat([dfload_arch_ee_sfh,dfload_arch_ee_mfh])

dferg_arch_ee = dfload_arch_ee.groupby('nd_id')['erg_diff'].sum().reset_index()
# dferg_arch_ee['nd_id_new'] = dferg_arch_dhw.nd_id

# %% COP profile
#
#dfcop_pr_35 = aql.read_sql('grimsel_1', 'profiles_raw','cop_35')
dfcop_pr_60 = pd.read_csv(base_dir + '/ee_dhw/cop/cop_60.csv')
# dfcop_pr_60 = aql.read_sql('grimsel_1', 'profiles_raw','cop_60')
#
dfcop_pr_60_dhw = dfcop_pr_60 
dfcop_pr_60_dhw['pp_id'] = dfcop_pr_60.pp_id.str.replace('HP','DHW')
#dfcop_pr_35 = dfcop_pr_35.set_index('DateTime')
#dfcop_pr_35.index = pd.to_datetime(dfcop_pr_35.index)
# dfcop_pr_60 = dfcop_pr_60.set_index('DateTime')
# dfcop_pr_60.index = pd.to_datetime(dfcop_pr_60.index)
dfcop_pr_60_dhw = dfcop_pr_60_dhw.set_index('DateTime')
dfcop_pr_60_dhw.index = pd.to_datetime(dfcop_pr_60_dhw.index)
#
#dfcop_pr_35['hy'] = 24*dfcop_pr_35.doy - 24
dfcop_pr_60_dhw['hy'] = 24*dfcop_pr_60_dhw.doy - 24
# %% ~~~~~~~~~~~~~~~~~~   DEF_NODE
df_def_node_0 = pd.read_csv(data_path_prv + '/def_node.csv')
# df_def_node_0 = aql.read_sql(db, sc, 'def_node')

df_def_node = df_def_node_0.copy()

df_nd_res_el = df_def_node_0.loc[~df_def_node_0.nd.str.contains('HT') & df_def_node_0.nd.str.contains('SFH|MFH')]
df_nd_not_res = df_def_node_0.loc[~df_def_node_0.nd.str.contains('MFH|SFH')]
df_nd_arch_el = df_def_node_0.loc[~df_def_node_0.nd.str.contains('HT') & df_def_node_0.nd.str.contains('SFH|MFH|OCO|IND')]
df_nd_arch_ht = df_def_node_0.loc[df_def_node_0.nd.str.contains('HT')]
df_nd_ch0_el = df_def_node_0.loc[df_def_node_0.nd.str.contains('CH0')]


dict_nd_res_el = df_nd_res_el.set_index('nd')['nd_id'].to_dict()
dict_nd_arch_ht = df_nd_arch_ht.set_index('nd')['nd_id'].to_dict()


# %% ~~~~~~~~~~~~~~~~~~~~~~~ DEF_PP_TYPE

df_def_pp_type_0 = pd.read_csv(data_path_prv + '/def_pp_type.csv')
# df_def_pp_type_0 = aql.read_sql(db, sc, 'def_pp_type')

df_def_pp_type = df_def_pp_type_0.copy().head(0)

for npt, pt, cat, color in ((0, 'DHW_BO_SFH', 'DHW_BOILER_SFH', '#D9F209'),
                            (1, 'DHW_BO_MFH', 'DHW_BOILER_MFH', '#D9F209'),
                            (2, 'DHW_STO_SFH', 'DHW_STORAGE_SFH', '#28A503'),
                            (3, 'DHW_STO_MFH', 'DHW_STORAGE_MFH', '#1A6703'),
                            (4, 'DHW_AW_SFH', 'DHW_HEATPUMP_AIR_SFH', '#F2D109'),
                            (5, 'DHW_WW_SFH', 'DHW_HEATPUMP_WAT_SFH', '#F2D109'),
                            (6, 'DHW_AW_MFH', 'DHW_HEATPUMP_AIR_MFH', '#F2D109'),
                            (7, 'DHW_WW_MFH', 'DHW_HEATPUMP_WAT_MFH', '#F2D109'),
#                            (8, 'STO_HT_SFH', 'HEAT_STORAGE_SFH', '#F2D109'),
#                            (9, 'STO_HT_MFH', 'HEAT_STORAGE_MFH', '#F2D109'),):
#                            (10, 'STO_CAES_CH0', 'NEW_STORAGE_CAES_CH0', '#D9F209')
                            ):

    df_def_pp_type.loc[npt] = (npt, pt, cat, color)


df_def_pp_type.loc[:,'pt_id'] = np.arange(0, len(df_def_pp_type)) + df_def_pp_type_0.pt_id.max() + 1



# %% ~~~~~~~~~~~~~~~~~~~~~~ DEF_FUEL for DHW

# 
df_def_fuel_0 = pd.read_csv(data_path_prv + '/def_fuel.csv')
# df_def_fuel_0 = aql.read_sql(db, sc, 'def_fuel')

df_def_fuel = df_def_fuel_0.copy().head(0)

for nfl, fl, co2_int, ca, constr, color in ((0, 'ca_dhw', 0,0,0, 'p'),
                                           (1, 'dhw_storage', 0,0,0, 'r'),
                                            (2, 'ca_dhw_aw', 0,0,0, 'r'),
                                            (3, 'ca_dhw_ww', 0,0,0, 'r'),
                                            ):
#                

    df_def_fuel.loc[nfl] = (nfl, fl, co2_int, ca, constr, color)


df_def_fuel.loc[:,'fl_id'] = np.arange(0, len(df_def_fuel)) + df_def_fuel_0.fl_id.max() + 1

# %% ~~~~~~~~~~~~~~~~~~~~~~ DEF_ENCAR for DHW

# 
df_def_encar_0 = pd.read_csv(data_path_prv + '/def_encar.csv')
# df_def_encar_0 = aql.read_sql(db, sc, 'def_encar')

df_def_encar = df_def_encar_0.copy().head(0)

for nca, fl_id, ca in ((0, 27, 'HW'),
                       (1, 29, 'HA'),
                       (2, 30, 'HB'),
                       ):
    
    df_def_encar.loc[nca] = (nca, fl_id, ca)

df_def_encar.loc[:,'ca_id'] = np.arange(0, len(df_def_encar)) + df_def_encar_0.ca_id.max() + 1


# %% ~~~~~~~~~~~~~~~~~~~~~~~ DEF_PLANT


df_def_plant_0 = pd.read_csv(data_path_prv + '/def_plant.csv')
# df_def_plant_0 = aql.read_sql(db, sc, 'def_plant')


df_pp_add_arch = pd.DataFrame(df_nd_res_el.nd).rename(columns={'nd': 'nd_id'})

df_pp_add_1 = df_pp_add_arch.nd_id.str.slice(stop=3)
df_pp_add = pd.DataFrame()

#TO do here maybe add different boilers storage 
for sfx, fl_id, pt_id, set_1 in [('_DHW_BO', 'ca_electricity', 'DHW_BO_', ['set_def_pp']),
                                 ('_DHW_STO', 'dhw_storage', 'DHW_STO_', ['set_def_st']),

                                 ]:

    new_pp_id = df_def_plant_0.pp_id.max() + 1
    data = dict(pp=df_pp_add_arch + sfx,
                fl_id=fl_id, pt_id=pt_id + df_pp_add_1 , pp_id=np.arange(new_pp_id, new_pp_id + len(df_pp_add_arch)),
                **{st: 1 if st in set_1 else 0 for st in [c for c in df_def_plant_0.columns if 'set' in c]})

    df_pp_add = df_pp_add.append(df_pp_add_arch.assign(**data), sort=True)

df_pp_add.pp_id = np.arange(0, len(df_pp_add)) + df_pp_add.pp_id.min()


df_pp_add_ht = pd.DataFrame(df_nd_arch_ht.nd).rename(columns={'nd': 'nd_id'})
df_pp_add_2 = df_pp_add_ht.nd_id.str.slice(stop=3)


for sfx, fl_id, pt_id, set_1 in [
                                  ('_DHW_AW', 'ca_electricity', 'DHW_AW_', ['set_def_pp']),
                                 ('_DHW_WW', 'ca_electricity', 'DHW_WW_', ['set_def_pp']),
                                ]:

    new_pp_id = df_def_plant_0.pp_id.max() + 1
    data = dict(pp=df_pp_add_ht + sfx,
                fl_id=fl_id, pt_id=pt_id + df_pp_add_2 , pp_id=np.arange(new_pp_id, new_pp_id + len(df_pp_add_ht)),
                **{st: 1 if st in set_1 else 0 for st in [c for c in df_def_plant_0.columns if 'set' in c]})

    df_pp_add = df_pp_add.append(df_pp_add_ht.assign(**data), sort=True)

df_pp_add.pp_id = np.arange(0, len(df_pp_add)) + df_pp_add.pp_id.min()


df_def_plant = df_pp_add[df_def_plant_0.columns].reset_index(drop=True)

for df, idx in [(pd.concat([df_def_fuel_0,df_def_fuel]), 'fl'), (df_def_pp_type, 'pt'), (pd.concat([df_def_node_0]), 'nd')]:

    df_def_plant, _ = translate_id(df_def_plant, df, idx)

#df_def_plant_new = pd.concat([df_def_plant_0,df_def_plant]).reset_index(drop=True)
# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DEF_PROFILE

df_def_profile_0 = pd.read_csv(data_path_prv + '/def_profile.csv')
# df_def_profile_0 = aql.read_sql(db, sc, 'def_profile')

## COP profile 
df_def_profile_cop_60 = df_nd_arch_ht.nd.copy().rename('primary_nd').reset_index()
df_def_profile_cop_60['pf'] = 'cop_60_' + df_def_profile_cop_60.primary_nd
df_def_profile_cop_60['pf_id'] = df_def_profile_cop_60.index.rename('pf_id') + df_def_profile_0.pf_id.max() + 1
df_def_profile_cop_60 = df_def_profile_cop_60[df_def_profile_0.columns]

# Demand profile decentral DHW
df_def_profile_dmnd_dhw = df_nd_res_el.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd_dhw['pf'] = 'demand_DHW_' + df_def_profile_dmnd_dhw.primary_nd
df_def_profile_dmnd_dhw['pf_id'] = df_def_profile_dmnd_dhw.index.rename('pf_id') + df_def_profile_cop_60.pf_id.max() + 1
df_def_profile_dmnd_dhw = df_def_profile_dmnd_dhw[df_def_profile_0.columns]

# Demand profiles heat A/W and W/W
#
df_def_profile_dmnd_dhw_aw = df_nd_arch_ht.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd_dhw_aw['pf'] = 'demand_DHW_AW_' + df_def_profile_dmnd_dhw_aw.primary_nd
df_def_profile_dmnd_dhw_aw['pf_id'] = df_def_profile_dmnd_dhw_aw.index.rename('pf_id') + df_def_profile_dmnd_dhw.pf_id.max() + 1
df_def_profile_dmnd_dhw_aw = df_def_profile_dmnd_dhw_aw[df_def_profile_0.columns]

df_def_profile_dmnd_dhw_ww = df_nd_arch_ht.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd_dhw_ww['pf'] = 'demand_DHW_WW_' + df_def_profile_dmnd_dhw_ww.primary_nd
df_def_profile_dmnd_dhw_ww['pf_id'] = df_def_profile_dmnd_dhw_ww.index.rename('pf_id') + df_def_profile_dmnd_dhw_aw.pf_id.max() + 1
df_def_profile_dmnd_dhw_ww = df_def_profile_dmnd_dhw_ww[df_def_profile_0.columns]
#

# Demand profile for EE

df_def_profile_dmnd_ee_2035 = df_nd_res_el.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd_ee_2035['pf'] = 'demand_EL_' + df_def_profile_dmnd_ee_2035.primary_nd + '_diff_2035_2015'
df_def_profile_dmnd_ee_2035['pf_id'] = df_def_profile_dmnd_ee_2035.index.rename('pf_id') + df_def_profile_dmnd_dhw_ww.pf_id.max() + 1
df_def_profile_dmnd_ee_2035 = df_def_profile_dmnd_ee_2035[df_def_profile_0.columns]


df_def_profile_dmnd_ee_2050 = df_nd_res_el.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd_ee_2050['pf'] = 'demand_EL_' + df_def_profile_dmnd_ee_2050.primary_nd + '_diff_2050_2015'
df_def_profile_dmnd_ee_2050['pf_id'] = df_def_profile_dmnd_ee_2050.index.rename('pf_id') + df_def_profile_dmnd_ee_2035.pf_id.max() + 1
df_def_profile_dmnd_ee_2050 = df_def_profile_dmnd_ee_2050[df_def_profile_0.columns]

df_def_profile_dmnd_ee_best_2035 = df_nd_res_el.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd_ee_best_2035['pf'] = 'demand_EL_' + df_def_profile_dmnd_ee_best_2035.primary_nd + '_diff_best_2035_2015'
df_def_profile_dmnd_ee_best_2035['pf_id'] = df_def_profile_dmnd_ee_best_2035.index.rename('pf_id') + df_def_profile_dmnd_ee_2050.pf_id.max() + 1
df_def_profile_dmnd_ee_best_2035 = df_def_profile_dmnd_ee_best_2035[df_def_profile_0.columns]


#A/W and W/W
# df_def_profile = df_def_profile_dmnd_dhw

df_def_profile = pd.concat([df_def_profile_cop_60,df_def_profile_dmnd_dhw,
                            df_def_profile_dmnd_dhw_aw,df_def_profile_dmnd_dhw_ww,
                            df_def_profile_dmnd_ee_2035,df_def_profile_dmnd_ee_2050,
                            df_def_profile_dmnd_ee_best_2035
                            ], axis=0)
df_def_profile = df_def_profile.reset_index(drop=True)
    
df_def_profile



# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ NODE_ENCAR for DHW

df_node_encar_0 = pd.read_csv(data_path_prv + '/node_encar.csv')
# df_node_encar_0 = aql.read_sql(db, sc, 'node_encar')

df_ndca_add_dhw_decentral = (dferg_arch_dhw.loc[dferg_arch_dhw.nd_id_new.isin(df_nd_res_el.nd), ['nd_id_new', 'erg_tot']]
                         .rename(columns={'erg_tot': 'dmnd_sum', 'nd_id_new': 'nd_id'}))

df_ndca_add_dhw_central = (dferg_arch_dhw_central.loc[dferg_arch_dhw_central.nd_id_new.isin(df_nd_arch_ht.nd), ['nd_id_new', 'erg_tot']]
                         .rename(columns={'erg_tot': 'dmnd_sum', 'nd_id_new': 'nd_id'}))

data_3 = dict(vc_dmnd_flex=0, ca_id=3, grid_losses=0, grid_losses_absolute=0)
data_4 = dict(vc_dmnd_flex=0, ca_id=4, grid_losses=0, grid_losses_absolute=0)
data_5 = dict(vc_dmnd_flex=0, ca_id=5, grid_losses=0, grid_losses_absolute=0)

df_node_encar_dhw = df_ndca_add_dhw_decentral.assign(**data_3).reindex(columns=df_node_encar_0.columns).reset_index(drop=True)
df_node_encar_dhw_aw = df_ndca_add_dhw_central.assign(**data_4).reindex(columns=df_node_encar_0.columns).reset_index(drop=True)
df_node_encar_dhw_ww = df_ndca_add_dhw_central.assign(**data_5).reindex(columns=df_node_encar_0.columns).reset_index(drop=True)

df_node_encar_dhw = pd.merge(df_node_encar_dhw, df_def_profile_dmnd_dhw, left_on='nd_id', right_on='primary_nd', how='inner')
df_node_encar_dhw_aw = pd.merge(df_node_encar_dhw_aw, df_def_profile_dmnd_dhw_aw, left_on='nd_id', right_on='primary_nd', how='inner')
df_node_encar_dhw_ww = pd.merge(df_node_encar_dhw_ww, df_def_profile_dmnd_dhw_ww, left_on='nd_id', right_on='primary_nd', how='inner')


df_node_encar_dhw = pd.concat([df_node_encar_dhw,df_node_encar_dhw_aw,df_node_encar_dhw_ww]).reset_index(drop=True)


list_dmnd = [c for c in df_node_encar_dhw if 'dmnd_sum' in c]

df_node_encar_dhw = df_node_encar_dhw.assign(**{c: df_node_encar_dhw.dmnd_sum
                                        for c in list_dmnd})
#df_node_encar_dhw.update(df_node_encar_dhw.loc[df_node_encar_dhw.ca_id==0].assign(**{c: 0
#                                        for c in list_dmnd}))


df_node_encar_dhw['dmnd_pf_id'] = df_node_encar_dhw.pf
df_node_encar_dhw = df_node_encar_dhw.loc[:, df_node_encar_0.columns]

for df, idx in [(df_def_node, 'nd'), (df_def_profile, ['pf', 'dmnd_pf'])]:
    df_node_encar_dhw, _ = translate_id(df_node_encar_dhw, df, idx)

# Energy efficiency
# df_def_profile_dmnd_ee_0 = pd.concat([df_def_profile_dmnd_ee_2035,df_def_profile_dmnd_ee_2050])

# df_ndca_add_ee['dmnd_pf_id'] = 'demand_EL_'+ df_ndca_add_ee.dmnd_pf_id

# df_node_encar_ee = pd.merge(df_ndca_add_ee, df_def_profile_dmnd_ee_0, left_on='dmnd_pf_id', right_on='pf')#, how='inner')

# df_node_encar_ee = df_node_encar_ee.loc[:, df_node_encar_0.columns]

# for df, idx in [(df_def_node, 'nd'), (df_def_profile, ['pf', 'dmnd_pf'])]:
#     df_node_encar_ee, _ = translate_id(df_node_encar_ee, df, idx)

#Substract electricity from dhw

df_node_encar_wo_dhw = (df_node_encar_0.set_index('nd_id').loc[:,list_dmnd] - df_node_encar_dhw.set_index('nd_id').loc[:,list_dmnd]).reset_index()
df_node_encar_wo_dhw = df_node_encar_wo_dhw.loc[df_node_encar_wo_dhw.nd_id.isin(dict_nd_res_el.values())].set_index('nd_id')


#df_node_encar_ht = df_node_encar_ht.sort_values(by='ca_id', ascending=False).reset_index(drop=True)
#check if we add a factor for heat load (climate correction) or just retrofit scenario
fct_dmnd_dhw = pd.read_csv(base_dir+'/ee_dhw/demand/dhw_factor_dmnd_future_years_aw_ww.csv',sep=';')
fct_dhw = fct_dmnd_dhw.filter(like='dmnd_sum')
# df_0 = df_node_encar_dhw.copy().loc[df_node_encar_dhw.nd_id.isin(dict_nd_arch_ht.values())].reset_index(drop=True).filter(like='dmnd_sum')*fct_dhw
# # df_node_encar_dhw.loc[df_node_encar_dhw.nd_id.isin(dict_nd_arch_ht.values())].reset_index(drop=True).update(df_0)

# df_node_encar_dhw_cen = df_node_encar_dhw.loc[df_node_encar_dhw.nd_id.isin(dict_nd_arch_ht.values())].reset_index(drop=True)
# df_node_encar_dhw_cen.update(df_0)

df_0 = df_node_encar_dhw.loc[df_node_encar_dhw.ca_id.isin([4,5])].set_index(['nd_id','ca_id']).filter(like='dmnd_sum')
fct_dhw.index = df_0.index
df_0 = df_0*fct_dhw
df_node_encar_dhw_tmp = df_node_encar_dhw.set_index(['nd_id','ca_id'])
df_node_encar_dhw_tmp.update(df_0)
df_node_encar_dhw_tmp = df_node_encar_dhw_tmp.reset_index()
df_node_encar_dhw_cen = df_node_encar_dhw_tmp.loc[df_node_encar_dhw_tmp.ca_id.isin([4,5])].reset_index(drop=True)


df_node_encar_0_wo_dhw = df_node_encar_0.set_index('nd_id')
df_node_encar_0_wo_dhw.update(df_node_encar_wo_dhw)

df_node_encar_dhw_dec = df_node_encar_dhw.loc[df_node_encar_dhw.nd_id.isin(dict_nd_res_el.values())]

df_node_encar_dhw = pd.concat([df_node_encar_0_wo_dhw.reset_index(),df_node_encar_dhw_dec,df_node_encar_dhw_cen])

# df_node_encar_add = pd.concat([df_node_encar_dhw, df_node_encar_ee])
#df_node_encar_dhw = df_node_encar_dhw.set_index('nd_id')

#df_node_encar_dhw.update(df_node_encar_wo_dhw)

df_node_encar_new = df_node_encar_dhw.reset_index(drop=True)
# df_node_encar_new = df_node_encar_add.reset_index(drop=True)



# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PROFDMND for DHW
df_tm_st =pd.read_csv(base_dir+'/ee_dhw/timemap/timestamp_template.csv')
df_tm_st['datetime'] = df_tm_st['datetime'].astype('datetime64[ns]')

# df_tm_st = aql.read_sql(db, 'profiles_raw', 'timestamp_template',filt=[('year', [2015],  '=')])

df_profdmnd_0 = pd.read_csv(data_path_prv + '/profdmnd.csv')
# df_profdmnd_0 = aql.read_sql(db, sc, 'profdmnd')
#df_profdmnd_0 = pd.merge(df_profdmnd_0, df_tm_st[['slot','doy']].rename(columns={'slot':'hy'}), on='hy')

# Decrease DHW in electrical profile
dict_dmnd_pf_res_el = df_def_profile_0.loc[df_def_profile_0.pf.str.contains('EL_MFH|EL_SFH')&~df_def_profile_0.pf.str.contains('HT')]
dict_dmnd_pf_res_el = dict_dmnd_pf_res_el.set_index('pf')['pf_id'].to_dict()
dferg_arch_0 = df_profdmnd_0.groupby('dmnd_pf_id')['value'].sum().reset_index()
df_factor_dmnd = pd.merge(dferg_arch_0.loc[dferg_arch_0.dmnd_pf_id.isin(dict_dmnd_pf_res_el.values())],
                         df_node_encar_new[['dmnd_pf_id','dmnd_sum']], on = 'dmnd_pf_id').assign(
                        factor_dmnd = lambda x: x.dmnd_sum/x.value)

df_profdmnd_0_res_el = pd.merge(df_profdmnd_0.loc[df_profdmnd_0.dmnd_pf_id.isin(dict_dmnd_pf_res_el.values())],
                                                 df_factor_dmnd[['dmnd_pf_id','factor_dmnd']],on='dmnd_pf_id').assign(
                                                         value_wo_dhw = lambda x: x.value * x.factor_dmnd)
df_profdmnd_0_res_el_wo_dhw = df_profdmnd_0_res_el.drop(columns=['value','factor_dmnd']).rename(columns={'value_wo_dhw':'value'})

df_profdmnd_0_other = df_profdmnd_0.loc[~df_profdmnd_0.dmnd_pf_id.isin(dict_dmnd_pf_res_el.values())]

df_profdmnd_0_wo_dhw = pd.concat([df_profdmnd_0_other,df_profdmnd_0_res_el_wo_dhw])

df_dmnd_dhw_add = dfload_arch_dhw.copy()

df_dmnd_dhw_add_aw = dfload_arch_dhw_central_aw.copy()
df_dmnd_dhw_add_ww = dfload_arch_dhw_central_ww.copy()


df_dmnd_dhw_add['ca_id'] = 3
df_dmnd_dhw_add_aw['ca_id'] = 4
df_dmnd_dhw_add_ww['ca_id'] = 5


df_dmnd_dhw_add = pd.merge(df_dmnd_dhw_add, df_def_profile_dmnd_dhw[['pf_id', 'primary_nd']], left_on='nd_id', right_on='primary_nd')
df_dmnd_dhw_add = df_dmnd_dhw_add.rename(columns={'erg_tot': 'value', 'pf_id': 'dmnd_pf_id'})
df_dmnd_dhw_add['nd_id'] = df_dmnd_dhw_add.nd_id.replace(dict_nd_res_el)
df_dmnd_dhw_add['doy'] = (df_dmnd_dhw_add.hy + 24)//24

df_dmnd_dhw_add['erg_tot_fossil'] = 0
df_dmnd_dhw_add['erg_tot_retr_1pc'] = 0
df_dmnd_dhw_add['erg_tot_retr_2pc'] = 0
df_dmnd_dhw_add['erg_tot_retr_1pc_fossil'] = 0
df_dmnd_dhw_add['erg_tot_retr_2pc_fossil'] = 0

df_dmnd_dhw_add_aw = pd.merge(df_dmnd_dhw_add_aw, df_def_profile_dmnd_dhw_aw[['pf_id', 'primary_nd']], left_on='nd_id', right_on='primary_nd')
df_dmnd_dhw_add_aw = df_dmnd_dhw_add_aw.rename(columns={'erg_tot': 'value', 'pf_id': 'dmnd_pf_id'})
df_dmnd_dhw_add_aw['nd_id'] = df_dmnd_dhw_add_aw.nd_id.replace(dict_nd_arch_ht)
df_dmnd_dhw_add_aw['hy'] = 24*df_dmnd_dhw_add_aw.doy - 24

#
df_dmnd_dhw_add_ww = pd.merge(df_dmnd_dhw_add_ww, df_def_profile_dmnd_dhw_ww[['pf_id', 'primary_nd']], left_on='nd_id', right_on='primary_nd')
df_dmnd_dhw_add_ww = df_dmnd_dhw_add_ww.rename(columns={'erg_tot': 'value', 'pf_id': 'dmnd_pf_id'})
df_dmnd_dhw_add_ww['nd_id'] = df_dmnd_dhw_add_ww.nd_id.replace(dict_nd_arch_ht)
df_dmnd_dhw_add_ww['hy'] = 24*df_dmnd_dhw_add_ww.doy - 24


df_dmnd_ee_add = dfload_arch_ee.copy()
df_dmnd_ee_add['ca_id'] = 0

df_def_profile_dmnd_ee_2035_new = df_def_profile_dmnd_ee_2035.copy()
df_def_profile_dmnd_ee_2050_new = df_def_profile_dmnd_ee_2050.copy()
df_def_profile_dmnd_ee_best_2035_new = df_def_profile_dmnd_ee_best_2035.copy()

df_def_profile_dmnd_ee_2035_new['primary_nd_new'] = df_def_profile_dmnd_ee_2035_new.primary_nd+'_diff_2035_2015'
df_def_profile_dmnd_ee_2050_new['primary_nd_new'] = df_def_profile_dmnd_ee_2050_new.primary_nd+'_diff_2050_2015'
df_def_profile_dmnd_ee_best_2035_new['primary_nd_new'] = df_def_profile_dmnd_ee_best_2035_new.primary_nd+'_diff_best_2035_2015'

df_def_profile_dmnd_ee = pd.concat([df_def_profile_dmnd_ee_2035_new,df_def_profile_dmnd_ee_2050_new,
                                    df_def_profile_dmnd_ee_best_2035_new])

df_dmnd_ee_add = pd.merge(df_dmnd_ee_add, df_def_profile_dmnd_ee[['pf_id', 'primary_nd_new']], left_on='nd_id', right_on='primary_nd_new')
# df_dmnd_dhw_add_ee = pd.merge(df_dmnd_dhw_add_ee, df_def_profile_dmnd_ee_2050[['pf_id', 'primary_nd']], left_on='nd_id', right_on='primary_nd')

df_dmnd_ee_add = df_dmnd_ee_add.rename(columns={'erg_diff': 'value', 'pf_id': 'dmnd_pf_id'})
df_dmnd_ee_add['nd_id'] = df_dmnd_ee_add.nd_id.replace(dict_nd_res_el)
df_dmnd_ee_add['doy'] = (df_dmnd_ee_add.hy + 24)//24


df_dmnd_add = pd.concat([df_dmnd_dhw_add,df_dmnd_dhw_add_aw,df_dmnd_dhw_add_ww,df_dmnd_ee_add])
#df_profdmnd_dhw = df_dmnd_dhw_add[df_profdmnd_0.columns.tolist()].reset_index(drop=True)
df_profdmnd_add = df_dmnd_add[df_profdmnd_0_wo_dhw.columns.tolist()].reset_index(drop=True)

#df_profdmnd_ht_el = df_dmnd_ht_el_add[df_profdmnd_0.columns.tolist()].reset_index(drop=True)

#df_profdmnd_new = pd.concat([df_profdmnd_0,df_profdmnd_dhw])#,df_profdmnd_ht_el])
df_profdmnd_new = pd.concat([df_profdmnd_0_wo_dhw,df_profdmnd_add])

# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~ PROFPRICE

# --> NO CHANGES!


# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PROFSUPPLY

# --> NO CHANGES!


# %% ~~~~~~~~~~~~~~~~~~~~~~~ PLANT_ENCAR (needs profsupply data)

dict_pp_new = pd.Series(df_def_plant.pp_id.values,index=df_def_plant.pp).to_dict()
#dict_nd_id_all = dict(pd.Series(df_def_node_0.nd_id.values,index=df_def_node_0.nd).to_dict(), **dict_nd_id)
dict_pt_id_all = dict(pd.Series(df_def_pp_type_0.pt_id.values,index=df_def_pp_type_0.pt).to_dict(),
                      **pd.Series(df_def_pp_type.pt_id.values,index=df_def_pp_type.pt))

df_plant_encar = pd.read_csv(data_path_prv + '/plant_encar.csv')
# df_plant_encar = aql.read_sql(db, sc, 'plant_encar')


df_bo_dhw_scen = pd.read_csv(base_dir + '/ee_dhw/dhw_capacity/dhw_pp_bo_cap.csv',sep=';')
df_hp_cen_full_dhw_scen = pd.read_csv(base_dir + '/ee_dhw/dhw_capacity/dhw_pp_hp_full_cap.csv',sep=';')
df_hp_cen_fossil_dhw_scen = pd.read_csv(base_dir + '/ee_dhw/dhw_capacity/dhw_pp_hp_fossil_cap.csv',sep=';')


df_bo_dhw_scen['pp_id'] = df_bo_dhw_scen['pp'].map(dict_pp_new)
df_hp_cen_full_dhw_scen['pp_id'] = df_hp_cen_full_dhw_scen['pp'].map(dict_pp_new)
df_hp_cen_fossil_dhw_scen['pp_id'] = df_hp_cen_fossil_dhw_scen['pp'].map(dict_pp_new)

df_pp_add = df_bo_dhw_scen.drop(columns='pp')
df_pp_add_1 = pd.merge(df_hp_cen_full_dhw_scen,df_hp_cen_fossil_dhw_scen).drop(columns='pp')



df_plant_encar_1 = pd.DataFrame()
df_plant_encar_1 = pd.concat([df_plant_encar, df_pp_add,df_pp_add_1])



df_plant_encar_new = df_plant_encar_1.reset_index(drop=True)#(drop=True)  

# %% ~~~~~~~~~~~~~~~~~~~~ NODE_CONNECT
# --> NO CHANGES!

# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ FUEL_NODE_ENCAR
# --> NO CHANGES!

# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DF_PROFPRICE
#
##df_profprice = aql.read_sql(db, sc, 'profprice') <- NO CHANGE
# %% COP 
#
df_def_cop_pr_60_dhw = dfcop_pr_60_dhw.copy()
for df, idx in [(df_def_plant, 'pp')]:#[(df_def_node, 'nd'), (df_def_profile, ['pf', 'dmnd_pf'])]: 
    df_def_cop_pr_60_dhw, _ = translate_id(df_def_cop_pr_60_dhw, df, idx)

df_def_cop_pr_60_dhw = df_def_cop_pr_60_dhw.rename(columns={'cop_60':'value'})
df_def_cop_pr_60_dhw.drop(columns='index').reset_index().to_csv(data_path + '/def_cop_60_dhw.csv', index=False)

# %%

#df_node_encar_new
#df_profdmnd_new
#df_plant_encar_new

# #list_tb_col = [
# #           (df_plant_encar_new, 'plant_encar', ['pp_id', 'ca_id'])
# #           ]

# list_tb_new = [
# #            (df_def_plant_new, 'def_plant', ['pp_id']),
#            (df_node_encar_new, 'node_encar', ['nd_id', 'ca_id']),
#            (df_profdmnd_new, 'profdmnd', ['dmnd_pf_id']),
#            (df_plant_encar_new, 'plant_encar', ['pp_id', 'ca_id']),
#            ]

# list_tb = [
# #        (df_fuel_node_encar, 'fuel_node_encar', ['nd_id', 'fl_id', 'ca_id']),
# #           (df_node_encar_new, 'node_encar', ['nd_id', 'ca_id']),
# #           (df_profdmnd_new, 'profdmnd', ['dmnd_pf_id']),
# #           (df_profsupply, 'profsupply', ['supply_pf_id']), <-- NO CHANGE
# #           (df_profprice, 'profprice', ['price_pf_id']),, <-- NO CHANGE
# #           (df_node_connect, 'node_connect', ['nd_id', 'nd_2_id']),
# #           (df_plant_encar_new, 'plant_encar', ['pp_id', 'ca_id']),
#            (df_def_plant, 'def_plant', ['pp_id']),
# #           (df_def_node, 'def_node', ['nd_id']),
#            (df_def_encar, 'def_encar', ['ca_id']),
#            (df_def_fuel, 'def_fuel', ['fl_id']), 
#            (df_def_pp_type, 'def_pp_type', ['pt_id']),
#            (df_def_profile, 'def_profile', ['pf_id'])
#            ]

# # tables with foreign keys first
# #df, tb, ind = (df_def_plant, 'def_plant', ['pp_id'])

# #df, tb = (df_def_plant_new, 'def_plant')
# #replace_table(df,tb)
# df, tb = (df_plant_encar_new, 'plant_encar')
# #append_new_cols(df, tb)
# replace_table(df,tb)
# df, tb = (df_node_encar_new, 'node_encar')
# replace_table(df,tb)
# df, tb = (df_profdmnd_new, 'profdmnd')
# replace_table(df,tb)
# #for df, tb, ind in list_tb_col:
# #    print('Replacing table %s'%tb)
# #    append_new_cols(df, tb)


# for df, tb, ind in list_tb:
#     print('Deleting from table %s'%tb)
#     del_new_rows(ind, tb, df)

# # tables with foreign keys last
# for df, tb, ind in reversed(list_tb):
#     print('Appending to table %s'%tb)
#     append_new_rows(df, tb)





# for tb in aql.get_sql_tables(sc, db):
#     print(tb)
#     df = aql.read_sql(db, sc, tb)

#     if 'prof' in tb and 'value' in df.columns:
#         df['value'] = df['value'].round(13)

#     df.to_csv(os.path.join(data_path, '%s.csv'%tb), index=False)



list_tb_app = {
               'def_encar':df_def_encar,
                  'def_pp_type':df_def_pp_type,
                'def_fuel': df_def_fuel,
                'def_plant': df_def_plant,
                'def_profile':df_def_profile,
                }
list_tb_new = {'plant_encar' : df_plant_encar_new,
                    'node_encar' : df_node_encar_new,
                    'profdmnd' : df_profdmnd_new, 
                    }
import glob
csv_files_previous = glob.glob(os.path.join(data_path_prv, "*.csv"))

for f in csv_files_previous:
      
    # read the csv file
    df_prv = pd.read_csv(f)
    table_name = f.split("/")[-1][:-4]
    
    if table_name in list_tb_app.keys():
        df_app = pd.concat([df_prv,list_tb_app[table_name]])
        df_app.to_csv(os.path.join(data_path, '%s.csv'%table_name), index=False)
        print('Table append to previous data:',f.split("/")[-1])
    elif table_name in list_tb_new.keys():
        df_new = list_tb_new[table_name]
        df_new.to_csv(os.path.join(data_path, '%s.csv'%table_name), index=False)
        print('Table new replacing previous data:',f.split("/")[-1])

    else:
        df_prv.to_csv(os.path.join(data_path, '%s.csv'%table_name), index=False)
        print('Tabel no change compare to previous data:',f.split("/")[-1])




