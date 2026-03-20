from main import *
import matplotlib.pyplot as plt
import smbus3
import numpy as np
from plastic_analysis import *
import pandas as pd
import keyboard as kb

class data():

    def __init__(self,file_path,ex_cal_factor,zero_disp_voltage,strain_gauge=False,strain_gauge_cal=None):
        self.funDAQ = DAQ(file_path=file_path)
        self.funADC = ADC()
        self.buffer = 1000
        self.file_path = file_path
        self.ex_cal_factor = ex_cal_factor/25.4 # in/V
        self.zero_disp_voltage = zero_disp_voltage
        self.strain_gauge = strain_gauge
        self.strain_gauge_cal = strain_gauge_cal

    def run(self):
        i = 0
        loadcell_voltage = np.zeros(self.buffer)
        force = np.zeros(self.buffer)
        time_ = np.zeros(self.buffer)
        extensometer_voltage = np.zeros(self.buffer)
        strain = np.zeros(self.buffer)
        place_holder = np.zeros(self.buffer)
        time0 = time.monotonic()
        while True:
            loadcell_voltage[i] = self.funADC.readVoltage(device='load_cell')
            force[i] = loadcell_voltage[i]*(1000/1)*.224809 # load cell cal factor 1v/1000N, .223809 lb/N
            extensometer_voltage[i] = self.funADC.readVoltage(device='extensometer_differential')
            time_[i] = time.monotonic()-time0
            if self.strain_gauge==False:
                initial_gauge_length = (.5 -((self.zero_disp_voltage-extensometer_voltage[0])*self.ex_cal_factor))
                extensometer_displacement = (extensometer_voltage[i]-extensometer_voltage[0])*self.ex_cal_factor # calculate displacement
                strain[i] = extensometer_displacement/initial_gauge_length # calculate strain
            else:
                strain[i] = extensometer_voltage[i]*self.strain_gauge_cal
            place_holder[i] = i
            i += 1
            if i==1000:
                i=0
                self.funDAQ.save(force=place_holder,
                                 pressure=place_holder,
                                 displacement=place_holder,
                                 setpoint=place_holder,
                                 control=place_holder,
                                 temp1=loadcell_voltage,
                                 temp2=extensometer_voltage,
                                 temp3=force,
                                 temp4=strain,
                                 time_=time_)
            if kb.is_pressed('q'):
                temp_loadcell_voltage = np.zeros(i)
                temp_extensometer_voltage = np.zeros(i)
                temp_force = np.zeros(i)
                temp_strain = np.zeros(i)
                temp_time = np.zeros(i)
                temp_placeholder = np.zeros(i)
                temp_loadcell_voltage = loadcell_voltage[0:i]
                temp_extensometer_voltage = extensometer_voltage[0:i]
                temp_force = force[0:i]
                temp_strain = strain[0:i]
                temp_time = time_[0:i]
                temp_placeholder = place_holder[0:i]
                self.funDAQ.save(force=temp_placeholder,
                                 pressure=temp_placeholder,
                                 displacement=temp_placeholder,
                                 setpoint=temp_placeholder,
                                 control=temp_placeholder,
                                 temp1=temp_loadcell_voltage,
                                 temp2=temp_extensometer_voltage,
                                 temp3=temp_force,
                                 temp4=temp_strain,
                                 time_=temp_time)
                break

    def calculate_mod(self,width,thickness,start_bound,end_bound,file,plot=False,new_name=None,save_data=False,directory=None):
        data = pd.read_csv(filepath_or_buffer=file)
        loadcell_voltage = data['temp1'].to_numpy() 
        force = loadcell_voltage*(1000/1)*(1/4.44822) # load cell cal factor 1v/1000N, .223809 lb/N
        stress = force/(width*thickness) #calculate stress
        extensometer_voltage = data['temp2'].to_numpy()

        initial_gauge_length = (.5 -((self.zero_disp_voltage-extensometer_voltage[0])*self.ex_cal_factor))
        extensometer_displacement = (extensometer_voltage-extensometer_voltage[0])*self.ex_cal_factor # calculate displacement
        strain = extensometer_displacement/initial_gauge_length # calculate strain
        print(np.max(extensometer_voltage))
        print(np.min(extensometer_voltage))
        #exit()
        time_ = data['time_'].to_numpy()
        start_bound_es = np.argmin(abs(loadcell_voltage-.05))
        diff_array = np.zeros(len(force))
        for i in range(int(len(force)/2)):
            target = .05 # v
            diff_array[i] = np.abs(target-loadcell_voltage[-i])
        end_bound_es = np.argmin(diff_array)
        print(f"start bound = {start_bound}, end bound = {end_bound}")
        E = np.polyfit(strain[start_bound:end_bound],stress[start_bound:end_bound],1)[0]
        print(f"elastic modulus = {E*(10**-6)}")
        if save_data==True:
            path = directory+new_name
            data['temp3'] = stress
            data['temp4'] = strain
            data.to_csv(path,index=False)
        if plot==True:
            plt.plot(strain[start_bound:end_bound],stress[start_bound:end_bound])
            #plt.plot(strain,stress)
            plt.xlabel("Strain in/in")
            plt.ylabel("Stress (psi)")
            plt.title("new_name")
            plt.show()

    def calculate_mod_sg(self,width,thickness,start_bound,end_bound,file,plot=False,new_name=None,save_data=False,directory=None):
        data = pd.read_csv(filepath_or_buffer=file)
        loadcell_voltage = data['temp1'].to_numpy() 
        force = loadcell_voltage*(1000/1)*(1/4.44822) # load cell cal factor 1v/1000N, .223809 lb/N
        stress = force/(width*thickness) #calculate stress
        strain_gauge_voltage = data['temp2'].to_numpy()

        strain = strain_gauge_voltage*5.96236876e-3#5.969014608e-3 # calculate strain
        time_ = data['time_'].to_numpy()
        start_bound_es = np.argmin(abs(loadcell_voltage-.05))
        diff_array = np.zeros(len(force))
        for i in range(int(len(force)/2)):
            target = .05 # v
            diff_array[i] = np.abs(target-loadcell_voltage[-i])
        end_bound_es = np.argmin(diff_array)
        print(f"start bound = {start_bound}, end bound = {end_bound}")
        E = np.polyfit(strain[start_bound:end_bound],stress[start_bound:end_bound],1)[0]
        print(f"elastic modulus = {E*(10**-6)}")
        if save_data==True:
            path = directory+new_name
            data['temp3'] = stress
            data['temp4'] = strain
            data.to_csv(path,index=False)
        if plot==True:
            plt.plot(strain[start_bound:end_bound],stress[start_bound:end_bound])
            #plt.plot(strain,stress)
            plt.xlabel("Strain in/in")
            plt.ylabel("Stress (psi)")
            plt.title("new_name")
            plt.show()

funData = data(file_path="ATS/ATS_clone/ats_suite/Expiremental Data/MTS testing/test",
               ex_cal_factor=1,#.803312626, # 1 mm/V
               zero_disp_voltage=2.504,#2.484, # 2.504 .0045mm disp
               strain_gauge=False,
               strain_gauge_cal=1)
#funData.run()

# funData.calculate_mod(width=.12535,
#                       thickness=.125,
#                       start_bound=3090,
#                       end_bound=10830,
#                       file="ATS/ATS_clone/ats_suite/Expiremental Data/MTS testing/25-D2-7075_MOD7",
#                       plot=True,
#                       new_name="25-A35_MOD1_SS",
#                       save_data=False,
#                       directory="ATS/ATS_clone/ats_suite/Expiremental Data/MTS testing/")

funData.calculate_mod_sg(width=.125,
                         thickness=.125,
                         start_bound=3500,
                         end_bound=14000,
                         file="ATS/ATS_clone/ats_suite/Expiremental Data/MTS testing/P04(5)_G8_MOD1",
                         plot=True,
                         new_name="25-A35_MOD1_SS",
                         save_data=False,
                         directory="ATS/ATS_clone/ats_suite/Expiremental Data/MTS testing/")

# 25-A35 MOD2 2808 - 11690
# 25-A35 MOD3 3767 - 12060

#25-B28 MOD1 3520 - 14700
#25-B28 MOD2 3715 - 14875
#25-B28 MOD3 3830 - 14188
#25-B28 MOD4 EX 3120 - 14290
#25-B28 MOD5 EX 2710 - 13880
#25-B28 MOD6 EX 2980 - 14150
#25-B28 MOD7 EX 3010 - 14185

#25-D2-7075 MOD1 3320 - 11100
#25-D2-7075 MOD3 3035 - 10855
#25-D2-7075 MOD4 EX 2930 - 10700
#25-D2-7075 MOD6 EX 2900 - 10690
#25-D2-7075 MOD7 EX 3090 - 10830

#P04(7) MOD1 3200 - 14365
#P04(7) MOD2 3145 - 14300
#P04(7) MOD3 3145 - 14300


#extensometer cal factor = .803312626mm/V, zero disp voltage = 2.484


# funADC = ADC()
# a = []
# for i in range(500):

#     a.append(funADC.readVoltage(device='extensometer_differential'))
#     #a.append(funADC.readRaw(device='extensometer'))

# print('%.4f' % np.average(a))



# funADC = ADC()
# v = np.zeros(500)
# for i in range(500):
#     v[i] = funADC.readVoltage(device='load_cell')
#     #v[i] = funADC.readVoltage(device='extensometer_differential')
# print(f"voltage = {round(np.average(v),4)}, stddev = {round(np.std(v),0)}")
#plt.plot(range(500),v)
#plt.show()

def slope():
    input = [.5,1,1.5,2,2.5,3,3.5,4,4.5,5] # ch1
    output = [2665,5330,7995,10660,13325,15960,18655,21320,23985,26650] #ch1
    #input = [.5,1,1.5,2,2.5,3,3.5,4,4.5,5] # ch1
    #output = [2665,5330,7995,10659,13323,15987,18651,21848,23979,26642] #ch1
    slope = np.polyfit(output,input,1)
    print(f"slope = {slope[0]}, offset = {slope[1]}")
#slope()
