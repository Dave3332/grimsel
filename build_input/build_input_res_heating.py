# -*- coding: utf-8 -*-
"""
Created on Tue Jan 29 08:35:09 2019

@author: user
"""

# build input first with archetype disaggragetion
# import build_input_archetype_disaggr
print('####################')
print('BUILDING INPUT DATA FOR INCLUDING SWISS RESIDENTIAL HEATING')
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
data_path_prv = conf.PATH_CSV + '_archetype_disaggr'

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

exec_strg = '''
               AlTER TABLE {sc}.def_node
              ALTER COLUMN nd TYPE varchar(20);
                '''.format(sc=sc)
# aql.exec_sql(exec_strg, db=db)

# aql.exec_sql('''
#              ALTER TABLE lp_input_paper3.def_node
#              ALTER COLUMN nd TYPE varchar(20);
#              ''', db=db)

# %% Heatin loads
#Bau load
dfload_arch_ht = pd.read_csv(base_dir+'/res_heating/demand/dmnd_archetypes_ht.csv')
# dfload_arch_ht = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_ht')#,filt=[('nd_id', ['CH0'],'!=')])

dfload_arch_ht['erg_tot'] = dfload_arch_ht.erg_tot/1000/24 # kWh -> MWh -> MW

dfload_arch_ht = dfload_arch_ht.set_index('DateTime')
dfload_arch_ht.index = pd.to_datetime(dfload_arch_ht.index)

#fossil  load
dfload_arch_ht_fossil = pd.read_csv(base_dir+'/res_heating/demand/dmnd_archetypes_ht_fossil.csv')
# dfload_arch_ht_fossil = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_ht_fossil')#,filt=[('nd_id', ['CH0'],'!=')])

dfload_arch_ht_fossil['erg_tot_fossil'] = dfload_arch_ht_fossil.erg_tot/1000/24 # kWh -> MWh -> MW
dfload_arch_ht_fossil = dfload_arch_ht_fossil.drop(columns='erg_tot')

dfload_arch_ht_fossil = dfload_arch_ht_fossil.set_index('DateTime')
dfload_arch_ht_fossil.index = pd.to_datetime(dfload_arch_ht_fossil.index)

#retr_1pc load
dfload_arch_ht_retr_1pc = pd.read_csv(base_dir+'/res_heating/demand/dmnd_archetypes_ht_retr_1pc.csv')
# dfload_arch_ht_retr_1pc = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_ht_retr_1pc')#,filt=[('nd_id', ['CH0'],'!=')])

dfload_arch_ht_retr_1pc['erg_tot_retr_1pc'] = dfload_arch_ht_retr_1pc.erg_tot/1000/24 # kWh -> MWh -> MW
dfload_arch_ht_retr_1pc = dfload_arch_ht_retr_1pc.drop(columns='erg_tot')

dfload_arch_ht_retr_1pc = dfload_arch_ht_retr_1pc.set_index('DateTime')
dfload_arch_ht_retr_1pc.index = pd.to_datetime(dfload_arch_ht_retr_1pc.index)

#retr_2pc load
dfload_arch_ht_retr_2pc = pd.read_csv(base_dir+'/res_heating/demand/dmnd_archetypes_ht_retr_2pc.csv')
# dfload_arch_ht_retr_2pc = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_ht_retr_2pc')#,filt=[('nd_id', ['CH0'],'!=')])

dfload_arch_ht_retr_2pc['erg_tot_retr_2pc'] = dfload_arch_ht_retr_2pc.erg_tot/1000/24 # kWh -> MWh -> MW
dfload_arch_ht_retr_2pc = dfload_arch_ht_retr_2pc.drop(columns='erg_tot')

dfload_arch_ht_retr_2pc = dfload_arch_ht_retr_2pc.set_index('DateTime')
dfload_arch_ht_retr_2pc.index = pd.to_datetime(dfload_arch_ht_retr_2pc.index)

#retr_1pc fossil load
dfload_arch_ht_retr_1pc_fossil = pd.read_csv(base_dir+'/res_heating/demand/dmnd_archetypes_ht_retr_1pc_fossil.csv')
# dfload_arch_ht_retr_1pc_fossil = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_ht_retr_1pc_fossil')#,filt=[('nd_id', ['CH0'],'!=')])

dfload_arch_ht_retr_1pc_fossil['erg_tot_retr_1pc_fossil'] = dfload_arch_ht_retr_1pc_fossil.erg_tot/1000/24 # kWh -> MWh -> MW
dfload_arch_ht_retr_1pc_fossil = dfload_arch_ht_retr_1pc_fossil.drop(columns='erg_tot')

dfload_arch_ht_retr_1pc_fossil = dfload_arch_ht_retr_1pc_fossil.set_index('DateTime')
dfload_arch_ht_retr_1pc_fossil.index = pd.to_datetime(dfload_arch_ht_retr_1pc_fossil.index)

#retr_2pc fossil load
dfload_arch_ht_retr_2pc_fossil = pd.read_csv(base_dir+'/res_heating/demand/dmnd_archetypes_ht_retr_2pc_fossil.csv')
# dfload_arch_ht_retr_2pc_fossil = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_ht_retr_2pc_fossil')#,filt=[('nd_id', ['CH0'],'!=')])

dfload_arch_ht_retr_2pc_fossil['erg_tot_retr_2pc_fossil'] = dfload_arch_ht_retr_2pc_fossil.erg_tot/1000/24 # kWh -> MWh -> MW
dfload_arch_ht_retr_2pc_fossil = dfload_arch_ht_retr_2pc_fossil.drop(columns='erg_tot')

dfload_arch_ht_retr_2pc_fossil = dfload_arch_ht_retr_2pc_fossil.set_index('DateTime')
dfload_arch_ht_retr_2pc_fossil.index = pd.to_datetime(dfload_arch_ht_retr_2pc_fossil.index)

dfload_arch_ht = dfload_arch_ht.reset_index()
dfload_arch_ht = pd.merge(dfload_arch_ht,dfload_arch_ht_fossil,on=['index','doy','nd_id'])
dfload_arch_ht = pd.merge(dfload_arch_ht,dfload_arch_ht_retr_1pc,on=['index','doy','nd_id'])
dfload_arch_ht = pd.merge(dfload_arch_ht,dfload_arch_ht_retr_2pc,on=['index','doy','nd_id'])
dfload_arch_ht = pd.merge(dfload_arch_ht,dfload_arch_ht_retr_1pc_fossil,on=['index','doy','nd_id'])
dfload_arch_ht = pd.merge(dfload_arch_ht,dfload_arch_ht_retr_2pc_fossil,on=['index','doy','nd_id'])

dfload_arch_ht = dfload_arch_ht.set_index('DateTime')
dfload_arch_ht.index = pd.to_datetime(dfload_arch_ht.index)



# %%

dferg_arch_ht_0 = dfload_arch_ht.groupby('nd_id')['erg_tot'].sum().reset_index()
dferg_arch_ht = dferg_arch_ht_0.copy()
dferg_arch_ht['erg_tot'] = dferg_arch_ht_0.erg_tot* 24
#dferg_arch_ht = dferg_arch_ht.reset_index()
dferg_arch_ht['nd_id_new'] = dferg_arch_ht.nd_id

dict_nd_ht = dferg_arch_ht.set_index('nd_id')['nd_id_new'].to_dict()

#dfmax_dmnd_arch_ht = dfload_arch_ht.groupby('nd_id')['erg_tot'].max()
#dfmax_dmnd_arch_ht = dfmax_dmnd_arch_ht.reset_index().rename(columns={'erg_tot':'max_dmnd'})
#dfmax_dmnd_arch_ht['nd_id_new'] = dfmax_dmnd_arch_ht.nd_id

# %% Seperation for aw and bw heat pumps demand

dfload_arch_ht_aw = dfload_arch_ht.copy()
dfload_arch_ht_aw[['erg_tot', 'erg_tot_fossil',
       'erg_tot_retr_1pc', 'erg_tot_retr_2pc', 'erg_tot_retr_1pc_fossil',
       'erg_tot_retr_2pc_fossil']] *= 0.615
dfload_arch_ht_ww = dfload_arch_ht.copy()
dfload_arch_ht_ww[['erg_tot', 'erg_tot_fossil',
       'erg_tot_retr_1pc', 'erg_tot_retr_2pc', 'erg_tot_retr_1pc_fossil',
       'erg_tot_retr_2pc_fossil']] *= 0.385
                   


# %% COP profile

# dfcop_pr_35 = aql.read_sql('grimsel_1', 'profiles_raw','cop_35')
# dfcop_pr_60 = aql.read_sql('grimsel_1', 'profiles_raw','cop_60')

dfcop_pr_35 = pd.read_csv(base_dir+'/res_heating/cop/cop_35.csv')
dfcop_pr_60 = pd.read_csv(base_dir+'/res_heating/cop/cop_60.csv')


dfcop_pr_35 = dfcop_pr_35.set_index('DateTime')
dfcop_pr_35.index = pd.to_datetime(dfcop_pr_35.index)
dfcop_pr_60 = dfcop_pr_60.set_index('DateTime')
dfcop_pr_60.index = pd.to_datetime(dfcop_pr_60.index)

dfcop_pr_35['hy'] = 24*dfcop_pr_35.doy - 24
dfcop_pr_60['hy'] = 24*dfcop_pr_60.doy - 24
# %% ~~~~~~~~~~~~~~~~~~   DEF_NODE
color_nd = {'MFH_RUR_HT_0':       '#472503',
            'MFH_RUR_HT_1':       '#472503',
            'MFH_RUR_HT_2':       '#472503',
            'MFH_RUR_HT_3':       '#472503',
            'MFH_SUB_HT_0':       '#041FA3',
            'MFH_SUB_HT_1':       '#041FA3',
            'MFH_SUB_HT_2':       '#041FA3',
            'MFH_SUB_HT_3':       '#041FA3',
            'MFH_URB_HT_0':       '#484A4B',
            'MFH_URB_HT_1':       '#484A4B',
            'MFH_URB_HT_2':       '#484A4B',
            'MFH_URB_HT_3':       '#484A4B',
            'SFH_RUR_HT_0':       '#0A81EE',
            'SFH_RUR_HT_1':       '#0A81EE',
            'SFH_RUR_HT_2':       '#0A81EE',
            'SFH_RUR_HT_3':       '#0A81EE',
            'SFH_SUB_HT_0':       '#6D3904',
            'SFH_SUB_HT_1':       '#6D3904',
            'SFH_SUB_HT_2':       '#6D3904',
            'SFH_SUB_HT_3':       '#6D3904',
            'SFH_URB_HT_0':       '#818789',
            'SFH_URB_HT_1':       '#818789',
            'SFH_URB_HT_2':       '#818789',
            'SFH_URB_HT_3':       '#818789'
            }
col_nd_df = pd.DataFrame.from_dict(color_nd, orient='index').reset_index().rename(columns={'index': 'nd',0:'color'})

df_def_node_0 = pd.read_csv(data_path_prv + '/def_node.csv')
# df_def_node_0 = aql.read_sql(db, sc, 'def_node')
df_nd_add = pd.DataFrame(pd.concat([dferg_arch_ht.nd_id_new.rename('nd'),
                                    ], axis=0)).reset_index(drop=True)

nd_id_max = df_def_node_0.loc[~df_def_node_0.nd.isin(df_nd_add.nd)].nd_id.max()
df_nd_add['nd_id'] = np.arange(0, len(df_nd_add)) + nd_id_max + 1

df_nd_add = pd.merge(df_nd_add,col_nd_df, on = 'nd')

df_def_node = df_nd_add.reindex(columns=df_def_node_0.columns.tolist()).fillna(0)

dict_nd_id = df_nd_add.set_index('nd')['nd_id'].to_dict()

dict_nd_id = {nd_old: dict_nd_id[nd] for nd_old, nd in dict_nd_ht.items()
              if nd in dict_nd_id}

df_nd_res_el = df_def_node_0.loc[df_def_node_0.nd.str.contains('MFH|SFH')]
df_nd_not_res = df_def_node_0.loc[~df_def_node_0.nd.str.contains('MFH|SFH')]
df_nd_arch_el = df_def_node_0.loc[df_def_node_0.nd.str.contains('_0|_1|_2|_3|OCO|IND')]
df_nd_ch0_el = df_def_node_0.loc[df_def_node_0.nd.str.contains('CH0')]

# %% set nd_id number to the corresponding nd_id new

dferg_arch_ht = dferg_arch_ht.set_index(dferg_arch_ht['nd_id_new'])

for key, value in dict_nd_id.items():
    dferg_arch_ht.loc[key,'nd_id'] = value

# %% ~~~~~~~~~~~~~~~~~~~~~~~ DEF_PP_TYPE

df_def_pp_type_0 = pd.read_csv(data_path_prv + '/def_pp_type.csv')
# df_def_pp_type_0 = aql.read_sql(db, sc, 'def_pp_type')

# TODO change color and see if we add more technologies

df_def_pp_type = df_def_pp_type_0.copy().head(0)

for npt, pt, cat, color in ((0, 'STO_VR_SFH', 'NEW_STORAGE_VR_SFH', '#7B09CC'),
                            (1, 'STO_VR_MFH', 'NEW_STORAGE_VR_MFH', '#59F909'),
                            (2, 'STO_VR_OCO', 'NEW_STORAGE_VR_OCO', '#28A503'),
                            (3, 'STO_VR_IND', 'NEW_STORAGE_VR_IND', '#1A6703'),
                            (4, 'HP_AW_SFH', 'HEATPUMP_AIR_SFH', '#F2D109'),
                            (5, 'HP_WW_SFH', 'HEATPUMP_WAT_SFH', '#F2D109'),
                            (6, 'HP_AW_MFH', 'HEATPUMP_AIR_MFH', '#F2D109'),
                            (7, 'HP_WW_MFH', 'HEATPUMP_WAT_MFH', '#F2D109'),
                            (8, 'STO_HT_SFH', 'HEAT_STORAGE_SFH', '#F2D109'),
                            (9, 'STO_HT_MFH', 'HEAT_STORAGE_MFH', '#F2D109'),):
#                            (10, 'STO_CAES_CH0', 'NEW_STORAGE_CAES_CH0', '#D9F209'),):

    df_def_pp_type.loc[npt] = (npt, pt, cat, color)


df_def_pp_type.loc[:,'pt_id'] = np.arange(0, len(df_def_pp_type)) + df_def_pp_type_0.pt_id.max() + 1


# %% ~~~~~~~~~~~~~~~~~~~~~~ DEF_FUEL for A/W and W/W

df_def_fuel_0 = pd.read_csv(data_path_prv + '/def_fuel.csv')
# df_def_fuel_0 = aql.read_sql(db, sc, 'def_fuel')

df_def_fuel = df_def_fuel_0.copy().head(0)

for nfl, fl, co2_int, ca, constr, color in ((0, 'ca_heat_aw', 0,0,0, 'r'),
                                           (1, 'ca_heat_ww', 0,0,0, 'r'),
                                            (2, 'heat_storage', 0,0,0, 'r'),):
                

    df_def_fuel.loc[nfl] = (nfl, fl, co2_int, ca, constr, color)


df_def_fuel.loc[:,'fl_id'] = np.arange(0, len(df_def_fuel)) + df_def_fuel_0.fl_id.max() + 1

# %% ~~~~~~~~~~~~~~~~~~~~~~ DEF_ENCAR for A/W and W/W

# 
df_def_encar_0 = pd.read_csv(data_path_prv + '/def_encar.csv')
# df_def_encar_0 = aql.read_sql(db, sc, 'def_encar')

df_def_encar = df_def_encar_0.head(0)

for nca, fl_id, ca in ((1, 24, 'AW'),
                       (2, 25, 'WW')):
    
    df_def_encar.loc[nca] = (nca, fl_id, ca)

#df_def_encar['ca_id'] = np.arange(0, len(df_def_encar)) + df_def_encar_0.ca_id.max() + 1


# %% ~~~~~~~~~~~~~~~~~~~~~~~ DEF_PLANT

df_def_plant_0 = pd.read_csv(data_path_prv + '/def_plant.csv')
# df_def_plant_0 = aql.read_sql(db, sc, 'def_plant')

#df_def_plant_0['set_def_eff'] = 0

dict_pp_id_all = df_def_plant_0.set_index('pp')['pp_id'].to_dict()

df_pp_add_ht = pd.DataFrame(df_nd_add.nd).rename(columns={'nd': 'nd_id'})
df_pp_add_arch = pd.DataFrame(df_nd_arch_el.nd).rename(columns={'nd': 'nd_id'})
df_pp_add_ch0 = pd.DataFrame(df_nd_ch0_el.nd).rename(columns={'nd': 'nd_id'})

# Adding first vanadium storage (arch el level)
df_pp_add_1 = df_pp_add_arch.nd_id.str.slice(stop=3)
df_pp_add = pd.DataFrame()
    
for sfx, fl_id, pt_id, set_1 in [('_STO_VR', 'new_storage', 'STO_VR_', ['set_def_st','set_def_add']),
                                 ]:

    new_pp_id = df_def_plant_0.pp_id.max() + 1
    data = dict(pp=df_pp_add_arch + sfx,
                fl_id=fl_id, pt_id=pt_id + df_pp_add_1 , pp_id=np.arange(new_pp_id, new_pp_id + len(df_pp_add_arch)),
                **{st: 1 if st in set_1 else 0 for st in [c for c in df_def_plant_0.columns if 'set' in c]})

    df_pp_add = df_pp_add.append(df_pp_add_arch.assign(**data), sort=True)

df_pp_add.pp_id = np.arange(0, len(df_pp_add)) + df_pp_add.pp_id.min()

# Adding then compressed air (CH0 level) NOT FOR NOW
#df_pp_add_1 = df_pp_add_ch0.nd_id.str.slice(stop=3)
#
#for sfx, fl_id, pt_id, set_1 in [('_STO_CAES', 'new_storage', 'STO_CAES_', ['set_def_st','set_def_add']),
#                                 ]:
#
#    new_pp_id = df_def_plant_0.pp_id.max() + 1
#    data = dict(pp=df_pp_add_ch0 + sfx,
#                fl_id=fl_id, pt_id=pt_id + df_pp_add_1 , pp_id=np.arange(new_pp_id, new_pp_id + len(df_pp_add_ch0)),
#                **{st: 1 if st in set_1 else 0 for st in [c for c in df_def_plant_0.columns if 'set' in c]})
#
#    df_pp_add = df_pp_add.append(df_pp_add_ch0.assign(**data), sort=True)
#
#df_pp_add.pp_id = np.arange(0, len(df_pp_add)) + df_pp_add.pp_id.min()

# Adding then heating tech (new nodes)
df_pp_add_1 = df_pp_add_ht.nd_id.str.slice(stop=3)


for sfx, fl_id, pt_id, set_1 in [
                                 ('_HP_AW', 'ca_electricity', 'HP_AW_', ['set_def_pp']),#,'set_def_eff']),#,'set_def_add']),
                                 ('_HP_WW', 'ca_electricity', 'HP_WW_', ['set_def_pp']),#,'set_def_add']),
                                 ('_STO_HT', 'heat_storage', 'STO_HT_', ['set_def_st']),#,'set_def_add']),
                                 ]:

    new_pp_id = df_def_plant_0.pp_id.max() + 1
    data = dict(pp=df_pp_add_ht + sfx,
                fl_id=fl_id, pt_id=pt_id + df_pp_add_1 , pp_id=np.arange(new_pp_id, new_pp_id + len(df_pp_add_ht)),
                **{st: 1 if st in set_1 else 0 for st in [c for c in df_def_plant_0.columns if 'set' in c]})

    df_pp_add = df_pp_add.append(df_pp_add_ht.assign(**data), sort=True)

df_pp_add.pp_id = np.arange(0, len(df_pp_add)) + df_pp_add.pp_id.min()


df_def_plant = df_pp_add[df_def_plant_0.columns].reset_index(drop=True)

for df, idx in [(pd.concat([df_def_fuel_0,df_def_fuel]), 'fl'), (df_def_pp_type, 'pt'), (pd.concat([df_def_node_0,df_def_node]), 'nd')]:

    df_def_plant, _ = translate_id(df_def_plant, df, idx)

#df_def_plant_new = pd.concat([df_def_plant_0,df_def_plant]).reset_index(drop=True)
# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DEF_PROFILE

df_def_profile_0 = pd.read_csv(data_path_prv + '/def_profile.csv')
# df_def_profile_0 = aql.read_sql(db, sc, 'def_profile')

# Demand profiles heat A/W and W/W

df_def_profile_dmnd_ht_aw = df_def_node.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd_ht_aw['pf'] = 'demand_HT_AW_' + df_def_profile_dmnd_ht_aw.primary_nd
df_def_profile_dmnd_ht_aw['pf_id'] = df_def_profile_dmnd_ht_aw.index.rename('pf_id') + df_def_profile_0.pf_id.max() + 1
df_def_profile_dmnd_ht_aw = df_def_profile_dmnd_ht_aw[df_def_profile_0.columns]

df_def_profile_dmnd_ht_ww = df_def_node.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd_ht_ww['pf'] = 'demand_HT_WW_' + df_def_profile_dmnd_ht_ww.primary_nd
df_def_profile_dmnd_ht_ww['pf_id'] = df_def_profile_dmnd_ht_ww.index.rename('pf_id') + df_def_profile_dmnd_ht_aw.pf_id.max() + 1
df_def_profile_dmnd_ht_ww = df_def_profile_dmnd_ht_ww[df_def_profile_0.columns]

# Demand profiles el in heat nodes
df_def_profile_dmnd_ht_el = df_def_node.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd_ht_el['pf'] = 'demand_EL_' + df_def_profile_dmnd_ht_el.primary_nd
df_def_profile_dmnd_ht_el['pf_id'] = df_def_profile_dmnd_ht_el.index.rename('pf_id') + df_def_profile_dmnd_ht_ww.pf_id.max() + 1
df_def_profile_dmnd_ht_el = df_def_profile_dmnd_ht_el[df_def_profile_0.columns]

# COP profile 
df_def_profile_cop_35 = df_def_node.nd.copy().rename('primary_nd').reset_index()
df_def_profile_cop_35['pf'] = 'cop_35_' + df_def_profile_cop_35.primary_nd
df_def_profile_cop_35['pf_id'] = df_def_profile_cop_35.index.rename('pf_id') + df_def_profile_dmnd_ht_el.pf_id.max() + 1
df_def_profile_cop_35 = df_def_profile_cop_35[df_def_profile_0.columns]

# COP profile 
df_def_profile_cop_60 = df_def_node.nd.copy().rename('primary_nd').reset_index()
df_def_profile_cop_60['pf'] = 'cop_60_' + df_def_profile_cop_60.primary_nd
df_def_profile_cop_60['pf_id'] = df_def_profile_cop_60.index.rename('pf_id') + df_def_profile_cop_35.pf_id.max() + 1
df_def_profile_cop_60 = df_def_profile_cop_60[df_def_profile_0.columns]


#A/W and W/W
df_def_profile = df_def_profile_dmnd_ht_aw

df_def_profile = pd.concat([df_def_profile_dmnd_ht_aw,df_def_profile_dmnd_ht_ww,df_def_profile_dmnd_ht_el,df_def_profile_cop_35], axis=0)
df_def_profile = df_def_profile.reset_index(drop=True)
    
df_def_profile


# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ NODE_ENCAR for A/W and W/W

df_node_encar_0 = pd.read_csv(data_path_prv + '/node_encar.csv')
# df_node_encar_0 = aql.read_sql(db, sc, 'node_encar')

# ADD demand profile for heat
df_ndca_add_ht = (dferg_arch_ht.loc[dferg_arch_ht.nd_id_new.isin(df_nd_add.nd), ['nd_id_new', 'erg_tot']]
                         .rename(columns={'erg_tot': 'dmnd_sum', 'nd_id_new': 'nd_id'}))

#data = dict(vc_dmnd_flex=[0,0], ca_id=[0,1], grid_losses=[0,0], grid_losses_absolute=[0,0])
data_2 = dict(vc_dmnd_flex=0, ca_id=2, grid_losses=0, grid_losses_absolute=0)
data_1 = dict(vc_dmnd_flex=0, ca_id=1, grid_losses=0, grid_losses_absolute=0)
data_0 = dict(vc_dmnd_flex=0, ca_id=0, grid_losses=0, grid_losses_absolute=0)

df_node_encar_ht_2 = df_ndca_add_ht.assign(**data_2).reindex(columns=df_node_encar_0.columns).reset_index(drop=True)
df_node_encar_ht_1 = df_ndca_add_ht.assign(**data_1).reindex(columns=df_node_encar_0.columns).reset_index(drop=True)
df_node_encar_ht_0 = df_ndca_add_ht.assign(**data_0).reindex(columns=df_node_encar_0.columns).reset_index(drop=True)

df_node_encar_ht_2 = pd.merge(df_node_encar_ht_2, df_def_profile_dmnd_ht_ww, left_on='nd_id', right_on='primary_nd', how='inner')
df_node_encar_ht_1 = pd.merge(df_node_encar_ht_1, df_def_profile_dmnd_ht_aw, left_on='nd_id', right_on='primary_nd', how='inner')
df_node_encar_ht_0 = pd.merge(df_node_encar_ht_0, df_def_profile_dmnd_ht_el, left_on='nd_id', right_on='primary_nd', how='inner')

df_node_encar_ht = pd.concat([df_node_encar_ht_1,df_node_encar_ht_2,df_node_encar_ht_0]).reset_index(drop=True)
#df_node_encar_ht = df_node_encar_ht_1.reset_index(drop=True)

list_dmnd = [c for c in df_node_encar_ht if 'dmnd_sum' in c]

df_node_encar_ht = df_node_encar_ht.assign(**{c: df_node_encar_ht.dmnd_sum
                                        for c in list_dmnd})
df_node_encar_ht.update(df_node_encar_ht.loc[df_node_encar_ht.ca_id==0].assign(**{c: 0
                                        for c in list_dmnd}))


#df_node_encar_ht = pd.merge(df_node_encar_ht, df_def_profile_dmnd_ht, left_on='nd_id', right_on='primary_nd', how='inner')
df_node_encar_ht['dmnd_pf_id'] = df_node_encar_ht.pf
df_node_encar_ht = df_node_encar_ht.loc[:, df_node_encar_0.columns]


for df, idx in [(df_def_node, 'nd'), (df_def_profile, ['pf', 'dmnd_pf'])]:
    df_node_encar_ht, _ = translate_id(df_node_encar_ht, df, idx)

df_node_encar_ht = df_node_encar_ht.sort_values(by='ca_id', ascending=False).reset_index(drop=True)
#TODO check if we add a factor for heat load (climate correction) or just retrofit scenario
fct_dmnd_ht = pd.read_csv(base_dir+'/res_heating/demand/heat_factor_dmnd_future_years_aw_ww.csv',sep=';')
# fct_dmnd_ht = pd.read_csv(os.path.join(base_dir,'../heating_data/heat_factor_dmnd_future_years_aw_ww.csv'),sep=';')
fct_ht = fct_dmnd_ht.filter(like='dmnd_sum')

# df_0 = df_node_encar_ht.loc[df_node_encar_ht.ca_id.isin([1,2])].filter(like='dmnd_sum').reset_index(drop=True)*fct_ht
# df_node_encar_ht.loc[df_node_encar_ht.ca_id.isin([1,2])].update(df_0)
# df_node_encar_ht.update(df_0)

df_0 = df_node_encar_ht.loc[df_node_encar_ht.ca_id.isin([1,2])].set_index(['nd_id','ca_id']).filter(like='dmnd_sum')
fct_ht.index = df_0.index
df_0 = df_0*fct_ht
df_node_encar_ht_tmp = df_node_encar_ht.set_index(['nd_id','ca_id'])
df_node_encar_ht_tmp.update(df_0)
df_node_encar_ht = df_node_encar_ht_tmp.reset_index()


df_node_encar_new = pd.concat([df_node_encar_0,df_node_encar_ht])
df_node_encar_new = df_node_encar_new.reset_index(drop=True)


# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PROFDMND for A/W and W/W
df_tm_st =pd.read_csv(base_dir+'/res_heating/timemap/timestamp_template.csv')
df_tm_st['datetime'] = df_tm_st['datetime'].astype('datetime64[ns]')

# df_tm_st = aql.read_sql(db, 'profiles_raw', 'timestamp_template',filt=[('year', [2015],  '=')])

df_profdmnd_0 = pd.read_csv(data_path_prv + '/profdmnd.csv')
# df_profdmnd_0 = aql.read_sql(db, sc, 'profdmnd')
df_profdmnd_0 = pd.merge(df_profdmnd_0, df_tm_st[['slot','doy']].rename(columns={'slot':'hy'}), on='hy')

df_dmnd_ht_add_aw = dfload_arch_ht_aw.copy()
df_dmnd_ht_add_ww = dfload_arch_ht_ww.copy()

df_dmnd_ht_add_aw['ca_id'] = 1
df_dmnd_ht_add_ww['ca_id'] = 2

df_dmnd_ht_add_aw = pd.merge(df_dmnd_ht_add_aw, df_def_profile_dmnd_ht_aw[['pf_id', 'primary_nd']], left_on='nd_id', right_on='primary_nd')
df_dmnd_ht_add_aw = df_dmnd_ht_add_aw.rename(columns={'erg_tot': 'value', 'pf_id': 'dmnd_pf_id'})
df_dmnd_ht_add_aw['nd_id'] = df_dmnd_ht_add_aw.nd_id.replace(dict_nd_id)
df_dmnd_ht_add_aw['hy'] = 24*df_dmnd_ht_add_aw.doy - 24

#
df_dmnd_ht_add_ww = pd.merge(df_dmnd_ht_add_ww, df_def_profile_dmnd_ht_ww[['pf_id', 'primary_nd']], left_on='nd_id', right_on='primary_nd')
df_dmnd_ht_add_ww = df_dmnd_ht_add_ww.rename(columns={'erg_tot': 'value', 'pf_id': 'dmnd_pf_id'})
df_dmnd_ht_add_ww['nd_id'] = df_dmnd_ht_add_ww.nd_id.replace(dict_nd_id)
df_dmnd_ht_add_ww['hy'] = 24*df_dmnd_ht_add_ww.doy - 24

df_profdmnd_0['erg_tot_fossil'] = 0
df_profdmnd_0['erg_tot_retr_1pc'] = 0
df_profdmnd_0['erg_tot_retr_2pc'] = 0
df_profdmnd_0['erg_tot_retr_1pc_fossil'] = 0
df_profdmnd_0['erg_tot_retr_2pc_fossil'] = 0

df_dmnd_ht_add = pd.concat([df_dmnd_ht_add_aw,df_dmnd_ht_add_ww])
df_profdmnd_ht = df_dmnd_ht_add[df_profdmnd_0.columns.tolist()].reset_index(drop=True)
#df_profdmnd_ht_el = df_dmnd_ht_el_add[df_profdmnd_0.columns.tolist()].reset_index(drop=True)

df_profdmnd_new = pd.concat([df_profdmnd_0,df_profdmnd_ht])#,df_profdmnd_ht_el])

# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~ PROFPRICE

# --> NO CHANGES! HOUSEHOLDS USE CH0 PRICE PROFILES


# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PROFSUPPLY

# --> NO CHANGES!


# %% ~~~~~~~~~~~~~~~~~~~~~~~ PLANT_ENCAR (needs profsupply data)

dict_pp_new = pd.Series(df_def_plant.pp_id.values,index=df_def_plant.pp).to_dict()
dict_nd_id_all = dict(pd.Series(df_def_node_0.nd_id.values,index=df_def_node_0.nd).to_dict(), **dict_nd_id)
dict_pt_id_all = dict(pd.Series(df_def_pp_type_0.pt_id.values,index=df_def_pp_type_0.pt).to_dict(),
                      **pd.Series(df_def_pp_type.pt_id.values,index=df_def_pp_type.pt))

df_plant_encar = pd.read_csv(data_path_prv + '/plant_encar.csv')
# df_plant_encar = aql.read_sql(db, sc, 'plant_encar')

#dfplant_costs = pd.read_csv(os.path.join(base_dir,'Costs/cost_tech_node_paper2.csv'),sep=';')
#dfplant_costs = pd.read_csv(os.path.join(base_dir,'Costs/cost_tech_node_paper2_vr19yr.csv'),sep=';')
#dfplant_costs = pd.read_csv(os.path.join(base_dir,'Costs/cost_tech_node_paper2_vr25yr.csv'),sep=';')
#dfplant_costs = pd.read_csv(os.path.join(base_dir,'Costs/cost_tech_node_paper2_vrpwr15erg25.csv'),sep=';')
# dfplant_costs = pd.read_csv(os.path.join(base_dir,'Costs/cost_tech_node_paper2_vrpwr15erg25_aw_ww.csv'),sep=';')
dfplant_costs = pd.read_csv(base_dir + '/res_heating/costs/cost_tech_node_paper2_vrpwr15erg25_aw_ww.csv',sep=';')


df_hp_scen = pd.read_csv(base_dir + '/res_heating/hp_scenarios/hp_scenario.csv',sep=';')
df_hp_scen_fossil = pd.read_csv(base_dir + '/res_heating/hp_scenarios/hp_scenario_fossil.csv',sep=';')
df_hp_scen_retr_1pc = pd.read_csv(base_dir + '/res_heating/hp_scenarios/hp_scenario_retr_1pc.csv',sep=';')
df_hp_scen_retr_2pc = pd.read_csv(base_dir + '/res_heating/hp_scenarios/hp_scenario_retr_2pc.csv',sep=';')
df_hp_scen_retr_1pc_fossil = pd.read_csv(base_dir + '/res_heating/hp_scenarios/hp_scenario_retr_1pc_fossil.csv',sep=';')
df_hp_scen_retr_2pc_fossil = pd.read_csv(base_dir + '/res_heating/hp_scenarios/hp_scenario_retr_2pc_fossil.csv',sep=';')

df_hp_scen_all = pd.merge(df_hp_scen,df_hp_scen_fossil,on='pp')
df_hp_scen_all = pd.merge(df_hp_scen_all,df_hp_scen_retr_1pc,on='pp')
df_hp_scen_all = pd.merge(df_hp_scen_all,df_hp_scen_retr_2pc,on='pp')
df_hp_scen_all = pd.merge(df_hp_scen_all,df_hp_scen_retr_1pc_fossil,on='pp')
df_hp_scen_all = pd.merge(df_hp_scen_all,df_hp_scen_retr_2pc_fossil,on='pp')

df_ppca_add = dfplant_costs.copy()
df = df_ppca_add.loc[df_ppca_add.nd_id.str.contains('SFH|MFH')]
df_new = df.copy().head(0)
for i in (0,1,2,3):
    for j in df.index:
        row_add = df.copy().loc[j]
        row_add['nd_id'] = str(row_add.nd_id)+'_'+str(i)
        df_new = df_new.append(row_add)

df_ppca_add = df_ppca_add.loc[~df_ppca_add.nd_id.str.contains('SFH|MFH')]       
df_ppca_add = df_ppca_add.append(df_new).reset_index(drop=True)


df_ppca_add['nd_id'] = df_ppca_add.nd_id.replace(dict_nd_id_all)
df_ppca_add['pt_id'] = df_ppca_add.pt_id.replace(dict_pt_id_all)

df_ppca_add = pd.merge(df_ppca_add, df_def_plant[['pp_id','pt_id','nd_id']], on= ['pt_id','nd_id'])
df_ppca_add = df_ppca_add.drop(columns=['nd_id','pt_id'])


df_ppca_add = df_ppca_add.assign(
                                 factor_lin_0=0, factor_lin_1=0,
                                 cap_avlb=1, vc_ramp=0,
                                 vc_om=0, erg_chp=None)



df_plant_encar_1 = pd.DataFrame()
df_plant_encar_1 = pd.concat([df_plant_encar, df_ppca_add])

df_pp_htsto_add = df_pp_add.loc[df_pp_add.fl_id=='heat_storage']

list_cap = [c for c in df_plant_encar.columns if 'cap_pwr_leg' in c]
#Set 0 capacity heat storage for now
df_plant_encar_2 = df_plant_encar_1.loc[df_plant_encar_1.pp_id.isin(df_pp_add.pp_id)].assign(**{cap: 0 for cap in list_cap}).set_index('pp_id')

df_plant_encar_1 = df_plant_encar_1.set_index('pp_id')
df_plant_encar_1.update(df_plant_encar_2) 
df_plant_encar_1 = df_plant_encar_1.reset_index()

dict_pp_id_hp = df_def_plant[['pp_id','pp']].loc[df_def_plant.pp.str.contains('HP')].set_index('pp')['pp_id'].to_dict()
dict_nd_id_hp = df_def_plant[['pp_id','pp','nd_id']].loc[df_def_plant.pp.str.contains('HP')].set_index('pp')['nd_id'].to_dict()

#dfmax_dmnd_arch_ht['pwr_max_2050'] = dfmax_dmnd_arch_ht.max_dmnd * 0.93 / 3
df_hp_scen['pp_id'] = df_hp_scen['pp'].map(dict_pp_id_hp)
df_hp_scen = df_hp_scen.set_index(df_hp_scen.pp_id).drop(columns=['pp_id','pp'])

df_hp_scen_all['pp_id'] = df_hp_scen_all['pp'].map(dict_pp_id_hp)
df_hp_scen_all = df_hp_scen_all.set_index(df_hp_scen_all.pp_id).drop(columns=['pp_id','pp'])

list_add_col_cap = list(set(df_hp_scen_all.columns.to_list()) - set(list_cap))
list_add_col_cap.sort()
for i in list_add_col_cap:
    df_plant_encar_1[i] = np.nan
df_plant_encar_1 = df_plant_encar_1.set_index('pp_id')
#df_plant_encar_1.update(df_hp_scen)
df_plant_encar_1.update(df_hp_scen_all)
df_plant_encar_1 = df_plant_encar_1.reset_index()


df_plant_encar_new = df_plant_encar_1.reset_index(drop=True)#(drop=True)  

# %% ~~~~~~~~~~~~~~~~~~~~ NODE_CONNECT

df_node_connect = pd.read_csv(data_path_prv + '/node_connect.csv').query(
                        'nd_id in %s and nd_2_id not in %s'%(
                        df_nd_ch0_el.nd_id.tolist(),df_nd_not_res.nd_id.tolist())).reset_index(drop=True)
# df_node_connect = aql.read_sql(db, sc, 'node_connect',
#                                filt=[('nd_id', df_nd_ch0_el.nd_id.tolist(),  ' = ', ' AND '),
#                                      ('nd_2_id', df_nd_not_res.nd_id.tolist(), ' != ', ' AND ')])

node_sfh_rur = df_def_node.loc[df_def_node.nd.str.contains('SFH_RUR')].nd.values
node_sfh_sub = df_def_node.loc[df_def_node.nd.str.contains('SFH_SUB')].nd.values
node_sfh_urb = df_def_node.loc[df_def_node.nd.str.contains('SFH_URB')].nd.values
node_mfh_rur = df_def_node.loc[df_def_node.nd.str.contains('MFH_RUR')].nd.values
node_mfh_sub = df_def_node.loc[df_def_node.nd.str.contains('MFH_SUB')].nd.values
node_mfh_urb = df_def_node.loc[df_def_node.nd.str.contains('MFH_URB')].nd.values

node_sfh_rur_0 = df_def_node_0.loc[df_def_node_0.nd.str.contains('SFH_RUR')].nd.values
node_sfh_sub_0 = df_def_node_0.loc[df_def_node_0.nd.str.contains('SFH_SUB')].nd.values
node_sfh_urb_0 = df_def_node_0.loc[df_def_node_0.nd.str.contains('SFH_URB')].nd.values
node_mfh_rur_0 = df_def_node_0.loc[df_def_node_0.nd.str.contains('MFH_RUR')].nd.values
node_mfh_sub_0 = df_def_node_0.loc[df_def_node_0.nd.str.contains('MFH_SUB')].nd.values
node_mfh_urb_0 = df_def_node_0.loc[df_def_node_0.nd.str.contains('MFH_URB')].nd.values

#for i in 
data_sfh_rur = dict(nd_id=node_sfh_rur_0, nd_2_id=node_sfh_rur, ca_id=0, mt_id='all',cap_trme_leg=1e9,cap_trmi_leg=0)
data_sfh_sub = dict(nd_id=node_sfh_sub_0, nd_2_id=node_sfh_sub, ca_id=0, mt_id='all',cap_trme_leg=1e9,cap_trmi_leg=0)
data_sfh_urb = dict(nd_id=node_sfh_urb_0, nd_2_id=node_sfh_urb, ca_id=0, mt_id='all',cap_trme_leg=1e9,cap_trmi_leg=0)
data_mfh_rur = dict(nd_id=node_mfh_rur_0, nd_2_id=node_mfh_rur, ca_id=0, mt_id='all',cap_trme_leg=1e9,cap_trmi_leg=0)
data_mfh_sub = dict(nd_id=node_mfh_sub_0, nd_2_id=node_mfh_sub, ca_id=0, mt_id='all',cap_trme_leg=1e9,cap_trmi_leg=0)
data_mfh_urb = dict(nd_id=node_mfh_urb_0, nd_2_id=node_mfh_urb, ca_id=0, mt_id='all',cap_trme_leg=1e9,cap_trmi_leg=0)

df_typ_ht = pd.concat([pd.DataFrame(data_sfh_rur), pd.DataFrame(data_sfh_sub),pd.DataFrame(data_sfh_urb),
                       pd.DataFrame(data_mfh_rur), pd.DataFrame(data_mfh_sub),pd.DataFrame(data_mfh_urb)])

df_typ_ht = expand_rows(df_typ_ht, ['mt_id'], [range(12)])
df_typ_ht[['mt_id']] = df_typ_ht.mt_id.astype(int)

df_node_connect = df_typ_ht[df_node_connect.columns]

dft = pd.concat([pd.read_csv(data_path_prv + '/def_node.csv'), df_def_node])

for idx in [('nd'), (['nd', 'nd_2'])]:

    df_node_connect, _ = translate_id(df_node_connect, dft, idx)
    
df_node_connect = df_node_connect.reset_index(drop=True)
# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ FUEL_NODE_ENCAR
df_fuel_node_encar_0 = pd.read_csv(data_path_prv + '/fuel_node_encar.csv')
# df_fuel_node_encar_0 = aql.read_sql(db, sc, 'fuel_node_encar')

df_flndca_add = df_ppca_add.copy()[['pp_id', 'ca_id']]
df_flndca_add = df_flndca_add.join(df_def_plant.set_index('pp_id')[['fl_id', 'nd_id']], on='pp_id')
df_flndca_add = df_flndca_add.drop('pp_id', axis=1).drop_duplicates()

df_fuel_node_encar = df_flndca_add.reindex(columns=df_fuel_node_encar_0.columns)

fill_cols = [c for c in df_fuel_node_encar.columns
             if any(pat in c for pat in ['vc_fl', 'erg_inp'])]
df_fuel_node_encar[fill_cols] = df_fuel_node_encar.reindex(columns=fill_cols).fillna(0)

# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DF_PROFPRICE

#df_profprice = aql.read_sql(db, sc, 'profprice') <- NO CHANGE
# %% COP 
df_def_cop_pr_35 = dfcop_pr_35.copy()
for df, idx in [(df_def_plant, 'pp')]:#[(df_def_node, 'nd'), (df_def_profile, ['pf', 'dmnd_pf'])]:
    df_def_cop_pr_35, _ = translate_id(df_def_cop_pr_35, df, idx)

df_def_cop_pr_35 = df_def_cop_pr_35.rename(columns={'cop_35':'value'})
# df_def_cop_pr_35.drop(columns='index').reset_index().to_csv(os.path.join(archetypes_input_base.data_path, 'def_cop_35.csv'), index=False)
df_def_cop_pr_35.drop(columns='index').reset_index().to_csv(data_path + '/def_cop_35.csv', index=False)

df_def_cop_pr_60 = dfcop_pr_60.copy()
for df, idx in [(df_def_plant, 'pp')]:#[(df_def_node, 'nd'), (df_def_profile, ['pf', 'dmnd_pf'])]:
    df_def_cop_pr_60, _ = translate_id(df_def_cop_pr_60, df, idx)

df_def_cop_pr_60 = df_def_cop_pr_60.rename(columns={'cop_60':'value'})
df_def_cop_pr_60.drop(columns='index').reset_index().to_csv(data_path + '/def_cop_60.csv', index=False)

# %%

# #df_node_encar_new
# #df_profdmnd_new
# #df_plant_encar_new

# list_tb_col = [
#            (df_plant_encar_new, 'plant_encar', ['pp_id', 'ca_id'])
#            ]

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
#            (df_node_connect, 'node_connect', ['nd_id', 'nd_2_id']),
# #           (df_plant_encar_new, 'plant_encar', ['pp_id', 'ca_id']),
#            (df_def_plant, 'def_plant', ['pp_id']),
#            (df_def_node, 'def_node', ['nd_id']),
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


list_tb_app = {'def_node':df_def_node,
               'def_encar':df_def_encar,
                  'def_pp_type':df_def_pp_type,
                'def_fuel': df_def_fuel,
                'node_connect': df_node_connect,
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




