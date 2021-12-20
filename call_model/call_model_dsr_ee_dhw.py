#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 16:38:56 2019

@author: arthurrinaldi
"""

import sys, os, socket

import numpy as np
import pandas as pd
from importlib import reload

import grimsel_config as config


import pyomo.environ as po

import grimsel.core.model_loop as model_loop
from grimsel.core.model_base import ModelBase as MB
from grimsel.core.io import IO as IO
from grimsel.auxiliary.aux_m_func import set_to_list


import grimsel.core.io as io
import model_loop_modifier_dsr_ee_dhw as model_loop_modifier

#from pyAndy import PlotPageData, PlotTiled

import logging

logger = logging.getLogger('grimsel')
logger.setLevel(logging.INFO)



# sc_inp currently only used to copy imex_comp and priceprof_comp to sc_out
sc_inp = config.SCHEMA
db = config.DATABASE


sc_out = os.path.abspath('....../output/test_multi_1')

# %%
IO._close_all_hdf_connections()

reload(model_loop)
reload(model_loop_modifier)
reload(config)

# ~~~~~ ADD nd_weight TO DEF_NODE
path_dfnd = os.path.join(config.PATH_CSV, 'def_node.csv')
df_def_node = pd.read_csv(path_dfnd)
df_def_node = df_def_node[[c for c in df_def_node.columns if not 'Unnamed' in c]]
df_def_node['nd_weight'] = 1 
#(df_def_node.nd.where( df_def_node.nd.str.contains('SFH'), 1).where(~df_def_node.nd.str.contains('SFH'), 10))
                                          
df_def_node.to_csv(path_dfnd, index=False)
#

# ~~~~~
path_coppr = os.path.join(config.PATH_CSV, 'def_cop_35.csv')
df_def_cop_35 = pd.read_csv(path_coppr)
df_def_cop_35['DateTime'] = pd.to_datetime(df_def_cop_35.DateTime)

path_coppr = os.path.join(config.PATH_CSV, 'def_cop_60.csv')
df_def_cop_60 = pd.read_csv(path_coppr)
df_def_cop_60['DateTime'] = pd.to_datetime(df_def_cop_60.DateTime)

path_coppr = os.path.join(config.PATH_CSV, 'def_cop_60_dhw.csv')
df_def_cop_60_dhw = pd.read_csv(path_coppr)
df_def_cop_60_dhw['DateTime'] = pd.to_datetime(df_def_cop_60_dhw.DateTime)

df_def_cop_mean = pd.merge(df_def_cop_35,df_def_cop_60,on=['DateTime','doy','pp_id','hy']).assign(
        value = lambda x: (x.value_x+x.value_y)/2)
excl_pt = [
#  '%PRC%', '%SLL%',
# # '%%STO%SFH',
#   '%PHO',
# ## '%PHO_SFH%',
#   '%GAS_NEW%',
#   '%GAS_LIN%',
#   '%NUC%', '%HCO%', '%LIG%',
# # '%LOL%',
#     '%HYD_RES%',
#     '%HYD_ST%',
#     '%HYD_ROR%',
#   '%OIL%', '%GEO%', '%BAL%', '%BIO%', '%WAS%', '%WIN%',
#     '%HP%',
# # '%CAES%',
#    '%STO_LI%',
#   '%STO_VR%',
# # #  '%DMND_FLE%',
#    # '%HT%',
'%STO_HT%',
# '%BO%',
# '%DHW_STO%',
# '%DHW_AW%',
# '%DHW_WW%',
 ]

if excl_pt == []:
    slct_pt = pd.read_csv(os.path.join(config.PATH_CSV, 'def_pp_type.csv')).pt.tolist()
else:
    slct_pt = pd.read_csv(os.path.join(config.PATH_CSV, 'def_pp_type.csv'))
    slct_pt = slct_pt.loc[np.invert(slct_pt.pt.str.contains('|'.join([pt.replace('%','') for pt in excl_pt])))].pt.tolist()
slct_pt
# %%
nd_nt = df_def_node.loc[df_def_node.nd.isin([ 'AT0', 'IT0', 'FR0', 'DE0'])].nd_id.tolist()
nd_ch0 = df_def_node.loc[df_def_node.nd.isin(['CH0'])].nd_id.tolist()
nd_nt_ch0 = nd_nt + nd_ch0
nd_arch = df_def_node.loc[np.invert(df_def_node.nd.isin(['CH0', 'AT0', 'IT0', 'FR0', 'DE0']))].nd_id.tolist()
nd_arch_ht = df_def_node.loc[df_def_node.nd.str.contains('HT')].nd_id.tolist()
nd_arch_dsr = df_def_node.loc[df_def_node.nd.str.contains('DSR')].nd_id.tolist()
nd_arch_el = list(set(nd_arch) - set(nd_arch_ht) - set(nd_arch_dsr))
nd_arch_el_res = df_def_node.loc[df_def_node.nd.str.contains('SFH|MFH')].nd_id.tolist()
nd_arch_el_res = list(set(nd_arch_el_res) - set(nd_arch_ht))
nd_arch_ch = nd_ch0 + nd_arch
nd_arch_ht_str = df_def_node.loc[df_def_node.nd.str.contains('HT')].nd.tolist()
nd_arch_not_ht_str = df_def_node.loc[np.invert(df_def_node.nd.str.contains('HT'))].nd.tolist()
nd_all_str = df_def_node.nd.tolist()
nd_arch_el_res_str = df_def_node.loc[(df_def_node.nd.str.contains('SFH|MFH'))&~(df_def_node.nd.str.contains('HT'))].nd.tolist()
nd_arch_dsr_str = df_def_node.loc[df_def_node.nd.str.contains('DSR')].nd.tolist()

path_dfplant = os.path.join(config.PATH_CSV, 'def_plant.csv')
df_def_plant = pd.read_csv(path_dfplant)
pp_hp_aw = df_def_plant.loc[df_def_plant.pp.str.contains('HP_AW')].pp_id.tolist()
pp_hp_ww = df_def_plant.loc[df_def_plant.pp.str.contains('HP_WW')].pp_id.tolist()

nhours_dict_ht = {nd : (24,24) for nd in nd_arch_ht_str} 
# nhours_dict_el = {nd: (12,12) for nd in nd_arch_not_ht_str}
# nhours_dict_el_res = {nd: (24,24) for nd in nd_arch_el_res_str}
# nhours_dict_el_res_12h = {nd: (12,12) for nd in nd_arch_el_res_str}
nhours_dict_dsr = {nd: (24,24) for nd in nd_arch_dsr_str}
# nhours_dict = dict(nhours_dict_el,**nhours_dict_ht)
nhours_dict = dict(nhours_dict_dsr,**nhours_dict_ht)

# additional kwargs for the model
mkwargs = {
           'slct_encar': 
                # ['EL','AW','WW'],
                # ['EL','HW','HA','HB'],
                # ['EL','HA','HB'],
                ['EL','AW','WW','HW','HA','HB'],
                # ['EL','AW','WW','HA','HB'],
                # ['EL','HW'],
                # ['EL'],
           'slct_node': 
#               ['FR0', 'DE0'],
                        nd_all_str,
#                       ['CH0', 'AT0', 'IT0', 'FR0', 'DE0',
# #                            'IND_RUR',
# ##                            'IND_SUB',
# ##                            'IND_URB',
# ###                            'MFH_RUR',
# ###                            'MFH_SUB',
# ###                            'MFH_URB',
# ###                            'OCO_RUR',
# #                            'OCO_SUB',
# ###                            'OCO_URB',
# ###                            'SFH_RUR',
# ###                            'SFH_SUB',
# ###                            'SFH_URB',
# ##                                    ],
#                 # ['CH0','SFH_SUB_2'],
                # ['CH0','SFH_SUB_2','MFH_RUR_2'],
#                 # ['CH0','SFH_SUB_2','SFH_SUB_HT_2'],
                # ['CH0','IND_SUB','SFH_SUB_2','SFH_SUB_2_DSR'],
#                 # ['CH0','SFH_SUB_2','SFH_SUB_2_DSR','SFH_SUB_HT_2'],
#                 # ['CH0','IND_SUB','SFH_SUB_2'],
#                 'SFH_SUB_2','SFH_SUB_2_DSR','SFH_SUB_HT_2',
#                 'MFH_SUB_2','MFH_SUB_2_DSR','MFH_SUB_HT_2',
#                 'IND_SUB','OCO_SUB'],#'MFH_RUR_2','MFH_RUR_HT_2'],
            'nhours':nhours_dict,
            # 'nhours':nhours_dict_ht,
            # 'nhours':nhours_dict_el_res_12h,
#               {**{'CH0': 24, 'SFH_SUB_2': 24}, **nhours_dict_ht},
#               1,
           'slct_pp_type': slct_pt,
#           'skip_runs': True,
           'tm_filt': [
                    ('mt_id', [0]),
# #                       ('wk_id', [2,26]),
                        ('day', [1,4]),
##			('hour', [12]),
#                       ('hom', [0]),
#                       ('hour', range(1,25,6))
#                   ('hom', range(24))
           ],
           'symbolic_solver_labels': False, # Set to True for debugging (set name to pyomo indices in cplex files)
           'constraint_groups': 
               MB.get_constraint_groups(excl=['ror','supply']),#BE CAREFUL WITH THIS
#               'chp','chp_new']),
           'nthreads': 2, # Only passed to CPLEX 
           'keepfiles': False, # Set to True to keep tmp files
           }

# additional kwargs for the i/o
iokwargs = {'sc_warmstart': False,
            'cl_out': sc_out,
            'resume_loop': False,
#            'data_path': PATH_CSV,
            'no_output': False,
            'replace_runs_if_exist': False,
            'autocomplete_curtailment': False,
            'sql_connector': None,
            'data_path': config.PATH_CSV,
            'output_target': 'fastparquet',#'fastparquet',#'hdf5',#
            'dev_mode': True
           }

nsteps_default = [('swfy', 8, np.arange),    # future years
                  ('swch', 1, np.arange),    # swiss scenarios
                  ('swhp', 3, np.arange),    # heatpumps scenarios
                  ('swtr', 5, np.arange),    # transmissions scenarios
                  ('swrf', 3, np.arange),    # retrofit scenario
                  ('swdpf', 2, np.arange),    # original, EE loads

                  
                  ]

mlkwargs = {#'sc_inp': 'lp_input_levels',
#            'db': db,
            'nsteps': nsteps_default,
            }

ml = model_loop.ModelLoop(**mlkwargs, mkwargs=mkwargs, iokwargs=iokwargs)
self = ml.m
ml.init_run_table()
# %

ml.io.read_model_data()

# %
ml.m.init_maps()

ml.m.map_to_time_res()


# %
ml.io.write_runtime_tables()


ml.m.get_setlst()
ml.m.define_sets()


ml.m.add_parameters()

ml.m.define_variables()
# %

ml.m.add_all_constraints()

#%%
# MB.delete_component(self,comp_name='supply')

df_cop_35 = df_def_cop_mean.loc[df_def_cop_mean.pp_id.isin([i for i in self.pp])]

df_cop_60_dhw = df_def_cop_60_dhw.loc[df_def_cop_60_dhw.pp_id.isin([i for i in self.pp])]

list_pp_cop = df_cop_35.pp_id.unique()
list_pp_hp = self.df_def_plant.loc[df_def_plant.pp.str.contains('HP')].pp_id.to_list()
list_pp_hp_eff =  list(set(list_pp_hp) - set(list_pp_cop))
list_pp_cop = list(set(list_pp_hp) - set(list_pp_hp_eff))

list_pp_dhw_cop = df_cop_60_dhw.pp_id.unique()
list_pp_hp_dhw = self.df_def_plant.loc[df_def_plant.pp.str.contains('DHW_AW|DHW_WW')].pp_id.to_list()
list_pp_hp_dhw_eff =  list(set(list_pp_hp_dhw) - set(list_pp_dhw_cop))
list_pp_dhw_cop = list(set(list_pp_hp_dhw) - set(list_pp_hp_dhw_eff))

list_pp_dhw_bo = self.df_def_plant.loc[df_def_plant.pp.str.contains('DHW_BO')].pp_id.to_list()
#def add_supply_rules(self):

def get_transmission(sy, nd, nd_2, ca, export=True):
            '''
            If called by supply rule, the order nd, nd_2 is always the ndcnn
            order, therefore also trm order.

            * **Case 1**: ``nd`` has higher time resolution (min) |rarr| just
              use ``trm[tm, sy, nd, nd_2, ca]``
            * **Case 2**: ``nd`` has lower time resolution (not min) |rarr|
              average ``avg(trm[tm, sy_2, nd, nd_2, ca])`` for all ``sy_2``
              defined by the
               ``grimsel.core.model_base.ModelBase.dict_sysy[nd, nd_2, sy]``

            Parameters
            ----------
            sy : int
                current time slot in nd
            nd : int
                outgoing node
            nd_2 : int
                incoming node
            ca : int
                energy carrier
            export : bool
                True if export else False

            '''
            if self.is_min_node[(nd if export else nd_2,
                                 nd_2 if export else nd)]:
                trm = self.trm[sy, nd, nd_2, ca]
                return trm

            else: # average over all of the other sy
                list_sy2 = self.dict_sysy[nd if export else nd_2,
                                          nd_2 if export else nd, sy]

                avg = 1/len(list_sy2) * sum(self.trm[_sy, nd, nd_2, ca]
                                            for _sy in list_sy2)
                return avg


def supply_rule(self, sy, nd, ca):
    ''' Balance supply/demand '''

    list_neg = self.sll | self.curt
#            list_dmnd_keys = self.dmnd.iterkeys()    
    prod = (# power output; negative if energy selling plant
                sum(self.pwr[sy, pp, ca]
                    * (-1 if pp in list_neg else 1)
                    for (pp, nd, ca)
                    in set_to_list(self.ppall_ndca, [None, nd, ca])))
    
    dmnd = 0
    exports = 0  
    if nd in nd_nt:
        prod += (
                # incoming inter-node transmission
               sum(get_transmission(sy, nd, nd_2, ca, False)
                      / self.nd_weight[nd_2]
                      for (nd, nd_2, ca)
                      in set_to_list(self.ndcnn, [None, nd, ca]))
               )
               
        dmnd += (self.dmnd[sy, nd, ca] 
                + sum(self.pwr_st_ch[sy, st, ca] for (st, nd, ca)
                  in set_to_list(self.st_ndca, [None, nd, ca]))) * (1 + self.grid_losses[nd, ca])
        
        exports += sum(get_transmission(sy, nd, nd_2, ca, True)
                  / self.nd_weight[nd]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [nd, None, ca]))
    
    elif nd in nd_ch0:
        prod += (
                # incoming inter-node transmission
               sum(get_transmission(sy, nd, nd_2, ca, False)
                      / self.nd_weight[nd_2]
                      for (nd, nd_2, ca)
                      in set_to_list(self.ndcnn, [nd_nt, nd, ca]))
               + sum(get_transmission(sy, nd, nd_2, ca, False) * ((1 - self.grid_losses[nd, ca])**0.5)
                      / self.nd_weight[nd_2]
                      for (nd, nd_2, ca)
                      in set_to_list(self.ndcnn, [nd_arch_el, nd, ca]))
               )
               
        dmnd += (self.dmnd[sy, nd, ca] 
                + sum(self.pwr_st_ch[sy, st, ca] for (st, nd, ca)
                  in set_to_list(self.st_ndca, [None, nd, ca]))) * (1 + self.grid_losses[nd, ca])
        
        exports += (sum(get_transmission(sy, nd, nd_2, ca, True) * ((1 - self.grid_losses[nd, ca])**0.5)
                  / self.nd_weight[nd]
                      for (nd, nd_2, ca)
                      in set_to_list(self.ndcnn, [nd, nd_arch_el, ca]))
                + sum(get_transmission(sy, nd, nd_2, ca, True)
                  / self.nd_weight[nd]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [nd, nd_nt, ca])))
        
    elif nd in nd_arch_el:
        prod += (
                sum(get_transmission(sy, nd, nd_2, ca, False) * ((1 - self.grid_losses[nd, ca])**0.5)
                  / self.nd_weight[nd_2]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [None, nd, ca]))
                )
        dmnd += (self.dmnd[sy, nd, ca] 
                + sum(self.pwr_st_ch[sy, st, ca] for (st, nd, ca)
                  in set_to_list(self.st_ndca, [None, nd, ca])))
        
        exports += (sum(get_transmission(sy, nd, nd_2, ca, True) * ((1 - self.grid_losses[nd, ca])**0.5)
                    / self.nd_weight[nd]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [nd, nd_ch0, ca]))
                + sum(get_transmission(sy, nd, nd_2, ca, True)
                    / self.nd_weight[nd]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [nd, nd_arch_ht + nd_arch_dsr, ca])))
    
    elif nd in nd_arch_ht:
        prod += (
                # incoming inter-node transmission
               sum(get_transmission(sy, nd, nd_2, ca, False)
                      / self.nd_weight[nd_2]
                      for (nd, nd_2, ca)
                      in set_to_list(self.ndcnn, [None, nd, ca]))
               )
               
        dmnd += (self.dmnd[sy, nd, ca] 
                + sum(self.pwr_st_ch[sy, st, ca] for (st, nd, ca)
                  in set_to_list(self.st_ndca, [None, nd, ca])))
        
        exports += sum(get_transmission(sy, nd, nd_2, ca, True)
                  / self.nd_weight[nd]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [nd, None, ca]))
    
    elif nd in nd_arch_dsr:
        prod += (
                # incoming inter-node transmission
               sum(get_transmission(sy, nd, nd_2, ca, False)
                      / self.nd_weight[nd_2]
                      for (nd, nd_2, ca)
                      in set_to_list(self.ndcnn, [None, nd, ca]))
               )
               
        dmnd += (self.dmnd[sy, nd, ca] 
                + sum(self.pwr_st_ch[sy, st, ca] for (st, nd, ca)
                  in set_to_list(self.st_ndca, [None, nd, ca])))
        
        exports += sum(get_transmission(sy, nd, nd_2, ca, True)
                  / self.nd_weight[nd]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [nd, None, ca]))
        
    # demand of plants using ca as an input
    ca_cons = (po.ZeroConstant if not self.pp_ndcaca else
               sum(self.pwr[sy, pp, ca_out] / self.pp_eff[pp, ca_out]
                   for (pp, nd, ca_out, ca)
                   in set_to_list(self.pp_ndcaca,
                                  [list_pp_hp_eff + list_pp_dhw_bo + list_pp_hp_dhw_eff, nd, None, ca])))
    ca_cons += (po.ZeroConstant if not self.pp_ndcaca else
                sum(self.pwr[sy, pp, ca_out] / df_cop_35.loc[(df_cop_35.pp_id == pp) &
                    (df_cop_35.doy == self.df_tm_soy_full.loc[(self.df_tm_soy_full.sy == sy) & (self.df_tm_soy_full.tm_id == 1)].doy.reset_index(drop=True)[0])].reset_index(drop=True).value[0]
                   for (pp, nd, ca_out, ca)
                   in set_to_list(self.pp_ndcaca,
                                  [list_pp_cop, nd, None, ca])))
    ca_cons += (po.ZeroConstant if not self.pp_ndcaca else
                sum(self.pwr[sy, pp, ca_out] / df_cop_60_dhw.loc[(df_cop_60_dhw.pp_id == pp) &
                    (df_cop_60_dhw.doy == self.df_tm_soy_full.loc[(self.df_tm_soy_full.sy == sy) & (self.df_tm_soy_full.tm_id == 1)].doy.reset_index(drop=True)[0])].reset_index(drop=True).value[0]
                   for (pp, nd, ca_out, ca)
                   in set_to_list(self.pp_ndcaca,
                                  [list_pp_dhw_cop, nd, None, ca])))
    gl = (self.grid_losses[nd, ca] if hasattr(self, 'grid_losses')
          else po.ZeroConstant)

    return prod == dmnd + ca_cons * (1 + gl) + exports

self.cadd('supply', self.sy_ndca, rule=supply_rule)

pp_hp_aw = sorted(self.df_def_plant.loc[self.df_def_plant.pp.str.contains('HP_AW')].pp_id.tolist())
pp_hp_ww = sorted(self.df_def_plant.loc[self.df_def_plant.pp.str.contains('HP_WW')].pp_id.tolist())

nd_arch_ht = sorted(self.df_def_node.loc[self.df_def_node.nd.str.contains('HT')].nd_id.unique().tolist())
nd_arch_dsr = sorted(self.df_def_node.loc[self.df_def_node.nd.str.contains('DSR')].nd_id.unique().tolist())
nd_arch_res = sorted(self.df_def_node.loc[self.df_def_node.nd.str.contains('SFH|MFH')].nd_id.unique().tolist())
nd_arch_el_res = sorted(list(set(nd_arch_res) - set(nd_arch_ht) - set(nd_arch_dsr)))


for sy in np.linspace(0.0,ml.m.sy.last(),num=int(ml.m.sy.last()+1.0)):
    for nd_el, nd_ht, hp_aw, hp_ww in zip(nd_arch_el_res,nd_arch_ht,pp_hp_aw,pp_hp_ww):
        ml.m.trm[(int(sy), nd_el, nd_ht, 0)].setub(
                     (ml.m.cap_pwr_leg[(hp_aw, 1)]/df_cop_35.loc[(df_cop_35.pp_id == hp_aw)].value.max()+ml.m.cap_pwr_leg[(hp_ww, 2)]/ml.m.pp_eff[(hp_ww, 2.0)])) # with aw and ww energy carier


#%%
ml.m.init_solver()

# %

ml.io.init_output_tables()

ml.select_run(0)

# init ModelLoopModifier
mlm = model_loop_modifier.ModelLoopModifier(ml)

self = mlm

#%% Multiprocessing or not
    
def run_model(run_id):
#for irow in list(range(irow_0, len(ml.df_def_run))):
#    run_id = irow

    ml.select_run(run_id)

    logger.info('reset_parameters')
    ml.m.reset_all_parameters()

    logger.info('select_swiss_scenarios')
    slct_ch = mlm.select_swiss_scenarios()
    
    logger.info('select_hp_scenarios')
    slct_hp = mlm.select_hp_scenarios()
#    
    logger.info('select_transmission_scenarios')
    slct_tr = mlm.select_transmission_scenarios()

    logger.info('select_retrofit_scenarios')
    slct_rf = mlm.select_retrofit_scenarios()

    logger.info('select_demand_profile_res')
    slct_dpf = mlm.select_demand_profile_res()
#    
    logger.info('set_future_year')
    mlm.set_future_year(slct_ch=slct_ch, slct_tr=slct_tr, slct_hp=slct_hp,slct_rf=slct_rf, slct_dpf=slct_dpf)#, slct_st=slct_st)#, slct_tr=slct_tr)
    
    logger.info('keep_cap_new')
    mlm.keep_cap_new()
#    #########################################
    ############### RUN MODEL ###############

    logger.info('fill_peaker_plants')
    ml.m.fill_peaker_plants(demand_factor=5,
#                            list_peak=[(ml.m.mps.dict_pp_id['CH_GAS_LIN'], 0)]
                            )

    logger.info('_limit_prof_to_cap')
    ml.m._limit_prof_to_cap()

    ml.perform_model_run(warmstart=False)
    
#    for fn in [f for f in list(os.walk('.'))[0][2] if f.startswith('tmp')]:
#        os.remove(fn)

from grimsel.auxiliary.multiproc import run_parallel, run_sequential
print('RUNNING')
run_parallel(ml, run_model, 3, groupby=['swhp','swrf','swdpf','swtr'], adjust_logger_levels=True)
# run_sequential(ml, run_model)


