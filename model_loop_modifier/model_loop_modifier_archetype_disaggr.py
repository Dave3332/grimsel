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
import pandas as pd
import numpy as np
import logging

import pyomo.environ as po

from grimsel.core.io import IO
import grimsel.auxiliary.sqlutils.aux_sql_func as aql
from grimsel.auxiliary.aux_m_func import cols2tuplelist
import grimsel.auxiliary.maps as maps
from grimsel import _get_logger

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

    def select_storage_scenarios(self, dict_st=None): 
        
        ''' Select storage scenario for archetypes for future years '''
        
        if dict_st is None:
            dict_st = {0: 'default', 1: 'low_adopt', 2: 'hi_adopt'}

        slct_st = dict_st[self.ml.dct_step['swst']]

        self.ml.dct_vl['swst_vl'] = slct_st

        return slct_st
    
    def select_transmission_scenarios(self, dict_tr=None): 
        
        ''' Select transmission scenario for archetypes for future years '''
        
        if dict_tr is None:
            dict_tr = {0: 'default', 1: 'min_5pc', 2: 'plus_5pc'}

        slct_tr = dict_tr[self.ml.dct_step['swtr']]

        self.ml.dct_vl['swtr_vl'] = slct_tr

        return slct_tr
    
    def set_future_year(self, slct_ch, slct_st, slct_tr, dict_fy=None): #slct_st, slct_tr
        
        df_pho = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('_PHO')]
        list_pho_arch = df_pho.loc[~df_pho.pp.str.contains('SOL')].pp_id.tolist()
#        list_prcsll = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('PRC|SLL')].pp_id.tolist()
#        list_prc = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('PRC')].pp_id.tolist()

        list_sfh = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('SFH')].pp_id.tolist()
        list_mfh = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('MFH')].pp_id.tolist()
        list_oco = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('OCO')].pp_id.tolist()
        list_ind = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('IND')].pp_id.tolist()

        df_sto = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('_STO')]
        list_sto_arch = df_sto.loc[~df_sto.pp.str.contains('HYD')].pp_id.tolist()
        
        list_sto_pho_arch = list_pho_arch + list_sto_arch
        
        list_sfh_sto = list(set(list_sfh) & set(list_sto_arch))
        list_mfh_sto = list(set(list_mfh) & set(list_sto_arch))
#        list_sfh_prc = list(set(list_sfh) & set(list_prc))
#        list_mfh_prc = list(set(list_mfh) & set(list_prc))
        
        list_oco_sto = list(set(list_oco) & set(list_sto_arch))
        list_ind_sto = list(set(list_ind) & set(list_sto_arch))
#        list_oco_prc = list(set(list_oco) & set(list_prc))
#        list_ind_prc = list(set(list_ind) & set(list_prc))
        
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
        def set_dmnd(str_fy=None):
            ''' Scale demand profiles for selected year. '''

            if str_fy == None:
                str_fy = ''

            slct_col = 'dmnd_sum' + str_fy
            slct_col_prev = 'dmnd_sum' + str_fyp
            msg = ('Setting dmnd_sum to values' + str_fy.replace('_', ' ')
                   + ' from column {}'.format(slct_col))

            logger.info(msg)

            last_dmnd = self.ml.m.df_node_encar.set_index(['nd_id', 'ca_id'])[slct_col_prev]
            next_dmnd = self.ml.m.df_node_encar.set_index(['nd_id', 'ca_id'])[slct_col]

            scaling_factor = (next_dmnd / last_dmnd).rename('scale')


            df = IO.param_to_df(self.ml.m.dmnd)
            df = df.join(scaling_factor, on=scaling_factor.index.names)
            df['value_new'] = df.value * df.scale

            dct_dmnd = (df.set_index(['sy', 'nd_id', 'ca_id'])['value_new'].to_dict())

            for kk, vv in dct_dmnd.items():
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
          
        def set_storage_capacity(slct_st, str_fy=None):
            ''' Select storage scenario for  archetypes'''
            
            if str_fy == None:
                str_fy = ''
                
            slct_col = 'cap_pwr_leg' + str_fy
            msg = ('Setting cap_pwr_leg to values for STORAGE' + str_fy.replace('_', ' ') +
                   ' from column {}'.format(slct_col) + ' for scenario ' + slct_st)
            logger.info(msg)
            
            dct_capst_sfh = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_sfh_sto)]
                             .set_index(['pp_id', 'ca_id'])[slct_col]
                             .to_dict())
            
            dct_capst_mfh = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_mfh_sto)]
                             .set_index(['pp_id', 'ca_id'])[slct_col]
                             .to_dict())
            
            dct_capst_oco = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_oco_sto)]
                             .set_index(['pp_id', 'ca_id'])[slct_col]
                             .to_dict())
            
            dct_capst_ind = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_ind_sto)]
                             .set_index(['pp_id', 'ca_id'])[slct_col]
                             .to_dict())
            
            if slct_st == 'default': # defaults means 5h storage (sum_dmnd * 5/8760)
                
                for kk, vv in dct_capst_sfh.items():
                    self.ml.m.cap_pwr_leg[kk] = vv
                    
                for kk, vv in dct_capst_mfh.items():
                    self.ml.m.cap_pwr_leg[kk] = vv
                    
                for kk, vv in dct_capst_oco.items():
                    self.ml.m.cap_pwr_leg[kk] = vv
                    
                for kk, vv in dct_capst_ind.items():
                    self.ml.m.cap_pwr_leg[kk] = vv
             
            elif slct_st == 'low_adopt': # low adoption means 2h storage (sum_dmnd * 2/8760)
                
                for kk, vv in dct_capst_sfh.items():
                    self.ml.m.cap_pwr_leg[kk] = vv*0.4
                    
                for kk, vv in dct_capst_mfh.items():
                    self.ml.m.cap_pwr_leg[kk] = vv*0.4
                    
                for kk, vv in dct_capst_oco.items():
                    self.ml.m.cap_pwr_leg[kk] = vv*0.4
                    
                for kk, vv in dct_capst_ind.items():
                    self.ml.m.cap_pwr_leg[kk] = vv*0.4
                    
            elif slct_st == 'hi_adopt': # hi adoption means 8h storage (sum_dmnd * 8/8760)
                
                for kk, vv in dct_capst_sfh.items():
                    self.ml.m.cap_pwr_leg[kk] = vv*1.6
                    
                for kk, vv in dct_capst_mfh.items():
                    self.ml.m.cap_pwr_leg[kk] = vv*1.6
                    
                for kk, vv in dct_capst_oco.items():
                    self.ml.m.cap_pwr_leg[kk] = vv*1.6
                    
                for kk, vv in dct_capst_ind.items():
                    self.ml.m.cap_pwr_leg[kk] = vv*1.6
                
#                
#                
         #######################################################################            
##                                                                              
#                 
            
        def set_cap_trm_leg(slct_tr, str_fy=None):
            ''' Select transmission capacity scenario for archetypes. '''
            
            
            node_arch_id = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.str.contains('_')].nd_id.tolist()
#            node_rur_id = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.str.contains('RUR')].nd_id.tolist()
#            node_sub_id = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.str.contains('SUB')].nd_id.tolist()
#            node_urb_id = self.ml.m.df_def_node.loc[self.ml.m.df_def_node.nd.str.contains('URB')].nd_id.tolist()

            if str_fy == None:
                str_fy = ''

            slct_col_trme = 'cap_trme_leg' 
            slct_col_trmi = 'cap_trmi_leg' #+ (str_hy if not reset else '')
            msg = ('Setting transmission capacity for archetypes'+ str_fy.replace('_', ' ') +
                    'for scenario ' + slct_tr)
            logger.info(msg)
            
            dct_cap_trme_leg = (self.ml.m.df_node_connect
                                   .loc[self.ml.m.df_node_connect.nd_2_id.isin(node_arch_id)]
                                   .set_index(['mt_id', 'nd_id',
                                               'nd_2_id', 'ca_id'])[slct_col_trme]
                                   .to_dict())
            dct_cap_trmi_leg = (self.ml.m.df_node_connect
                                   .loc[self.ml.m.df_node_connect.nd_2_id.isin(node_arch_id)]
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
                
                if slct_tr == 'min_5pc':
                    
                    for kk, vv in dct_cap_trme_leg.items():
                        self.ml.m.cap_trme_leg[kk] = vv*0.95 # or /1.05
                    for kk, vv in dct_cap_trmi_leg.items():
                        self.ml.m.cap_trmi_leg[kk] = vv*0.95
                
                if slct_tr == 'plus_5pc':
                    
                    for kk, vv in dct_cap_trme_leg.items():
                        self.ml.m.cap_trme_leg[kk] = vv*1.05
                    for kk, vv in dct_cap_trmi_leg.items():
                        self.ml.m.cap_trmi_leg[kk] = vv*1.05


        
         # resetting everything to base year values
        # Note: inflow profiles are static and scaled by erg_inp in the constraint


#        mask_sfh = self.ml.m.df_def_plant.pp.str.contains('SFH')
#        excl_pp = self.ml.m.df_def_plant.loc[mask_sfh].pp_id.tolist()
#        excl_pp = list_sto_pho_arch  # for pv and st opt
#        excl_pp = list_sto_arch # for stopt
        excl_pp = list_pho_arch # exclude PHO pp for archetypes not for CH0  # for pvopt
#        excl_fl = []

        set_fuel_prices(str_fy)
        set_cap_pwr_leg(slct_ch, str_fy, excl_pp=excl_pp)
        set_cap_avlb(str_fy)
        set_dmnd(str_fy)
        set_co2_price(str_fy)
        set_erg_inp(slct_ch, str_fy)
        set_erg_chp(str_fy)
        set_fc_cap(str_fy)
        set_fc_om(str_fy)
        set_cap_trm_leg(slct_tr, str_fy)
#        set_supprof(str_hy)
#        set_priceprof(str_hy)
        set_storage_capacity(slct_st, str_fy)
        

        self.ml.dct_vl['swfy_vl'] = 'yr' + str(dict_fy[slct_fy])
        
#      #         TO CONTINUE HERE
    def keep_cap_new(self, dict_fy=None): 
        ''' Keep the output capacity for power plants in set add for selected year '''
        
        df_pho = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('_PHO')]
        list_pho_arch = df_pho.loc[~df_pho.pp.str.contains('SOL')].pp_id.tolist()
        
        df_sto = self.ml.m.df_def_plant.loc[self.ml.m.df_def_plant.pp.str.contains('_STO')]
        list_sto_arch = df_sto.loc[~df_sto.pp.str.contains('HYD')].pp_id.tolist()
        
        list_sto_pho_arch = list_pho_arch + list_sto_arch
        
        
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

            dct_cap = (self.ml.m.df_plant_encar.loc[self.ml.m.df_plant_encar.pp_id.isin(list_pho_arch)] # list_sto_arch for stopt
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
            msg = ('Setting previous capacity added for PP ADD' + str(fy_val) +
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
                                    where='run_id in %s and pp_id in %s'%(str(slct_run_id),str(list_pho_arch))) #list_sto_arch for stopt
        
                df_cpl = pd.read_hdf(self.ml.io.cl_out, 'par_cap_pwr_leg',
                                    where='run_id in %s and pp_id in %s'%(str(slct_run_id),str(list_pho_arch)))
                
                dict_cpn_add = (df_cpn.set_index(['pp_id', 'ca_id'])['value'] 
                                + df_cpl.set_index(['pp_id', 'ca_id'])['value']).to_dict()
            elif self.ml.io.modwr.output_target == 'psql':
                raise RuntimeError('exogenous_node_ops: Fix nd_weight for psql')
 
                
            for kk, vv in dict_cpn_add.items():
                self.ml.m.cap_pwr_leg[kk] = vv 
                

        
        
        
       
