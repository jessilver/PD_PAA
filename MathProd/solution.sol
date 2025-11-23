Problem:    adp_model
Rows:       26
Columns:    18 (9 integer, 9 binary)
Non-zeros:  72
Status:     INTEGER OPTIMAL
Objective:  Total_Cost = -25.34 (MINimum)

   No.   Row name        Activity     Lower bound   Upper bound
------ ------------    ------------- ------------- -------------
     1 Total_Cost            -8.8525                             
     2 One_EV_Per_Connector[1,0]
                                   1                           1 
     3 One_EV_Per_Connector[1,1]
                                   1                           1 
     4 One_EV_Per_Connector[2,0]
                                   0                           1 
     5 One_Connector_Per_EV[101]
                                   1                           1 
     6 One_Connector_Per_EV[102]
                                   0                           1 
     7 One_Connector_Per_EV[103]
                                   1                           1 
     8 Max_Charger_Power[1,0,101]
                                 -22                          -0 
     9 Max_Charger_Power[1,0,102]
                                   0                          -0 
    10 Max_Charger_Power[1,0,103]
                                   0                          -0 
    11 Max_Charger_Power[1,1,101]
                                   0                          -0 
    12 Max_Charger_Power[1,1,102]
                                   0                          -0 
    13 Max_Charger_Power[1,1,103]
                                 -22                          -0 
    14 Max_Charger_Power[2,0,101]
                                   0                          -0 
    15 Max_Charger_Power[2,0,102]
                                   0                          -0 
    16 Max_Charger_Power[2,0,103]
                                   0                          -0 
    17 Grid_Capacity_Limit
                                   0                       1e+09 
    18 Demand_Satisfaction[1,0,101]
                                   0                          40 
    19 Demand_Satisfaction[1,0,102]
                                   0                          10 
    20 Demand_Satisfaction[1,0,103]
                                   0                          25 
    21 Demand_Satisfaction[1,1,101]
                                   0                          40 
    22 Demand_Satisfaction[1,1,102]
                                   0                          10 
    23 Demand_Satisfaction[1,1,103]
                                   0                          25 
    24 Demand_Satisfaction[2,0,101]
                                   0                          40 
    25 Demand_Satisfaction[2,0,102]
                                   0                          10 
    26 Demand_Satisfaction[2,0,103]
                                   0                          25 

   No. Column name       Activity     Lower bound   Upper bound
------ ------------    ------------- ------------- -------------
     1 X[1,0,101]   *              1             0             1 
     2 X[1,1,101]   *              0             0             1 
     3 X[2,0,101]   *              0             0             1 
     4 X[1,0,102]   *              0             0             1 
     5 X[1,1,102]   *              0             0             1 
     6 X[2,0,102]   *              0             0             1 
     7 X[1,0,103]   *              0             0             1 
     8 X[1,1,103]   *              1             0             1 
     9 X[2,0,103]   *              0             0             1 
    10 Q[1,0,101]                  0             0               
    11 Q[1,0,102]                  0             0               
    12 Q[1,0,103]                  0             0               
    13 Q[1,1,101]                  0             0               
    14 Q[1,1,102]                  0             0               
    15 Q[1,1,103]                  0             0               
    16 Q[2,0,101]                  0             0               
    17 Q[2,0,102]                  0             0               
    18 Q[2,0,103]                  0             0               

Integer feasibility conditions:

KKT.PE: max.abs.err = 0.00e+00 on row 0
        max.rel.err = 0.00e+00 on row 0
        High quality

KKT.PB: max.abs.err = 0.00e+00 on row 0
        max.rel.err = 0.00e+00 on row 0
        High quality

End of output
