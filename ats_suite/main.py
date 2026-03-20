import smbus3
import time
import datetime
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from subprocess import check_output
from simple_pid import PID
from datetime import datetime
from solver import *
from scipy.signal import savgol_filter
from sklearn.linear_model import LinearRegression
import shutil

bus = smbus3.SMBus(1) #creates an object to communicate over i2c with smbus


class ADC(): #ADS1115 Chip

    def __init__(self):
        self.refresh()

    def refresh(self):
        self.address = 0x48

    def config(self,device):
        config_register = 0b00000001 #config register
        if device=='LVDT':
            config = [0b00000000,0b11100011] # configuration is set to standard operation, continuous conversion, 860SPS, AIN0 = +, AIN1 = - (differential)
        elif device=="pressure_transducer":
            config = [0b01100000,0b11100011] # configuration is set to standard operation, continuous conversion, 860SPS, AIN2 = +, GND = - (single-ended)
        else:
            print("ERROR: ADC input device not recognized...")
        bus.write_i2c_block_data(self.address,config_register,config) # write configuration to configuration register
        time.sleep(1/520) # wait for configuration to activate

    def readVoltage(self,device):
        self.config(device) # configure ADC to read from selected device
        rawData = bus.read_i2c_block_data(self.address,0b00000000,2) # Read 16-bit voltage value from conversion register
        myCodevalue = (rawData[0]<<8 | rawData[1]) # convert (2) 8-bit numbers to 16 bit integer
        voltage = (5*myCodevalue)/26715 # approximate voltage

        return float("%.4f" % voltage) # return formatted voltage
    
    def readRaw(self,device):
        self.config(device) # configure ADC to read from selected device
        rawData = bus.read_i2c_block_data(self.address,0b00000000,2) # Reads 16-bit voltage value from conversion register
        myCodevalue = (rawData[0]<<8 | rawData[1]) # convert (2) 8-bit numbers to 16 bit integer
        
        return myCodevalue # return 16-bit integer voltage value

class DAC():

    def __init__(self,log_callback,status_callback):
        self.refresh(log_callback,status_callback)

    def refresh(self,log_callback,status_callback):
        self.address = 0x60
        self.funPT = PT(log_callback=log_callback,
                        status_callback=status_callback,
                        current_pressure_callback=None,
                        current_force_callback=None) # instantiate PT class
        self.log = log_callback
        self.status = status_callback
        if os.path.exists('IP_calibration_log.csv'):
            df = pd.read_csv('IP_calibration_log.csv')
            self.slope = df['slope'].to_numpy()[-1] # convert slope to numpy array, use last value
            self.zero = df['zero'].to_numpy()[-1] # convert zero to numpy array, use last value (psi)
        else:
            self.log("No I/P calibration data found. Please calibrate before use") # log command
        try:
            os.remove("IP_temp.csv") # remove temp file before calibrating
        except FileNotFoundError:
            pass  # it didn’t exist, which is fine

    def record_calibration_point(self,input_pressure,output_pressure,measurement_method_external,num_points):

        if measurement_method_external==True: # if measuring pressure externally, use the output pressure variable that was input into the function
            pass
        elif measurement_method_external==False: # if measuring pressure internally, output pressure is read through pressure transducer
            output_pressure = self.funPT.readPSI(callback=False) # read I/P output pressure, use callback
        df = pd.DataFrame({'input pressure':[input_pressure],'output pressure':[output_pressure]}) # create data frame
        write_header = not os.path.exists('IP_temp.csv') # check to see if the file exists, if so, define as false
        df.to_csv('IP_temp.csv',mode='a',header=write_header,index=False) # append data frame to csv
        df_read = pd.read_csv("IP_temp.csv") # read csv
        num_lines = len(df_read) # read number of rows in csv
        if (num_lines+1)<=num_points:
            self.log(f"Pressure {num_lines} recorded... continue to next measurement") # log point
            self.status(False) # log incomplete calibration status (plot temp file)
        else:
            input_pressure_data = df_read['input pressure'].to_numpy() # convert input pressure data to numpy array
            output_pressure_data = df_read['output pressure'].to_numpy() # convert output pressure data to numpy array
            self.log(f"Pressure {num_lines} recorded...")
            self.calibrate(input_pressure_data=input_pressure_data,output_pressure_data=output_pressure_data) # calibrate with value
            self.status(True) # log complete calibration stats (plot new file name)
        
    def calibrate(self,input_pressure_data,output_pressure_data):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cal_curve = np.polyfit(output_pressure_data,input_pressure_data,1) # linear curve fit degree 1.
        self.slope = cal_curve[0]
        self.zero = cal_curve[1] # zero point (psi))
        df = pd.DataFrame({'date':[timestamp],'slope':[self.slope],'zero':[self.zero]}) # create data frame with these values
        write_header = not os.path.exists('IP_calibration_log.csv') # check to see if the file exists, if so, define as false
        df.to_csv('IP_calibration_log.csv',mode='a',header=write_header,index=False) # append data frame to csv
        self.log("I/P transducer calibration complete...")

    def zero_reading(self):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            slope =self.slope # get current slope
        except NameError:
            self.log("No I/P transducer calibration data found, please calibrate before zeroing...")
        self.zero = slope*self.funPT.readPSI(callback=True) # record current pressure and calculate zero (psi))
        df = pd.DataFrame({'date':[timestamp],'slope':[slope],'zero':[self.zero]}) # create data frame with these values
        write_header = not os.path.exists('IP_calibration_log.csv') # check to see if the file exists, if so, define as false
        df.to_csv('IP_calibration_log.csv',mode='a',header=write_header,index=False) # append data frame to csv
        self.log("I/P transducer zero position set....")

    def writePSI(self,psi,callback=False):
        
        if psi > 98:
            self.log("Pressure cannot exceed 98 psi...") # log command
            psi = 98 # set maximum pressure
        elif psi < 3:
            self.log("Pressure must be at least 3 psi...") # log command
            psi = 3 # set minimum pressure

        try: # try writing calibrated pressure
            calibrated_psi = (psi*self.slope)+self.zero # calculate calibrated psi - units are in psi
            line = np.polyfit([0,98],[0,10],1) # linear fit
            voltage = (line[0]*calibrated_psi)-line[1] # calibrated voltage
        except AttributeError: # except if no calibration exists
            voltage = (10/98)*psi
        self.writeVoltage(voltage)
        if callback==False:
            pass
        elif callback==True:
            self.log(f"Pressure set to {psi} psi...") # log set pressure command

    def writeVoltage(self,voltage):

        if voltage > 10:
            voltage =10 # define maximum voltage
        elif voltage < 0:
            voltage = 0 # define minimum voltage
        
        codeValue = int(409.5*voltage) # converts the voltage to a 12-bit number
        byte1 = codeValue>>4
        byte2 = (codeValue&15)<<4
        data = [byte1,byte2]
        bus.write_i2c_block_data(self.address,0x40,data) # writing data to register

class PT():

    def __init__(self,log_callback,status_callback,current_pressure_callback,current_force_callback):
        self.refresh(log_callback,status_callback,current_pressure_callback,current_force_callback)

    def refresh(self,log_callback,status_callback,current_pressure_callback,current_force_callback):
        self.funADC = ADC()
        self.log = log_callback
        self.status = status_callback
        self.current_pressure = current_pressure_callback
        self.current_force = current_force_callback
        if os.path.exists('PT_calibration_log.csv'):
            df = pd.read_csv('PT_calibration_log.csv')
            self.slope = df['slope'].to_numpy()[-1] # convert slope to numpy array, use last value
            self.zero = df['zero'].to_numpy()[-1] # convert zero to numpy array, use last value
        else:
            self.log("No pressure transducer calibration data found. Please calibrate before use")
        try:
            os.remove("PT_temp.csv") # remove temp file before calibrating
        except FileNotFoundError:
            pass  # it didn’t exist, which is fine

    def record_calibration_point(self,pressure,num_points):

        counts = self.funADC.readRaw(device='pressure_transducer') # record current "Raw count" value
        df = pd.DataFrame({'pressure':[pressure],'counts':[counts]}) # create data frame
        write_header = not os.path.exists('PT_temp.csv') # check to see if the file exists, if so, define as false
        df.to_csv('PT_temp.csv',mode='a',header=write_header,index=False) # append data frame to csv
        df_read = pd.read_csv("PT_temp.csv") # read csv
        num_lines = len(df_read) # read number of rows in csv
        if (num_lines+1)<=num_points:
            self.log(f"Pressure {num_lines} recorded... continue to next measurement") # log point
            self.status(False) # log incomplete calibration status (plot temp file)
        else:
            pressure_data = df_read['pressure'].to_numpy() # convert displacement data to numpy array
            raw_data = df_read['counts'].to_numpy() # convert voltage data to numpy array
            self.log(f"Pressure {num_lines} recorded...")
            self.calibrate(pressure_data=pressure_data,raw_data=raw_data) # calibrate with value
            self.status(True) # log complete calibration stats (plot new file name)
        
    def calibrate(self,pressure_data,raw_data):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cal_curve = np.polyfit(raw_data,pressure_data,1) # linear curve fit degree 1.
        self.slope = cal_curve[0]
        self.zero = round(cal_curve[1],6) # zero point (bits)
        df = pd.DataFrame({'date':[timestamp],'slope':[self.slope],'zero':[self.zero]}) # create data frame with these values
        write_header = not os.path.exists('PT_calibration_log.csv') # check to see if the file exists, if so, define as false
        df.to_csv('PT_calibration_log.csv',mode='a',header=write_header,index=False) # append data frame to csv
        self.log("Pressure Transducer calibration complete...")

    def zero_reading(self):
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            slope =self.slope # get current slope
        except NameError:
            self.log("No Pressure Transducer calibration data found, please calibrate before zeroing...")
        self.zero = -slope*self.funADC.readRaw(device='pressure_transducer') # get current pressure value - "zero" point - convert counts to psi - zero is negative
        df = pd.DataFrame({'date':[timestamp],'slope':[slope],'zero':[self.zero]}) # create data frame with these values
        write_header = not os.path.exists('PT_calibration_log.csv') # check to see if the file exists, if so, define as false
        df.to_csv('PT_calibration_log.csv',mode='a',header=write_header,index=False) # append data frame to csv
        self.log("Pressure Transducer zero position set....")

    def readPSI(self,callback=False):

        try:
            pressure = (self.funADC.readRaw(device='pressure_transducer')*self.slope + self.zero) # measure pressure        
        except AttributeError:
            self.log('MEASUREMENT ERROR: No calibration data available, please calibrate and try again...')
        if callback==False:
            pass
        elif callback==True:
            self.current_pressure(pressure) # log current pressure
            self.log("Pressure measurement recorded...") # log measurement recorded
        return float("%.3f" % pressure)

    def readForce(self,callback=False):

        try:
            pressure = (self.funADC.readRaw(device='pressure_transducer')*self.slope + self.zero) # measure pressure        
        except AttributeError:
            self.log('MEASUREMENT ERROR: No calibration data available, please calibrate and try again...')
        force = (26.79*pressure)
        if callback==False:
            pass
        elif callback==True:
            self.current_force(force) # log current pressure
        return float("%.2f" % force)
        
class LVDT():

    def __init__(self,log_callback,status_callback,current_position_callback,current_voltage_callback):
        self.refresh(log_callback,status_callback,current_position_callback,current_voltage_callback)

    def refresh(self,log_callback,status_callback,current_position_callback,current_voltage_callback):

        self.funADC = ADC()
        self.log = log_callback # create log attribute
        self.status = status_callback # create status attribute
        self.current_position = current_position_callback
        self.current_voltage = current_voltage_callback
        if os.path.exists('LVDT_calibration_log.csv'):
            df = pd.read_csv('LVDT_calibration_log.csv')
            self.slope = df['slope'].to_numpy()[-1] # convert slope to numpy array, use last value
            self.zero = df['zero'].to_numpy()[-1] # convert zero to numpy array, use last value
        else:
            self.log("No LVDT calibration data found. Please calibrate before using LVDT")
        try:
            os.remove("LVDT_temp.csv") # remove temp file before calibrating
        except FileNotFoundError:
            pass  # it didn’t exist, which is fine
    
    def record_calibration_point(self,displacement,num_points):

        counts = self.funADC.readRaw(device='LVDT') # record current "Raw count" value
        df = pd.DataFrame({'displacement':[displacement],'counts':[counts]}) # create data frame
        write_header = not os.path.exists('LVDT_temp.csv') # check to see if the file exists, if so, define as false
        df.to_csv('LVDT_temp.csv',mode='a',header=write_header,index=False) # append data frame to csv
        df_read = pd.read_csv("LVDT_temp.csv") # read csv
        num_lines = len(df_read) # read number of rows in csv
        if (num_lines+1)<=num_points:
            self.log(f"Displacement {num_lines} recorded... continue to next measurement") # log point
            self.status(False) # log incomplete calibration status (plot temp file)
        else:
            displacement_data = df_read['displacement'].to_numpy() # convert displacement data to numpy array
            raw_data = df_read['counts'].to_numpy() # convert voltage data to numpy array
            self.log(f"Displacement{num_lines} recorded...")
            self.calibrate(displacement_data=displacement_data,raw_data=raw_data) # calibrate with value
            self.status(True) # log complete calibration stats (plot new file name)

    def calibrate(self,displacement_data,raw_data):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cal_curve = np.polyfit(raw_data,displacement_data,1) # linear curve fit degree 1. inches/volt
        self.slope = cal_curve[0]
        self.zero = cal_curve[1] # zero point
        df = pd.DataFrame({'date':[timestamp],'slope':[self.slope],'zero':[self.zero]}) # create data frame with these values
        write_header = not os.path.exists('LVDT_calibration_log.csv') # check to see if the file exists, if so, define as false
        df.to_csv('LVDT_calibration_log.csv',mode='a',header=write_header,index=False) # append data frame to csv
        self.log("LVDT calibration complete...")

    def zero_position(self):
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            slope =self.slope # get current slope
        except NameError:
            self.log("No LVDT calibration data found, please calibrate before zeroing...")
        self.zero = slope*self.funADC.readRaw(device='LVDT') # get current displacement value - "zero" point
        df = pd.DataFrame({'date':[timestamp],'slope':[slope],'zero':[self.zero]}) # create data frame with these values
        write_header = not os.path.exists('LVDT_calibration_log.csv') # check to see if the file exists, if so, define as false
        df.to_csv('LVDT_calibration_log.csv',mode='a',header=write_header,index=False) # append data frame to csv
        self.log("LVDT zero position set....")

    def measure(self,callback=False):

        if callback==False:
            try:
                position = (self.funADC.readRaw(device='LVDT')*self.slope - self.zero) # measure position
            except AttributeError:
                self.log('MEASUREMENT ERROR: No calibration data available, please calibrate and try again...')
        elif callback==True:
            try:
                position = (self.funADC.readRaw(device='LVDT')*self.slope - self.zero) # measure position
                self.current_position(position) # callback current position
                self.log("LVDT measurement recorded...")
            except AttributeError:
                self.log('MEASUREMENT ERROR: No calibration data available, please calibrate and try again...')
        return float("%.8f" % position)
    
    def measure_voltage(self,callback=False):

        voltage = self.funADC.readVoltage(device='LVDT') # measure LVDT voltage
        if callback==False:
            pass
        elif callback==True:
            self.current_voltage(voltage) # callback current voltage reading
        return voltage

class MUX():

    def __init__(self):
        self.refresh()

    def refresh(self):

        self.address = 0x70
        self.open_channels() # open channels on startup

    def open_channels(self,):

        bus.write_byte(self.address,0b11111111) # open all channels

class DAQ():

    def __init__(self,file_path,log_data_save_callback=False):
        self.refresh(file_path,log_data_save_callback)

    def refresh(self,file_path,log_data_save_callback):
        self.file_path = file_path
        self.log_data_save = log_data_save_callback
        
    def save(self,force,pressure,displacement,setpoint,control,time_):
        for i in range(len(force)):
            force[i] = float("%.2f" % force[i])
            pressure[i] = float("%.2f" % pressure[i])
            displacement[i] = float("%.5f" % displacement[i])
            setpoint[i] = float("%.5f" % setpoint[i])
            control[i] = float("%.2f" % control[i])
            time_[i] = float("%.5f" % time_[i])

        df = pd.DataFrame({'force':    force,
                           'pressure': pressure,
                           'displacement': displacement,
                           'setpoint': setpoint,
                           'control':  control,
                           'time_':    time_}) # create data frame with values
        write_header = not os.path.exists(self.file_path) # do not write header if it already exists
        df.to_csv(self.file_path,mode='a',index=False,header=write_header) # append/write data to file

class test():

    def __init__(self,log_callback,test_status_callback):
        self.refresh(log_callback,test_status_callback) # run on_start method

    def refresh(self,log_callback,test_status_callback):
        # ===== Instantiate Classes =====
        self.funDAC = DAC(log_callback=log_callback,
                          status_callback=None)
        self.funADC = ADC()
        self.funPT = PT(log_callback=log_callback,
                        status_callback=None,
                        current_pressure_callback=None,
                        current_force_callback=None)
        self.funLVDT = LVDT(log_callback=log_callback,
                            status_callback=None,
                            current_position_callback=None,
                            current_voltage_callback=None)
        # ----- Callbacks -----
        self.log = log_callback # define log variable
        self.test_status = test_status_callback # define test status variable
        # ===== Instantiate Test Variables =====
        self.stop_event = False # define stop event
        self.is_FC_running = False
        self.base_dir = os.getcwd() # get base directory
        self.buffer_size = 100 #buffer size in number of array elements
        self.setpoint_array = np.zeros(self.buffer_size)
        self.control_array = np.zeros(self.buffer_size)
        self.control_array_load = np.zeros(self.buffer_size)
        self.pressure_data = np.zeros(self.buffer_size)
        self.force_data = np.zeros(self.buffer_size)
        self.displacement_data = np.zeros(self.buffer_size)
        self.strain_data = np.zeros(self.buffer_size)
        self.temp1 = np.zeros(self.buffer_size)
        self.temp2 = np.zeros(self.buffer_size)
        self.temp3 = np.zeros(self.buffer_size)
        self.temp4 = np.zeros(self.buffer_size)
        self.time_array = np.zeros(self.buffer_size)

    def stop_test(self):
        self.stop_event = True # trigger stop event
        self.log("Stopping Test...")

    def frame_compliance(self,file_path,maxload,num_tests):
        self.is_FC_running = True # define attribute to determine if frame compliance is running
        base_name = os.path.basename(file_path) # get file names base name (without directory)
        os.chdir(os.path.dirname(file_path)) # change diretory to file path directory
        os.makedirs(base_name) # create a folder with the file name of file_path basename
        self.log("Compliance testing started...")
        # ===== Run Compliance Tests =====
        for i in range(num_tests):
            if self.stop_event==False:
                self.funDAC.writePSI(3) # set pressure to minimum
                time.sleep(3) # allow presure to equalize
                self.MODcheck(file_path=os.path.join(base_name,f"FC_test_{i}.csv"),
                            maxload=maxload,
                            load_rate=40,
                            status_callback='calibration')
            if self.stop_event==True: # if test is stopped
                self.funDAC.writePSI(3) # set pressure to minimum
                self.stop_event = False # reset stop event
                shutil.rmtree(file_path) # delete partially filled folder
                return
        # ===== Calculate Linear Fit =====
        force = np.array([]) # create empty numpy array
        displacement = np.array([]) # create empty numpy array
        os.chdir(base_name) # enter into base_name directory where test files are stored
        for i in range(num_tests):
            df = pd.read_csv(f'FC_test_{i}.csv')
            force = np.append(force,df['force'].to_numpy()) # append force values
            displacement = np.append(displacement,df['displacement'].to_numpy()) # append displacement values
        linear_fit = np.polyfit(y=displacement,x=force,deg=1) # generate force vs. displacement function
        # ===== Aggregate Data =====
        df = pd.DataFrame({'force':force,'displacement':displacement}) # create data frame with aggregate force and displacement values
        write_header = not os.path.exists('FC_test_aggregate.csv') # check to see if the file exists, if so, define as false
        df.to_csv('FC_test_aggregate.csv',mode='a',header=write_header,index=False) # append data frame to csv
        self.log("Compliance test complete...")

    def MODcheck(self,maxload,load_rate,file_path,status_callback="default"):
        funDAQ = DAQ(file_path=file_path,log_data_save_callback=None) # instantiate DAQ class
        n = 0 # loop counter
        step_size_psi = .01 # set step size in psi
        piston_area = 26.79 # define the area of the piston for force calculation
        max_pressure = 2*(maxload/piston_area) # maximum load divided by the piston area - multiplied by two for setpoint array buffer
        min_pressure = 3 # define minimum pressure
        num_points =  round((max_pressure-min_pressure)/(2*step_size_psi))# calculate the total number of points to be collected (pressure range/step size) - divide by 2 to keep step size the same given the buffer
        pressure_setpoint_array = np.linspace(3,max_pressure,num_points) # pressure setpoint array from min to max load in PSI
        total_test_time = maxload/load_rate # calculate total test time in seconds
        time_interval = total_test_time/num_points # calculate expected time interval
        start_time = time.time() # get start time
        while True:
            for i in range(self.buffer_size):
                current_time = time.time() # get current time
                # ===== Read Data =====
                self.pressure_data[i] = self.funPT.readPSI(callback=False) # get current pressure
                self.force_data[i] = self.pressure_data[i]*piston_area # pressure*area=force
                self.displacement_data[i] = self.funLVDT.measure(callback=False) # get current displacement
                self.time_array[i] = current_time-start_time # assign time elapsed
                self.funDAC.writePSI(pressure_setpoint_array[i+(self.buffer_size*n)]) # write pressure accounting for loop itterations
                # ===== End Test If Max Load Is Reached =====
                if self.force_data[i]>=maxload or self.stop_event==True: # if maxload is reached or stop event is triggered, end test
                    self.funDAC.writePSI(3)
                    temp_force = np.zeros(i) 
                    temp_pressure = np.zeros(i)
                    temp_displacement = np.zeros(i)
                    temp_setpoint_array = np.zeros(i)
                    temp_control_array = np.zeros(i)
                    temp_time = np.zeros(i)
                    for j in range(i):# ensures remaining data outside buffer is saved
                        temp_force[j] = self.force_data[j] 
                        temp_pressure[j] = self.pressure_data[j]
                        temp_displacement[j] = self.displacement_data[j]
                        temp_setpoint_array[j] = pressure_setpoint_array[j]
                        temp_control_array[j] = pressure_setpoint_array[j]
                        temp_time[j] = self.time_array[j]
                    funDAQ.save(force = temp_force,
                                pressure = temp_pressure,
                                displacement = temp_displacement,
                                setpoint = temp_setpoint_array,
                                control = temp_control_array,
                                time_ = temp_time)
                    self.log("Modulus Check Complete...")
                    if status_callback=='default':
                        self.test_status('MODcheck','default-True') # test is complete - plot on pre-test tab
                    elif status_callback=='calibration':
                        self.test_status('MODcheck','calibration-True') # test is complete - plot on calibration tab
                    elif status_callback=='None':
                        pass
                    return # break out of the function while keeping GUI running
                else:
                    pass
                # ===== Wait To Continue =====
                while True:
                    temp_time = time.time()
                    time_elapsed = temp_time-current_time # 
                    if time_elapsed >= time_interval: # if time elapsed is equal to or greater than time interval
                        break # break out of loop
                    else:
                        pass
            # ===== End of For Loop - Save Data =====
            n += 1 # increase loop counter
            funDAQ.save(force = self.force_data,
                        pressure = self.pressure_data,
                        displacement = self.displacement_data,
                        setpoint = pressure_setpoint_array[-self.buffer_size:],
                        control = pressure_setpoint_array[-self.buffer_size:],
                        time_ = self.time_array)
            if status_callback=='default':
                self.test_status('MODcheck','default-updated') # test status is 'updated' - data saved - plot on pre-test tab
            elif status_callback=='calibration':
                self.test_status('MODcheck','calibration-updated') # test status is 'updated' - data saved - plot on calibration tab
            elif status_callback==None:
                pass

    def tensile(self,kp,stroke_rate,file_path,status_callback='default'):
        funDAQ = DAQ(file_path=file_path,log_data_save_callback=None) # instantiate DAQ class
        stroke_rate = .03 # in/min stroke control
        piston_area = 26.79 # define the area of the piston for force calculation
        self.max_load = 0
        stop_condition = False
        ki=0;kd=0;setpoint=0
        pid = PID(kp,ki,kd,setpoint)#PID controller with constants and setpoint
        pid.output_limits = (3,98) #sets limit on output of PID
        start_time = time.time() # get start time
        while True:
            for i in range(self.buffer_size):
                current_time = time.time() # get current time
                # ===== Read Data =====
                self.pressure_data[i] = self.funPT.readPSI(callback=False) # get current pressure
                self.force_data[i] = self.pressure_data[i]*piston_area # pressure*area=force
                self.displacement_data[i] = self.funLVDT.measure(callback=False) # measure displacement
                self.time_array[i] = current_time-start_time # measure elapsed time
                setpoint = stroke_rate*self.time_array[i]*(1/60)
                pid.setpoint = setpoint # update PID controller setpoint
                self.setpoint_array[i] = setpoint # assign setpoint to data array
                self.control_array[i] = pid(self.displacement_data[i]) # assign control value to data array
                self.control_array_load[i] = self.control_array[i]*26.79 # convert control in psi to force (lbs)
                self.funDAC.writePSI(self.control_array[i]) # write the control pressure
                if i==self.buffer_size:
                    if np.max(self.force_data)>self.max_load: # if max load is increasing
                        self.max_load = np.max(self.force_data)
                        stop_threshold = (.2*np.average(self.force_data[:self.buffer_size]))
                        if stop_threshold<=100:
                            stop_threshold = 100
                    else: # if max load is not increasing -> past UTS
                        if np.average(self.force_data[:self.buffer_size])<=stop_threshold: # if average force is lower than stop threshold
                            stop_condition = True
                if  stop_condition or self.stop_event==True:
                    self.funDAC.writePSI(3)
                    temp_force = np.zeros(i)
                    temp_pressure = np.zeros(i)
                    temp_displacement = np.zeros(i)
                    temp_setpoint_array = np.zeros(i)
                    temp_control_array = np.zeros(i)
                    temp_time = np.zeros(i)
                    for j in range(i):# ensures remaining data outside buffer is saved
                        temp_force[j] = self.force_data[j] 
                        temp_pressure[j] = self.pressure_data[j]
                        temp_displacement[j] = self.displacement_data[j]
                        temp_setpoint_array[j] = self.setpoint_array[j]
                        temp_control_array[j] = self.control_array[j]
                        temp_time[j] = self.time_array[j]
                    funDAQ.save(force = temp_force,
                                pressure = temp_pressure,
                                displacement = temp_displacement,
                                setpoint = temp_setpoint_array,
                                control = temp_control_array,
                                time_ = temp_time)
                    self.log("Tensile Test Complete...")
                    if status_callback=='default':
                        self.test_status('tensile','default-True') # test is complete - plot on pre-test tab
                    elif status_callback=='None':
                        pass
                    return # break out of the function while keeping GUI running
                else:
                    pass
            # ===== End of For Loop - Save Data =====
            funDAQ.save(force = self.force_data,
                        pressure = self.pressure_data,
                        displacement = self.displacement_data,
                        setpoint = self.setpoint_array,
                        control = self.control_array,
                        time_ = self.time_array)
            if status_callback=='default':
                self.test_status('tensile','default-updated') # test status is 'updated' - data saved - plot on pre-test tab
            elif status_callback==None:
                pass

    def PIDtuning(self,kp,stroke_rate,max_load,file_path,status_callback='default'):
        funDAQ = DAQ(file_path=file_path,log_data_save_callback=None) # instantiate DAQ class
        stroke_rate = .03 # in/min stroke control
        piston_area = 26.79 # define the area of the piston for force calculation
        ki=0;kd=0;setpoint=0
        pid = PID(kp,ki,kd,setpoint)#PID controller with constants and setpoint
        pid.output_limits = (3,98) #sets limit on output of PID
        start_time = time.time() # get start time
        while True:
            for i in range(self.buffer_size):
                current_time = time.time() # get current time
                # ===== Read Data =====
                self.pressure_data[i] = self.funPT.readPSI(callback=False) # get current pressure
                self.force_data[i] = self.pressure_data[i]*piston_area # pressure*area=force
                self.displacement_data[i] = self.funLVDT.measure(callback=False) # measure displacement
                self.time_array[i] = current_time-start_time # measure elapsed time
                setpoint = stroke_rate*self.time_array[i]*(1/60)
                pid.setpoint = setpoint # update PID controller setpoint
                self.setpoint_array[i] = setpoint # assign setpoint to data array
                self.control_array[i] = pid(self.displacement_data[i]) # assign control value to data array
                self.control_array_load[i] = self.control_array[i]*26.79 # convert control in psi to force (lbs)
                self.funDAC.writePSI(self.control_array[i]) # write the control pressure
                # ===== End Test If Max Load Is Reached =====
                if self.force_data[i]>=max_load or self.stop_event==True: # stops test when max load is reached orstop test button is pressed
                    self.funDAC.writePSI(3)
                    # assign empty variables with length of current array - AVOIDS SAVING DATA WITH UNFILLED ZEROS
                    temp_force = np.zeros(i) 
                    temp_pressure = np.zeros(i)
                    temp_displacement = np.zeros(i)
                    temp_setpoint_array = np.zeros(i)
                    temp_control_array = np.zeros(i)
                    temp_time = np.zeros(i)
                    for j in range(i):# ensures remaining data outside buffer is saved
                        temp_force[j] = self.force_data[j] 
                        temp_pressure[j] = self.pressure_data[j]
                        temp_displacement[j] = self.displacement_data[j]
                        temp_setpoint_array[j] = self.setpoint_array[j]
                        temp_control_array[j] = self.control_array[j]
                        temp_time[j] = self.time_array[j]
                    funDAQ.save(force = temp_force,
                                pressure = temp_pressure,
                                displacement = temp_displacement,
                                setpoint = temp_setpoint_array,
                                control = temp_control_array,
                                time_ = temp_time)
                    self.log("Tuning Test Complete...")
                    measured_stroke_rate = round(np.polyfit(self.time_array,self.displacement_data,deg=1)[0]*60,5) # get measured stroke rate
                    self.log(f"Measured Stroke Rate (in/min): {measured_stroke_rate}")
                    if status_callback=='default':
                        self.test_status('tuning','default-True') # test is complete - plot on pre-test tab
                    elif status_callback=='None':
                        pass
                    return # break out of the function while keeping GUI running
                else:
                    pass
            # ===== End of For Loop - Save Data =====
            funDAQ.save(force = self.force_data,
                        pressure = self.pressure_data,
                        displacement = self.displacement_data,
                        setpoint = self.setpoint_array,
                        control = self.control_array,
                        time_ = self.time_array)
            if status_callback=='default':
                self.test_status('tuning','default-updated') # test status is 'updated' - data saved - plot on pre-test tab
            elif status_callback==None:
                pass