# -*- coding: utf-8 -*-
"""
Created on Tue Jan 29 08:35:09 2019

@author: user
"""

# build first input with noational aggregation
# import build_input_national_aggr
print('####################')
print('BUILDING INPUT DATA FOR DISAGGREGATION OF SWITZERLAND INTO ARCHETYPES')
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
data_path_prv = conf.PATH_CSV + '_national_aggr'

seed = 2

np.random.seed(seed)

db = conf.DATABASE
sc = conf.SCHEMA

#db = 'grimsel_1'
#sc = 'lp_input_ee_dsm'

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

#def replace_table(df, tb):
#
##    list_col = list(aql.get_sql_cols(tb, sc, db).keys())
#    
#    aql.write_sql(df, db=db, sc=sc, tb=tb, if_exists='replace')
 

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

#%%

dfprop_era_arch = pd.read_csv(base_dir+'/archetype_disaggr/PV/prop_era_arch.csv', sep = ';')


#dfpv_arch = pd.read_csv(os.path.join(base_dir,'PV/surf_prod_arch_pv.csv'),sep=';')
#dfpv_arch = pd.read_csv(os.path.join(base_dir,'PV/surf_prod_arch_pv_prop_0.csv'),sep=';')
dfpv_arch = pd.read_csv(base_dir+'/archetype_disaggr/PV/surf_prod_arch_pv_prop_new.csv',sep=';')

# set nd_id to that potential 


#dfpv_arch['pv_power_pot'] = dfpv_arch['el_prod']/(1000*dfkev['flh'].mean())
dfpv_arch = dfpv_arch.groupby(dfpv_arch.nd_id_new).sum()
#dfpv_arch['nd_id_new'] = dfpv_arch.nd_id
#dfpv_arch.loc[:,dfpv_arch.nd_id_new.str.contains('OTH')] == 'OTH_TOT'


#dfpv_arch['cap_pv'] = 1666*(dfpv_arch['pv_power_pot']/dfpv_arch['pv_power_pot'].sum()) # 1666 MW SFOE 2016
dfpv_arch['cap_pv'] = 1666*(dfpv_arch['pv_power_tot_est']/dfpv_arch['pv_power_tot_est'].sum()) # 1666 MW SFOE 2016
dfpv_arch['cap_st_pwr'] = 0
#
#dfpv_arch_CH0 = dfpv_arch.loc['CH0']
#dfpv_arch = dfpv_arch.drop(['CH0'], axis = 0)

dfpv_arch = dfpv_arch.reset_index()



# %%
dfload_arch = pd.read_csv(base_dir+'/archetype_disaggr/demand/dmnd_archetypes_0.csv').query(
                    'nd_id not in %s'%(['CH0'])).reset_index(drop=True)
dfload_arch['DateTime'] = dfload_arch['DateTime'].astype('datetime64[ns]')

dfload_arch_res = pd.read_csv(base_dir+'/archetype_disaggr/demand/dmnd_archetypes_0.csv').query(
    'nd_id.str.contains("SFH") or nd_id.str.contains("MFH")',engine='python').reset_index(drop=True)
dfload_arch_res['DateTime'] = dfload_arch_res['DateTime'].astype('datetime64[ns]')

dfload_arch_notres = pd.read_csv(base_dir+'/archetype_disaggr/demand/dmnd_archetypes_0.csv').query(
    'nd_id.str.contains("OCO") or nd_id.str.contains("IND")',engine='python').reset_index(drop=True)
dfload_arch_notres['DateTime'] = dfload_arch_notres['DateTime'].astype('datetime64[ns]')

dfload_arch_CH0 = pd.read_csv(base_dir+'/archetype_disaggr/demand/dmnd_archetypes_0.csv').query(
                    'nd_id in %s'%(['CH0'])).reset_index(drop=True)
dfload_arch_CH0['DateTime'] = dfload_arch_CH0['DateTime'].astype('datetime64[ns]')

# dfload_arch = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_0',filt=[('nd_id', ['CH0'],'!=')])
# dfload_arch_res= aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_0',filt=[('nd_id', ['SFH%','MFH%'],'LIKE')])
# dfload_arch_notres= aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_0',filt=[('nd_id', ['OCO%','IND%'],'LIKE')])
# dfload_arch_CH0_1 = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes_0',filt=[('nd_id', ['CH0'])])

#dfload_arch = aql.read_sql('grimsel_1', 'profiles_raw','dmnd_archetypes')
dfload_dict ={}
dfload_dict_new = {}
df = dfload_arch_res.copy()
df['nd_id_new'] = 0
df['erg_tot_new'] = 0
for i in df.nd_id.unique():
    
    dfload_dict[i] = df.loc[df.nd_id == i]
    for l in (0,1,2,3):
        df_1 = dfload_dict[i].copy()
        df_1['erg_tot_new'] = df_1.loc[:,'erg_tot'] * dfprop_era_arch.loc[dfprop_era_arch.nd_el.str.contains(i+'_'+str(l)),'prop'].reset_index(drop=True).loc[0]
        df_1['nd_id_new'] = i+'_'+str(l)
        dfload_dict_new[i+'_'+str(l)] = df_1
        
dfload_arch_res_new = dfload_arch_notres.head(0) 
  
for j in dfload_dict_new:
    dfload_arch_res_new = dfload_arch_res_new.append(dfload_dict_new[j],ignore_index=True)
    
dfload_arch_notres['nd_id_new'] = dfload_arch_notres[['nd_id']]
dfload_arch_notres['erg_tot_new'] = dfload_arch_notres[['erg_tot']]  

dfload_arch = dfload_arch_res_new.append(dfload_arch_notres,ignore_index=True)

dfload_arch = dfload_arch.set_index('DateTime')
dfload_arch.index = pd.to_datetime(dfload_arch.index)

dfload_arch_CH0 = dfload_arch_CH0.set_index('DateTime')


dfload_arch = dfload_arch.drop(columns=['nd_id','erg_tot']).rename(columns={'nd_id_new':'nd_id','erg_tot_new':'erg_tot'})


# %%

np.random.seed(3)

dferg_arch = dfload_arch.groupby('nd_id')['erg_tot'].sum()
dferg_arch = dferg_arch.reset_index()
dferg_arch['nd_id_new'] = dferg_arch.nd_id

dict_nd = dferg_arch.set_index('nd_id')['nd_id_new'].to_dict()

# %%

df_solar_canton_raw = pd.read_csv(base_dir+'/archetype_disaggr/PV/swiss_location_solar.csv')[['value', 'hy', 'canton','DateTime']]
df_solar_canton_raw['DateTime'] = df_solar_canton_raw['DateTime'].astype('datetime64[ns]')

# df_solar_canton_raw_test = aql.read_sql(db, 'profiles_raw', 'swiss_location_solar',
#                      keep=['value', 'hy', 'canton','DateTime'])

df_solar_canton_raw_1 = df_solar_canton_raw.pivot_table(index='DateTime',columns='canton', values='value')
df_solar_canton_1h = df_solar_canton_raw_1.resample('1h').sum()/4

df_solar_canton_1h['avg_all'] = df_solar_canton_1h.mean(axis=1)

df_solar_canton_1h['DateTime'] = df_solar_canton_1h.index
df_solar_canton_1h = df_solar_canton_1h.reset_index(drop=True)
df_solar_canton_1h['hy'] = df_solar_canton_1h.index
df_solar_canton_raw_1h = pd.melt(df_solar_canton_1h, id_vars=['DateTime','hy'], var_name='canton', value_name='value')

df_solar_canton_1h.index = df_solar_canton_1h['DateTime']
df_solar_canton_1h = df_solar_canton_1h.drop(columns=['DateTime','hy'])
cols = df_solar_canton_1h.columns.tolist()
cols = cols[-1:] + cols[:-1]
df_solar_canton_1h = df_solar_canton_1h[cols]
#list_ct = df_solar_canton_raw.canton.unique().tolist()
list_ct = df_solar_canton_1h.columns.tolist()




# %% ~~~~~~~~~~~~~~~~~~   DEF_NODE
#
#df_def_node_0 = aql.read_sql(db, sc, 'def_node', filt=[('nd', ['SFH%'], ' NOT LIKE ')])
#df_nd_add = pd.DataFrame(pd.concat([dferg_filt.nd_id_new.rename('nd'),
#                                    ], axis=0)).reset_index(drop=True)
color_nd = {'IND_RUR':       '#472503',
            'IND_SUB':        '#041FA3',
            'IND_URB':        '#484A4B',
            'MFH_RUR_0':        '#924C04',
            'MFH_SUB_0':        '#0A81EE',
            'MFH_URB_0':        '#BDC3C5',
            'MFH_RUR_1':        '#924C04',
            'MFH_SUB_1':        '#0A81EE',
            'MFH_URB_1':        '#BDC3C5',
            'MFH_RUR_2':        '#924C04',
            'MFH_SUB_2':        '#0A81EE',
            'MFH_URB_2':        '#BDC3C5',
            'MFH_RUR_3':        '#924C04',
            'MFH_SUB_3':        '#0A81EE',
            'MFH_URB_3':        '#BDC3C5',
            'OCO_RUR':        '#6D3904',
            'OCO_SUB':        '#0A31EE',
            'OCO_URB':        '#818789',
            'SFH_RUR_0':        '#BD6104',
            'SFH_SUB_0':        '#0EBADF',
            'SFH_URB_0':        '#A9A4D8',
            'SFH_RUR_1':        '#BD6104',
            'SFH_SUB_1':        '#0EBADF',
            'SFH_URB_1':        '#A9A4D8',
            'SFH_RUR_2':        '#BD6104',
            'SFH_SUB_2':        '#0EBADF',
            'SFH_URB_2':        '#A9A4D8',
            'SFH_RUR_3':        '#BD6104',
            'SFH_SUB_3':        '#0EBADF',
            'SFH_URB_3':        '#A9A4D8',
            }
col_nd_df = pd.DataFrame.from_dict(color_nd, orient='index').reset_index().rename(columns={'index': 'nd',0:'color'})

df_def_node_0 = pd.read_csv(data_path_prv + '/def_node.csv')
# df_def_node_0 = aql.read_sql(db, sc, 'def_node')
df_nd_add = pd.DataFrame(pd.concat([dferg_arch.nd_id_new.rename('nd'),
                                    ], axis=0)).reset_index(drop=True)

# reduce numbar
#df_nd_add = df_nd_add

nd_id_max = df_def_node_0.loc[~df_def_node_0.nd.isin(df_nd_add.nd)].nd_id.max()
df_nd_add['nd_id'] = np.arange(0, len(df_nd_add)) + nd_id_max + 1
#df_nd_add['color'] = 'g'
df_nd_add = pd.merge(df_nd_add,col_nd_df, on = 'nd')

df_def_node = df_nd_add.reindex(columns=df_def_node_0.columns.tolist()).fillna(0)

dict_nd_id = df_nd_add.set_index('nd')['nd_id'].to_dict()

dict_nd_id = {nd_old: dict_nd_id[nd] for nd_old, nd in dict_nd.items()
              if nd in dict_nd_id}


# %% set nd_id number to the corresponding nd_id new


dfpv_arch = dfpv_arch.set_index(dfpv_arch['nd_id_new'])

for key, value in dict_nd_id.items():
    dfpv_arch.loc[key,'nd_id'] = value
    
dferg_arch = dferg_arch.set_index(dfpv_arch['nd_id_new'])

for key, value in dict_nd_id.items():
    dferg_arch.loc[key,'nd_id'] = value
    

# %% ~~~~~~~~~~~~~~~~~~~~~~~ DEF_PP_TYPE

df_def_pp_type_0 = pd.read_csv(data_path_prv + '/def_pp_type.csv')
# df_def_pp_type_0 = aql.read_sql(db, sc, 'def_pp_type')

df_def_pp_type = df_def_pp_type_0.copy().head(0)

for npt, pt, cat, color in ((0, 'STO_LI_SFH', 'NEW_STORAGE_LI_SFH', '#7B09CC'),
                            (1, 'STO_LI_MFH', 'NEW_STORAGE_LI_MFH', '#59F909'),
                            (2, 'STO_LI_OCO', 'NEW_STORAGE_LI_OCO', '#28A503'),
                            (3, 'STO_LI_IND', 'NEW_STORAGE_LI_IND', '#1A6703'),
                            (4, 'PHO_SFH', 'PHOTO_SFH', '#D9F209'),
                            (5, 'PHO_MFH', 'PHOTO_MFH', '#F2D109'),
                            (6, 'PHO_OCO', 'PHOTO_OCO', '#F27E09'),
                            (7, 'PHO_IND', 'PHOTO_IND', '#F22C09'),):


    df_def_pp_type.loc[npt] = (npt, pt, cat, color)


df_def_pp_type['pt_id'] = np.arange(0, len(df_def_pp_type)) + df_def_pp_type_0.pt_id.max() + 1


# %% ~~~~~~~~~~~~~~~~~~~~~~ DEF_FUEL

# all there
df_def_fuel = pd.read_csv(data_path_prv + '/def_fuel.csv')
# df_def_fuel_test = aql.read_sql(db, sc, 'def_fuel')


# %% ~~~~~~~~~~~~~~~~~~~~~~~ DEF_PLANT

df_def_plant_0 = pd.read_csv(data_path_prv + '/def_plant.csv')
# df_def_plant_test = aql.read_sql(db, sc, 'def_plant')

dict_pp_id_all = df_def_plant_0.set_index('pp')['pp_id'].to_dict()

df_pp_add_0 = pd.DataFrame(df_nd_add.nd).rename(columns={'nd': 'nd_id'})

df_pp_add_1 = df_pp_add_0.nd_id.str.slice(stop=3)
df_pp_add = pd.DataFrame()

    
for sfx, fl_id, pt_id, set_1 in [('_PHO', 'photovoltaics', 'PHO_', ['set_def_pr','set_def_add']),
                                 ('_STO_LI', 'new_storage', 'STO_LI_', ['set_def_st','set_def_add']),

                                 ]:

    new_pp_id = df_def_plant_0.pp_id.max() + 1
    data = dict(pp=df_pp_add_0 + sfx,
                fl_id=fl_id, pt_id=pt_id + df_pp_add_1 , pp_id=np.arange(new_pp_id, new_pp_id + len(df_pp_add_0)),
                **{st: 1 if st in set_1 else 0 for st in [c for c in df_def_plant_0.columns if 'set' in c]})

    df_pp_add = df_pp_add.append(df_pp_add_0.assign(**data), sort=True)

df_pp_add.pp_id = np.arange(0, len(df_pp_add)) + df_pp_add.pp_id.min()


df_def_plant = df_pp_add[df_def_plant_0.columns].reset_index(drop=True)

for df, idx in [(df_def_fuel, 'fl'), (df_def_pp_type, 'pt'), (df_def_node, 'nd')]:

    df_def_plant, _ = translate_id(df_def_plant, df, idx)

# selecting random profiles from canton list
#np.random.seed(4)

dict_pp_id = df_pp_add.set_index('pp')['pp_id'].to_dict()

df_pp_add_pho = df_pp_add.loc[df_pp_add.fl_id == 'photovoltaics']

dict_pp_id_pho = df_pp_add_pho.set_index('pp')['pp_id'].to_dict()
# solar profile dictionary by node
dict_ct = {pp: list_ct[npp%len(list_ct)]
           for npp, pp in enumerate(df_pp_add.loc[df_pp_add.fl_id == 'photovoltaics',
                                   'nd_id'].tolist())}
dict_ct = {pp: list_ct[0]
       for npp, pp in enumerate(df_pp_add.loc[df_pp_add.fl_id == 'photovoltaics',
                               'nd_id'].tolist())}


# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DEF_PROFILE

df_def_profile_0 = pd.read_csv(data_path_prv + '/def_profile.csv')
# df_def_profile_test = aql.read_sql(db, sc, 'def_profile')


df_def_profile_sup = pd.DataFrame({'primary_nd': df_solar_canton_1h.columns}) + '_PHO' 
df_def_profile_sup['pf'] = 'supply_' + df_def_profile_sup.primary_nd
df_def_profile_sup['pf_id'] = df_def_profile_sup.index.rename('pf_id') + df_def_profile_0.pf_id.max() + 1
df_def_profile_sup = df_def_profile_sup[df_def_profile_0.columns]
df_def_profile_sup.drop(df_def_profile_sup.tail(23).index,inplace=True) # to keep only average for now

# Demand profiles
df_def_profile_dmnd = df_def_node.nd.copy().rename('primary_nd').reset_index()
df_def_profile_dmnd['pf'] = 'demand_EL_' + df_def_profile_dmnd.primary_nd
df_def_profile_dmnd['pf_id'] = df_def_profile_dmnd.index.rename('pf_id') + df_def_profile_sup.pf_id.max() + 1
df_def_profile_dmnd = df_def_profile_dmnd[df_def_profile_0.columns]


df_def_profile = pd.concat([df_def_profile_sup, df_def_profile_dmnd], axis=0)
#                            df_def_profile_prc], axis=0)
df_def_profile = df_def_profile.reset_index(drop=True)
#df_def_profile = pd.concat([df_def_profile_sup, df_def_profile_dmnd], axis=0)
    
df_def_profile

# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ NODE_ENCAR

df_node_encar_0 = pd.read_csv(data_path_prv + '/node_encar.csv')
# df_node_encar_0 = aql.read_sql(db, sc, 'node_encar')

df_node_encar_0_CH0 = df_node_encar_0.copy().loc[(df_node_encar_0.nd_id == 1)]

factor_CH0_dmnd = dfload_arch_CH0.erg_tot.sum()/df_node_encar_0.loc[(df_node_encar_0.nd_id == 1)].dmnd_sum
factor_CH0_dmnd = factor_CH0_dmnd.reset_index(drop=True)
df = df_node_encar_0_CH0.filter(like='dmnd_sum')*factor_CH0_dmnd.loc[0]
df_node_encar_0_CH0.update(df)

#exec_str = '''UPDATE sc.node_encar SET 
#            SET sc.dmnd_sum = df_node_encar_0_CH0.dmnd_sum
#            WHERE nd_id = 1
#
#          '''  
#aql.exec_sql(exec_str=exec_str,db=db)
#df_ndca_add = (dferg_filt.loc[dferg_filt.nd_id_new.isin(df_nd_add.nd), ['nd_id_new', 'erg_tot_filled']]
#                         .rename(columns={'erg_tot_filled': 'dmnd_sum', 'nd_id_new': 'nd_id'}))


df_ndca_add = (dferg_arch.loc[dferg_arch.nd_id_new.isin(df_nd_add.nd), ['nd_id_new', 'erg_tot']]
                         .rename(columns={'erg_tot': 'dmnd_sum', 'nd_id_new': 'nd_id'}))

#TODO maybe add here some grid losses

data = dict(vc_dmnd_flex=0.1, ca_id=0, grid_losses=0.0413336227316051, grid_losses_absolute=0)

df_node_encar = df_ndca_add.assign(**data).reindex(columns=df_node_encar_0.columns)

list_dmnd = [c for c in df_node_encar if 'dmnd_sum' in c]

df_node_encar = df_node_encar.assign(**{c: df_node_encar.dmnd_sum
                                        for c in list_dmnd})

df_node_encar = pd.merge(df_node_encar, df_def_profile_dmnd, left_on='nd_id', right_on='primary_nd', how='inner')
df_node_encar['dmnd_pf_id'] = df_node_encar.pf
df_node_encar = df_node_encar.loc[:, df_node_encar_0.columns]


for df, idx in [(df_def_node, 'nd'), (df_def_profile, ['pf', 'dmnd_pf'])]:
    df_node_encar, _ = translate_id(df_node_encar, df, idx)

fct_dmnd = pd.read_csv(base_dir+'/archetype_disaggr/demand/factor_dmnd_future_years.csv',sep=';')

df = df_node_encar.filter(like='dmnd_sum')*fct_dmnd
df_node_encar.update(df)


df_0 = df_node_encar_0[df_node_encar_0.nd_id !=1]
# TODO REPLACE INSTEAD OF UPDATE
df_node_encar_new = pd.concat([df_0,df_node_encar_0_CH0,df_node_encar])
# set the absolute losses 
df_node_encar_new.loc[df_node_encar_new.nd_id ==1,['grid_losses_absolute']] = 142320

df_node_encar_new = df_node_encar_new.reset_index(drop=True)

# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PROFDMND

df_profdmnd_0 = pd.read_csv(data_path_prv + '/profdmnd.csv').query('dmnd_pf_id not in %s'%([0]))
# df_profdmnd_test = aql.read_sql(db, sc, 'profdmnd', filt=[('dmnd_pf_id', [0], '!=')])
#df_profdmnd_0 = aql.read_sql(db, sc, 'profdmnd', filt=[('hy', [0])], limit=1)


df_dmnd_add = dfload_arch
df_dmnd_add_CH0 = dfload_arch_CH0
#
#df_dmnd_add = dfload_arch.loc[dfload_arch.nd_id.isin([{val: key for key, val in dict_nd_id.items()}[nd] for nd in df_nd_add.nd_id])]
#
#df_dmnd_add = dfcr_filt.loc[dfcr_filt.nd_id.isin([{val: key for key, val in dict_nd_id.items()}[nd] for nd in df_nd_add.nd_id])]
df_dmnd_add['nd_id'] = df_dmnd_add.nd_id.replace(dict_nd)
df_dmnd_add['ca_id'] = 0
df_dmnd_add = pd.merge(df_dmnd_add, df_def_profile[['pf_id', 'primary_nd']], left_on='nd_id', right_on='primary_nd')

df_dmnd_add = df_dmnd_add.rename(columns={'erg_tot': 'value', 'pf_id': 'dmnd_pf_id'})

df_dmnd_add_CH0['ca_id'] = 0
df_dmnd_add_CH0['pf_id'] = 0
df_dmnd_add_CH0['primary_nd'] = 'CH0'
df_dmnd_add_CH0 = df_dmnd_add_CH0.rename(columns={'erg_tot': 'value', 'pf_id': 'dmnd_pf_id'})

#df_dmnd_add['value'] = df_dmnd_add.value / 1e3

df_profdmnd = df_dmnd_add[df_profdmnd_0.columns.tolist()].reset_index(drop=True)
df_profdmnd_CH0 = df_dmnd_add_CH0[df_profdmnd_0.columns.tolist()].reset_index(drop=True)

# TODO REPLACE INSTEAD OF UPDATE
df_profdmnd_new = pd.concat([df_profdmnd_CH0,df_profdmnd_0,df_profdmnd])



# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~ PROFPRICE

# --> NO CHANGES! HOUSEHOLDS USE CH0 PRICE PROFILES


# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PROFSUPPLY
# 
df_profsupply = pd.read_csv(data_path_prv + '/profsupply.csv').head()

# df_profsupply = aql.read_sql(db, sc, 'profsupply', filt=[('hy', [0])], limit=1)

df_sup_add = df_pp_add.loc[df_pp_add.fl_id == 'photovoltaics', ['pp_id', 'nd_id']]
df_sup_add['canton'] = df_sup_add.nd_id.replace(dict_ct)
df_sup_add = df_sup_add[['canton']].drop_duplicates()
df_sup_add_new = pd.merge(df_sup_add, df_solar_canton_raw_1h, on='canton', how='inner')

dict_pf_id = df_def_profile_sup.set_index('pf')['pf_id'].to_dict()
#dict_pf_id = {ct: dict_pf_id['supply_' + ct + '_PHO'] for ct in list_ct}
dict_pf_id = {'avg_all': dict_pf_id['supply_' + 'avg_all' + '_PHO']}
df_sup_add_new['supply_pf_id'] = df_sup_add_new.canton.replace(dict_pf_id)

df_profsupply = df_sup_add_new[df_profsupply.columns.tolist()]


# %% ~~~~~~~~~~~~~~~~~~~~~~~ PLANT_ENCAR (needs profsupply data)

df_plant_encar = pd.read_csv(data_path_prv + '/plant_encar.csv')

# df_plant_encar = aql.read_sql(db, sc, 'plant_encar')

# Setting CH0 PV capacity to zero
df_plant_encar.loc[df_plant_encar.pp_id==dict_pp_id_all['CH_SOL_PHO'],
                   df_plant_encar.columns.str.contains('cap_pwr_leg')] = 0
# TODO choose for storage cap_pwr_leg

#dfpvbatt_costs = pd.read_csv(os.path.join(base_dir,'Costs/cost_tech_node.csv'),sep=';')
#dfpvbatt_costs = pd.read_csv(os.path.join(base_dir,'Costs/cost_tech_node_li12yr.csv'),sep=';')
# dfpvbatt_costs = pd.read_csv(os.path.join(base_dir,'Costs/cost_tech_node_li15yr.csv'),sep=';')
dfpvbatt_costs = pd.read_csv(os.path.join(base_dir+ '/archetype_disaggr/costs/cost_tech_node_li15yr.csv'),sep=';')

df_ppca_add = (dfpv_arch.set_index('nd_id_new')
                        .loc[df_nd_add.nd, ['cap_pv', 'cap_st_pwr']]
                        .rename(columns={'cap_pv': 'PHO',
                                         'cap_st_pwr': 'STO_LI'})
                        .stack().reset_index()
                        .rename(columns={'level_1': 'pt_id',
                                         'nd_id_new': 'nd_id',
                                         0: 'cap_pwr_leg'}))

    
#df_ppca_add_1 = pd.merge(df_ppca_add, dfpv_arch.reset_index(drop=True)[['pv_power_pot','nd_id_new']], left_on='nd_id', right_on='nd_id_new', how='inner')
df_ppca_add_1 = pd.merge(df_ppca_add, dfpv_arch.reset_index(drop=True)[['pv_power_tot_est','nd_id_new']], left_on='nd_id', right_on='nd_id_new', how='inner')

df_ppca_add_1 = df_ppca_add_1.drop(columns='nd_id_new')
#df_ppca_add_1.loc[df_ppca_add_1.pt_id.str.contains('STO_LI'),'pv_power_pot'] = 0
df_ppca_add_1.loc[df_ppca_add_1.pt_id.str.contains('STO_LI'),'pv_power_tot_est'] = 0

#    
#df_ppca_add = (dferg_filt.set_index('nd_id_new')
#                        .loc[df_nd_add.nd, ['cap_pv', 'cap_st_pwr']]
#                        .rename(columns={'cap_pv': 'PHO_SFH',
#                                         'cap_st_pwr': 'STO_SFH'})
#                        .stack().reset_index()
#                        .rename(columns={'level_1': 'pt_id',
#                                         'nd_id_new': 'nd_id',
#                                         0: 'cap_pwr_leg'}))

df_ppca_add['supply_pf_id'] = 'supply_' + df_ppca_add.nd_id.replace(dict_ct) + '_PHO'
df_ppca_add['pt_id'] = df_ppca_add['pt_id'] + '_' + df_ppca_add.nd_id.replace(dict_nd).str.slice(stop=3)

df_ppca_add.loc[~df_ppca_add.pt_id.str.contains('PHO'), 'supply_pf_id'] = None

df_ppca_add_2 = df_ppca_add.copy()
df_ppca_add = df_ppca_add.set_index(df_ppca_add.pt_id) 
#dfpvbatt_costs = dfpvbatt_costs.set_index(dfpvbatt_costs.pt_id).drop(columns=['nd_id','pt_id'])

df_ppca_add = pd.merge(dfpvbatt_costs,df_ppca_add_2, on=['pt_id','nd_id'])
#df_ppca_add = pd.concat([dfpvbatt_costs,df_ppca_add],axis=1)
df_ppca_add = df_ppca_add.reset_index(drop=True)

## sale and purches capacity is 110% of maximum
list_nd_0 = [nd_0 for nd_0, nd in dict_nd.items()
             if nd in df_def_node.nd.tolist()]

cap_prc = dfload_arch.loc[dfload_arch.nd_id.isin(list_nd_0)].pivot_table(index='nd_id', values='erg_tot', aggfunc='max') * 1
cap_prc = cap_prc.rename(columns={'erg_tot': 'cap_pwr_leg'}).reset_index().assign(supply_pf_id=None)
cap_prc = cap_prc.set_index(['nd_id'])

df_pp_add_1 = df_pp_add.set_index(['nd_id'])
cap_prc['pt_id'] = df_pp_add_1.loc[df_pp_add_1.pt_id.str.contains('PRC')].pt_id
cap_prc = cap_prc.reset_index()  


df_ppca_add = df_ppca_add.assign(ca_id=0, pp_eff=1,
                                 factor_lin_0=0, factor_lin_1=0,
                                 cap_avlb=1, vc_ramp=0,
                                 vc_om=0, erg_chp=None)

# translate to ids before joining pp_id column
for df, idx in [(df_def_pp_type, 'pt'), (df_def_node, 'nd'), (df_def_profile, ['pf', 'supply_pf'])]:
    df_ppca_add, _ = translate_id(df_ppca_add, df, idx)
df_ppca_add['supply_pf_id'] = pd.to_numeric(df_ppca_add.supply_pf_id)
join_idx = ['pt_id', 'nd_id']
df_ppca_add = (df_ppca_add.join(df_def_plant.set_index(join_idx)[['pp', 'pp_id']],
                                      on=join_idx))
list_cap = [c for c in df_plant_encar.columns if 'cap_pwr_leg' in c]
df_ppca_add = df_ppca_add.assign(**{cap: df_ppca_add.cap_pwr_leg for cap in list_cap})


df_plant_encar_1 = pd.concat([df_plant_encar, df_ppca_add])


df_plant_encar_1 = df_plant_encar_1.drop(columns=['nd_id','pt_id','pp'])
#df_plant_encar = df_ppca_add.loc[:, df_plant_encar.columns]

df_plant_encar_1 = df_plant_encar_1.set_index('pp_id')

for key, value in dict_pp_id_pho.items():
    df_plant_encar_1.loc[value, 'pwr_pot'] = dfpv_arch.loc[key[0:-4],'pv_power_tot_est']

# TODO REPLACE INSTEAD OF UPDATE

df_plant_encar_new = df_plant_encar_1.reset_index()  

# %% ~~~~~~~~~~~~~~~~~~~~ NODE_CONNECT

df_node_connect = pd.read_csv(data_path_prv + '/node_connect.csv')
# df_node_connect = aql.read_sql(db, sc, 'node_connect',
#                                 filt=[('nd_id', df_def_node.nd_id.tolist(), ' != ', ' AND '),
#                                       ('nd_2_id', df_def_node.nd_id.tolist(), ' != ', ' AND ')])

    
node_sfh = df_def_node.loc[df_def_node.nd.str.contains('SFH')].nd.values
node_mfh = df_def_node.loc[df_def_node.nd.str.contains('MFH')].nd.values
node_oco = df_def_node.loc[df_def_node.nd.str.contains('OCO')].nd.values
node_ind = df_def_node.loc[df_def_node.nd.str.contains('IND')].nd.values
#node_oth = df_def_node.loc[df_def_node.nd.str.contains('OTH')].nd.values

node_rur = df_def_node.loc[df_def_node.nd.str.contains('RUR')].nd.values
node_sub = df_def_node.loc[df_def_node.nd.str.contains('SUB')].nd.values
node_urb = df_def_node.loc[df_def_node.nd.str.contains('URB')].nd.values


#def get_cap_sllprc(sllprc):
#    dict_nd_id = df_def_node.set_index('nd_id')['nd'].to_dict()
#    df_cap = pd.merge(df_def_plant.loc[df_def_plant.pp.str.contains(sllprc)],
#                      df_plant_encar, on='pp_id', how='inner')
#    df_cap['nd_id'] = df_cap.nd_id.replace(dict_nd_id)
#    return df_cap.set_index('nd_id')['cap_pwr_leg']

def get_cap_sllprc(sllprc):
    dict_nd_id = df_def_node.set_index('nd_id')['nd'].to_dict()
    df_cap = pd.merge(df_def_plant.loc[df_def_plant.pp.str.contains(sllprc)],
                      df_plant_encar_new, on='pp_id', how='inner')
    df_cap['nd_id'] = df_cap.nd_id.replace(dict_nd_id)
    return df_cap.set_index('nd_id')['cap_pwr_leg']


df_cap = cap_prc.set_index('nd_id')['cap_pwr_leg']

df_cap_rur = df_cap[df_cap.index.str.contains('RUR')] * (1.05 + (1-(1-data['grid_losses'])**0.5))
df_cap_urb = df_cap[df_cap.index.str.contains('URB')] * (1.15 + (1-(1-data['grid_losses'])**0.5))
df_cap_sub = df_cap[df_cap.index.str.contains('SUB')] * (1.1  + (1-(1-data['grid_losses'])**0.5))

df_cap = pd.concat([df_cap_rur, df_cap_sub, df_cap_urb])
# external connection hh load+PV <-> grid
#data = dict(nd_id='CH0', nd_2_id=node_sfh, ca_id=0, mt_id='all')
data_sfh = dict(nd_id='CH0', nd_2_id=node_sfh, ca_id=0, mt_id='all')
data_mfh = dict(nd_id='CH0', nd_2_id=node_mfh, ca_id=0, mt_id='all')
data_oco = dict(nd_id='CH0', nd_2_id=node_oco, ca_id=0, mt_id='all')
data_ind = dict(nd_id='CH0', nd_2_id=node_ind, ca_id=0, mt_id='all')
#data_oth = dict(nd_id='CH0', nd_2_id=node_oth, ca_id=0, mt_id='all')

data_rur = dict(nd_id='CH0', nd_2_id=node_rur, ca_id=0, mt_id='all')
data_sub = dict(nd_id='CH0', nd_2_id=node_sub, ca_id=0, mt_id='all')
data_urb = dict(nd_id='CH0', nd_2_id=node_urb, ca_id=0, mt_id='all')


    
df_typ_gd = pd.concat([pd.DataFrame(data_rur), pd.DataFrame(data_sub),pd.DataFrame(data_urb)])
df_typ_gd = expand_rows(df_typ_gd, ['mt_id'], [range(12)])

df_typ_gd = pd.merge(df_typ_gd, df_cap.rename('cap_trmi_leg').reset_index(),
                    left_on='nd_2_id', right_on='nd_id', suffixes=('', '_temp')).drop('nd_id_temp', axis=1)
df_typ_gd = pd.merge(df_typ_gd, df_cap.rename('cap_trme_leg').reset_index(),
                    left_on='nd_2_id', right_on='nd_id', suffixes=('', '_temp')).drop('nd_id_temp', axis=1)

df_node_connect = df_typ_gd[df_node_connect.columns]

dft = pd.concat([df_def_node, pd.read_csv(data_path_prv + '/def_node.csv')])

for idx in [('nd'), (['nd', 'nd_2'])]:

    df_node_connect, _ = translate_id(df_node_connect, dft, idx)




# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ FUEL_NODE_ENCAR

df_fuel_node_encar_0 = pd.read_csv(data_path_prv + '/fuel_node_encar.csv')

# df_fuel_node_encar_0 = aql.read_sql(db, sc, 'fuel_node_encar')

df_flndca_add = df_ppca_add.copy()[['pp_id', 'ca_id']]
df_flndca_add = df_flndca_add.join(df_def_plant.set_index('pp_id')[['fl_id', 'nd_id']], on='pp_id')
df_flndca_add['nd_id'] = df_flndca_add.nd_id.replace(df_def_node.set_index('nd_id')['nd'].to_dict())
df_flndca_add['fl_id'] = df_flndca_add.fl_id.replace(df_def_fuel.set_index('fl_id')['fl'].to_dict())
df_flndca_add = df_flndca_add.drop('pp_id', axis=1).drop_duplicates()

# has_profile points to the nd_id for which the profile is defined
#df_flndca_add.loc[df_flndca_add.fl_id == 'electricity', 'pricesll_pf_id'] = 'pricesll_electricity_CH0_15min'
#df_flndca_add.loc[df_flndca_add.fl_id == 'electricity', 'pricebuy_pf_id'] = 'pricebuy_electricity_CH0_15min'

df_flndca_add.loc[df_flndca_add.fl_id == 'electricity', 'pricesll_pf_id'] = 'pricesll_electricity_CH0_1h'
df_flndca_add.loc[df_flndca_add.fl_id == 'electricity', 'pricebuy_pf_id'] = 'pricebuy_electricity_CH0_1h'

#df_flndca_add.loc[df_flndca_add.fl_id == 'electricity', 'pricesll_pf_id'] = 'pricesll_electricity_CH0'
#df_flndca_add.loc[df_flndca_add.fl_id == 'electricity', 'pricebuy_pf_id'] = 'pricebuy_electricity_CH0'

df_fuel_node_encar = df_flndca_add.reindex(columns=df_fuel_node_encar_0.columns)


fill_cols = [c for c in df_fuel_node_encar.columns
             if any(pat in c for pat in ['vc_fl', 'erg_inp'])]
df_fuel_node_encar[fill_cols] = df_fuel_node_encar[fill_cols].fillna(0)



for df, idx in [(df_def_fuel, 'fl'), (df_def_node, 'nd')]:
#                (df_def_profile_prc, ['pf', 'pricesll_pf']),
#                (df_def_profile_prc, ['pf', 'pricebuy_pf'])]:
    df_fuel_node_encar, _ = translate_id(df_fuel_node_encar, df, idx)



# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DF_PROFPRICE

df_profprice = pd.read_csv(data_path_prv + '/profprice.csv') 
# df_profprice = aql.read_sql(db, sc, 'profprice') 
# %% ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DF_PROFPRICE
#list_pf = df_def_profile_0.loc[df_def_profile_0.pf.str.contains('pricebuy_electricity_CH0|pricesll_electricity_CH0')].pf_id.tolist()
#
#df_profprice_0 = aql.read_sql(db, sc, 'profprice', filt=[('price_pf_id', list_pf)])
#
#def expand(df):
#
#    df_ret = pd.merge(df_profsupply[['hy']].drop_duplicates(), df,
#                      on='hy', how='outer')
#    df_ret['price_pf_id'] = df_ret.price_pf_id.fillna(method='ffill')
#
#    df_ret.value = df_ret.value.interpolate()
#
#    return df_ret
#
#df_profprice = df_profprice_0.assign(hy=df_profprice_0.hy.astype(float)).groupby('price_pf_id').apply(expand).reset_index(drop=True)
#df_profprice = pd.merge(df_profprice, df_def_profile_0[['pf_id', 'pf']], left_on='price_pf_id', right_on='pf_id', how='left')
##df_profprice['pf'] = df_profprice.pf + '_15min'
#df_profprice['pf'] = df_profprice.pf + '_1h'
#df_profprice = df_profprice.drop(['pf_id', 'price_pf_id'], axis=1)
#df_profprice = df_profprice.join(df_def_profile_prc.set_index('pf').pf_id.rename('price_pf_id'), on='pf').drop('pf', axis=1)
#
#df_profprice = df_profprice[df_profprice_0.columns]

# %%

#df_node_encar_new
#df_profdmnd_new
#df_plant_encar_new

# list_tb_col = [
#            (df_plant_encar_new, 'plant_encar', ['pp_id', 'ca_id'])
#            ]

# list_tb_new = [
#            (df_node_encar_new, 'node_encar', ['nd_id', 'ca_id']),
#            (df_profdmnd_new, 'profdmnd', ['dmnd_pf_id']),
#            (df_plant_encar_new, 'plant_encar', ['pp_id', 'ca_id']),
#            ]

# list_tb = [(df_fuel_node_encar, 'fuel_node_encar', ['nd_id', 'fl_id', 'ca_id']),
#            (df_node_encar_new, 'node_encar', ['nd_id', 'ca_id']),
#            (df_profdmnd_new, 'profdmnd', ['dmnd_pf_id']),
#            (df_profsupply, 'profsupply', ['supply_pf_id']),
#            (df_profprice, 'profprice', ['price_pf_id']),
#            (df_node_connect, 'node_connect', ['nd_id', 'nd_2_id']),
#            (df_plant_encar_new, 'plant_encar', ['pp_id', 'ca_id']),
#            (df_def_plant, 'def_plant', ['pp_id']),
#            (df_def_node, 'def_node', ['nd_id']),
# #          (df_def_fuel, 'def_fuel', ['fl_id']), <-- NO CHANGE
#            (df_def_pp_type, 'def_pp_type', ['pt_id']),
#            (df_def_profile, 'def_profile', ['pf_id'])
#            ]

# # tables with foreign keys first
# #df, tb, ind = (df_def_plant, 'def_plant', ['pp_id'])

# df, tb = (df_plant_encar_new, 'plant_encar')
# append_new_cols(df, tb)

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
                'def_pp_type':df_def_pp_type,
                'fuel_node_encar': df_fuel_node_encar,
                'profsupply': df_profsupply,
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
    
    

