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
import model_loop_modifier_archetype_disaggr as model_loop_modifier

#from pyAndy import PlotPageData, PlotTiled

import logging

logger = logging.getLogger('grimsel')
logger.setLevel(logging.INFO)



# sc_inp currently only used to copy imex_comp and priceprof_comp to sc_out
sc_inp = config.SCHEMA
db = config.DATABASE

sc_out = os.path.abspath('......../output/12h_pvopt_stscen_lin_trnsscen_comp.hdf')


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
# ~~~~~


excl_pt = [
# '%PRC%', '%SLL%',
# '%%STO%SFH',
# '%PHO',
# '%PHO_SFH%',
# '%GAS_NEW%',
# '%GAS_LIN%',
# '%NUC%', '%HCO%', '%LIG%',
# '%LOL%',
# '%HYD_RES%',
# '%HYD_ST%',
# '%HYD_ROR%',
# '%OIL%', '%GEO%', '%BAL%', '%BIO%', '%WAS%', '%WIN%'
 ]

slct_pt = pd.read_csv(os.path.join(config.PATH_CSV, 'def_pp_type.csv'))
slct_pt = slct_pt.loc[~slct_pt.pt.str.contains('|'.join([pt.replace('%', '')
                      for pt in excl_pt]))].pt.tolist()

nd_nt = df_def_node.loc[df_def_node.nd.isin([ 'AT0', 'IT0', 'FR0', 'DE0'])].nd_id.tolist()
nd_ch0 = df_def_node.loc[df_def_node.nd.isin(['CH0'])].nd_id.tolist()
nd_nt_ch0 = nd_nt + nd_ch0
nd_arch = df_def_node.loc[~df_def_node.nd.isin(['CH0', 'AT0', 'IT0', 'FR0', 'DE0'])].nd_id.tolist()
nd_arch_ch = nd_ch0 + nd_arch
# additional kwargs for the model
mkwargs = {
           'slct_encar': ['EL'],
           'slct_node': ['CH0', 'AT0', 'IT0', 'FR0', 'DE0',
                            'IND_RUR',
                            'IND_SUB',
                            'IND_URB',
                            'MFH_RUR',
                            'MFH_SUB',
                            'MFH_URB',
                            'OCO_RUR',
                            'OCO_SUB',
                            'OCO_URB',
                            'OTH_TOT',
                            'SFH_RUR',
                            'SFH_SUB',
                            'SFH_URB',
                                    ],
           'nhours': 12,
           'slct_pp_type': slct_pt,
#           'skip_runs': True,
           'tm_filt': [
#                   ('mt_id', [6]),
#                       ('wk_id', [26]),
#                       ('day', [1]),
#			('hour', [12]),
#                       ('hom', [0]),
#                       ('hour', range(1,25,6))
#                   ('hom', range(24))
           ],
           'symbolic_solver_labels': True,
           'constraint_groups': MB.get_constraint_groups(excl=['ror','supply']),
           'nthreads': 8
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
            'output_target': 'hdf5',
            'dev_mode': True
           }

nsteps_default = [('swfy', 8, np.arange),    # future years
                  ('swch', 1, np.arange),    # swiss scenarios
                  ('swst', 3, np.arange),    # storage scenarios
                  ('swtr', 3, np.arange),    # transmissions scenarios
                  ]

mlkwargs = {#'sc_inp': 'lp_input_levels',
            'db': db,
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

# %

ml.m.get_setlst()
ml.m.define_sets()

# %

ml.m.add_parameters()

ml.m.define_variables()
# %

ml.m.add_all_constraints()


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
                      in set_to_list(self.ndcnn, [nd_arch, nd, ca]))
               )
               
        dmnd += (self.dmnd[sy, nd, ca] 
                + sum(self.pwr_st_ch[sy, st, ca] for (st, nd, ca)
                  in set_to_list(self.st_ndca, [None, nd, ca]))) * (1 + self.grid_losses[nd, ca])
        
        exports += (sum(get_transmission(sy, nd, nd_2, ca, True) * ((1 - self.grid_losses[nd, ca])**0.5)
                  / self.nd_weight[nd]
                      for (nd, nd_2, ca)
                      in set_to_list(self.ndcnn, [nd, nd_arch, ca]))
                + sum(get_transmission(sy, nd, nd_2, ca, True)
                  / self.nd_weight[nd]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [nd, nd_nt, ca])))
        
    elif nd in nd_arch:
        prod += (
                sum(get_transmission(sy, nd, nd_2, ca, False) * ((1 - self.grid_losses[nd, ca])**0.5)
                  / self.nd_weight[nd_2]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [None, nd, ca]))
                )
        dmnd += (self.dmnd[sy, nd, ca] 
                + sum(self.pwr_st_ch[sy, st, ca] for (st, nd, ca)
                  in set_to_list(self.st_ndca, [None, nd, ca])))
        
        exports += sum(get_transmission(sy, nd, nd_2, ca, True) * ((1 - self.grid_losses[nd, ca])**0.5)
                    / self.nd_weight[nd]
                  for (nd, nd_2, ca)
                  in set_to_list(self.ndcnn, [nd, None, ca]))
        
    # demand of plants using ca as an input
    ca_cons = (po.ZeroConstant if not self.pp_ndcaca else
               sum(self.pwr[sy, pp, ca_out] / self.pp_eff[pp, ca_out]
                   for (pp, nd, ca_out, ca)
                   in set_to_list(self.pp_ndcaca,
                                  [None, nd, None, ca])))
    gl = (self.grid_losses[nd, ca] if hasattr(self, 'grid_losses')
          else po.ZeroConstant)

    return prod == dmnd + ca_cons * (1 + gl) + exports

self.cadd('supply', self.sy_ndca, rule=supply_rule)

#ml.m.supply[(0,5,0)].deactivate()


ml.m.init_solver()

# %

ml.io.init_output_tables()

ml.select_run(0)

# init ModelLoopModifier
mlm = model_loop_modifier.ModelLoopModifier(ml)

self = mlm

# starting row of loop
irow_0 = ml.io.resume_loop if ml.io.resume_loop else 0

# loop over all rows of the resulting ml.df_def_run;
# corresponding modifications to the model a.exitt()re performed here;
# the model run method is called at the end
irow = 0

for irow in list(range(irow_0, len(ml.df_def_run))):
    run_id = irow

    ml.select_run(run_id)

    logger.info('reset_parameters')
    ml.m.reset_all_parameters()

    logger.info('select_swiss_scenarios')
    slct_ch = mlm.select_swiss_scenarios()
    
    logger.info('select_storage_scenarios')
    slct_st = mlm.select_storage_scenarios()
    
    logger.info('select_transmission_scenarios')
    slct_tr = mlm.select_transmission_scenarios()

    logger.info('set_future_year')
    mlm.set_future_year(slct_ch=slct_ch, slct_tr=slct_tr, slct_st=slct_st)#, slct_tr=slct_tr)
    logger.info('keep_cap_new')
    mlm.keep_cap_new()
    #########################################
    ############### RUN MODEL ###############

    logger.info('fill_peaker_plants')
    ml.m.fill_peaker_plants(demand_factor=5,
#                            list_peak=[(ml.m.mps.dict_pp_id['CH_GAS_LIN'], 0)]
                            )

    logger.info('_limit_prof_to_cap')
    ml.m._limit_prof_to_cap()

    ml.perform_model_run(warmstart=False)
    
    for fn in [f for f in list(os.walk('.'))[0][2] if f.startswith('tmp')]:
        os.remove(fn)
