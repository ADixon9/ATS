import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from solver import *
import matplotlib.pyplot as plt
import time
import os
pd.set_option('display.max_rows', None)  # Show all rows
pd.set_option('display.max_columns', None)  # Show all columns

class analyize():

    def __init__(self,
                 path,
                 thickness,
                 g_width,
                 t_width,
                 D1,
                 gauge_length_initial,
                 CH_hole2mark_initial,
                 AC_hole2mark_initial,
                 CH_hole2mark_final,
                 AC_hole2mark_final,
                 base_dir,
                 log_callback):
        '''
        DEFINITIONS:
        path: file path leading to test data
        thickness: specimen thickness in inches
        g_width: specimen gauge width in inches
        t_width: specimen tab width in inches (average)
        D1: specimen pin-hole diameter (average)
        gauge_length_initial: length of initial gauge marking
        CH_hole2mark_initial: initial distance from gauge mark to hole center, crosshead side
        AC_hole2mark_initial: initial distance from gauge mark to hole center, actuator side
        CH_hole2mark_final: final distance from gauge mark to hole center, crosshead side
        AC_hole2mark_final: final distance from gauge mark to hole center, actuator side
        base_dir: base directory used to load compliance data
        '''
        # ===== initialize attributes =====
        self.log = log_callback # define log callback attribute
        self.thickness = thickness
        self.g_width = g_width
        self.t_width = t_width
        self.x_section_area = g_width*thickness # calculate specimen cross-sectional area
        self.base_dir = base_dir # set base directory attribute
        try:
            self.D1 = D1
            self.gauge_length_initial = gauge_length_initial
            self.hole2mark_initial = np.average([CH_hole2mark_initial,AC_hole2mark_initial]) # average initial hole to mark distance
            self.hole2mark_final = np.average([CH_hole2mark_final,AC_hole2mark_final]) # average final hole to mark distance
        except TypeError:
            pass # running modcheck analysis, these values dont exist
        try:
            self.path = path
        except TypeError:
            # Data hasn't been loaded yet
            pass
        os.chdir(self.base_dir) # set working directory to base directory to load compliance data
        try:
            df = pd.read_csv("frame_compliance_log.csv") # read frame compliance log
            self.frame_displacement_function = df['slope'].to_numpy()[-1] # get latest frame displacement function
            self.frame_displacement_function_zero = df['zero'].to_numpy()[-1] # get latest zero frame displacement
        except FileNotFoundError as error:
            self.log(f"No compliance data available for analysis: {error}")

    def read_data(self):
        '''read csv data'''
        self.data = pd.read_csv(filepath_or_buffer=self.path)
        self.force = self.data['force'].to_numpy() # pull force data from file, convert to numpy array
        self.stress = self.force/self.x_section_area #calculate stress
        self.displacement = self.data['displacement'].to_numpy() # pull displacement data from file, convert to numpy array
        self.extensometer_voltage = self.data['temp1'].to_numpy() # get extensometer voltage
        os.chdir(self.base_dir) # set working directory back to base directory after opening data file

    def calculate_elastic_modulus(self):
        # ===== Define Strain =====
        R = .2970920099 #ratio of gauge 9/16" displacement to pin displacement - update 6/30/25
        frame_displacement = (self.frame_displacement_function*self.force)#+self.frame_displacement_function_zero # frame displacement function
        self.specimen_displacement = self.displacement-frame_displacement # calculate specimen displacement
        self.elastic_gauge_displacement = R*self.specimen_displacement # 9/16" gauge displacement
        self.elastic_gauge_strain = self.elastic_gauge_displacement/.5625 # dL/Li, (L-L0)/Li, L0=0
        #self.elastic_gauge_strain = self.elastic_gauge_strain-self.elastic_gauge_strain[0] # offset elastic gauge strain to be zero
        min_points = 300 # minimum linear fit window size
        n = len(self.displacement) # number of data points
        # ===== Find best end index starting from index 0 =====
        best_r2 = -np.inf # negative infinity
        best_end = n
        for i in range(min_points,len(self.displacement),1):
            x = self.displacement[:i].reshape(-1, 1) # reshape displacement for linear regression
            y = self.force[:i] # assign force array to end value
            model = LinearRegression().fit(x, y) # initialize model with xy data
            r2 = r2_score(y, model.predict(x)) # score model based on r^2
            if r2 > best_r2:
                best_r2 = r2 # re-assign best R2
                best_end = i # find index of best fit R2
            if (best_r2-r2)>=(.1*best_r2): # if current r2 is more than 10% different than best r2
                break
        # ===== With best end index, find best start index =====
        best_r2_final = -np.inf # negative infinity
        best_start = 0
        for i in range(0, best_end - min_points + 1):
            x = self.displacement[i:best_end].reshape(-1, 1) # reshape displacement for linear regression
            y = self.stress[i:best_end]
            model = LinearRegression().fit(x, y)
            r2 = r2_score(y, model.predict(x))
            if r2 > best_r2_final:
                best_r2_final = r2 # re-assign best R2
                best_start = i # find inex of best fit R2
        # ===== Final Linear Regression =====
        final_x = self.elastic_gauge_strain[best_start:best_end].reshape(-1,1) # define final x indicies, reshape for linear regression
        final_y =self.stress[best_start:best_end] # define final y indicies
        final_model = LinearRegression().fit(final_x.reshape(-1,1), final_y)
        temp_model=LinearRegression().fit(self.elastic_gauge_strain[-500:].reshape(-1,1),self.stress[-500:])
        print(f"moduli {final_model.coef_[0]*(10**-6)}")
        print(f"start {best_start}")
        print(f"end {best_end}")
        self.elastic_modulus = final_model.coef_[0]
        self.model_start = best_start # define model_start attribute
        self.model_end = best_end # define best_end attribute
        return self.elastic_modulus,best_start,best_end

    def elastic_conversion(self):
        linear_fit_y = (self.elastic_modulus*self.elastic_gauge_strain)-self.stress[0] # linear fit elastic region
        res = abs(self.stress-linear_fit_y) # calculate residuals of force and linear fit
        standard_dev = np.std(res[self.model_start:self.model_end]) # calculate standard deviation within best fit window
        #plt.plot(self.elastic_gauge_strain,self.stress)
        #plt.plot(self.elastic_gauge_strain[0:3000],linear_fit_y[0:3000])
        #plt.show()
        a = 0 # counter
        ''' ADJUST LATER IF NECESSARY - FINE TUNE STD DEV REQUIREMENT'''
        for i in range(self.model_start,len(self.force)):
            if res[i]<=(3*standard_dev):
                self.yield_index = i#+1 # define yield index
                a=0
            a += 1 # increase counter
            if a>=1000: # if yield index doesnt update in 1000 points
                break
                #self.yield_index = len(self.stress)#+1 # define yield index as the last index
        print(f"yield index {self.yield_index}")
        print(f"True yield strength = {self.stress[self.yield_index]}")
        ''' elastic values will need joined with plastic values before returning to save data for tensile'''
        return self.stress[:self.yield_index], self.elastic_gauge_strain[:self.yield_index]
        
    def plastic_conversion(self):
        # ===== Calculate Plastic Strain
        funSolver = solver(path=self.path,
                           log_callback=None,
                           base_dir=self.base_dir) # initialize solver class
        self.UTS_strain = funSolver.calculate_dL(thickness=self.thickness,
                                                 g_width=self.g_width,
                                                 t_width=self.t_width,
                                                 D1=self.D1,
                                                 E=self.elastic_modulus,
                                                 gauge_length=self.gauge_length_initial,
                                                 hole2mark_initial=self.hole2mark_initial,
                                                 hole2mark_final=self.hole2mark_final)
        UTS_index = np.argmax(self.stress) # define UTS index
        scaling_index_length = int(UTS_index-self.yield_index) # number of indices between UTS and yield point
        yield_diff = self.displacement[self.yield_index]-self.elastic_gauge_strain[self.yield_index] # gap between displacement and strain @ true yield point
        UTS_diff = self.UTS_strain-(self.displacement[UTS_index])#length of gap between values to scale
        scaling_array = np.linspace(0,(UTS_diff+yield_diff),num=scaling_index_length) #displacement is shifted to match at true yield point
        self.plastic_strain = np.zeros(len(self.elastic_gauge_strain)-self.yield_index) # allocate plastic strain array
        self.strain = np.zeros(len(self.elastic_gauge_strain)) # allocate total strain array
        for i in range(len(self.plastic_strain)):
            if i<=scaling_index_length-11: # if we're between the yield point and UTS
                self.plastic_strain[i] = self.displacement[i+self.yield_index]+scaling_array[i]-yield_diff
            else: # if we're past UTS
                self.plastic_strain[i] = self.displacement[i+self.yield_index]+scaling_array[-1]-yield_diff
        # ===== Define Total Strain =====
        self.strain[:self.yield_index] = self.elastic_gauge_strain[:self.yield_index] # define elastic strain
        self.strain[self.yield_index:] = self.plastic_strain # define plastic strain
        # ===== Calculate Results =====
        # ----- UTS -----
        self.UTS = self.stress[UTS_index] # identify UTS
        # ----- Yield Stress-----
        offset_yield_line = (self.elastic_modulus*(self.strain-.002))-self.stress[0] # linear fit elastic region
        int_diff = self.stress-offset_yield_line # find the intersection point
        offset_yield_idx = np.argwhere(np.diff(np.sign(self.stress-offset_yield_line)))[0][0]#np.where(np.diff(np.sign(int_diff)))[0] # intersection index
        self.yield_stress = self.stress[self.yield_index] # get true yield stress
        self.offset_yield_stress = self.stress[offset_yield_idx] # get offset yield stress
        print(self.stress[offset_yield_idx])
        #plt.plot(self.strain,self.stress)
        #plt.scatter(self.strain[UTS_index],self.stress[UTS_index],color='r')
        #plt.plot(self.strain[1000:4000],offset_yield_line[1000:4000],color='b')
        #plt.show()
    
    def total_conversion(self):
        self.elastic_conversion() # run elastic strain conversion first
        self.plastic_conversion() # run plastic strain conversion last
        return self.stress,self.strain,self.elastic_modulus,self.yield_stress,self.offset_yield_stress,self.UTS,self.UTS_strain

    def extensometer_conversion(self,cal_factor,save_data=False):
        cal_factor_inches = cal_factor/25.4 # convert mm/V to in/V
        initial_gauge_length = (.5-(2/25.4))+self.extensometer_voltage[0]*cal_factor_inches # .5" gauge length minus 2mm offset plus starting offset
        extensometer_displacement = (self.extensometer_voltage-self.extensometer_voltage[0])*cal_factor_inches # calculate displacement
        extensometer_strain = extensometer_displacement/initial_gauge_length # calculate strain
        self.data['temp1'] = extensometer_strain # replace voltage data with strain data
        adjusted_stress = self.stress-self.stress[0]
        mod = np.polyfit(extensometer_strain,adjusted_stress,deg=1)[0]
        print(f"Elastic modulus extensometer = {mod*(10**-6)}")
        if save_data==True:
            self.data.to_csv(self.path,index=False)
        else:
            pass

