==========
Grimsel
==========

**G**\ene\ **R**\al **I**\ntegrated **M**\odeling environment for the **S**\upply of **E**\lectricity and **L**\ow-temperature heat

* Linear/Quadratic programming framework for the cost-optimization of operation and composition of multi-carrier energy systems
* Based on Pyomo
* Input given as normalized tables
* Focus on modification of model structure and parameter values for the efficient generation of large numbers of model runs.
* Currently relies on CPLEX. Other solvers (compatible with Pyomo) could be added easily, as long as they support quadratic objectives (or as long as no power plants with linear cost supply curves are used).

============
Installation
============

Steps to use Grimsel:

1. Create a conda environment with the packages requirements which can be found in `<https://github.com/arthurrinaldi/grimsel/blob/master/requirements.txt>`_
2. Make sure you have CPLEX installed or other solvers (would require some changes in the code) compatible with Pyomo
3. Create a *config_local.py* file with the path of the input csv files (and additional path to rebuild the input files)
4. Download the full code or clone it on your local repository which contains the following folders:

    * The folder **grimsel** contains the model code (`<https://github.com/arthurrinaldi/grimsel/tree/master/grimsel>`_)

    * The folder **call_model** contains the python files to call the model and reproduce the results of previous studies (`<https://github.com/arthurrinaldi/grimsel/tree/master/call_model>`_)
    * The folder **input_data** contains all the csv input files to reproduce the results of previous studies (`<https://github.com/arthurrinaldi/grimsel/tree/master/input_data>`_)
    * The folder **model_loop_modifier** contains the python files to reproduce the different scenarios of the previous studies (`<https://github.com/arthurrinaldi/grimsel/tree/master/model_loop_modifier>`_)
    * The folder **build_input** contains the python files and the raw data to rebuild the input data found in folder **input_data** (`<https://github.com/arthurrinaldi/grimsel/tree/master/build_input>`_)

All folders and files have suffix names depending on the scope and the study:

* Suffix *_national_aggr*: All data are aggregated at the national level (1 node per country) for Switzerland, France, Italy, Austria and Germany
* Suffix *_archetype_disaggr*: Switzerland disaggregated by archetype (12 nodes) by consumer types and urban settings, results for this study `<https://doi.org/10.1016/j.jclepro.2020.120762>`_
* Suffix *_res_heating*: Extension of the model to heating in the Swiss residential sector, sector coupling, (24 heating nodes and 30 electricity nodes), results for this study `<https://doi.org/10.1016/j.apenergy.2020.116110>`_
* Suffix *_ee_dhw* and *_dsr_ee_dhw*: Including many flexibility options such as demand-side response (DSR), domestic hot water electric boilers (DHW) and electrical energy efficiency, results for this study *under review*

=============
Documentation
=============

`<https://grimsel.readthedocs.io/>`_

============
Publications
============
  * \A. Rinaldi *et al.*, Decarbonising heat with optimal PV and storage investments: A detailed sector coupling modelling framework with flexible heat pump operation, Applied Energy, `<https://doi.org/10.1016/j.apenergy.2020.116110>`_.
  * \M. C. Soini *et al.*, Does bulk electricity storage assist wind and solar in replacing dispatchable power production?, Energy Economics, `<https://doi.org/10.1016/j.eneco.2019.104495>`_.
  * \A. Rinaldi *et al.*, Optimised allocation of PV and storage capacity among different consumer types and urban settings: A prospective analysis for Switzerland, Journal of Cleaner Production, `<https://doi.org/10.1016/j.jclepro.2020.120762>`_.
  * \M. C. Soini *et al.*, Impact of prosumer battery operation on the cost of power supply, Journal of Energy Storage `<https://doi.org/10.1016/j.est.2020.101323>`_.
