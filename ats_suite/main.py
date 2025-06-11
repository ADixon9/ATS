import smbus3
import time
import datetime
import os
import numpy as np
import pandas as pd
import pigpio
import matplotlib.pyplot as plt
from subprocess import check_output
from simple_pid import PID
from datetime import datetime
bus = smbus3.SMBus(1) #creates an object to communicate over i2c with smbus


''' TO DO
-add a help description at the start of every class and function
-Consider adding a function to set sample rate
-allow user to toggle on and off measuring temperatures (will increase speed)
-load rate is not accurate



'''


class ADC(): #ADS1115 Chip

    '''ADC Class serves to provide methods for configuring and reading data from the ADC
    ADC was measured to read up to ~960 SPS using function generator, 860 is advertised
    '''


    def __init__(self):
        
        self.address = 0x48

    def config(self,device):
        ''' Maximum SPS: 525 tested for errors switching between devices @ 100k samples zero errors'''
        config_register = 0b00000001 #config register
        if device=='LVDT':
            config = [0b00000000,0b11100011] # see pg 18 of ADS1115 data sheet to change configuration. This configuration is set to standard operation, continuous conversion, 860SPS, AIN0 = +, AIN1 = - (differential)
        elif device=="pressure_transducer":
            config = [0b01100000,0b11100011] # see pg 18 of ADS1115 data sheet to change configuration. This configuration is set to standard operation, continuous conversion, 860SPS, AIN2 = +, AIN3 = - (differential)
        else:
            print("ERROR: ADC input device not recognized...")
        bus.write_i2c_block_data(self.address,config_register,config) # write configuration to configuration register
        time.sleep(1/525) # wait for configuration to activate


    def readVoltage(self,device):
        self.config(device) # configure ADC to read from selected device
        rawData = bus.read_i2c_block_data(self.address,0b00000000,2) ## Reads binary 16-bit voltage value from conversion register
        myCodevalue = (rawData[0]<<8 | rawData[1]) ## (<<8 is pushing the first byte 8 bits to the left to position the first byte)(MSB is +/- sign, reads 0 since only +)
        voltage = (5*myCodevalue)/26715 # calibrated to read 5v out with a 5v input. Verified using a fluke multimeter. ideal value is 32767
        return float("%.4f" % voltage) ## formats to three decimal places. (.3f means 3 decimals, (f) float)
    
    def readRaw(self,device):
        # used for the LVDT/pressure transducer. No need for a dual calibration
        self.config(device) # configure ADC to read from selected device
        rawData = bus.read_i2c_block_data(self.address,0b00000000,2) ## Reads binary 16-bit voltage value from conversion register
        myCodevalue = (rawData[0]<<8 | rawData[1]) ## (<<8 is pushing the first byte 8 bits to the left to position the first byte)(MSB is +/- sign, reads 0 since only +)
        
        return myCodevalue

class DAC():

    ''' Need to add a calibration function at a later point.'''

    def __init__(self,log_callback,status_callback):

        self.address = 0x60 ## sets address attribute for DAC
        self.funPT = PT(log_callback=log_callback,
                        status_callback=status_callback,
                        current_pressure_callback=None,
                        current_force_callback=None) # instantiate PT class
        self.log = log_callback # define log attribute
        self.status = status_callback # define status attribute
        if os.path.exists('IP_calibration_log.csv'):
            df = pd.read_csv('IP_calibration_log.csv')
            self.slope = df['slope'].to_numpy()[-1] # convert slope to numpy array, use last value
            self.zero = df['zero'].to_numpy()[-1] # convert zero to numpy array, use last value, VALUE IS IN PSI
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
        self.zero = cal_curve[1] # zero point - VALUE IS IN PSI
        df = pd.DataFrame({'date':[timestamp],'slope':[self.slope],'zero':[self.zero]}) # create data frame with these values
        write_header = not os.path.exists('IP_calibration_log.csv') # check to see if the file exists, if so, define as false
        df.to_csv('IP_calibration_log.csv',mode='a',header=write_header,index=False) # append data frame to csv
        self.log("I/P transducer calibration complete...")

    def zero_reading(self):
        '''CURRENTLY NOT USING'''
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            slope =self.slope # get current slope
        except NameError:
            self.log("No I/P transducer calibration data found, please calibrate before zeroing...")
        self.zero = slope*self.funPT.readPSI(callback=True) # record current pressure and calculate zero - VALUE IS IN PSI
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
            voltage = (((10/95)*calibrated_psi)-(30/95)) # eq. of line given (0v, 3psi) & (10v, 98psi)
        except AttributeError: # except if no calibration exists
            voltage = (((10/95)*psi)-(30/95)) # eq. of line given (0v, 3psi) & (10v, 98psi)
        self.writeVoltage(voltage)
        if callback==False:
            pass
        elif callback==True:
            self.log(f"Pressure set to {psi} psi...") # log set pressure command

    def writeVoltage(self,voltage):

        #checks that the voltage is in the range of the device
        if voltage > 10:
            voltage =10 # define maximum voltage
        elif voltage < 0:
            voltage = 0 # define minimum voltage
        
        codeValue = int(409.5*voltage) #converts the voltage to a 12-bit number
        #configure data into a format the device can read and send it
        byte1 = codeValue>>4 ## Cuts off last 4 registers by shifting right 4 places
        byte2 = (codeValue&15)<<4 ## Cuts off first 8 bits and shifts remaining 4 bits left 4 registers
        ''' codeValue&15 cuts off first 12 bits. & opperator returns 0 if only one comparison value is 1. If both values are 1, returns 1'''
        ''' Ex. 2074 = 100000011010. 15 = 000000001111. 4095&15 --> 000000001010'''
        data = [byte1,byte2] ## 12 bit data, sending in two pairs of 8 bits. last 4 bits of register are unused
        bus.write_i2c_block_data(self.address,0x40,data)## 0x40 is register for WRITE DAC Register (SEE PG 25 2nd byte). Writing data to register

class DAC_furnace():

    def __init__(self):

        self.address = 0xf ## sets address attribute for DAC
        ''' smallest change in voltage is approximately .02V or 20mV'''
        '''0x0f address'''

    def writeVoltage(self,voltage):

        #checks that the voltage is in the range of the device
        if voltage > 5:
            raise Exception("Voltage cannot exceed 5 volts")
        elif voltage < 0:
            raise Exception("Voltage must be positive")
        
        codeValue = int(65535*voltage*(1/5)) #converts the voltage to a 12-bit number. 1/5 factor is max code value at 5v
        
        #configure data into a format the device can read and send it
        
        byte1 = codeValue>>8 ## Cuts off last 8 registers by shifting right 8 places
        byte2 = (codeValue&0b11111111)<<8 ## Cuts off first 8 bits and shifts remaining 8 bits left 8 registers
        ''' codeValue&0b11111111 cuts off first 8 bits. & opperator returns 0 if only one comparison value is 1. If both values are 1, returns 1'''
        ''' Ex. 2074 = 100000011010. 15 = 000000001111. 4095&15 --> 000000001010'''
        data = [byte1,byte2] ## 16 bit data, sending in two pairs of 8 bits.
        
        bus.write_i2c_block_data(0x0f,0x40,data)## 0x40 is the configuration command. Writing data to register
        #bus.write_block_data(0xf,0x40,data)## 0x40 is the configuration command. Writing data to register

class PT():

    ''' Need to add a calibration function at a later point.'''

    def __init__(self,log_callback,status_callback,current_pressure_callback,current_force_callback):

        self.funADC = ADC() # instantiate ADC class
        self.log = log_callback # define log attribute
        self.status = status_callback # define status attribute
        self.current_pressure = current_pressure_callback # define pressure attribute
        self.current_force = current_force_callback # define force attribute
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
        self.zero = cal_curve[1] # zero point
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
        ''''DO NOT USE DURING TESTING - FACTOR PSI INSTEAD OF READING TWICE'''
        try:
            pressure = (self.funADC.readRaw(device='pressure_transducer')*self.slope + self.zero) # measure pressure        
        except AttributeError:
            self.log('MEASUREMENT ERROR: No calibration data available, please calibrate and try again...')
        if callback==False:
            pass
        elif callback==True:
            self.current_pressure(pressure) # log current pressure
            self.log("Pressure measurement recorded...") # log measurement recorded
        self.force = (26.79*pressure)
        return float("%.2f" % self.force)

class TCamp():

    def __init__(self,config_register=0b00000110,resolution=0b00000000,TC_config_register=0b00000101,TC_type=0b01000000):
        ''' SEE READ_ME FOR CONFIGURATION SETTINGS. TC_TYPE: 0b00000000 for K-Type filter off, 0b01000000 for S-Type filter off'''
        t=.05
        self.addr = addr = [0x64,0x65,0x66,0x67]
        for i in range(len(addr)):
            bus.write_byte_data(addr[i],config_register,resolution)#writing to device configuration register, 18-bit nominal resolution
            time.sleep(t)
        # for i in range(len(addr)):
        #     bus.write_byte(addr[i],resolution)#writing 18-bit nominal resolution to configuration register
        #     time.sleep(t)
        for i in range(len(addr)):
            bus.write_byte_data(addr[i],TC_config_register,TC_type)#writing to TC configuration register, S-Type TC, filter off
            time.sleep(t)
        # for i in range(len(addr)):
        #     bus.write_byte(addr[i],TC_type)#writing S-type TC, filter off
        #     time.sleep(t)

    def measure(self,channel1=True,channel2=True,channel3=True,channel4=True):
        '''
        NOTE: SEE PNLF_READ_ME FOR CONVERSION TIMES. MUST BE ACCOUNTED FOR DURING TESTING
        '''
        temperature = raw_temp = np.zeros(4)
        if channel1==True:
            raw_data1 = bus.read_i2c_block_data(self.addr[0],0b00000000,2)# reading 3 bytes from hot temp junction
            temperature[0] = (raw_data1[0]*16)+(raw_data1[1]/16)
        if channel2==True:
            raw_data2 = bus.read_i2c_block_data(self.addr[1],0b00000000,2)# reading 3 bytes from hot temp junction
            temperature[1] = (raw_data2[0]*16)+(raw_data2[1]/16)
        if channel3==True:
            raw_data3 = bus.read_i2c_block_data(self.addr[2],0b00000000,2)# reading 3 bytes from hot temp junction
            temperature[2] = (raw_data3[0]*16)+(raw_data3[1]/16)
        if channel4==True:
            raw_data4 = bus.read_i2c_block_data(self.addr[3],0b00000000,2)# reading 3 bytes from hot temp junction
            temperature[3] = (raw_data4[0]*16)+(raw_data4[1]/16)

        return temperature
        
class LVDT():

    def __init__(self,log_callback,status_callback,current_position_callback):
        #live_plot_callback
        self.funADC = ADC() #initializes function instance of ADC class
        self.log = log_callback # create log attribute
        self.status = status_callback # create status attribute
        self.current_position = current_position_callback
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
        return float("%.8f" % position) # View later to determine required number of decimals

class MUX():

    def __init__(self):
        ''' default address is 0x70'''
        self.address = 0x70
        self.open_channels # open channels on startup

    def open_channels(self,):

        bus.write_byte(self.address,0b11111111) # open all channels

        '''This code is written for the PCA9547 chip which can only have one channel open at a time'''
        # if channel==0:
        #     bus.write_byte(self.address,0b00001000) # open channel 0
        #     print(f"channel {channel} selected")
        # elif channel==1:
        #     bus.write_byte(self.address,0b00001001) # open channel 1
        #     print(f"channel {channel} selected")
        # elif channel==2:
        #     bus.write_byte(self.address,0b00001010) # open channel 2
        #     print(f"channel {channel} selected")
        # elif channel==3:
        #     bus.write_byte(self.address,0,0b00001011) # open channel 3
        #     print(f"channel {channel} selected")
        # elif channel==4:
        #     bus.write_byte(self.address,0,0b00001100) # open channel 4
        #     print(f"channel {channel} selected")
        # elif channel==5:
        #     bus.write_byte(self.address,0b00001101) # open channel 5
        #     print(f"channel {channel} selected")
        # elif channel==6:
        #     bus.write_byte(self.address,0b00001110) # open channel 6
        #     print(f"channel {channel} selected")
        # elif channel==7:
        #     bus.write_byte(self.address,0b00001111) # open channel 7
        #     print(f"channel {channel} selected")
        # else:
        #     bus.write_byte(self.address,0b00000000)
        #     raise ValueError("A channel value out of range was selected. Please select a channel value between 0 and 7")

class furnace_control():

    def __init__(self):

        self.funDAC_furnace = DAC_furnace() #initialize instance of furnace DAC class inside furnace_control class
        self.funTCamp = TCamp()
        self.kp = 0.15; self.ki = 0.002; self.kd = 0 #PID tuning parameters for Maintaining temperature Kd was .001
        self.temperature_array = []

    def heat(self,setpoint,target):
        
        kp = .1; ki=0; kd=0
        time_elapsed = []
        initial_temp = self.funTCamp.measure()[0]
        pidh = PID(kp,ki,kd,setpoint,output_limits=(0,5)) #initialize PID class with output limits between 0v and 5v. Setpoint is ideal rate in C/min
        i=0
        j=0
        time0 = time.time()
        while True:
            self.temperature_array.append(self.funTCamp.measure()[0])# measuring channel 1 of temperature bank. S-Type ONLY!!!
            time_now = time.time()
            time_elapsed.append((time_now-time0)/60) # time elapsed in minutes
            pidh.setpoint = (setpoint*time_elapsed[i])+initial_temp
            control = pidh(self.temperature_array[i])
            self.funDAC_furnace.writeVoltage(control) #write control voltage
            if j==1000:
                print(f"control = {control}")
                print(f"temp = {self.temperature_array[i]}")
                print(f"setpoint {setpoint*time_elapsed[i]+initial_temp}")
                j=0
            if abs(self.temperature_array[i]-target)<=10:
                last_output=control # last furnace DAC control voltage
                ans = input("Would you like to maintain current setpoint temperature? [Y/N]")
                if ans.upper().strip() == 'Y':
                    self.maintain(target,starting_output=last_output)
                if ans.upper().strip() == 'N':
                    print(f"Last output value was {last_output} Volts")
                    break
                else:
                    print(f"ERROR: Value entered was neither Y or N. Last output was {last_output} Volts")
            else:
                i += 1 # increase counter
                j += 1
    
    def heat_tuning(self,setpoint,target):

        kp = .1; ki=0; kd=0
        initial_temp = self.funTCamp.measure()[0]
        pidh = PID(kp,ki,kd,setpoint,output_limits=(0,5)) #initialize PID class with output limits between 0v and 5v. Setpoint is ideal rate in C/min
        i=0; j=0
        time_elapsed = []
        time0 = time.time()
        while True:
            self.temperature_array.append(self.funTCamp.measure()[0])# measuring channel 1 of temperature bank. S-Type ONLY!!!
            time_now = time.time()
            time_elapsed.append((time_now-time0)/60) # time elapsed in minutes
            pidh.setpoint = (setpoint*time_elapsed[i])+initial_temp
            control = pidh(self.temperature_array[i])
            self.funDAC_furnace.writeVoltage(control)
            if j==1000:
                print(f"control = {control}")
                print(f"temp = {self.temperature_array[i]}")
                print(f"setpoint {setpoint*time_elapsed[i]+initial_temp}")
                j=0
            if abs(self.temperature_array[i]-target)<=10:
                ideal_temp = []
                for i in range(len(time_elapsed)):
                    ideal_temp.append(setpoint*time_elapsed[i]+initial_temp) #ideal temperature curve f(t)
                fig, ax = plt.subplots()
                plt.axis
                ax.plot(time_elapsed,self.temperature_array, color='red')
                ax.plot(time_elapsed,ideal_temp,color='blue')
                ax.set_title('Temperature vs. Time')
                ax.set(xlabel='Time (min)', ylabel='Temperature (C)')
                plt.show()
                break
            else:
                i += 1
                j += 1

    def maintain_tuning(self,target,starting_output):

        kp = .15; ki=0.002; kd=0.001

        pidm = PID(kp,ki,kd,target,output_limits=(0,5)) #initialize PID class with output limits between 0v and 5v
        pidm.starting_output = starting_output
        time_array = []
        time0 = time.time()
        i=0; j=0
        while True:
            self.temperature_array.append(self.funTCamp.measure()[0])# measuring channel 1 of temperature bank. S-Type ONLY!!!
            time_array.append(time.time()-time0)
            control = pidm(self.temperature_array[i]) #input current temperature to PID
            self.funDAC_furnace.writeVoltage(control) #write PID control value to furnace DAC
            if j==1000:
                print(f"control = {control}")
                print(f"temp = {self.temperature_array[i]}")
                j=0
            if time_array[i]>1200:
                break
            else:
                i += 1
                j +=1
        ideal_temp = []
        for i in range(len(time_array)):
            ideal_temp.append(target) #ideal temperature
        fig, ax = plt.subplots()
        plt.axis
        ax.plot(time_array,self.temperature_array, color='red')
        ax.plot(time_array,ideal_temp,color='blue')
        ax.set_title('Temperature vs. Time')
        ax.set(xlabel='Time (min)', ylabel='Temperature (C)')
        plt.show()

    def maintain(self,target,last_output=None):

        '''PID oscilates above 1000C due to the drop to zero when the PID is reset'''
        
        if last_output==None:
            self.heat(int(input("Running heating function, please enter a heat rate in C/MIN")),target=int(input("Enter a desired target temperature in C")))
        else:
            pidm = PID(self.kp,self.ki,self.kd,target,output_limits=(0,5),starting_output=last_output) #initialize PID class with output limits between 0v and 5v
            j=0
            while True:
                temperature = self.funTCamp.measure()[0]# measuring channel 1 of temperature bank. S-Type ONLY!!!
                control = pidm(temperature) #input current temperature to PID
                self.funDAC_furnace.writeVoltage(control) #write PID control value to furnace DAC
                if j==1000:
                    print(f"control = {control}")
                    print(f"temp = {temperature}")
                    j=0
                else:
                    j += 1
    
    def maintain_callable(self,target,starting_output):
        a=1

    def set_power(self,power):
        '''
        Definintions:
        power: furnace power ranging from 0%-100%
        '''
        if 0<=power<=100:
            control = (power/100)*5 # scaled power (voltage)
        else:
            print("ERROR: Out of range")
        self.funDAC_furnace.writeVoltage(control) #write control voltage

class DAQ():

    def __init__(self,file_path,log_data_save_callback=False):

        self.file_path = file_path # define file path variable
        self.log_data_save = log_data_save_callback # define log data save variable
        
    def save(self,force,pressure,position,setpoint,control,temp1,temp2,temp3,temp4,time_):
        for i in range(len(force)):
            force[i] = float("%.2f" % force[i])
            pressure[i] = float("%.2f" % pressure[i])
            position[i] = float("%.5f" % position[i])
            setpoint[i] = float("%.5f" % setpoint[i])
            control[i] = float("%.2f" % control[i])
            temp1[i] = float("%.5f" % temp1[i])
            temp2[i] = float("%.3f" % temp2[i])
            temp3[i] = float("%.3f" % temp3[i])
            temp4[i] = float("%.3f" % temp4[i])
            time_[i] = float("%.5f" % time_[i])

        df = pd.DataFrame({'force':    force,
                           'pressure': pressure,
                           'position': position,
                           'setpoint': setpoint,
                           'control':  control,
                           'temp1':    temp1,
                           'temp2':    temp2,
                           'temp3':    temp3,
                           'temp4':    temp4,
                           'time_':    time_}) # create data frame with values
        write_header = not os.path.exists(self.file_path) # do not write header if it already exists
        df.to_csv(self.file_path,mode='a',index=False,header=write_header) # append/write data to file


class test():

    def __init__(self,log_callback,test_status_callback):
        # ===== Instantiate Classes =====
        self.funDAC = DAC(log_callback=None,
                          status_callback=None) #creates instance of DAC class internal to "test" function
        self.funADC = ADC() #creates instance of ADC class internal to "test" function
        self.funPT = PT(log_callback=None,
                        status_callback=None,
                        current_pressure_callback=None,
                        current_force_callback=None) #creates instance of PT class internal to "test" function
        self.funLVDT = LVDT(log_callback=None,
                            status_callback=None,
                            current_position_callback=None) #creates instance of LVDT class internal to "test" function
        self.funTCamp = TCamp() # creates instance of TC amp class internal to "test" function
        # ----- Callbacks -----
        self.log = log_callback # define log variable
        self.test_status = test_status_callback # define test status variable
        # ===== Instantiate Test Variables =====
        self.buffer_size = 100 #buffer size in number of array elements
        self.setpoint_array = np.zeros(self.buffer_size)
        self.control_array = np.zeros(self.buffer_size)
        self.control_array_load = np.zeros(self.buffer_size)
        self.pressure_data = np.zeros(self.buffer_size)
        self.force_data = np.zeros(self.buffer_size)
        self.position_data = np.zeros(self.buffer_size)
        self.strain_data = np.zeros(self.buffer_size)
        self.temp1 = np.zeros(self.buffer_size)
        self.temp2 = np.zeros(self.buffer_size)
        self.temp3 = np.zeros(self.buffer_size)
        self.temp4 = np.zeros(self.buffer_size)
        self.time_array = np.zeros(self.buffer_size)
        self.LVDTresolution = 10/(2**15) # 10v/15-bit system (resolution in volts)

    def MODcheck(self,maxload,load_rate,file_path):
        funDAQ = DAQ(file_path=file_path,log_data_save_callback=None)


        # ===== Calculate Number of Data Points To Be Collected ======
        n = 0 # counter
        step_size_psi = .01 # set step size in psi
        piston_area = 26.79 # define the area of the piston
        max_pressure = 2*(maxload/piston_area) # maximum load divided by the piston area - multiplied by two for setpoint array buffer
        min_pressure = 3 # define minimum pressure
        min_load = min_pressure*piston_area # cacluate minimum load
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
                self.position_data[i] = self.funLVDT.measure(callback=False) # get current position
                temperature = self.funTCamp.measure() # measure all four temperatures
                self.temp1[i] = temperature[0] # assign temp 1
                self.temp2[i] = temperature[1] # assign temp 2
                self.temp3[i] = temperature[2] # assign temp 3
                self.temp4[i] = temperature[3] # assign temp 4
                self.time_array[i] = current_time-start_time # assign time elapsed
                self.funDAC.writePSI(pressure_setpoint_array[i+(self.buffer_size*n)]) # write pressure accounting for loop itterations
                # ===== End Test If Max Load Is Reached =====
                if self.force_data[i]>=maxload: # if maxload is reached, end test
                    self.funDAC.writePSI(3)
                    # assign empty variables with length of current array - AVOIDS SAVING DATA WITH UNFILLED ZEROS
                    temp_force = np.zeros(i) 
                    temp_pressure = np.zeros(i)
                    temp_position = np.zeros(i)
                    temp_setpoint_array = np.zeros(i)
                    temp_control_array = np.zeros(i)
                    temp_temp1 = np.zeros(i)
                    temp_temp2 = np.zeros(i)
                    temp_temp3 = np.zeros(i)
                    temp_temp4 = np.zeros(i)
                    temp_time = np.zeros(i)
                    for j in range(i):# ensures remaining data outside buffer is saved
                        temp_force[j] = self.force_data[j] 
                        temp_pressure[j] = self.pressure_data[j]
                        temp_position[j] = self.position_data[j]
                        temp_setpoint_array[j] = pressure_setpoint_array[j]
                        temp_control_array[j] = pressure_setpoint_array[j]
                        temp_temp1[j] = self.temp1[j]
                        temp_temp2[j] = self.temp2[j]
                        temp_temp3[j] = self.temp3[j]
                        temp_temp4[j] = self.temp4[j]
                        temp_time[j] = self.time_array[j]
                    funDAQ.save(force = temp_force,
                                pressure = temp_pressure,
                                position = temp_position,
                                setpoint = temp_setpoint_array,
                                control = temp_control_array,
                                temp1 = temp_temp1,
                                temp2 = temp_temp2,
                                temp3 = temp_temp3,
                                temp4 = temp_temp4,
                                time_ = temp_time)
                    self.log("Modulus Check Complete...")
                    self.test_status('MODcheck',True) # test is complete
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
            n += 1 # add to counter - counting loops
            funDAQ.save(force = self.force_data,
                        pressure = self.pressure_data,
                        position = self.position_data,
                        setpoint = pressure_setpoint_array[-self.buffer_size:],
                        control = pressure_setpoint_array[-self.buffer_size:],
                        temp1 = self.temp1,
                        temp2 = self.temp2,
                        temp3 = self.temp3,
                        temp4 = self.temp4,
                        time_ = self.time_array)
            self.test_status('MODcheck','updated') # test status is 'updated' - data saved

    def load_control(self,file_name=None):


        kp = 2000; ki = 0; kd = 0; n = 0 # ORIGINAL TEST CONDUCTED AT KP = 8000; KI = 1000
        load_rate = .03 # lbs/min load control
        if input(f"Test Conditions: Method: LOAD CONTROL, Rate: {load_rate} lbf/min" + "\n" + "Is this correct? Type YES to conintue, Press any other button to cancel ").upper().strip()=="YES":
            pass
        else:
            exit()
        setpoint = load_rate # setpoint in lbs/min
        inp = input("Please enter a file name for the tensile test data: ")
        funDAQ = DAQ(inp)
        force_data = self.force_data
        pressure_data = self.pressure_data
        position_data = self.position_data
        setpoint_array = self.setpoint_array
        control_array = self.control_array
        control_array_load = self.control_array_load
        temp1 = self.temp1; temp2 = self.temp2; temp3 = self.temp3; temp4 = self.temp4
        time_array = self.time_array
        self.funDAC.writePSI(3) # starts pressure at zero point
        time.sleep(5) # allows pressure to equalize
        pid = PID(kp,ki,kd,setpoint)#PID controller with constants and setpoint. MUST BE SET AFTER WAIT TIME. PID() HAS INTERNAL TIMER
        pid.output_limits = (3,95) #sets limit on output of PID
        j=0
        time0 = time.time()
        while True:
            for i in range(self.buffer_size):
                force_data[i] = self.funADC.readForce()
                print(force_data[i])
                pressure_data[i] = self.funPT.readPSI()
                position_data[i] = -self.funLVDT.measure()
                temp = self.funTCamp.measure()
                temp1[i] = temp[0]; temp2[i] = temp[1]; temp3[i] = temp[2]; temp4[i] = temp[3]
                time_array[i] = time.time()-time0
                control_array[i] = pid(pressure_data[i])
                control_array_load[i] = control_array[i]*26.79
                self.funDAC.writePSI(control_array[i])

                if force_data[i] <= 50: # Stops test when load is less than 50lb (minimum cylinder load ~80lb)
                    self.funDAC.writePSI(3)
                    temp_force = np.zeros(i); temp_pressure = np.zeros(i); temp_position = np.zeros(i) #;temp_strain = np.zeros(i)
                    temp_setpoint_array = np.zeros(i); temp_control_array_load = np.zeros(i)
                    temp_temp1 = np.zeros(i); temp_temp2 = np.zeros(i); temp_temp3 = np.zeros(i); temp_temp4 = np.zeros(i)
                    temp_time = np.zeros(i)
                    for j in range(i):
                        temp_force[j] = force_data[j] # ensures remaining data outside buffer is saved
                        temp_pressure[j] = pressure_data[j]
                        temp_position[j] = position_data[j]
                        temp_setpoint_array[j] = setpoint_array[j]
                        temp_control_array_load[j] = control_array_load[j]
                        temp_temp1[j] = temp1[j]
                        temp_temp2[j] = temp2[j]
                        temp_temp3[j] = temp3[j]
                        temp_temp4[j] = temp4[j]
                        temp_time[j] = time_array[j]
                    n = 1
                    break

                else:
                    continue
            if n==0:
                funDAQ.save(force_data,pressure_data,position_data,setpoint_array,control_array_load,temp1,temp2,temp3,temp4,time_array)
            elif n==1:
                funDAQ.save(temp_force,temp_pressure,temp_position,temp_setpoint_array,temp_control_array_load,temp_temp1,temp_temp2,temp_temp3,temp_temp4,temp_time)
                break
            else:
                print("ERROR")

    def MODcheck_strain(self,estyield,saftey_factor=1.4,ramp_rate=25,estMOD=None):

        inp = input("Please enter a file name for the modulus check data: ")
        funDAQ = DAQ(inp)

        if saftey_factor <=1.25:
            print('Saftey factor must be larger than 1.25. Try Again')
            exit()
        else:
            pass
        LVDT_inch_resolution = self.LVDTresolution*(.5/10) # voltage(resolution)*.5"/10V (.5" travel per 10V)
        if estMOD == None:
            num_points = 100 # 100 data points to be collectd
        else:
            sigma = ((1/saftey_factor)*estyield)/estMOD # strain at yield with our saftey factor
            dL = sigma*.5625 # strain times constant cross-sectional length (9/16"). dL is delta length, how much the specimen should elongate 
            num_points = dL/LVDT_inch_resolution # total allowable elongation divided by measurement resolution
            print(f"Total data points to be collected: {num_points}")

        maxload = (1/saftey_factor)*(estyield*(1/64)) # maximum load reached during MOD check
        pressure_array = np.linspace(3, ((maxload-150)/26.79),num_points) # load array from min to max load in PSI
        force_data = np.zeros(num_points); pressure_data = np.zeros(num_points); position_data = np.zeros(num_points); strain_data = np.zeros(num_points) # allocating force,pressure, and position array
        temp1 = np.zeros(num_points); temp2 = np.zeros(num_points); temp3 = np.zeros(num_points); temp4 = np.zeros(num_points) # allocating temperature arrays
        setpoint_array = np.zeros(num_points); control_array = np.zeros(num_points)
        time_array = np.zeros(num_points)
        test_time = maxload/ramp_rate # test time in seconds
        timeint = test_time/num_points # time interval between steps

        inp2 = input(f"Max load is set to {maxload} lbs. Type CONTINUE to continue, press any key to exit()")
        if inp2.upper().strip()=='CONTINUE':
            self.funDAC.writePSI(3)
            time.sleep(5)
            pass
        else:
            print("MODcheck exited")
            exit()
        time0 = time.time()
        for i in range(num_points):
            time1 = time.time()
            force_data[i] = self.funADC.readForce()
            if force_data[i]>=maxload:
                self.funDAC.writePSI(3)
                print("Max load reached. Try again ")
                exit()
            else:
                pass
            pressure_data[i] = self.funPT.readPSI()
            position_data[i] = -self.funLVDT.measure()
            strain_data[i] = ((4/10))*self.funADC.readVoltage(channel=0b01,rate=0b01)/25.4
            temperature = self.funTCamp.measure()
            temp1[i] = temperature[0]; temp2[i] = temperature[1]; temp3[i] = temperature[2]; temp4[i] = temperature[3]
            while True:
                time2 = time.time()
                time_array[i] = time2-time0
                dt = time2-time1
                if dt >= timeint:
                    break
                else:
                    pass
            self.funDAC.writePSI(pressure_array[i])
            print(force_data[i])
        self.funDAC.writePSI(3) # END MODCHECK
        funDAQ.save(force_data,pressure_data,position_data,setpoint_array,control_array,strain_data,temp2,temp3,temp4,time_array)
        df = np.zeros(num_points-1); stress = np.zeros(num_points-1); ds = np.zeros(num_points-2); E = np.zeros(num_points-2); strain = np.zeros(num_points-1) # initializing delta arrays
        for i in range(num_points-1):
            stress[i] = force_data[i+1]/(1/64)
            strain[i] = (strain_data[i+1]-strain_data[0])/(.5-(strain_data[0])) # instantaneous strain
            #print(strain[i])
            #strain[i] = (strain_data[i+1]-strain_data[0])/.5
        ef = np.polyfit(strain,stress,deg=1)
        # elasticity = ef[0]*(10**-6)
        print(f"Modulus of Elasticity (E) = {ef[0]} psi" + "\n" + "MOD CHECK COMPLETE")
        sk = np.polyfit(position_data,force_data,deg=1)
        stiffnessk = sk[0]
        print(f"Stiffness K = {stiffnessk} lbs/in" + "\n" + "MOD CHECK COMPLETE")

        plt.rcParams.update({'font.size': 18})
    
        fig, ax = plt.subplots()
        fig2, ax2 = plt.subplots()
        ax.set_xlim(0,max(position_data)+.002)
        ax.set_ylim(0,max(force_data)+50)
        ax2.set_ylim(0,max(stress)+1000)
        ax2.set_xlim(0,max(strain)+.0002)
        plt.axis()
        ax.plot(abs(position_data),force_data, color='red')
        ax2.plot(strain,stress,color='red')
        ax.set_title(f'Force vs. Displacement: Stifness = {stiffnessk}')
        ax.set(xlabel='Displacement (in)', ylabel='Force (Lbs)')
        ax2.set_title(f"Stress vs Strain: E = {ef[0]} psi")
        ax2.set(xlabel='Strain (in/in)', ylabel="Stress (psi)")
        #print(stress)
        #print(strain_data)
        plt.show()

    def linear_elastic(self,max_load,ramp_rate=25):

        inp = input("Please enter a file name for the linear elastic data: ")
        funDAQ = DAQ(inp)

        LVDT_inch_resolution = self.LVDTresolution*(.5/10) # voltage(resolution)*.5"/10V (.5" travel per 10V)
        num_points = 100 # 100 data points to be collectd

        pressure_array = np.linspace(3, (max_load/26.79),num_points) # load array from min to max load in PSI
        force_data = np.zeros(num_points); pressure_data = np.zeros(num_points); position_data = np.zeros(num_points); strain_data = np.zeros(num_points) # allocating force,pressure, and position array
        temp1 = np.zeros(num_points); temp2 = np.zeros(num_points); temp3 = np.zeros(num_points); temp4 = np.zeros(num_points) # allocating temperature arrays
        setpoint_array = np.zeros(num_points); control_array = np.zeros(num_points)
        time_array = np.zeros(num_points)
        test_time = max_load/ramp_rate # test time in seconds
        timeint = test_time/num_points # time interval between steps

        inp2 = input(f"Max load is set to {max_load} lbs. Type CONTINUE to continue, press any key to exit()")
        if inp2.upper().strip()=='CONTINUE':
            self.funDAC.writePSI(3)
            time.sleep(5)
            pass
        else:
            print("MODcheck exited")
            exit()
        time0 = time.time()
        for i in range(num_points):
            time1 = time.time()
            force_data[i] = self.funADC.readForce()
            if force_data[i]>=(max_load+50):
                self.funDAC.writePSI(3)
                print("Max load reached. Try again ")
                exit()
            else:
                pass
            pressure_data[i] = self.funPT.readPSI()
            position_data[i] = -self.funLVDT.measure()
            #strain_data[i] = (.225/25.4)*self.funADC.readVoltage(channel=0b01,rate=0b10) #.225mm/volt
            temperature = self.funTCamp.measure()
            temp1[i] = temperature[0]; temp2[i] = temperature[1]; temp3[i] = temperature[2]; temp4[i] = temperature[3]
            self.funDAC.writePSI(pressure_array[i])
            while True:
                time2 = time.time()
                time_array[i] = time2-time0
                dt = time2-time1
                if dt >= timeint:
                    break
                else:
                    pass
            print(force_data[i])
        self.funDAC.writePSI(3) # END MODCHECK
        funDAQ.save(force_data,pressure_data,position_data,setpoint_array,control_array,temp1,temp2,temp3,temp4,time_array)
        df = np.zeros(num_points-1); stress = np.zeros(num_points-1); ds = np.zeros(num_points-2); E = np.zeros(num_points-2); strain = np.zeros(num_points-1) # initializing delta arrays
        for i in range(num_points-1):
            stress[i] = force_data[i+1]/(1/64)
            strain[i] = (position_data[i+1]-position_data[0])/.5625 # instantaneous strain
            #strain[i] = (strain_data[i+1]-strain_data[0])/.5
        #ef = np.polyfit(strain,stress,deg=1)
        # elasticity = ef[0]*(10**-6)
        # print(f"Modulus of Elasticity (E) = {elasticity} Msi" + "\n" + "MOD CHECK COMPLETE")
        sk = np.polyfit(position_data,force_data,deg=1)
        stiffnessk = sk[0]
        print(f"Stiffness K = {stiffnessk} lbs/in" + "\n" + "MOD CHECK COMPLETE")

        plt.rcParams.update({'font.size': 18})
    
        fig, ax = plt.subplots()
        plt.xlim(0,max(position_data)+.002)
        plt.ylim(0,max(force_data)+50)
        plt.axis
        ax.plot(abs(position_data),force_data, color='red')
        ax.set_title(f'Force vs. Displacement: Stifness = {stiffnessk}')
        ax.set(xlabel='Displacement (in)', ylabel='Force (Lbs)')
        plt.show()

    def tensile(self,file_name=None):

        kp = 3000; ki = 0; kd = 0; n = 0 # ORIGINAL TEST CONDUCTED AT KP = 8000; KI = 1000
        '''
        First tensile test conducted at Kp = 8000; Ki = 1000
        Tensile test w/strain @ 14 bit Kp=4000; Ki=500
        760C Kp=3000; Ki=350, small oscilations still present, could be due to jump in strain (creaking)
        
        '''

        crosshead_rate = .03 # in/min stroke control
        if input(f"Test Conditions: Method: STROKE CONTROL, Rate: {crosshead_rate} in/min" + "\n" + "Is this correct? Type YES to conintue, Press any other button to cancel ").upper().strip()=="YES":
            pass
        else:
            exit()
        setpoint = 0
        inp = input("Please enter a file name for the tensile test data: ")
        funDAQ = DAQ(inp)
        
        force_data = self.force_data
        pressure_data = self.pressure_data
        position_data = self.position_data
        setpoint_array = self.setpoint_array
        control_array = self.control_array
        control_array_load = self.control_array_load
        temp1 = self.temp1; temp2 = self.temp2; temp3 = self.temp3; temp4 = self.temp4
        time_array = self.time_array
        offset_array = []; offset_sum = 0
        self.funDAC.writePSI(3) # starts pressure at zero point
        time.sleep(5) # allows pressure to equalize
        pid = PID(kp,ki,kd,setpoint)#PID controller with constants and setpoint. MUST BE SET AFTER WAIT TIME. PID() HAS INTERNAL TIMER
        pid.output_limits = (3,95) #sets limit on output of PID
        k=0; j=0; p=0; q=0

        time0 = time.time()
        while True:
            for i in range(self.buffer_size):
                force_data[i] = self.funADC.readForce()
                print(force_data[i])
                pressure_data[i] = self.funPT.readPSI()
                position_data[i] = -self.funLVDT.measure()
                temp = self.funTCamp.measure()
                temp1[i] = temp[0]; temp2[i] = temp[1]; temp3[i] = temp[2]; temp4[i] = temp[3]
                time_array[i] = time.time()-time0
                ideal_position = crosshead_rate*time_array[i]*(1/60)
                pid.setpoint = ideal_position
                setpoint_array[i] = ideal_position
                control_array[i] = pid(position_data[i])
                control_array_load[i] = control_array[i]*26.79
                self.funDAC.writePSI(control_array[i])

                if force_data[i] <= 50: # Stops test when load is less than 50lb (minimum cylinder load ~80lb)
                    self.funDAC.writePSI(3)
                    temp_force = np.zeros(i); temp_pressure = np.zeros(i); temp_position = np.zeros(i) #;temp_strain = np.zeros(i)
                    temp_setpoint_array = np.zeros(i); temp_control_array_load = np.zeros(i)
                    temp_temp1 = np.zeros(i); temp_temp2 = np.zeros(i); temp_temp3 = np.zeros(i); temp_temp4 = np.zeros(i)
                    temp_time = np.zeros(i)
                    for j in range(i):
                        temp_force[j] = force_data[j] # ensures remaining data outside buffer is saved
                        temp_pressure[j] = pressure_data[j]
                        temp_position[j] = position_data[j]
                        temp_setpoint_array[j] = setpoint_array[j]
                        temp_control_array_load[j] = control_array_load[j]
                        temp_temp1[j] = temp1[j]
                        temp_temp2[j] = temp2[j]
                        temp_temp3[j] = temp3[j]
                        temp_temp4[j] = temp4[j]
                        temp_time[j] = time_array[j]
                    n = 1
                    break

                else:
                    continue
            if n==0:
                funDAQ.save(force_data,pressure_data,position_data,setpoint_array,control_array_load,temp1,temp2,temp3,temp4,time_array)
            elif n==1:
                funDAQ.save(temp_force,temp_pressure,temp_position,temp_setpoint_array,temp_control_array_load,temp_temp1,temp_temp2,temp_temp3,temp_temp4,temp_time)
                break
            else:
                print("ERROR")

    def tensile_strain(self,file_name=None):

        kp = 3000; ki = 0; kd = 0; n = 0 # ORIGINAL TEST CONDUCTED AT KP = 8000; KI = 1000
        '''
        First tensile test conducted at Kp = 8000; Ki = 1000
        Tensile test w/strain @ 14 bit Kp=4000; Ki=500
        760C Kp=3000; Ki=350, small oscilations still present, could be due to jump in strain (creaking)
        
        '''

        crosshead_rate = .03 # in/min stroke control
        if input(f"Test Conditions: Method: STROKE CONTROL, Rate: {crosshead_rate} in/min" + "\n" + "Is this correct? Type YES to conintue, Press any other button to cancel ").upper().strip()=="YES":
            pass
        else:
            exit()
        setpoint = 0
        inp = input("Please enter a file name for the tensile test data: ")
        funDAQ = DAQ(inp)
        
        force_data = self.force_data
        pressure_data = self.pressure_data
        position_data = self.position_data
        strain_data = self.strain_data
        setpoint_array = self.setpoint_array
        control_array = self.control_array
        control_array_load = self.control_array_load
        temp1 = self.temp1; temp2 = self.temp2; temp3 = self.temp3; temp4 = self.temp4
        time_array = self.time_array
        offset_array = []; offset_sum = 0
        self.funDAC.writePSI(3) # starts pressure at zero point
        time.sleep(5) # allows pressure to equalize
        pid = PID(kp,ki,kd,setpoint)#PID controller with constants and setpoint. MUST BE SET AFTER WAIT TIME. PID() HAS INTERNAL TIMER
        pid.output_limits = (3,95) #sets limit on output of PID
        k=0; j=0; p=0; q=0

        time0 = time.time()
        while True:
            for i in range(self.buffer_size):
                force_data[i] = self.funADC.readForce()
                print(force_data[i])
                pressure_data[i] = self.funPT.readPSI()
                position_data[i] = -self.funLVDT.measure()
                strain_data[i] = self.funADC.readVoltage(channel=0b01,rate=0b01)
                temp = self.funTCamp.measure()
                temp1[i] = temp[0]; temp2[i] = temp[1]; temp3[i] = temp[2]; temp4[i] = temp[3]
                time_array[i] = time.time()-time0
                ideal_position = crosshead_rate*time_array[i]*(1/60)
                pid.setpoint = ideal_position
                setpoint_array[i] = ideal_position
                control_array[i] = pid(position_data[i])
                control_array_load[i] = control_array[i]*26.79
                self.funDAC.writePSI(control_array[i])

                if force_data[i] <= 50: # Stops test when load is less than 50lb (minimum cylinder load ~80lb)
                    self.funDAC.writePSI(3)
                    temp_force = np.zeros(i); temp_pressure = np.zeros(i); temp_position = np.zeros(i); temp_strain = np.zeros(i)
                    temp_setpoint_array = np.zeros(i); temp_control_array_load = np.zeros(i)
                    temp_temp1 = np.zeros(i); temp_temp2 = np.zeros(i); temp_temp3 = np.zeros(i); temp_temp4 = np.zeros(i)
                    temp_time = np.zeros(i)
                    for j in range(i):
                        temp_force[j] = force_data[j] # ensures remaining data outside buffer is saved
                        temp_pressure[j] = pressure_data[j]
                        temp_position[j] = position_data[j]
                        temp_strain[j] = strain_data[j]
                        temp_setpoint_array[j] = setpoint_array[j]
                        temp_control_array_load[j] = control_array_load[j]
                        temp_temp1[j] = temp1[j]
                        temp_temp2[j] = temp2[j]
                        temp_temp3[j] = temp3[j]
                        temp_temp4[j] = temp4[j]
                        temp_time[j] = time_array[j]
                    n = 1
                    break

                else:
                    continue
            if n==0:
                funDAQ.save(force_data,pressure_data,position_data,setpoint_array,control_array_load,strain_data,temp2,temp3,temp4,time_array)
            elif n==1:
                funDAQ.save(temp_force,temp_pressure,temp_position,temp_setpoint_array,temp_control_array_load,temp_strain,temp_temp2,temp_temp3,temp_temp4,temp_time)
                break
            else:
                print("ERROR")

    def PIDtuning(self,file_name=None):

        kp =4500; ki = 0; kd = 0; n = 0
        maxload = 1300; #lbs
        output_maxload = 1400
        
        print("Please Zero LVDT before tuning PID")

        crosshead_rate = .03 # in/min stroke control
        if input(f"Test Conditions: Method: STROKE CONTROL, Rate: {crosshead_rate} in/min" + "\n" + "Is this correct? Press enter to conintue").upper().strip()=="":
            pass
        else:
            exit()
        setpoint = 0
        #inp = input("Please enter a file name for the tensile test data: ")
        #funDAQ = DAQ(inp)
        force_data = self.force_data
        pressure_data = self.pressure_data
        position_data = self.position_data
        setpoint_array = self.setpoint_array
        control_array = self.control_array
        temp1 = self.temp1; temp2 = self.temp2; temp3 = self.temp3; temp4 = self.temp4
        time_array = self.time_array
        self.funDAC.writePSI(3) # starts pressure at zero point
        time.sleep(5) # allows pressure to equalize
        pid = PID(kp,ki,kd,setpoint)#PID controller with constants and setpoint. MUST BE SET AFTER WAIT TIME. PID() HAS INTERNAL TIMER
        pid.output_limits = (3,(output_maxload)/26.79) #sets limit on output of PID
        #pid.output_limits = (3,20)
        j=0

        time0 = time.time()
        while True:
            for i in range(self.buffer_size):
                force_data[i] = self.funADC.readForce()
                print(force_data[i])
                pressure_data[i] = self.funPT.readPSI()
                position_data[i] = -self.funLVDT.measure()
                temp = self.funTCamp.measure(); temp1[i] = temp[0]; temp2[i] = temp[1]; temp3[i] = temp[2]; temp4[i] = temp[3]
                time_array[i] = time.time()-time0
                ideal_position = crosshead_rate*time_array[i]*(1/60)
                pid.setpoint = ideal_position
                setpoint_array[i] = ideal_position
                control = pid(position_data[i])
                control_array[i] = control*26.79
                self.funDAC.writePSI(control)

                if force_data[i] >= maxload:
                    self.funDAC.writePSI(3)
                    print("Maximum load reached")
                    ideal_rate = np.zeros(len(position_data))
                    for j in range(len(ideal_rate)):
                        ideal_rate[j] = (.030/60)*time_array[j]
                        measured_rate = np.polyfit(time_array,position_data,1)
                    print("Measured Stroke Rate = " + str(measured_rate[0]*60))
                    plt.rcParams.update({'font.size': 18})
                    fig, ax = plt.subplots()
                    fig2, ax2 = plt.subplots()
                    ax.set_xlim(0,max(time_array)+2)
                    ax.set_ylim(0,max(ideal_rate)+.002)
                    ax2.set_xlim(0,max(time_array)+2)
                    ax2.set_ylim(0,max(force_data)+50)
                    plt.axis
                    ax.plot(time_array[0:i],position_data[0:i], color='red',label='Measured')
                    ax.plot(time_array[0:i],ideal_rate[0:i],color='blue',label='Setpoint')
                    ax2.plot(time_array[0:i],force_data[0:i],color='red',label='Measured')
                    ax2.plot(time_array[0:i],control_array[0:i],color='blue',label='Control')
                    ax.set_title('Displacement vs time')
                    ax2.set_title("Force vs Time")
                    ax2.set(xlabel="Time (s)", ylabel="Force (lb)")
                    ax.set(xlabel='Time (s)', ylabel='Displacement (in)')
                    ax.legend(loc='lower right')
                    ax2.legend(loc='lower right')
                    plt.show()
                    exit()

                elif force_data[i] <= 50: # Stops test when load is less than 50lb (minimum cylinder load ~80lb)
                    #if force_data[i]>=500:
                    #if i==130:
                    self.funDAC.writePSI(3)
                    temp_force = np.zeros(i); temp_pressure = np.zeros(i); temp_position = np.zeros(i) #;temp_strain = np.zeros(i)
                    temp_temp1 = np.zeros(i); temp_temp2 = np.zeros(i); temp_temp3 = np.zeros(i); temp_temp4 = np.zeros(i)
                    temp_time = np.zeros(i)
                    for j in range(i):
                        temp_force[j] = force_data[j] # ensures remaining data outside buffer is saved
                        temp_pressure[j] = pressure_data[j]
                        temp_position[j] = position_data[j]
                        #temp_strain[j] = strain_data[j]
                        temp_temp1[j] = temp1[j]
                        temp_temp2[j] = temp2[j]
                        temp_temp3[j] = temp3[j]
                        temp_temp4[j] = temp4[j]
                        temp_time[j] = time_array[j]
                    n = 1
                    break

                else:
                    continue
            if n==0:
                #funDAQ.save(force_data,pressure_data,position_data,temp1,temp2,temp3,temp4,time_array)
                abc = 1
            elif n==1:
                #funDAQ.save(temp_force,temp_pressure,temp_position,temp_temp1,temp_temp2,temp_temp3,temp_temp4,temp_time)
                efg = 1
                break
            else:
                print("ERROR")

