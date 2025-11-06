import numpy as np
import pandas as pd
import os

class solver():

    def __init__(self,path,log_callback,base_dir):
        '''
        DEFINITIONS:
        '''
        self.log = log_callback # define callback attribute
        # ===== Read Data =====
        file_ext = os.path.splitext(path)[1].lower()
        if file_ext=='.csv': # check for csv file type
            data = pd.read_csv(path) # read test data
        elif file_ext=='.txt': # check for .txt file type
            data = pd.read_csv(path,sep=r'\s+',header=None,names=["force",'pressure','displacement','setpoint','control','temp1','temp2','temp3','temp4','time']) # load old file type
        self.force = data['force'].to_numpy() # define force, convert to numpy array
        self.displacement = data['displacement'].to_numpy() # define displacement, convert to numpy array
        if base_dir==None: # if a base directory hasn't been selected
            pass
        else:
            os.chdir(base_dir) # change working directory to base directory
        try:
            df = pd.read_csv("frame_compliance_log.csv") # read frame compliance log
            self.frame_displacement_function = df['slope'].to_numpy()[-1] # get latest frame displacement function
            self.frame_displacement_function_zero = df['zero'].to_numpy()[-1] # get latest zero frame displacement
        except FileNotFoundError as error:
            self.log(f"No compliance data available for analysis: {error}")

    def calculate_area(self,poi,thickness,g_width,t_width,D1):
        # define piecewise cross-sectional area function, starting at the center of the gauge, calculated at point of interest (poi)
        '''
        poi: Point of interest along specimen in inches
        thickness: Specimen thickness in inches
        g_width: Width of gauge region in inches
        t_width: Width of tab region in inches
        D1: Diameter of pin-hole
        '''
        # ===== Pre-Defined Geometric Values =====
        p1 = .28125 # end of gauge area
        p2 = 1.25 # end of radial section
        p3 = 1.3125 # end of constant width tab section
        p4 = 1.40625 # center of pin-hole
        r0 = 1.8993565 # curvature radius
        r1 = D1/2 # hole radius
        a0 = g_width*thickness # calculate gauge cross-sectional area
        a0t = t_width*thickness # calculate constant area tab cross-sectional area
        # ===== Gauge Region =====
        if 0<=poi<=p1:
            # half of gauge area
            area = a0 # define cross-sectional area
        # ===== Radial Section =====
        elif p1<poi<p2:
            fpoi = poi-p1 # offset poi to zero at start of bound
                # calculate dr0
            theta = np.arcsin(fpoi/r0) # calculate angle in radians between verticle line and 'poi to center of radius' line
            r0_prime = r0*np.cos(theta)# calculate verticle distance to center 'r_prime' for a given poi (r_prime = r @ theta = 0 , r_prime = 0 @ theta = 90)
            dr0 = r0-r0_prime # verticle position at a given poi (i.e. calculate instantaneous thickness throughout the radius)
                # calculate area
            area = (2*dr0*thickness)+a0 # calculate instantaneous cross-sectional area - radial area + gauge area (a0)
        # ===== Constant-Area Tab Section =====
        elif p2<=poi<=p3:
            area = a0t # define cross-sectional area
        # ===== Pin-Hole Section =====
        elif p3<poi<=p4:
            fpoi = poi-p3 # offset poi to zero at start of bound
                # calculate dr1
            d = r1-fpoi # 'adjacent' length in hole
            theta = np.arccos(d/r1) # calculate angle in radians between horizontal axis and hypoteneus 
            r1_prime = r1*np.sin(theta) # calculate verticle distance to horizontal axis from hypoteneus intersection of hole (i.e. 'y' component)
            dr1 = r1-r1_prime # verticle position inside hole at a given poi (i.e. the dimension from edge of hole to hole intersection at poi)
                # calculate area
            area = ((t_width-D1)+(2*(dr1)))*thickness # calculate instantaneous cross-sectional area - curved area (around hole) + rectangular area
        else:
            print(f"poi = {poi} outside boundary, try again")
            exit()

        return area

    def calculate_elastic_deformation(self,elastic_modulus,max_load):
        specimen_elastic_deformation_slope = 6.49212*(10**-6)#7.06414*(10**-6) # specimen displacement as a function of load P04(5) - modeled in abaqus - VERIFIED 8/6/25 ITS CORRECT
        #update later to use FEA - REPLACES calculate_dl
        return specimen_elastic_deformation_slope

    def calculate_dL(self,
                     thickness,
                     g_width,
                     t_width,
                     D1,
                     E,
                     gauge_length,
                     hole2mark_initial,
                     hole2mark_final):
        '''
        num_points: number of intervals used in riemann sum for each section
        thicknesss: specimen thickness in inches
        g_width: gauge section width in inches
        t_width: tab width in inches
        E: Measured elastic modulus in psi
        final_length_UTS: LVDT displacement at UTS load
        gauge_length: measured gauge length of marked area
        hole2mark_initial: initial gauge mark distance to center of pin-hole average between both sides
        hole2mark_final: final gauge mark distance to center of pin-hole average between both sides
        '''

        '''Note: Two methods of calculation can be achieved.
            1: Integration and evaluation at boundaries
            2: Riemann sum

            calculation uses an adjusted form of hooke's law to solve for elastic displacement:
            U = (FL/AE)

            Note: ALL CALCULATIONS ARE DONE ASSUMING HALF SYMMETRY
        '''
        # ===== Riemann Sum Calculation =====
        idx = np.argmax(self.force) # find UTS index
        UTS_displacement = self.displacement[idx] # pin-to-pin displacement at UTS
        UTS_force = self.force[idx] # maximum force (UTS)
        p1 = .28125 # end of gauge area
        p2 = 1.25 # end of radial section
        p3 = 1.3125 # end of constant width tab section
        p4 = 1.40625 # center of pin-hole
        num_points = 750000 # number of points used in riemann sum calculation in each section

        # ===== Section 4: Pin-Hole Section =====
        L_PH = (p4-p3)/num_points # length increment of Pin-Hole Section - 'initial length' term in displacement formula
        R_PH = np.arange(p4,p3,-L_PH) # length range: p4 to p3 in increments of L_PH
            # ----- Elastic Deformation -----
        U_PH_E = np.zeros(num_points) # displacement array U for Pin-Hole (PH) section, Elastic        
        for i in range(num_points):
            U_PH_E[i] = (UTS_force*L_PH)/(self.calculate_area(poi=R_PH[i],thickness=thickness,g_width=g_width,t_width=t_width,D1=D1)*E)
        U_PH_E_TTL = sum(U_PH_E) # total elastic deformation in the Pin-Hole section

        # ===== Section 3: Tab - Constant Width Section =====
            # ----- Elastic Deformation -----
        L_TB = (p3-p2) # length of constant width tab region
        U_TB_E_TTL = (UTS_force*L_TB)/(self.calculate_area(poi=((p3+p2)/2),thickness=thickness,g_width=g_width,t_width=t_width,D1=D1)*E)
        # ===== Section 2: Radial Section =====
            # ----- Elastic Deformation -----
        L_RD = (p2-p1)/num_points # length increment of radial Section - 'initial length' term in displacement formula
        R_RD = np.arange(p2,p1,-L_RD) # length range: p2 to p1 in increments of L_RD
        U_RD_E = np.zeros(num_points) # displacement array U for Pin-Hole (PH) section, Elastic
        for i in range(num_points):
            U_RD_E[i] = (UTS_force*L_RD)/(self.calculate_area(poi=R_RD[i],thickness=thickness,g_width=g_width,t_width=t_width,D1=D1)*E)
        U_RD_E_TTL = sum(U_RD_E) # total elastic deformation in the Pin-Hole section

        # ===== Plastic Deformation Section 4 -> 2 =====
        U_4_2_P_TTL = hole2mark_final-hole2mark_initial # total plastic deformation outside gauge region

        # ===== Section 1: Gauge Section =====
            # ----- Elastic Deformation -----
        L_G = (p1) # length of gauge region (half)
        U_G_E_TTL = (UTS_force*L_G)/(self.calculate_area(poi=np.average(p1),thickness=thickness,g_width=g_width,t_width=t_width,D1=D1)*E)
            # ----- Plastic Deformation -----
        frame_displacement = self.frame_displacement_function*UTS_force # frame displacement function pulled from calibration log
        specimen_displacement = UTS_displacement-frame_displacement # isolate specimen displacement from LVDT measured displacement by subtracting frame displacement

        U_E_TTL = (U_PH_E_TTL+U_TB_E_TTL+U_RD_E_TTL+U_G_E_TTL) # total elastic deformation from all four sections #
        print(f"total elastic deformation {U_E_TTL}")
        #U_E_TTL = (U_PH_E_TTL+U_TB_E_TTL+U_RD_E_TTL) # total elastic deformation from all four sections minus the gauge
        U_G_TTL = specimen_displacement-(2*(U_E_TTL+U_4_2_P_TTL)) # total specimen displacement @ UTS minus plastic deformation outside gauge minus total elastic deformation
        '''


        NOTE***
        Elastic calculations are off by a small amount - ex: for P04(5)_LE7 total elastic deformation was calculated to be .0138", abaqus reported .0155"
        - Update later to use FEA to calculate elastic deformation
        


        '''
        #print(f"Specimen Displacement @ UTS = {specimen_displacement}")

        # ===== Calculations/Results =====
        UTS_strain = U_G_TTL/gauge_length # calculate strain at UTS using initial gauge marking length
        #print(f"Elastic Pin-Hole deformation = {2*U_PH_E_TTL:.4f}")
        #print(f"Elastic Tab deformation = {2*U_TB_E_TTL:.4f}")
        #print(f"Elastic Radial deformation = {2*U_RD_E_TTL:.4f}")
        #print(f"Elast Gauge deformation = {2*U_G_E_TTL:.4f}")
        # print(f"Plastic deformation Section 4-2 = {2*U_4_2_P_TTL:.4f}")
        # print(f"Total gauge deformation = {U_G_TTL:.4f}")
        # print(f"Total elastic deformation = {2*U_E_TTL:.4f}")
        # print(f"Strain at UTS = {UTS_strain*100:.2f}%")
        return UTS_strain
    
#test = solver(path="P04(5)_LE7.txt",log_callback=None,base_dir=None)
#test.calculate_dL(thickness=.125,g_width=.125,t_width=.656,D1=.1875,E=17119000,gauge_length=.5625,hole2mark_initial=1.1282,hole2mark_final=1.21935)