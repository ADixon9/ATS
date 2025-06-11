from main import *
import matplotlib.pyplot as plt
import numpy as np
funMUX = MUX()
funADC = ADC()
#funDAC = DAC()
#funDACF = DAC_furnace()
#funP = Psensor()
funMUX.open_channels()
#funADC.config()
#funDACF.writeVoltage(4.827)
#print(bus.read_i2c_block_data(0x28,0,4))
#funMUX.open_channels()
#print(funADC.readVoltage())

#print(funADC.readVoltage(device="pressure_transducer"))
# t=(1/525)
# pf = 0
# lf = 0
# for i in range(10000):
#     #funADC.config(device="pressure_transducer")
#     #time.sleep(t)
#     pv = funADC.readVoltage(device="pressure_transducer")
#     #print(pv)
#     if 0<=pv<=1:
#         pass
#     else:
#         pf+=1
#     #funADC.config(device="LVDT")
#     #time.sleep(t)
#     lv = funADC.readVoltage(device="LVDT")
#     #print(lv)
#     if 2.5<=lv<=3:
#         pass
#     else:
#         lf+=1
# print(f"Pressure transducer failures: {pf}")
# print(f"LVDT failures: {lf}")
#funDAC.writePSI(psi=3)
# time.sleep(5)
# a = np.zeros(10000)
# for i in range(len(a)):
#     a[i] = funP.readPSI()
# print(np.average(a))
# print("--")

#print(funP.readPSI())

# funDAC.writePSI(psi=98)
# time.sleep(5)
# funDAC.writePSI(3)packet = build_ncd_packet(payload)

# with serial.Serial('/dev/ttyUSB0',115200,timeout=1) as ser:
#     #print(packet)

#     #ser.write(packet)
#     pack = [0xAA,0x05,0xBE,0x0f,0x40,0x80,0x00,0x3C]
#     #pack = [0xAA,0x03,0xBE,0xf,0x40,0xFF]
    
#     #pack = [0xAA,0x02,0xFE,0x21,0xCB]
#     #pack = [0xAA,0x02,0xFE,0x00,0x1A]
    
#     #pack = [0xAA,0x06,0xBE,0x0f,0x30,0x80,0x00,0x2D]
#     #s = sum(pack)
#     #print(s)
#     #pack.append(sum)
#     #print(pack)
#     ser.write(pack)
#     response = ser.read(4)
#     print("response:",response)



# funDACF.writeVoltage(0)
# time.sleep(.1)
# num_samples = 500
# voltage = np.zeros(num_samples)
# time_ = np.zeros(num_samples)
# v = np.linspace(0,5,num_samples)
# time0 = time.time()

# for i in range(num_samples):
#     #funDACF.writeVoltage(v[i])
#     voltage[i] = funADC.readVoltage()
#     time_[i] = time.time() - time0
# #time1 = time.time()
# #time_ = np.linspace(0,time1-time0,num_samples)
# sps = num_samples/(time_[-1]-time_[0])
# print(sps)
# plt.plot(time_,voltage)
# plt.show()


