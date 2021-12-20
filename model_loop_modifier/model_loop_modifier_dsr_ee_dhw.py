#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 16:54:18 2019

@author: arthurrinaldi
"""

# -*- coding: utf-8 -*-
"""
Created on Fri Jul  6 11:23:06 2018

@author: martin-c-s
"""
import sys, os, socket
import pandas as pd
import numpy as np
import logging
from glob import glob

import pyomo.environ as po

from grimsel.core.io import IO
import grimsel.auxiliary.sqlutils.aux_sql_func as aql
from grimsel.auxiliary.aux_m_func import cols2tuplelist
import grimsel.auxiliary.maps as maps
from grimsel import _get_logger

import grimsel_config as config

import multiprocess as mp

logger = _get_logger(__name__)
logger.setLevel('DEBUG')


class ModelLoopModifier():
    '''
    The purpose of this class is to modify the parameters of the BaseModel
    objects in dependence on the current run_id.

    This might include the modification of parameters like CO2 prices,
    capacities, but also more profound modifications like the
    redefinition of constraints.
    '''

    def __init__(self, ml):
        '''
        To initialize, the ModelBase object is made an instance attribute.
        '''

        self.ml = ml

    def select_swiss_scenarios(self, dict_ch=None):

        if dict_ch is None:
            dict_ch = {0: 'default', 1: 'hi_gas', 2: 'hi_ren'}

        slct_ch = dict_ch[self.ml.dct_step['swch']]

        self.ml.dct_vl['swch_vl'] = slct_ch

        return slct_ch

    def select_hp_scenarios(self, dict_hp=None): 
        
        ''' Select heat-pumps scenario for archetypes for future years '''
        
        if dict_hp is None:
            dict_hp = {0: 'bau', 1: 'fossil', 2: 'full'}

        slct_hp = dict_hp[self.ml.dct_step['swhp']]

        self.ml.dct_vl['swhp_vl'] = slct_hp

        return slct_hp
    
    def select_transmission_scenarios(self, dict_tr=None): 
        
        ''' Select transmission scenario for archetypes for future years '''
        
        if dict_tr is None:
            dict_tr = {0: 'default', 1: 'min_5pc', 2: 'plus_5pc', 3: 'plus_10pc', 4: 'plus_15pc'}

        slct_tr = dict_tr[self.ml.dct_step['swtr']]

        self.ml.dct_vl['swtr_vl'] = slct_tr

        return slct_tr
    
    def select_retrofit_scenarios(self, dict_rf=None): 
        
        ''' Select retrofit scenario for archetypes for future years '''
        
        if dict_rf is None:
            dict_rf = {0: 'default', 1: 'retr_1pc', 2: 'retr_2pc'}

        slct_rf = dict_rf[self.ml.dct_step['swrf']]

        self.ml.dct_vl['swrf_vl'] = slct_rf

        return slct_rf
    
    def select_demand_profile_res(self, dict_dpf=None): 
        
        ''' Select demand profile (EE), for EL archetypes for future years '''
        
        if dict_dpf is None:
            dict_dpf = {0: 'default', 1: 'ee', 2: 'best'}

        slct_dpf = dict_dpf[self.ml.dct_step['swdpf']]

        self.ml.dct_vl['swdpf_vl'] = slct_dpf

        return slct_dpf
    
    
    def set_future_year(self, slct_ch, slct_tr, slct_hp, slct_rf, slct_dpf, dict_fy=None): #slct_hp, slct_rf
        
        list_hp_aw = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('HP_AW')].pp_id.tolist()
        list_hp_ww = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('HP_WW')].pp_id.tolist()
        list_dhw_aw = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('DHW_AW')].pp_id.tolist()
        list_dhw_ww = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('DHW_WW')].pp_id.tolist()

        df_pho = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('_PHO')]
        list_pho_arch = df_pho.loc[~df_pho.pp.str.contains('SOL')].pp_id.tolist()

        df_sto = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('_STO')]
        
        list_sto_el_arch = df_sto.loc[~df_sto.pp.str.contains('HYD|CH0|HT')].pp_id.tolist()

        list_sto_pho_arch = list_pho_arch + list_sto_el_arch
                
        list_hp_arch = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('HP')].pp_id.tolist()
        list_ht_sto_arch = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('HT_STO')].pp_id.tolist()
        list_ht_pp_arch = list_hp_arch + list_ht_sto_arch
        
        list_all_pp_arch = list_sto_pho_arch + list_ht_pp_arch
        list_all_add = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.set_def_add == 1].pp_id.tolist()
        
        nd_arch = self.ml.m.df_def_node.loc[np.invert(self.ml.m.df_def_node.nd.isin(['CH0', 'AT0', 'IT0', 'FR0', 'DE0']))].nd_id.tolist()
        nd_arch_ht = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.str.contains('HT')].nd_id.tolist()
        nd_arch_res = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.str.contains('SFH|MFH')].nd_id.tolist()
        nd_arch_dsr = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.str.contains('DSR')].nd_id.tolist()
        nd_arch_el = list(set(nd_arch) - set(nd_arch_ht) - set(nd_arch_dsr))
        nd_arch_el_res = list(set(nd_arch_res) - set(nd_arch_ht) - set(nd_arch_dsr))
        nd_arch_el_non_res = list(set(nd_arch_el) - set(nd_arch_el_res))
        nd_nat = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.isin(['CH0', 'AT0', 'IT0', 'FR0', 'DE0'])].nd_id.tolist()
        nd_all_el_non_res = nd_nat + nd_arch_el_non_res
        
        if dict_fy is None:
            dict_fy = {
                       0:  2015,
                       1:  2020,
                       2:  2025,
                       3:  2030,
                       4:  2035,
                       5:  2040,
                       6:  2045,
                       7:  2050,    
                      }


        rng_fy = np.arange(len(dict_fy))
        rng_fyp = np.ones(len(rng_fy)) * {val: key for key, val in dict_fy.items()}[2015]
        dict_previous = dict(np.array([rng_fy, rng_fyp]).T)


        slct_fy = self.ml.dct_step['swfy']

        str_fy = '_yr' + str(dict_fy[slct_fy]) if dict_fy[slct_fy] != 2015 else ''
        str_fyp = '_yr' + str(dict_fy[dict_previous[slct_fy]]) if dict_fy[dict_previous[slct_fy]] != 2015 else ''

        #######################################################################
        def set_fuel_prices(str_fy=None):
            ''' Select fuel price values for selected year. '''

            if not str_fy:
                str_fy = ''

            slct_col = 'vc_fl' + str_fy
            msg = ('Setting vc_fl to values' + str_fy.replace('_', ' ') +
                   ' from column {}'.format(slct_col))
            logger.info(msg)

            par = self.ml.m.dict_par['vc_fl']
            df_new = self.ml.m.df_fuel_node_encar[['fl_id', 'nd_id', slct_col]]
            df_new = df_new.rename(columns={slct_col: 'vc_fl'})
            col_mt_fact = 'mt_fact' if not str_fy else 'mt_fact_others'
            par.init_update(df_new, col_mt_fact)



        #######################################################################
        def set_cap_pwr_leg(slct_ch, str_fy=None, excl_pp=[]):
            ''' Select power plant capacities for selected year. '''

            if str_fy == None:
                str_fy = ''

            slct_col = 'cap_pwr_leg' + str_fy
            msg = ('Setting cap_pwr_leg to values' + str_fy.replace('_', ' ') +
                   ' from column {}'.format(slct_col))
            logger.info(msg)

            mask_excl = -self.ml.m.df_plant_encar.pp_id.isin(excl_pp)
            dct_cap = (self.ml.m.df_plant_encar.loc[mask_excl]
                             .set_index(['pp_id', 'ca_id'])[slct_col]
                             .to_dict())
        
            if slct_ch != 'default':

                df = self.ml.m.df_plant_encar_scenarios.copy()
                df = df.loc[df.scenario == slct_ch]

                dct_cap_scen = (df.set_index(['pp_id', 'ca_id'])[slct_col]
                                  .to_dict())

                dct_cap.update(dct_cap_scen)
                

                
            for kk, vv in dct_cap.items():
                self.ml.m.cap_pwr_leg[kk] = vv


        #######################################################################
        def set_cap_avlb(str_fy=None):

            if str_fy == None:
                str_fy = ''

            col_mt_fact = 'mt_fact' if not str_fy else 'mt_fact_others'

            msg = ('Setting cap_avlb monthly adjustment to values'
                   + ' from column {}'.format(col_mt_fact))

            logger.info(msg)

            par = self.ml.m.dict_par['cap_avlb']
            mask_pp = self.ml.m.df_plant_encar.pp_id.isin(self.ml.m.pp)
            df_new = self.ml.m.df_plant_encar.loc[mask_pp,
                                                  ['pp_id', 'ca_id', 'cap_avlb']]

            par.init_update(df_new, col_mt_fact)

            
        #######################################################################
        def set_dmnd(slct_hp, slct_rf, slct_dpf, str_fy=None):
            ''' Scale demand profiles for selected year. '''

            if str_fy == None:
                str_fy = ''
            
            slct_col = 'dmnd_sum' + str_fy
            slct_col_prev = 'dmnd_sum' + str_fyp
            # msg = ('Setting demand normal dmnd_sum to values' + str_fy.replace('_', ' ')
            #       + ' from column {}'.format(slct_col))

            # logger.info(msg)
            last_dmnd = self.ml.m.df_node_encar.set_index(['nd_id', 'ca_id'])[slct_col_prev]
            next_dmnd = self.ml.m.df_node_encar.set_index(['nd_id', 'ca_id'])[slct_col]
            
            ht_dmnd_2050 = self.ml.m.df_node_encar.set_index(['nd_id', 'ca_id'])['dmnd_sum_yr2050']
          
            scaling_factor = (next_dmnd / last_dmnd).rename('scale')
            scaling_factor_ht = (next_dmnd / ht_dmnd_2050).rename('scale')*0.882151# Climate correction
            scaling_factor_dhw = (next_dmnd / ht_dmnd_2050).rename('scale')# No Climate correction
            
            # Inlcude DSR node as not changing (default ee scen)
            df_el = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & ~(
                                                            IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_el_res+nd_arch_dsr))]
            df_el = df_el.join(scaling_factor, on=scaling_factor.index.names)
            df_el['scale'] = df_el['scale'].fillna(0) 
            df_el['value_new'] = df_el.value * df_el.scale
            df_el_res = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & (
                                                            IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_el_res+nd_arch_dsr))]
            
            # # To include no scaling on DSR demand if energy efficiency is default
            # if slct_dpf == 'default':
            #     df_el = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & ~(
            #                                                 IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_el_res+nd_arch_dsr))]
            #     df_el = df_el.join(scaling_factor, on=scaling_factor.index.names)
            #     df_el['scale'] = df_el['scale'].fillna(0) 
            #     df_el['value_new'] = df_el.value * df_el.scale
            #     df_el_res = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & (
            #                                                     IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_el_res+nd_arch_dsr))]
            
            # elif slct_dpf == 'ee':
            #     df_el = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & ~(IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_el_res))]
            #     df_el = df_el.join(scaling_factor, on=scaling_factor.index.names)
            #     df_el['scale'] = df_el['scale'].fillna(0) 
            #     df_el['value_new'] = df_el.value * df_el.scale
            #     df_el_res = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & (IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_el_res))]

            # RES with no scaling factor and non RES with scaling factor
            dct_dmnd_el = (df_el.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
            dct_dmnd_el_res = (df_el_res.set_index(['sy', 'nd_id', 'ca_id'])['value'].to_dict())

            df_dhw_bo = IO.param_to_df(self.ml.m.dmnd).loc[IO.param_to_df(self.ml.m.dmnd).ca_id == 3]
            df_dhw_bo = df_dhw_bo.join(scaling_factor, on=scaling_factor.index.names)
            df_dhw_bo['scale'] = df_dhw_bo['scale'].fillna(0) 
            df_dhw_bo['value_new'] = df_dhw_bo.value * df_dhw_bo.scale
            
            dct_dmnd_dhw_bo = (df_dhw_bo.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
            
            for kk, vv in dct_dmnd_el.items():
                self.ml.m.dmnd[kk] = vv
            
            for kk, vv in dct_dmnd_el_res.items():
                self.ml.m.dmnd[kk] = vv
                
            for kk, vv in dct_dmnd_dhw_bo.items():
                self.ml.m.dmnd[kk] = vv
            
            # HEAT
            pf_ca_id_1 = self.ml.m.df_node_encar.loc[self.ml.m.df_node_encar.ca_id == 1]['dmnd_pf_id'].to_list()
            pf_ca_id_2 = self.ml.m.df_node_encar.loc[self.ml.m.df_node_encar.ca_id == 2]['dmnd_pf_id'].to_list()
            dct_pf_id_dmnd_ht = self.ml.m.df_node_encar.loc[self.ml.m.df_node_encar.ca_id.isin([1,2])].set_index('dmnd_pf_id')['nd_id'].to_dict()
            list_pf_id_dmnd_ht = self.ml.m.df_node_encar.loc[self.ml.m.df_node_encar.ca_id.isin([1,2])]['dmnd_pf_id'].to_list()
            dict_tm_soy = self.ml.m.df_tm_soy_full.loc[self.ml.m.df_tm_soy_full.tm_id==1][['sy','doy']].set_index('doy')['sy'].to_dict()
            
            df_ht_other = self.ml.m.df_profdmnd.loc[self.ml.m.df_profdmnd.dmnd_pf_id.isin(list_pf_id_dmnd_ht)].copy()
            df_ht_other['nd_id'] = df_ht_other['dmnd_pf_id'].map(dct_pf_id_dmnd_ht)
            df_ht_other['sy'] = df_ht_other['doy'].map(dict_tm_soy)
            df_ht_other['ca_id'] = 0
            df_ht_other.loc[df_ht_other.dmnd_pf_id.isin(pf_ca_id_1),'ca_id'] = 1
            df_ht_other.loc[df_ht_other.dmnd_pf_id.isin(pf_ca_id_2),'ca_id'] = 2

                
            df_ht_other = df_ht_other.drop(columns=['dmnd_pf_id', 'hy', 'value','doy']).join(scaling_factor_ht, on=scaling_factor_ht.index.names)
            
            # DHW AW and WW
            pf_ca_id_4 = self.ml.m.df_node_encar.loc[self.ml.m.df_node_encar.ca_id == 4]['dmnd_pf_id'].to_list()
            pf_ca_id_5 = self.ml.m.df_node_encar.loc[self.ml.m.df_node_encar.ca_id == 5]['dmnd_pf_id'].to_list()
            dct_pf_id_dmnd_dhw = self.ml.m.df_node_encar.loc[self.ml.m.df_node_encar.ca_id.isin([4,5])].set_index('dmnd_pf_id')['nd_id'].to_dict()
            list_pf_id_dmnd_dhw = self.ml.m.df_node_encar.loc[self.ml.m.df_node_encar.ca_id.isin([4,5])]['dmnd_pf_id'].to_list()
            dict_tm_soy = self.ml.m.df_tm_soy_full.loc[self.ml.m.df_tm_soy_full.tm_id==1][['sy','doy']].set_index('doy')['sy'].to_dict()
            
            df_dhw_other = self.ml.m.df_profdmnd.loc[self.ml.m.df_profdmnd.dmnd_pf_id.isin(list_pf_id_dmnd_dhw)].copy()
            df_dhw_other['nd_id'] = df_dhw_other['dmnd_pf_id'].map(dct_pf_id_dmnd_dhw)
            df_dhw_other['sy'] = df_dhw_other['doy'].map(dict_tm_soy)
            df_dhw_other['ca_id'] = 0
            df_dhw_other.loc[df_dhw_other.dmnd_pf_id.isin(pf_ca_id_4),'ca_id'] = 4
            df_dhw_other.loc[df_dhw_other.dmnd_pf_id.isin(pf_ca_id_5),'ca_id'] = 5

            df_dhw_other = df_dhw_other.drop(columns=['dmnd_pf_id', 'hy', 'value','doy']).join(scaling_factor_dhw, on=scaling_factor_dhw.index.names)           
            
            if slct_rf == 'default':
                
                msg = ('Setting special heating dmnd_sum to values' + str_fy.replace('_', ' ')
                   + ' from column {}'.format(slct_col) + ' for retrofit scenario ' + slct_rf + ' and for HP scenario ' + slct_hp)

                logger.info(msg)
                #HEAT
                df_ht = IO.param_to_df(self.ml.m.dmnd).loc[IO.param_to_df(self.ml.m.dmnd).ca_id.isin([1,2])]
                df_ht = df_ht.join(scaling_factor_ht, on=scaling_factor_ht.index.names)
                df_ht['value_new'] = df_ht.value * df_ht.scale
    
                dct_dmnd_ht = (df_ht.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                df_ht_fossil = df_ht_other.copy()
                df_ht_fossil['value_new'] = df_ht_fossil.erg_tot_fossil * df_ht_fossil.scale
                
                df_ht_fossil = df_ht_fossil.loc[~df_ht_fossil.sy.isna()]
                dct_dmnd_ht_fossil = (df_ht_fossil.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                # DHW for AW and WW
                df_dhw = IO.param_to_df(self.ml.m.dmnd).loc[IO.param_to_df(self.ml.m.dmnd).ca_id.isin([4,5])]
                df_dhw = df_dhw.join(scaling_factor_dhw, on=scaling_factor_dhw.index.names)
                df_dhw['value_new'] = df_dhw.value * df_dhw.scale
    
                dct_dmnd_dhw = (df_dhw.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                df_dhw_fossil = df_dhw_other.copy()
                df_dhw_fossil['value_new'] = df_dhw_fossil.erg_tot_fossil * df_dhw_fossil.scale
                
                df_dhw_fossil = df_dhw_fossil.loc[~df_dhw_fossil.sy.isna()]
                dct_dmnd_dhw_fossil = (df_dhw_fossil.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                if slct_hp == 'full':
               
                    for kk, vv in dct_dmnd_ht.items():
                        self.ml.m.dmnd[kk] = vv
                    
                    for kk, vv in dct_dmnd_dhw.items():
                        self.ml.m.dmnd[kk] = vv
                        
                elif slct_hp == 'bau':
                  
                    for kk, vv in dct_dmnd_ht.items():
                        self.ml.m.dmnd[kk] = vv * 0.568
                        
                    for kk, vv in dct_dmnd_dhw.items():
                        self.ml.m.dmnd[kk] = vv * 0.568 
                        
                elif slct_hp == 'fossil':
                    
                    for kk, vv in dct_dmnd_ht_fossil.items():
                        self.ml.m.dmnd[kk] = vv
                    
                    for kk, vv in dct_dmnd_dhw_fossil.items():
                        self.ml.m.dmnd[kk] = vv
                        
            elif slct_rf == 'retr_1pc':
                
                msg = ('Setting special heating dmnd_sum to values' + str_fy.replace('_', ' ')
                   + ' from column {}'.format(slct_col) + ' for retrofit scenrio ' + slct_rf + ' and for HP scenario ' + slct_hp)

                logger.info(msg)
                
                # HEAT
                df_ht_retr_1pc = self.ml.m.df_profdmnd.loc[self.ml.m.df_profdmnd.dmnd_pf_id.isin(list_pf_id_dmnd_ht)].copy()
                df_ht_retr_1pc['nd_id'] = df_ht_retr_1pc['dmnd_pf_id'].map(dct_pf_id_dmnd_ht)
                df_ht_retr_1pc['sy'] = df_ht_retr_1pc['doy'].map(dict_tm_soy)
                df_ht_retr_1pc['ca_id'] = 0
                df_ht_retr_1pc.loc[df_ht_retr_1pc.dmnd_pf_id.isin(pf_ca_id_1),'ca_id'] = 1
                df_ht_retr_1pc.loc[df_ht_retr_1pc.dmnd_pf_id.isin(pf_ca_id_2),'ca_id'] = 2

                
                df_ht_retr_1pc = df_ht_retr_1pc[['nd_id', 'sy','erg_tot_retr_1pc','ca_id']].join(scaling_factor_ht, on=scaling_factor_ht.index.names)
                df_ht_retr_1pc['value_new'] = df_ht_retr_1pc.erg_tot_retr_1pc * df_ht_retr_1pc.scale
                
                df_ht_retr_1pc = df_ht_retr_1pc.loc[~df_ht_retr_1pc.sy.isna()]
                dct_dmnd_ht_retr_1pc = (df_ht_retr_1pc.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                
                df_ht_retr_1pc_fossil = df_ht_other.copy()
                df_ht_retr_1pc_fossil['value_new'] = df_ht_retr_1pc_fossil.erg_tot_retr_1pc_fossil * df_ht_retr_1pc_fossil.scale
                
                df_ht_retr_1pc_fossil = df_ht_retr_1pc_fossil.loc[~df_ht_retr_1pc_fossil.sy.isna()]
                dct_dmnd_ht_retr_1pc_fossil = (df_ht_retr_1pc_fossil.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                # DHW for AW and WW
                df_dhw = IO.param_to_df(self.ml.m.dmnd).loc[IO.param_to_df(self.ml.m.dmnd).ca_id.isin([4,5])]
                df_dhw = df_dhw.join(scaling_factor_dhw, on=scaling_factor_dhw.index.names)
                df_dhw['value_new'] = df_dhw.value * df_dhw.scale
    
                dct_dmnd_dhw = (df_dhw.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                df_dhw_fossil = df_dhw_other.copy()
                df_dhw_fossil['value_new'] = df_dhw_fossil.erg_tot_fossil * df_dhw_fossil.scale
                
                df_dhw_fossil = df_dhw_fossil.loc[~df_dhw_fossil.sy.isna()]
                dct_dmnd_dhw_fossil = (df_dhw_fossil.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                if slct_hp == 'full':
                 
                    for kk, vv in dct_dmnd_ht_retr_1pc.items():
                        self.ml.m.dmnd[kk] = vv
                    
                    for kk, vv in dct_dmnd_dhw.items():
                        self.ml.m.dmnd[kk] = vv
                        
                elif slct_hp == 'bau':
                   
                    for kk, vv in dct_dmnd_ht_retr_1pc.items():
                        self.ml.m.dmnd[kk] = vv * 0.568
                    
                    for kk, vv in dct_dmnd_dhw.items():
                        self.ml.m.dmnd[kk] = vv * 0.568
                        
                elif slct_hp == 'fossil':
                    
                    for kk, vv in dct_dmnd_ht_retr_1pc_fossil.items():
                        self.ml.m.dmnd[kk] = vv
                        
                    for kk, vv in dct_dmnd_dhw_fossil.items():
                        self.ml.m.dmnd[kk] = vv
                        
            elif slct_rf == 'retr_2pc':
                
                msg = ('Setting special heating dmnd_sum to values' + str_fy.replace('_', ' ')
                   + ' from column {}'.format(slct_col) + ' for retrofit scenario ' + slct_rf+ ' and for HP scenario ' + slct_hp)

                logger.info(msg)
                
                #HEAT
                df_ht_retr_2pc = self.ml.m.df_profdmnd.loc[self.ml.m.df_profdmnd.dmnd_pf_id.isin(list_pf_id_dmnd_ht)].copy()
                df_ht_retr_2pc['nd_id'] = df_ht_retr_2pc['dmnd_pf_id'].map(dct_pf_id_dmnd_ht)
                df_ht_retr_2pc['sy'] = df_ht_retr_2pc['doy'].map(dict_tm_soy)
                df_ht_retr_2pc['ca_id'] = 0
                df_ht_retr_2pc.loc[df_ht_retr_2pc.dmnd_pf_id.isin(pf_ca_id_1),'ca_id'] = 1
                df_ht_retr_2pc.loc[df_ht_retr_2pc.dmnd_pf_id.isin(pf_ca_id_2),'ca_id'] = 2

                
                df_ht_retr_2pc = df_ht_retr_2pc[['nd_id', 'sy','erg_tot_retr_2pc','ca_id']].join(scaling_factor_ht, on=scaling_factor_ht.index.names)
                df_ht_retr_2pc['value_new'] = df_ht_retr_2pc.erg_tot_retr_2pc * df_ht_retr_2pc.scale
                
                df_ht_retr_2pc = df_ht_retr_2pc.loc[~df_ht_retr_2pc.sy.isna()]
                dct_dmnd_ht_retr_2pc = (df_ht_retr_2pc.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                df_ht_retr_2pc_fossil = df_ht_other.copy()
                df_ht_retr_2pc_fossil['value_new'] = df_ht_retr_2pc_fossil.erg_tot_retr_2pc_fossil * df_ht_retr_2pc_fossil.scale
                
                df_ht_retr_2pc_fossil = df_ht_retr_2pc_fossil.loc[~df_ht_retr_2pc_fossil.sy.isna()]
                dct_dmnd_ht_retr_2pc_fossil = (df_ht_retr_2pc_fossil.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                # DHW for AW and WW
                df_dhw = IO.param_to_df(self.ml.m.dmnd).loc[IO.param_to_df(self.ml.m.dmnd).ca_id.isin([4,5])]
                df_dhw = df_dhw.join(scaling_factor_dhw, on=scaling_factor_dhw.index.names)
                df_dhw['value_new'] = df_dhw.value * df_dhw.scale
    
                dct_dmnd_dhw = (df_dhw.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                df_dhw_fossil = df_dhw_other.copy()
                df_dhw_fossil['value_new'] = df_dhw_fossil.erg_tot_fossil * df_dhw_fossil.scale
                
                df_dhw_fossil = df_dhw_fossil.loc[~df_dhw_fossil.sy.isna()]
                dct_dmnd_dhw_fossil = (df_dhw_fossil.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                
                if slct_hp == 'full':
                 
                    for kk, vv in dct_dmnd_ht_retr_2pc.items():
                        self.ml.m.dmnd[kk] = vv
                        
                    for kk, vv in dct_dmnd_dhw.items():
                        self.ml.m.dmnd[kk] = vv
                        
                elif slct_hp == 'bau':
                   
                    for kk, vv in dct_dmnd_ht_retr_2pc.items():
                        self.ml.m.dmnd[kk] = vv * 0.568
                    
                    for kk, vv in dct_dmnd_dhw.items():
                        self.ml.m.dmnd[kk] = vv * 0.568 
                        
                elif slct_hp == 'fossil':
                    
                    for kk, vv in dct_dmnd_ht_retr_2pc_fossil.items():
                        self.ml.m.dmnd[kk] = vv
                    
                    for kk, vv in dct_dmnd_dhw_fossil.items():
                        self.ml.m.dmnd[kk] = vv
            
            
            
            if slct_dpf == 'ee': # Energy efficiency
            
                slct_col = 'dmnd_sum' + str_fy
                slct_col_prev = 'dmnd_sum' + str_fyp
                
                dict_fy = {
                       0:  2015,
                       1:  2020,
                       2:  2025,
                       3:  2030,
                       4:  2035,
                       5:  2040,
                       6:  2045,
                       7:  2050,    
                      }
                slct_fy = self.ml.dct_step['swfy']
                fy_val = dict_fy[slct_fy]
                
                msg = ('Setting energy efficiency curves to residential and DSR for ' + str_fy.replace('_', ' ')
                      + ' from column {}'.format(slct_col) + ' for ee scenario ' + slct_dpf)
    
                logger.info(msg)
                
                # Load before as we need both for EE and DSR
                path_prof_id = os.path.join(config.PATH_CSV, 'def_profile.csv')
                path_dmnd = os.path.join(config.PATH_CSV, 'profdmnd.csv')
                
                df_def_profile = pd.read_csv(path_prof_id)
                df_dmnd = pd.read_csv(path_dmnd)[['dmnd_pf_id', 'hy', 'value', 'doy']]

                # Energy efficiency
                
                list_nd_name_res_el = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd_id.isin(nd_arch_el_res)].nd.to_list()
                dct_nd_id_res = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd_id.isin(nd_arch_el_res)].set_index('nd')['nd_id'].to_dict()

                df_def_profile_ee = df_def_profile.copy().loc[(df_def_profile.pf.str.contains('diff'))&
                                                              (df_def_profile.primary_nd.isin(list_nd_name_res_el))&
                                                              ~(df_def_profile.pf.str.contains('best'))]
                df_def_profile_ee['nd_id'] = df_def_profile_ee['primary_nd'].map(dct_nd_id_res)
                df_def_profile_ee_2035 = df_def_profile_ee.loc[df_def_profile_ee.pf.str.contains('2035_2015')]
                df_def_profile_ee_2050 = df_def_profile_ee.loc[df_def_profile_ee.pf.str.contains('2050_2015')]
                
                df_dmnd_ee_2035 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_ee_2035.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'diff_erg'})
                df_dmnd_ee_2035 = pd.merge(df_dmnd_ee_2035,df_def_profile_ee_2035,left_on='dmnd_pf_id', right_on='pf_id')
                df_dmnd_ee_2050 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_ee_2050.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'diff_erg'})
                df_dmnd_ee_2050 = pd.merge(df_dmnd_ee_2050,df_def_profile_ee_2050,left_on='dmnd_pf_id', right_on='pf_id')
                
                dict_tm_soy_hour = self.ml.m.df_tm_soy_full.loc[self.ml.m.df_tm_soy_full.tm_id==0][['sy','hy']].set_index('hy')['sy'].to_dict()
                df_dmnd_ee_2035['sy'] = df_dmnd_ee_2035['hy'].map(dict_tm_soy_hour)
                df_dmnd_ee_2050['sy'] = df_dmnd_ee_2050['hy'].map(dict_tm_soy_hour)
                df_el_res = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & (IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_el_res))]
                
                # DSR load under energy efficiency
                
                list_nd_name_dsr = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd_id.isin(nd_arch_dsr)].nd.to_list()
                dct_nd_id_dsr = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd_id.isin(nd_arch_dsr)].set_index('nd')['nd_id'].to_dict()
    
                df_def_profile_dsr = df_def_profile.copy().loc[(df_def_profile.pf.str.contains('DSR'))&
                                                               (df_def_profile.primary_nd.isin(list_nd_name_dsr))&
                                                              ~(df_def_profile.pf.str.contains('best'))]
                df_def_profile_dsr['nd_id'] = df_def_profile_dsr['primary_nd'].map(dct_nd_id_dsr)
                # df_def_profile_dsr_2015 = df_def_profile_dsr.loc[df_def_profile_dsr.pf.str.contains('2015')]
                df_def_profile_dsr_2035 = df_def_profile_dsr.loc[df_def_profile_dsr.pf.str.contains('2035')]
                df_def_profile_dsr_2050 = df_def_profile_dsr.loc[df_def_profile_dsr.pf.str.contains('2050')]
                
                # df_dmnd_dsr_2015 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_dsr_2015.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'dsr_load'})
                # df_dmnd_dsr_2015 = pd.merge(df_dmnd_dsr_2015,df_def_profile_dsr_2015,left_on='dmnd_pf_id', right_on='pf_id')
                df_dmnd_dsr_2035 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_dsr_2035.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'dsr_load'})
                df_dmnd_dsr_2035 = pd.merge(df_dmnd_dsr_2035,df_def_profile_dsr_2035,left_on='dmnd_pf_id', right_on='pf_id')
                df_dmnd_dsr_2050 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_dsr_2050.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'dsr_load'})
                df_dmnd_dsr_2050 = pd.merge(df_dmnd_dsr_2050,df_def_profile_dsr_2050,left_on='dmnd_pf_id', right_on='pf_id')
                
                dict_tm_soy_hour = self.ml.m.df_tm_soy_full.loc[self.ml.m.df_tm_soy_full.tm_id==1][['sy','hy']].set_index('hy')['sy'].to_dict()
                # df_dmnd_dsr_2015['sy'] = df_dmnd_dsr_2015['hy'].map(dict_tm_soy_hour)
                df_dmnd_dsr_2035['sy'] = df_dmnd_dsr_2035['hy'].map(dict_tm_soy_hour)
                df_dmnd_dsr_2050['sy'] = df_dmnd_dsr_2050['hy'].map(dict_tm_soy_hour)
                df_el_dsr = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & (IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_dsr))]

                if fy_val == 2015:
                    
                    dct_dmnd_res = (df_el_res.set_index(['sy', 'nd_id', 'ca_id'])['value'].to_dict())
                    for kk, vv in dct_dmnd_res.items():
                        self.ml.m.dmnd[kk] = vv
                    dct_dmnd_dsr = (df_el_dsr.set_index(['sy', 'nd_id', 'ca_id'])['value'].to_dict())
                    for kk, vv in dct_dmnd_dsr.items():
                        self.ml.m.dmnd[kk] = vv
                    
                elif fy_val == 2020:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(1/4))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(1/4))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                   
                elif fy_val == 2025:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(2/4))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(2/4))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv

                
                elif fy_val == 2030:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(3/4))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(3/4))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                
                elif fy_val == 2035:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(4/4))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(4/4))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                
                elif fy_val == 2040:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(5/7))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(5/7))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                
                elif fy_val == 2045:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(6/7))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(6/7))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                
                elif fy_val == 2050:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(7/7))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(7/7))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                        
            
            elif slct_dpf == 'best': # BEST Energy efficiency
            
                slct_col = 'dmnd_sum' + str_fy
                slct_col_prev = 'dmnd_sum' + str_fyp
                
                dict_fy = {
                       0:  2015,
                       1:  2020,
                       2:  2025,
                       3:  2030,
                       4:  2035,
                       5:  2040,
                       6:  2045,
                       7:  2050,    
                      }
                slct_fy = self.ml.dct_step['swfy']
                fy_val = dict_fy[slct_fy]
                
                msg = ('Setting energy efficiency curves to residential and DSR for ' + str_fy.replace('_', ' ')
                      + ' from column {}'.format(slct_col) + ' for ee scenario ' + slct_dpf)
    
                logger.info(msg)
                    
                # Load before as we need both for EE and DSR
                path_prof_id = os.path.join(config.PATH_CSV, 'def_profile.csv')
                path_dmnd = os.path.join(config.PATH_CSV, 'profdmnd.csv')
                
                df_def_profile = pd.read_csv(path_prof_id)
                df_dmnd = pd.read_csv(path_dmnd)[['dmnd_pf_id', 'hy', 'value', 'doy']]
                # Energy efficiency
                
                list_nd_name_res_el = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd_id.isin(nd_arch_el_res)].nd.to_list()
                dct_nd_id_res = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd_id.isin(nd_arch_el_res)].set_index('nd')['nd_id'].to_dict()

                df_def_profile_ee = df_def_profile.copy().loc[(df_def_profile.pf.str.contains('best_2035|2050'))&(df_def_profile.primary_nd.isin(list_nd_name_res_el))]
                df_def_profile_ee['nd_id'] = df_def_profile_ee['primary_nd'].map(dct_nd_id_res)
                df_def_profile_ee_2035 = df_def_profile_ee.loc[df_def_profile_ee.pf.str.contains('2035_2015')]
                df_def_profile_ee_2050 = df_def_profile_ee.loc[df_def_profile_ee.pf.str.contains('2050_2015')]
                
                df_dmnd_ee_2035 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_ee_2035.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'diff_erg'})
                df_dmnd_ee_2035 = pd.merge(df_dmnd_ee_2035,df_def_profile_ee_2035,left_on='dmnd_pf_id', right_on='pf_id')
                df_dmnd_ee_2050 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_ee_2050.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'diff_erg'})
                df_dmnd_ee_2050 = pd.merge(df_dmnd_ee_2050,df_def_profile_ee_2050,left_on='dmnd_pf_id', right_on='pf_id')
                
                dict_tm_soy_hour = self.ml.m.df_tm_soy_full.loc[self.ml.m.df_tm_soy_full.tm_id==0][['sy','hy']].set_index('hy')['sy'].to_dict()
                df_dmnd_ee_2035['sy'] = df_dmnd_ee_2035['hy'].map(dict_tm_soy_hour)
                df_dmnd_ee_2050['sy'] = df_dmnd_ee_2050['hy'].map(dict_tm_soy_hour)
                # df_dmnd_ee_2035 = df_dmnd_ee_2035.loc[~df_dmnd_ee_2035]
                df_el_res = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & (IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_el_res))]

                # DSR load under energy efficiency
                
                list_nd_name_dsr = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd_id.isin(nd_arch_dsr)].nd.to_list()
                dct_nd_id_dsr = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd_id.isin(nd_arch_dsr)].set_index('nd')['nd_id'].to_dict()
    
                df_def_profile_dsr = df_def_profile.copy().loc[(df_def_profile.pf.str.contains('DSR_best_2035|DSR_2050'))&
                                                               (df_def_profile.primary_nd.isin(list_nd_name_dsr))]
                df_def_profile_dsr['nd_id'] = df_def_profile_dsr['primary_nd'].map(dct_nd_id_dsr)
                # df_def_profile_dsr_2015 = df_def_profile_dsr.loc[df_def_profile_dsr.pf.str.contains('2015')]
                df_def_profile_dsr_2035 = df_def_profile_dsr.loc[df_def_profile_dsr.pf.str.contains('2035')]
                df_def_profile_dsr_2050 = df_def_profile_dsr.loc[df_def_profile_dsr.pf.str.contains('2050')]
                
                # df_dmnd_dsr_2015 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_dsr_2015.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'dsr_load'})
                # df_dmnd_dsr_2015 = pd.merge(df_dmnd_dsr_2015,df_def_profile_dsr_2015,left_on='dmnd_pf_id', right_on='pf_id')
                df_dmnd_dsr_2035 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_dsr_2035.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'dsr_load'})
                df_dmnd_dsr_2035 = pd.merge(df_dmnd_dsr_2035,df_def_profile_dsr_2035,left_on='dmnd_pf_id', right_on='pf_id')
                df_dmnd_dsr_2050 = df_dmnd.copy().loc[df_dmnd.dmnd_pf_id.isin(df_def_profile_dsr_2050.pf_id.to_list())].reset_index(drop=True).rename(columns={'value':'dsr_load'})
                df_dmnd_dsr_2050 = pd.merge(df_dmnd_dsr_2050,df_def_profile_dsr_2050,left_on='dmnd_pf_id', right_on='pf_id')
                
                dict_tm_soy_hour = self.ml.m.df_tm_soy_full.loc[self.ml.m.df_tm_soy_full.tm_id==1][['sy','hy']].set_index('hy')['sy'].to_dict()
                # df_dmnd_dsr_2015['sy'] = df_dmnd_dsr_2015['hy'].map(dict_tm_soy_hour)
                df_dmnd_dsr_2035['sy'] = df_dmnd_dsr_2035['hy'].map(dict_tm_soy_hour)
                df_dmnd_dsr_2050['sy'] = df_dmnd_dsr_2050['hy'].map(dict_tm_soy_hour)
                df_el_dsr = IO.param_to_df(self.ml.m.dmnd).loc[(IO.param_to_df(self.ml.m.dmnd).ca_id == 0) & (IO.param_to_df(self.ml.m.dmnd).nd_id.isin(nd_arch_dsr))]
                 
                if fy_val == 2015:
                    
                    dct_dmnd_res = (df_el_res.set_index(['sy', 'nd_id', 'ca_id'])['value'].to_dict())
                    for kk, vv in dct_dmnd_res.items():
                        self.ml.m.dmnd[kk] = vv
                    dct_dmnd_dsr = (df_el_dsr.set_index(['sy', 'nd_id', 'ca_id'])['value'].to_dict())
                    for kk, vv in dct_dmnd_dsr.items():
                        self.ml.m.dmnd[kk] = vv
                    
                elif fy_val == 2020:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(1/4))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(1/4))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                   
                elif fy_val == 2025:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(2/4))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(2/4))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv

                
                elif fy_val == 2030:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(3/4))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(3/4))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                
                elif fy_val == 2035:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(4/4))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2035,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(4/4))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                
                elif fy_val == 2040:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(5/7))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(5/7))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                
                elif fy_val == 2045:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(6/7))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(6/7))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                
                elif fy_val == 2050:
                    
                    df_el_res_ee = pd.merge(df_el_res,df_dmnd_ee_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value + x.diff_erg*(7/7))
                    df_el_dsr_ee = pd.merge(df_el_dsr,df_dmnd_dsr_2050,on=['sy','nd_id']).assign(
                                            value_new = lambda x: x.value - (x.value - x.dsr_load)*(7/7))
                    
                    dct_dmnd_res_ee = (df_el_res_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())
                    dct_dmnd_dsr_ee = (df_el_dsr_ee.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

                    for kk, vv in dct_dmnd_res_ee.items():
                        self.ml.m.dmnd[kk] = vv
                    for kk, vv in dct_dmnd_dsr_ee.items():
                        self.ml.m.dmnd[kk] = vv
                
        #######################################################################
        def set_co2_price(str_fy=None):
            ''' Select CO2 price for selected year. '''

            if str_fy == None:
                str_fy = ''

            slct_col = 'price_co2' + str_fy
            msg = ('Setting price_co2  to values' + str_fy.replace('_', ' ')
                   + ' from column {}'.format(slct_col))
            logger.info(msg)

            df_new = self.ml.m.df_def_node[['nd_id', slct_col]]
            par = self.ml.m.dict_par['price_co2']
            col_mt_fact = 'mt_fact' if not str_fy else 'mt_fact_others'
            par.init_update(df_new, col_mt_fact)

        #######################################################################

        def set_erg_inp(slct_ch, str_fy=None, excl_fl=[]):
            ''' Select exogenous energy production for selected year. '''

            if str_fy == None:
                str_fy = ''

            slct_col = 'erg_inp' + str_fy
            msg = ('Setting erg_inp to values ' + str_fy.replace('_', '')
                   + 'from column {}.'.format(slct_col))
            logger.info(msg)

            ind_col = ['nd_id', 'ca_id', 'fl_id']
            mask_excl = -self.ml.m.df_fuel_node_encar.fl_id.isin(excl_fl)
            dct_erg_inp = (self.ml.m.df_fuel_node_encar.loc[mask_excl]
                               .set_index(ind_col)[slct_col].to_dict())

            if slct_ch != 'default':

                df = self.ml.m.df_fuel_node_encar_scenarios.copy()
                df = df.loc[df.scenario == slct_ch]
                dct_erg_inp_scen = (df.set_index(ind_col)[slct_col].to_dict())
                dct_erg_inp.update(dct_erg_inp_scen)

            for kk, vv in dct_erg_inp.items():
                self.ml.m.erg_inp[kk] = vv
        #######################################################################

        def set_erg_chp(str_fy=None, excl_pp=[]):
            ''' Select exogenous chp energy production for selected year. '''

            if str_fy == None:
                str_fy = ''

            slct_col = 'erg_chp' +  str_fy
            msg = ('Setting erg_chp to values ' + str_fy.replace('_', '')
                   + ' from column {}.'.format(slct_col))
            logger.info(msg)

            dct_erg_chp = (self.ml.m.df_plant_encar
                               .loc[-self.ml.m.df_plant_encar.pp_id.isin(excl_pp)
                                   & self.ml.m.df_plant_encar.pp_id.isin(self.ml.m.chp)]
                               .set_index(['pp_id', 'ca_id'])[slct_col]
                               .to_dict())

            for kk, vv in dct_erg_chp.items():
                self.ml.m.erg_chp[kk] = vv

        #######################################################################
        
        def set_fc_cap(str_fy=None, excl_pp=[]):
            ''' Select capital costs for power plants for selected year. '''

            if str_fy == None:
                str_fy = ''

            slct_col = 'fc_cp_ann' +  str_fy
            msg = ('Setting fc_cp_ann to values ' + str_fy.replace('_', '')
                   + ' from column {}.'.format(slct_col))
            logger.info(msg)

            dct_fc_cp_ann = (self.ml.m.df_plant_encar
                               .loc[-self.ml.m.df_plant_encar.pp_id.isin(excl_pp)
                                   & self.ml.m.df_plant_encar.pp_id.isin(self.ml.m.add)]
                               .set_index(['pp_id', 'ca_id'])[slct_col]
                               .to_dict())

            for kk, vv in dct_fc_cp_ann.items():
                self.ml.m.fc_cp_ann[kk] = vv

#           To chekc if it is working (*0.01)            
#            dct_fc_cp_ann_sto = (self.ml.m.df_plant_encar
#                               .loc[-self.ml.m.df_plant_encar.pp_id.isin(list_pho_arch)
#                                   & self.ml.m.df_plant_encar.pp_id.isin(self.ml.m.add)]
#                               .set_index(['pp_id', 'ca_id'])[slct_col]
#                               .to_dict())
#
#            for kk, vv in dct_fc_cp_ann_sto.items():
#                self.ml.m.fc_cp_ann[kk] = vv * 0.01
        #######################################################################
        
        def set_fc_om(str_fy=None, excl_pp=[]):
            ''' Select O&M costs for power plants for selected year. '''

            if str_fy == None:
                str_fy = ''

            slct_col = 'fc_om' +  str_fy
            msg = ('Setting fc_om to values ' + str_fy.replace('_', '')
                   + ' from column {}.'.format(slct_col))
            logger.info(msg)

            dct_fc_om = (self.ml.m.df_plant_encar
                               .loc[-self.ml.m.df_plant_encar.pp_id.isin(excl_pp)
                                   & self.ml.m.df_plant_encar.pp_id.isin(self.ml.m.add)]
                               .set_index(['pp_id', 'ca_id'])[slct_col]
                               .to_dict())

            for kk, vv in dct_fc_om.items():
                self.ml.m.fc_om[kk] = vv
        
        #######################################################################
          
        def set_hp_capacity(slct_hp, slct_rf, str_fy=None):
            ''' Select heat pump scenario for archetypes'''
            
            if str_fy == None:
                str_fy = ''
                
            if slct_rf == 'default':
                
                slct_col = 'cap_pwr_leg' + str_fy
                slct_col_fossil = 'cap_pwr_leg' + str_fy + '_hp_' + slct_hp
                
                msg = ('Setting cap_pwr_leg to values for HP' + str_fy.replace('_', ' ') +
                       ' from column {}'.format(slct_col) + ' for scenario ' + slct_hp + ' and retrofit ' + slct_rf)
                logger.info(msg)
                
                dct_caphp = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_hp_aw + list_hp_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col]
                                 .to_dict())
                
                dct_capdhw = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_dhw_aw + list_dhw_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col]
                                 .to_dict())
                
                
                if slct_hp == 'full': # full heat pumps in 2050
                    
                    for kk, vv in dct_caphp.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
                        
                    for kk, vv in dct_capdhw.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
                        
                 
                elif slct_hp == 'bau': # bau heat pumps deployement in 2050
                    
                    for kk, vv in dct_caphp.items():
                        self.ml.m.cap_pwr_leg[kk] = vv * 0.568
                        
                    for kk, vv in dct_capdhw.items():
                        self.ml.m.cap_pwr_leg[kk] = vv * 0.568
                        
                elif slct_hp == 'fossil': # fossil fuel replacement heat pumps deployement in 2050
                    
                    dct_caphp_fossil = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_hp_aw + list_hp_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col_fossil]
                                 .to_dict())
                
                    dct_capdhw_fossil = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_dhw_aw + list_dhw_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col_fossil]
                                 .to_dict())
                    
                    for kk, vv in dct_caphp_fossil.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
                        
                    for kk, vv in dct_capdhw_fossil.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
            
            elif slct_rf == 'retr_1pc':
                
                slct_col = 'cap_pwr_leg' + str_fy + '_hp_' + slct_rf
                slct_col_fossil = 'cap_pwr_leg' + str_fy + '_hp_' + slct_rf + '_' + slct_hp

                msg = ('Setting cap_pwr_leg to values for HP' + str_fy.replace('_', ' ') +
                       ' from column {}'.format(slct_col) + ' for scenario ' + slct_hp + ' and retrofit ' + slct_rf)
                logger.info(msg)
                
                dct_caphp = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_hp_aw + list_hp_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col]
                                 .to_dict())
                
                dct_capdhw = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_dhw_aw + list_dhw_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col]
                                 .to_dict())
                
                
                if slct_hp == 'full': # full heat pumps in 2050
                    
                    for kk, vv in dct_caphp.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
                        
                    for kk, vv in dct_capdhw.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
                        
                 
                elif slct_hp == 'bau': # bau heat pumps deployement in 2050
                    
                    for kk, vv in dct_caphp.items():
                        self.ml.m.cap_pwr_leg[kk] = vv * 0.568
                        
                    for kk, vv in dct_capdhw.items():
                        self.ml.m.cap_pwr_leg[kk] = vv * 0.568
                        
                elif slct_hp == 'fossil': # fossil fuel replacement heat pumps deployement in 2050
                    
                    dct_caphp_fossil = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_hp_aw + list_hp_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col_fossil]
                                 .to_dict())
                
                    dct_capdhw_fossil = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_dhw_aw + list_dhw_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col_fossil]
                                 .to_dict())
                    
                    for kk, vv in dct_caphp_fossil.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
                        
                    for kk, vv in dct_capdhw_fossil.items():
                        self.ml.m.cap_pwr_leg[kk] = vv

           
            elif slct_rf == 'retr_2pc':
                
                slct_col = 'cap_pwr_leg' + str_fy + '_hp_' + slct_rf
                slct_col_fossil = 'cap_pwr_leg' + str_fy + '_hp_' + slct_rf + '_' + slct_hp

                msg = ('Setting cap_pwr_leg to values for HP' + str_fy.replace('_', ' ') +
                       ' from column {}'.format(slct_col) + ' for scenario ' + slct_hp + ' and retrofit ' + slct_rf)
                logger.info(msg)
                
                dct_caphp = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_hp_aw + list_hp_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col]
                                 .to_dict())
                
                dct_capdhw = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_dhw_aw + list_dhw_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col]
                                 .to_dict())
                
                
                if slct_hp == 'full': # full heat pumps in 2050
                    
                    for kk, vv in dct_caphp.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
                        
                    for kk, vv in dct_capdhw.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
                        
                 
                elif slct_hp == 'bau': # bau heat pumps deployement in 2050
                    
                    for kk, vv in dct_caphp.items():
                        self.ml.m.cap_pwr_leg[kk] = vv * 0.568
                        
                    for kk, vv in dct_capdhw.items():
                        self.ml.m.cap_pwr_leg[kk] = vv * 0.568
                        
                elif slct_hp == 'fossil': # fossil fuel replacement heat pumps deployement in 2050
                    
                    dct_caphp_fossil = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_hp_aw + list_hp_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col_fossil]
                                 .to_dict())
                
                    dct_capdhw_fossil = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_dhw_aw + list_dhw_ww)]
                                 .set_index(['pp_id', 'ca_id'])[slct_col_fossil]
                                 .to_dict())
                    
                    for kk, vv in dct_caphp_fossil.items():
                        self.ml.m.cap_pwr_leg[kk] = vv
                        
                    for kk, vv in dct_capdhw_fossil.items():
                        self.ml.m.cap_pwr_leg[kk] = vv


         #######################################################################            
            
        def set_cap_trm_leg(slct_tr, str_fy=None):
            ''' Select transmission capacity scenario for archetypes. '''
            
            # nd_arch = self.ml.m.df_def_node.loc[np.invert(self.ml.m.df_def_node.nd.isin(['CH0', 'AT0', 'IT0', 'FR0', 'DE0']))].nd_id.tolist()
            # nd_arch_ht = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.str.contains('HT')].nd_id.tolist()
            # nd_arch_res = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.str.contains('SFH|MFH')].nd_id.tolist()
            # nd_arch_el = list(set(nd_arch) - set(nd_arch_ht))
            # nd_arch_el_res = list(set(nd_arch_res) - set(nd_arch_ht))
            # nd_arch_el_non_res = list(set(nd_arch_el) - set(nd_arch_el_res))
            
            if str_fy == None:
                str_fy = ''

            slct_col_trme = 'cap_trme_leg' 
            slct_col_trmi = 'cap_trmi_leg' #+ (str_hy if not reset else '')
            msg = ('Setting transmission capacity for archetypes'+ str_fy.replace('_', ' ') +
                    ' for scenario ' + slct_tr)
            logger.info(msg)
            
            dct_cap_trme_leg = (self.ml.m.df_node_connect
                                   .loc[self.ml.m.df_node_connect.nd_2_id.isin(nd_arch_el)]
                                   .set_index(['mt_id', 'nd_id',
                                               'nd_2_id', 'ca_id'])[slct_col_trme]
                                   .to_dict())
            dct_cap_trmi_leg = (self.ml.m.df_node_connect
                                   .loc[self.ml.m.df_node_connect.nd_2_id.isin(nd_arch_el)]
                                   .set_index(['mt_id', 'nd_id',
                                               'nd_2_id', 'ca_id'])[slct_col_trmi]
                                   .to_dict())
            
            slct_fy = self.ml.dct_step['swfy']
            fy_val = dict_fy[slct_fy]
            
            if fy_val == 2015:
                
                for kk, vv in dct_cap_trme_leg.items():
                    self.ml.m.cap_trme_leg[kk] = vv
                for kk, vv in dct_cap_trmi_leg.items():
                    self.ml.m.cap_trmi_leg[kk] = vv
                    
            else:
                
                if slct_tr == 'default':
                    
                    for kk, vv in dct_cap_trme_leg.items():
                        self.ml.m.cap_trme_leg[kk] = vv
                    for kk, vv in dct_cap_trmi_leg.items():
                        self.ml.m.cap_trmi_leg[kk] = vv
                
                elif slct_tr == 'min_5pc':
                    
                    for kk, vv in dct_cap_trme_leg.items():
                        self.ml.m.cap_trme_leg[kk] = vv*0.95
                    for kk, vv in dct_cap_trmi_leg.items():
                        self.ml.m.cap_trmi_leg[kk] = vv*0.95
                
                elif slct_tr == 'plus_5pc':
                    
                    for kk, vv in dct_cap_trme_leg.items():
                        self.ml.m.cap_trme_leg[kk] = vv*1.05
                    for kk, vv in dct_cap_trmi_leg.items():
                        self.ml.m.cap_trmi_leg[kk] = vv*1.05
                
                elif slct_tr == 'plus_10pc':
                    
                    for kk, vv in dct_cap_trme_leg.items():
                        self.ml.m.cap_trme_leg[kk] = vv*1.1
                    for kk, vv in dct_cap_trmi_leg.items():
                        self.ml.m.cap_trmi_leg[kk] = vv*1.1
                        
                elif slct_tr == 'plus_15pc':
                    
                    for kk, vv in dct_cap_trme_leg.items():
                        self.ml.m.cap_trme_leg[kk] = vv*1.15
                    for kk, vv in dct_cap_trmi_leg.items():
                        self.ml.m.cap_trmi_leg[kk] = vv*1.15
                                    
 
        #######################################################################
        
         # resetting everything to base year values
        # Note: inflow profiles are static and scaled by erg_inp in the constraint


#        mask_sfh = self.ml.m.df_def_plant.pp.str.contains('SFH')
#        excl_pp = self.ml.m.df_def_plant.loc[mask_sfh].pp_id.tolist()
#        excl_pp = list_sto_pho_arch  # for pv and st opt
        excl_pp = list_all_add  # for all add

#        excl_pp = list_sto_arch # for stopt
#        excl_pp = list_pho_arch # exclude PHO pp for archetypes not for CH0  # for pvopt
#        excl_fl = []

        set_fuel_prices(str_fy)
        set_cap_pwr_leg(slct_ch, str_fy, excl_pp=excl_pp)
        set_cap_avlb(str_fy)
        set_dmnd(slct_hp, slct_rf, slct_dpf, str_fy)
        set_co2_price(str_fy)
        set_erg_inp(slct_ch, str_fy)
        set_erg_chp(str_fy)
        set_fc_cap(str_fy)
        set_fc_om(str_fy)
        set_cap_trm_leg(slct_tr, str_fy)
#        set_supprof(str_hy)
#        set_priceprof(str_hy)
        set_hp_capacity(slct_hp, slct_rf, str_fy)
        

        self.ml.dct_vl['swfy_vl'] = 'yr' + str(dict_fy[slct_fy])
        
    def keep_cap_new(self, dict_fy=None): 
        ''' Keep the output capacity for power plants in set add for selected year '''
        
#        df_pho = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('_PHO')]
#        list_pho_arch = df_pho.loc[~df_pho.pp.str.contains('SOL')].pp_id.tolist()
#        
#        df_sto = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('_STO')]
#        list_sto_arch = df_sto.loc[~df_sto.pp.str.contains('HYD')].pp_id.tolist()
#        
#        list_sto_pho_arch = list_pho_arch + list_sto_arch
        list_all_add = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.set_def_add == 1].pp_id.tolist()

        
        if dict_fy is None:
            dict_fy = {
                       0:  2015,
                       1:  2020,
                       2:  2025,
                       3:  2030,
                       4:  2035,
                       5:  2040,
                       6:  2045,
                       7:  2050,    
                      }
        
        slct_fy = self.ml.dct_step['swfy']
        fy_val = dict_fy[slct_fy]
#        self.ml.dct_vl['swch_vl'] = slct_ch
            
        if fy_val == 2015:
            
            slct_col = 'cap_pwr_leg'
            msg = ('Setting cap_pwr_leg for PP ADD to values' + str(fy_val) +
                   ' from column {}'.format(slct_col))
            logger.info(msg)

            dct_cap = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_all_add)] # list_sto_arch for stopt
                             .set_index(['pp_id', 'ca_id'])[slct_col]
                             .to_dict())
            
            for kk, vv in dct_cap.items():
                self.ml.m.cap_pwr_leg[kk] = vv
            
        
            for kk, vv in dct_cap.items():
                self.ml.m.cap_pwr_new[kk] = 0
                
            self.ml.m.cap_pwr_new.fix()
            
        else:
            
            self.ml.m.cap_pwr_new.unfix()
            
            slct_col = 'var_yr_cap_pwr_new'
            msg = ('Setting previous capacity added for PP ADD ' + str(fy_val) +
                   ' from column {}'.format(slct_col))
            logger.info(msg)
        
    
            filt = [(key, [val]) for key, val in self.ml.dct_step.items()
                 if not key == 'swfy'] + [('swfy', [self.ml.dct_step['swfy'] - 1])]
               
            if self.ml.io.modwr.output_target == 'hdf5':
                qry = ' & '.join(str(f[0] + '=' + '"%s"'%f[1][0]) for f in filt)
                slct_run_id = pd.read_hdf(self.ml.io.cl_out, 'def_run',
                                          where=qry,
                                          columns=['run_id']).run_id.tolist()
                df_cpn = pd.read_hdf(self.ml.io.cl_out, 'var_yr_cap_pwr_new',
                                    where='run_id in %s and pp_id in %s'%(str(slct_run_id),str(list_all_add))) #list_sto_arch for stopt
        
                df_cpl = pd.read_hdf(self.ml.io.cl_out, 'par_cap_pwr_leg',
                                    where='run_id in %s and pp_id in %s'%(str(slct_run_id),str(list_all_add)))
                
                dict_cpn_add = (df_cpn.set_index(['pp_id', 'ca_id'])['value'] 
                                + df_cpl.set_index(['pp_id', 'ca_id'])['value']).to_dict()
                
            elif self.ml.io.modwr.output_target == 'psql':
                raise RuntimeError('exogenous_node_ops: Fix nd_weight for psql')
 
            elif self.ml.io.modwr.output_target == 'fastparquet':
                qry = ' & '.join(str(f[0] + '==' + '"%s"'%f[1][0]) for f in filt)
                
#                if mp.active_children():
                if not mp.current_process().name == 'MainProcess':
                    msg = ('MULTIPROCESSING')
                    logger.info(msg)
                    df_def_run = pd.concat([pd.read_csv(fn) for fn in glob(self.ml.io.cl_out + '/def_run*.csv')])
                
                else:
                    msg = ('NO MULTIPROCESSING')
                    logger.info(msg)
                    df_def_run= pd.read_parquet(self.ml.io.cl_out + '/def_run.parq')
                                
                slct_run_id = df_def_run.query(qry)#.to_list()
                assert len(slct_run_id) == 1, 'Found multiple run_ids'
                slct_run_id = slct_run_id.run_id.reset_index(drop=True).get(0)
                
                df_cpn = pd.read_parquet(self.ml.io.cl_out + '/var_yr_cap_pwr_new' + '_{:04d}.parq'.format(slct_run_id))
                df_cpn = df_cpn.loc[df_cpn.pp_id.isin(list_all_add)]
                                
                df_cpl = pd.read_parquet(self.ml.io.cl_out + '/par_cap_pwr_leg' + '_{:04d}.parq'.format(slct_run_id))
                df_cpl = df_cpl.loc[df_cpl.pp_id.isin(list_all_add)]

                
                dict_cpn_add = (df_cpn.set_index(['pp_id', 'ca_id'])['value'] 
                                + df_cpl.set_index(['pp_id', 'ca_id'])['value']).to_dict()
                
            for kk, vv in dict_cpn_add.items():
                self.ml.m.cap_pwr_leg[kk] = vv 