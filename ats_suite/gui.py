import tkinter as tk
from tkinter import ttk, filedialog, PhotoImage
try: # run as package
    from .main import *
    from .solver import *
    from .plastic_analysis import *
except ImportError: # run at top-level
    from main import *
    from solver import *
    from plastic_analysis import *
import matplotlib
import random
import pandas as pd
import os
import glob
import threading
import webbrowser
from datetime import datetime

'''
To-Do List

priority: [1] - highest, [4] - lowest

-[4] add variable units in settings tab (imperial,metric), account for this in calibrations
-[4] Add error popups for incorrect inputs
    -tk.DoubleVar will throw a value error if a string is used
-[1] add input boxes for strain derivation into analysis tab. allow user to read and write configuration files that maintain these inputs
-[2] allow changing of buffer size in testing
-[4] include plot settings in settings tab (color, line width, line type, legend, etc)
-[4] add a setting to have live force, pressure and displacement values (change method when testing starts)
-[3] add a startup function that checks to make sure everything is connected to the pi (read all address and output "ADC Connected... DAC Connected... etc)
-[2] add a functions tab to allow user to do things such as read an individual force, pressure, position, write/read voltages, open MUX channels, read temperatures
-[3] add stop calibration button. make it restart if tab is left
-[4] add a watermark to calibration files so that you can't load calibration data from other sensors
-[3] make calibration tab plot data after calibration and when loading data file
-[3] allow calibration points to be random and not need to be in order
-[3] write an autocalibration sequence for the I/P where it will set values, wait some time, and measure the value with the pressure transducer
-[3] add read force button to pt function
-[4] autofill file name with loaded calibration data, make it read only
-[1] loading calibration files pulls current zero (LVDT Case) which is not accurate. update code to recalculate "zero" for the loaded calibration file
-[2] require a file name to be entered before testing
-[1] allow plotting of various different types under analysis tab (force vs displacement, force vs time, etc. (drop down box))
-[4] make widget sizes attributes for each tab
-[4] change enable plot labels and axes labels buttons to not rerun entire selection (takes too long)
-[3] eliminate tuning tab and add tuning method to pre-test tab
-[3] create functions to control furnace temperature, readouts,etc
-[1] update force,pressure, and position values at the top of pre-test and test
-***[1]*** Map stop button to actually stop tests
-***[1]*** Ensure calibrations are loaded immediately after completion. I believe they only load on startup (bind to tab switch)
-***[1]*** Output elastic modulus after modcheck
-***[1]*** Run plotting after running analysis
-***[1]*** Allow shifting plot in all directions (left,right,up,down) through entries
-***[1]*** standard deviation, r2 and sps is not being set in analysis tab
-***[1]*** snipping 0 on the right side makes the plot dissapear
-***[1]*** make min number of points and r2 threshold for linear regression an option in the setting menu
-***[1]*** append existing data file to add stress/strain instead of new file name
-***[1]*** format analysis output to be 4-5 floating decimals, make sure that running the test again will update values
-***[1]*** if either plot selection is stress or strain, include a button to generate data and plot a elastic modulus line, yield point, offset yield stress and UTS for given condition
-***[1]*** changing tabs will stop a test
-***[1]*** add method to reshape stress strain data to slide x and y to zero and output new data
-***[1]*** change __init__ to be a refresh function that is called under __init__. refresh system in help menu should re-run this refresh function
-[4] create montecarlo search method that changes left and right snip until the highest r^2 value is reached for FC compliance (while maintaining a minimum number of points)
-[2] shrink whitespace area of calibration tab plots similar to analysis tab plot
-[2] ON TEST STOP:
    -clear plots on test start (will keep plot from partial test until test is complete)
    -delete partial calibration file (wont start test because file already exists)
    -set directory back to base directory (wont find cal data)
    -make sure that test will start again properly
-[3] autofill axes labels depending on what the combobox selection is
-[1] get rid of browse button in pre-test tab
-[3] add plot feature to adjust y and x intercept
-[2] need to condense plotting area, not enough room when all are active
-[4] rewrite code such that it is more efficient. currently rehashing and reinstantiating classes multiple times when its unnecessary
-[4] make FC_test_aggregate include all values from tests, not just force and displacement (might be useful for plotting at a later date)
-[2] enable plot grid on all plots
-*************
-*****[1]***** Find a way to better improve frame compliance characterization - BIGGEST EFFECT ON ERROR
-*************
-[3] delete modcheck data after stopping test? (maybe)
-[2] frame compliance is plotting a flat line instead of plotting test 5
-[2] stress strain axis limits when pressing home on analysis plot is off
-[1] add a voltage measurement to functions tab - this will be used to determine where the LVDT position lies in its range
-[4] allow user to set default values for entries (i.e. kp, stroke rate, etc)
-*****[1]***** Add functionality to set the users maximum and minimum pressure, configure ADC channels and adjust force conversion factors in a settings tab


'''
# Use TkAgg backend
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AeroForce Test System")

        self.base_dir = os.path.dirname(__file__) # directory of current script
        self.parent_dir = os.path.abspath(os.path.join(self.base_dir,'..'))
        # ===== General =====
        self.force_var = tk.StringVar(value="0")
        self.force_label_tuning_tab_tk = tk.DoubleVar(value=0) # define current force reading for tuning tab
        self.pressure_var = tk.StringVar(value="0")
        self.displacement_var = tk.StringVar(value="0")
        self.stroke_rate_tk = tk.DoubleVar(value='0') # define stroke rate as a floating value
        self.kp_tk = tk.DoubleVar(value='0') # define Kp as a floating value
        self.tuning_max_load_tk = tk.DoubleVar(value='0') # define max_load as a floating value
        self.test_method_pretest = tk.StringVar(value="") # define string variable such that test_method can be updated
        self.test_method_test = tk.StringVar(value="") # define string variable such that test_method can be updated
        self.tuning_method_tuning_tab_tk = tk.StringVar(value='') # define string variable such that tuning_method can be updated
        self.plot_test_type_analysis_tk = tk.StringVar(value='') # define string variable for plotting - define test type to be plotted
        self.analysis_test_type_analysis_tk = tk.StringVar(value='') # define string variable for test type - analysis
        self.x_axis_selection_analysis_tab_tk = tk.StringVar(value='') # define string variable for x axis selection on analysis tab plot
        self.y_axis_selection_analysis_tab_tk = tk.StringVar(value='') # define string variable for y axis selection on analysis tab plot
        self.number_of_analysis_plots_tk = tk.IntVar(value=1) # define integer variable to select number of plots
        self.calibration_method = tk.StringVar(value="") # define string variable such that calibration_method can be updates
        self.IP_measure_method_use_external_gauge = tk.IntVar(value=0) # define integer variable to determine measurement method for I/P calibration
        self.enable_plot_labels_analysis_tab_tk = tk.IntVar(value=0) # define integer variable to enable/disable plot labels
        self.enable_axes_labels_analysis_tab_tk = tk.IntVar(value=0) # define integer variable to enable/disable axes labels
        self.enable_filtering_analysis_tab_tk = tk.IntVar(value=0) # define integer variable to enable/disable data filtering
        self.enable_snip_analysis_tab_tk = tk.IntVar(value=0) # define integer variable to enable/disable data snipping
        self.enable_x_shift_analysis_tab_tk = tk.IntVar(value=0) # define integer variable to enable/disable x shifting
        self.enable_y_shift_analysis_tab_tk = tk.IntVar(value=0) # define integer vairable to enable/disable y shifting
        self.num_calibration_pts = tk.IntVar(value=10) # define integer variable for number of calibration points
        # ===== LVDT =====
        self.LVDT_cal_input_displacement_tk = tk.DoubleVar(value=0) # define LVDT Displacement variable
        self.LVDT_current_position_tk = tk.DoubleVar(value=0) # define current LVDT displacement variable
        self.LVDT_current_voltage_tk = tk.DoubleVar(value=0) # define current LVDT voltage variable
        self.LVDT_cal_factor_tk = tk.DoubleVar(value=0) # define LVDT cal factor variable
        self.LVDT_cal_zero_tk = tk.DoubleVar(value=0) # define LVDT zero variable
        self.LVDT_cal_std_dev_tk = tk.DoubleVar(value=0) # define LVDT standard deviation variable
        self.LVDT_cal_linearity_tk = tk.DoubleVar(value=0) # define LVDT linearity variable
        self.LVDT_cal_R2_tk = tk.DoubleVar(value=0) # define LVDT R^2 calibration variable
        # ===== Pressure Transducer =====
            # ----- Calibration Tab -----
        self.PT_cal_input_pressure_tk = tk.DoubleVar(value=3) # define input (set) pressure variable
        self.PT_cal_measured_pressure_gauge_tk = tk.DoubleVar(value=0) # define measured pressure (external gauge) variable
        self.PT_cal_factor_tk = tk.DoubleVar(value=0) # define PT cal factor variable
        self.PT_cal_zero_tk = tk.DoubleVar(value=0) # define PT zero variable
        self.PT_cal_std_dev_tk = tk.DoubleVar(value=0) # define PT standard deviation variable
        self.PT_cal_linearity_tk = tk.DoubleVar(value=0) # define PT linearity variable
        self.PT_cal_R2_tk = tk.DoubleVar(value=0) # define PT R^2 calibration variable
            # ----- Function Tab -----
        self.PT_current_pressure_tk = tk.DoubleVar(value=0) # define current pressure variable
        self.PT_current_force_tk = tk.DoubleVar(value=0) # define current force variable
        # ===== I/P Transducer =====
        self.IP_cal_input_pressure_tk = tk.DoubleVar(value=3) # define IP Displacement variable
        self.IP_cal_output_pressure_tk = tk.DoubleVar(value=0) # define measured pressure variable
        self.IP_cal_factor_tk = tk.DoubleVar(value=0) # define IP cal factor variable
        self.IP_cal_zero_tk = tk.DoubleVar(value=0) # define IP zero variable
        self.IP_cal_std_dev_tk = tk.DoubleVar(value=0) # define IP standard deviation variable
        self.IP_cal_linearity_tk = tk.DoubleVar(value=0) # define IP linearity variable
        self.IP_cal_R2_tk = tk.DoubleVar(value=0) # define IP R^2 calibration variable
        # ===== Frame Compliance =====
            # ----- Calibration Tab -----
        self.FC_max_load_tk = tk.DoubleVar(value=0) # define max load variable
        self.FC_known_modulus_tk = tk.DoubleVar(value=0) # define known modulus variable
        self.left_snip_FC_tk = tk.IntVar(value=0) # define left snip variable
        self.right_snip_FC_tk = tk.IntVar(value=0) # define right snip variable
        self.FC_slope_tk = tk.DoubleVar(value=0) # define slope variable
        self.FC_zero_tk = tk.DoubleVar(value=0) # define zero variable
        self.FC_r2_tk = tk.DoubleVar(value=0) # define r2 variable
        # ===== DAC =====
        self.DAC_set_pressure_tk = tk.DoubleVar(value=3)# define set pressure variable
        # ===== Analysis Values =====
        # ----- Inputs -----
        self.gauge_width_tk = tk.DoubleVar(value=.1250) # define gauge width variable
        self.gauge_thickness_tk = tk.DoubleVar(value=.1250) # define gauge thickness variable
        self.tab_width_tk = tk.DoubleVar(value=.612) # define tab width variable
        self.hole_diameter_tk = tk.DoubleVar(value=.1875) # define hole diameter variable
        self.gauge_length_tk = tk.DoubleVar(value=.5625) # define gauge length variable
        self.CH_hole2mark_initial_tk = tk.DoubleVar(value=0) # define crosshead hole to mark initial length variable
        self.AC_hole2mark_initial_tk = tk.DoubleVar(value=0) # define actuator hole to mark initial length variable
        self.CH_hole2mark_final_tk = tk.DoubleVar(value=0) # define crosshead hole to mark final length variable
        self.AC_hole2mark_final_tk = tk.DoubleVar(value=0) # define actuator hole to mark initial length variable
        # ----- Outputs -----
        self.elastic_modulus_tk = tk.DoubleVar(value=0) # define elastic modulus variable
        self.yield_strength_tk = tk.DoubleVar(value=0) # define yield strength variable
        self.offset_yield_strength_tk = tk.DoubleVar(value=0) # define offset yield strength variable
        self.UTS_tk = tk.DoubleVar(value=0) # define UTS variable
        self.UTS_strain_tk = tk.DoubleVar(value=0) # define elongation at UTS variable
        # ----- Statistics -----
        self.linear_fit_R2_tk = tk.DoubleVar(value=0) # define r^2 variable for linear elastic fit
        self.linear_fit_std_dev_tk = tk.DoubleVar(value=0) # define standard deviation variable for linear elastic fit
        self.sample_rate_tk = tk.DoubleVar(value=0) # define sample rate variable
        self.linear_regression_elastic_start_tk = tk.DoubleVar(value=0) # define start point variable for linear regression
        self.linear_regression_elastic_end_tk = tk.DoubleVar(value=0) # define end point variable for linear regression
        # ===== Files =====
        self.file_name_pretest_tab_tk = tk.StringVar(value="") # define file name tk string variable for pretest tab
        self.file_name_test_tab_tk = tk.StringVar(value="") # define file name tk string variable for test tab
        self.file_name_calibration_tab = tk.StringVar(value="") # define file name tk string variable for calibration tab
        self.file_name_analysis_tab_tk = tk.StringVar(value='') # define file name tk string variable for analysis tab
        self.file_name_tuning_tab_tk = tk.StringVar(value='') # define file name tk string variable for tuning tab
        self.folder_path = tk.StringVar(value=os.getcwd())
        self.running = False
        # ===== Setup Tabs =====
        self.setup_tabs()
        # ===== Instantiate classes =====
        self.funtest = test(log_callback=self.log_command,
                            test_status_callback=self.test_status)
        self.funLVDT = LVDT(log_callback=self.log_command,
                            status_callback=self.calibration_status,
                            current_position_callback=self.LVDT_get_current_position,
                            current_voltage_callback=self.LVDT_get_current_voltage)
        self.funPT = PT(log_callback=self.log_command,
                        status_callback=self.calibration_status,
                        current_pressure_callback=self.PT_get_current_pressure,
                        current_force_callback=self.PT_get_current_force)
        self.funDAC = DAC(log_callback=self.log_command,
                          status_callback=self.calibration_status)
        # ===== Log Startup =====
        self.log_command("AeroForce Test System running...")

    def setup_tabs(self):
        notebook = ttk.Notebook(self.root) # create notebook (tab manager)
        self.menu = tk.Menu(self.root) # create menu bar
        notebook.bind("<<NotebookTabChanged>>", self.rehash) # bind tab change to rehash classes - make sure calibration files are up to date
        # ===== create frames for each tab =====
        self.pretest_tab = tk.Frame(notebook) # define variable through notebook manager
        self.test_tab = tk.Frame(notebook) # define variable through notebook manager
        self.analysis_tab = tk.Frame(notebook) # define variable through notebook manager
        self.calibration_tab = tk.Frame(notebook) # define variable through notebook manager
        self.functions_tab = tk.Frame(notebook) # define variable through notebook manager
        self.tuning_tab = tk.Frame(notebook) # define variable through notebook manager 
        # ===== add tabs to the notebook =====
        notebook.add(self.pretest_tab,text="Pre-Test") # create "Pre-Test" tab
        notebook.add(self.test_tab, text="Test") # create "Test" tab
        notebook.add(self.analysis_tab, text="Analysis") # create "Analysis" tab
        notebook.add(self.calibration_tab,text="Calibration") # create "Calibration" tab
        notebook.add(self.functions_tab,text='Functions') # create "functions" tab
        notebook.add(self.tuning_tab,text="Tuning") # create "Tuning" tab
        # ===== allow contents to expand when changing window size =====
        notebook.pack(expand=True, fill="both")
        
        self.create_menu() # create menu bar
        self.create_pretest_tab() # create pretest tab
        self.create_test_tab() # create test tab
        self.create_analysis_tab() # create analysis tab
        self.create_calibration_tab() # create calibration tab
        self.create_functions_tab() # create functions tab
        self.create_tuning_tab() # create tuning tab
    
    def create_menu(self):
        # ===== File Menu =====
        file_menu = tk.Menu(self.menu, tearoff=False)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit_program)
        self.menu.add_cascade(label="File", menu=file_menu)
        # ===== Settings Menu =====
        settings_menu = tk.Menu(self.menu, tearoff=False)
        #settings_menu.add_command(label="Units…", command=self.open_units_dialog)
        #settings_menu.add_command(label="Preferences…", command=self.open_settings)
        self.menu.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Analysis",command=self.open_settings_menu_analysis) # open analysis settings window
        # ===== Help Menu =====
        help_menu = tk.Menu(self.menu, tearoff=False)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation",command=lambda: webbrowser.open("https://github.com/ADixon9/ATS"))
        help_menu.add_command(label='Refresh System',command=lambda: (self.rehash(),self.log_command("System refreshed...")))
        # ===== Configure Root =====
        self.root.config(menu=self.menu)

    def create_pretest_tab(self):

        # ===== Define Text Variables =====
        self.max_load = tk.DoubleVar() # define maxload as a floating value
        self.load_rate = tk.DoubleVar() # define ramp rate as a floating value

        # ===== Create Frame/Labels/Buttons =====
        top_frame = tk.Frame(self.pretest_tab) # create top frame where values, entry boxes, and drop downs are housed on the test tab (notebook)
        top_frame.grid(row=0,column=0,padx=10, pady=0,sticky='ew') # size of top frame
        # ----- Force/Pressure/Displacement -----
        tk.Label(top_frame, text="Force (Lbf):").grid(row=0, column=0, sticky="e") # create force label, sticking to right side
        tk.Label(top_frame, textvariable=self.force_var).grid(row=0, column=1, sticky="w") # create force variable label, sticking to left side

        tk.Label(top_frame, text="Pressure (psi):").grid(row=0, column=2, sticky="e") # create pressure label, sticking to right side
        tk.Label(top_frame, textvariable=self.pressure_var).grid(row=0, column=3, sticky="w") # create pressure variable label, sticking to left side

        tk.Label(top_frame, text="Displacement (in):").grid(row=0, column=4, sticky="e") # create displacement label, sticking to right side
        tk.Label(top_frame, textvariable=self.displacement_var).grid(row=0, column=5, sticky="w") # create displacement variable label, sticking to left side
        # ===== Controls =====
        # ----- Parameter Frame -----
        self.middle_frame_pretest = tk.Frame(self.pretest_tab) # create middle frame for test methods and start/stop buttons
        self.middle_frame_pretest.grid(row=1,column=0,padx=10, pady=0,sticky='ew') # layout middle frame
        self.param_frame_pre_test_tab = tk.Frame(self.middle_frame_pretest) # create parameter frame in pre test tab
        self.param_frame_pre_test_tab.grid(row=1,column=0,sticky='new') # layout parameter frame in pre test tab
        ''' Parameter specific metrics are defined in on_selection_change_pre_test_tab and use rows 1 and 2'''
        # ----- Test Method -----
        tk.Label(self.middle_frame_pretest, text="Test Method:").grid(row=0, column=0, sticky="e") # create test method label, stick to the right side
        test_options = ["Modulus Check"] # list drop down items under "Test Method"
        self.test_box_pretest_tab = ttk.Combobox(self.middle_frame_pretest, textvariable=self.test_method_pretest, values=test_options, state="readonly") # create drop-down box
        self.test_box_pretest_tab.grid(row=0, column=1, sticky="w") # layout drop box
        self.test_box_pretest_tab.bind("<<ComboboxSelected>>",self.on_selection_change_pre_test_tab) # bind the drop down box to run selection change function
        # ----- File Name/Directory -----
        tk.Label(self.middle_frame_pretest, text="File Name:").grid(row=3, column=0, sticky="e") # create file name label, stick to the right side
        self.file_name_pretest_tab_entry = tk.Entry(self.middle_frame_pretest, textvariable=self.file_name_pretest_tab_tk,width=40) # create entry box for file name
        self.file_name_pretest_tab_entry.grid(row=3, column=1, sticky="w") # layout file name on pretest tab
        tk.Button(self.middle_frame_pretest,text="Select File Directory",command=self.select_folder).grid(row=3,column=2,sticky="w") # create button to select file directory for new file
        # ----- Start/Stop Buttons -----
        self.start_button_pretest_tab = tk.Button(self.middle_frame_pretest,
                                                  text="Start Test",
                                                  command=self.on_start_button_pretest_tab,
                                                  bg="green",
                                                  fg="white") # create start test button
        self.start_button_pretest_tab.grid(row=4, column=0, pady=5) # layout start button
        self.stop_button_pretest_tab = tk.Button(self.middle_frame_pretest,
                                                 text="Stop Test",
                                                 command=self.on_test_stop_button,
                                                 bg="red",
                                                 fg="white") # create button to stop test
        self.stop_button_pretest_tab.grid(row=4, column=1, pady=5) # layout stop button
        # ===== Live Plot =====
        # ----- Bottom Frame -----
        bottom_frame = tk.Frame(self.pretest_tab) # Create bottom frame for plotting
        bottom_frame.grid(row=2,column=0,padx=10, pady=5,sticky='nsew') # layout bottom frame
        # ----- Plotting -----
        # ----- Create Force vs Displacement (fd) Plot -----
        self.pretest_fd_fig, self.pretest_fd_ax = plt.subplots()
        self.pretest_fd_fig.tight_layout(rect=(0, 0.05, 1, 1))
        # ----- Embed Plot Using FigureCanvasTkAgg -----
        self.pretest_fd_plot = FigureCanvasTkAgg(self.pretest_fd_fig,master=bottom_frame) # Embed Plot
        self.pretest_fd_plot.draw() # draw plot
        self.pretest_fd_plot.get_tk_widget().grid(row=0,column=0,sticky="nsew") # configure plot dimensions
        toolbar_conv = NavigationToolbar2Tk(self.pretest_fd_plot,bottom_frame, pack_toolbar=False)
        toolbar_conv.update()
        toolbar_conv.grid(row=1, column=0, sticky="ew")
        # ===== Command Window =====
        cmd_frame = tk.LabelFrame(self.pretest_tab,text="Command Log",labelanchor='n') # create cmd_frame
        cmd_frame.grid(row=3,column=0,sticky='nsew')
        self.cmd_text_box_pretest = tk.Text(cmd_frame,height=4,state='disabled') # create text box window
        self.cmd_text_box_pretest.grid(row=0,column=0,sticky="nsew") # layout text box
        vsb = ttk.Scrollbar(cmd_frame, orient="vertical", command=self.cmd_text_box_pretest.yview)
        vsb.grid(row=0, column=0, sticky="nse")
        self.cmd_text_box_pretest.configure(yscrollcommand=vsb.set)
        # ===== Configure Columns/Rows =====
        self.pretest_tab.columnconfigure(0,weight=1)
        self.pretest_tab.rowconfigure(0,weight=0)
        self.pretest_tab.rowconfigure(1,weight=0)
        self.pretest_tab.rowconfigure(2,weight=1)

        top_frame.columnconfigure(5,weight=1) # make column 6 stretch to fill empty space
        top_frame.rowconfigure(0,weight=1)
        bottom_frame.columnconfigure(0,weight=1)
        bottom_frame.rowconfigure(0,weight=1)
        cmd_frame.columnconfigure(0,weight=1)
    
    def create_test_tab(self):
        # ===== Create Frame/Labels/Buttons =====
        top_frame = tk.Frame(self.test_tab) # create top frame where values, entry boxes, and drop downs are housed on the test tab (notebook)
        top_frame.grid(row=0,column=0,padx=10, pady=0,sticky='ew') # size of top frame
        # ----- Force/Pressure/Displacement -----
        tk.Label(top_frame, text="Force (Lbf):").grid(row=0, column=0, sticky="e") # create force label, sticking to right side
        tk.Label(top_frame, textvariable=self.force_var).grid(row=0, column=1, sticky="w") # create force variable label, sticking to left side

        tk.Label(top_frame, text="Pressure (psi):").grid(row=0, column=2, sticky="e") # create pressure label, sticking to right side
        tk.Label(top_frame, textvariable=self.pressure_var).grid(row=0, column=3, sticky="w") # create pressure variable label, sticking to left side

        tk.Label(top_frame, text="Displacement (in):").grid(row=0, column=4, sticky="e") # create displacement label, sticking to right side
        tk.Label(top_frame, textvariable=self.displacement_var).grid(row=0, column=5, sticky="w") # create displacement variable label, sticking to left side
        # ===== Controls =====
        self.middle_frame_test = tk.Frame(self.test_tab) # create middle frame for test methods and start/stop buttons
        self.middle_frame_test.grid(row=1,column=0,padx=10, pady=0,sticky='ew') # add padding in x and y, fill spacing in x direction
        # ----- Test Method -----
        tk.Label(self.middle_frame_test, text="Test Method:").grid(row=0, column=0, sticky="e") # create test method label, stick to the right side
        test_options = ["Tensile", "Creep", "Fatigue"] # list drop down items under "Test Method"
        self.test_box_test_tab = ttk.Combobox(self.middle_frame_test, textvariable=self.test_method_test, values=test_options, state="readonly") # create drop-down box
        self.test_box_test_tab.grid(row=0, column=1, sticky="w") # layout drop box
        self.test_box_test_tab.bind("<<ComboboxSelected>>",self.on_selection_change_test_tab) # bind the drop down box to run selection change function
        # ----- Test Specific Metric ------
        self.param_frame_test_tab = tk.Frame(self.middle_frame_test) # create test parameter frame - can be destroyed when changing selection
        self.param_frame_test_tab.grid(row=0,column=2,sticky="we")
        ''' These labels and entrys are bound in on_selection_change function and are found in row 0'''
        # ----- Kp -----
        tk.Label(self.middle_frame_test, text="Kp:").grid(row=2, column=0, sticky="e") # create Kp label
        tk.Entry(self.middle_frame_test, textvariable=self.kp_tk,width=40).grid(row=2, column=1, sticky="w") # create entry box for file name
        # ----- File Name/Directory -----
        tk.Label(self.middle_frame_test, text="File Name:").grid(row=3, column=0, sticky="e") # create file name label, stick to the right side
        tk.Entry(self.middle_frame_test, textvariable=self.file_name_test_tab_tk,width=40).grid(row=3, column=1, sticky="w") # create entry box for file name
        tk.Button(self.middle_frame_test,text="Select File Directory",command=self.select_folder).grid(row=3,column=2,sticky="w") # create button to select file directory for new file
        # ----- Start/Stop Buttons -----
        tk.Button(self.middle_frame_test,text="Start Test",
                  command=self.on_start_button_test_tab,
                  bg="green",
                  fg="white").grid(row=4, column=0, pady=5) # create button to start test
        tk.Button(self.middle_frame_test,
                  text="Stop Test",
                  command=self.on_test_stop_button,
                  bg="red",
                  fg="white").grid(row=4, column=1, pady=5) # create button to stop test
        # ===== Live Plot =====
        # ----- Bottom Frame -----
        bottom_frame = tk.Frame(self.test_tab) # Create bottom frame for plotting
        bottom_frame.grid(row=2,column=0,padx=10, pady=5,sticky='nsew') # add padding to x and y sides, fill both y and x directions
        # ----- Plotting -----
        # ----- Create Force vs Displacement (fd) Plot -----
        self.test_fd_fig, self.test_fd_ax = plt.subplots()
        self.test_fd_fig.tight_layout(rect=(0, 0.05, 1, 1))
        # ----- Embed Plot Using FigureCanvasTkAgg -----
        self.test_fd_plot = FigureCanvasTkAgg(self.test_fd_fig,master=bottom_frame) # Embed Plot
        self.test_fd_plot.draw() # draw plot
        self.test_fd_plot.get_tk_widget().grid(row=0,column=0,sticky="nsew") # configure plot dimensions
        toolbar_conv = NavigationToolbar2Tk(self.test_fd_plot,bottom_frame, pack_toolbar=False)
        toolbar_conv.update()
        toolbar_conv.grid(row=1, column=0, sticky="ew")
        # ===== Command Window =====
        cmd_frame = tk.LabelFrame(self.test_tab,text="Command Log",labelanchor='n') # create cmd_frame
        cmd_frame.grid(row=3,column=0,sticky='nsew')
        self.cmd_text_box_test = tk.Text(cmd_frame,height=4,state='disabled') # create text box window
        self.cmd_text_box_test.grid(row=0,column=0,sticky="nsew") # layout text box
        vsb = ttk.Scrollbar(cmd_frame, orient="vertical", command=self.cmd_text_box_test.yview)
        vsb.grid(row=0, column=0, sticky="nse")
        self.cmd_text_box_test.configure(yscrollcommand=vsb.set)
        # ===== Configure Columns/Rows =====
        self.test_tab.columnconfigure(0,weight=1)
        self.test_tab.rowconfigure(0,weight=0)
        self.test_tab.rowconfigure(1,weight=0)
        self.test_tab.rowconfigure(2,weight=1)

        top_frame.columnconfigure(5,weight=1) # make column 6 stretch to fill empty space
        top_frame.rowconfigure(0,weight=1)
        bottom_frame.columnconfigure(0,weight=1)
        bottom_frame.rowconfigure(0,weight=1)
        cmd_frame.columnconfigure(0,weight=1)
        
    def create_analysis_tab(self):
        '''
        Functions to include:
        - allow running average plotting for both axes
        - allow the user to overlay multiple plots from both different files and different axes
            - create drop down box that user can select number of plots they want - create a load file and axes selection for each plot - allow user to label
        '''
        # ===== Create Frames/Labels/Buttons =====
        top_frame = tk.Frame(self.analysis_tab,bd=1,relief='solid') # create top frame where values, entry boxes, and drop downs are housed on the analysis tab (notebook)
        top_frame.grid(row=0,column=0,padx=10, pady=0,sticky='ew') # size of top frame
        left_top_frame = tk.Frame(top_frame,bd=1,relief='solid') # create left frame inside top frame
        left_top_frame.grid(row=1,column=0,sticky='nsew') # layout left frame in top frame
        self.analysis_frame_analysis_tab = tk.Frame(left_top_frame,bd=1,relief='solid') # create analysis frame in left top frame
        self.analysis_frame_analysis_tab.grid(row=2,column=0,sticky='nsew',columnspan=4) # layout analysis frame
        right_top_frame = tk.Frame(top_frame,bd=1,relief='solid') # create right frame inside top frame
        right_top_frame.grid(row=1,column=1,sticky='nsew') # layout right frame in top frame
        self.plot_axes_frame_analysis_tab = tk.Frame(right_top_frame,bd=1,relief='solid') # create frame to display plot axes selection
        self.plot_axes_frame_analysis_tab.grid(row=4,column=0,columnspan=8,sticky='ew') # layout plot axes frame
        self.middle_frame_analysis = tk.Frame(self.analysis_tab,bd=1,relief='solid') # create middle frame
        self.middle_frame_analysis.grid(row=1,column=0,padx=10, pady=0,sticky='nsew') # layout middle frame
        self.left_middle_frame_analysis = tk.Frame(self.middle_frame_analysis,bd=1,relief='solid') # create left middle frame
        self.left_middle_frame_analysis.grid(row=0,column=0,sticky='nsew') # layout left middle frame
        self.right_middle_frame_analysis = tk.Frame(self.middle_frame_analysis,bd=1,relief='solid') # create right middle frame
        self.right_middle_frame_analysis.grid(row=0,column=1,sticky='nsew') # layout right middle frame
        # ===== Define Sizes =====
        combo_box_width = 30
        entry_width = 20
        # ----- Header -----
        tk.Label(left_top_frame,text='Analysis',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=0,column=0,columnspan=4,sticky='ew') # create and layout header
        tk.Label(right_top_frame,text='Plot',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=0,column=0,columnspan=4,sticky='ew') # create and layout header

        # ===== Analysis Results (left top frame)=====
        # ----- Select Test Type -----
        tk.Label(left_top_frame,text="Test Type:").grid(row=1,column=0,sticky='e') # create test type label
        self.analysis_test_type_analysis_tab = ttk.Combobox(left_top_frame,
                                                            textvariable=self.analysis_test_type_analysis_tk,
                                                            values=['Modulus Check','Tensile','Creep','Fatigue'],
                                                            state='readonly',
                                                            width=combo_box_width) # create drop down box to select number of plots
        self.analysis_test_type_analysis_tab.grid(row=1,column=1,sticky='w') # layout number of plots box
        self.analysis_test_type_analysis_tab.bind("<<ComboboxSelected>>",self.on_selection_change_analysis_test_type_analysis_tab) # bind the drop down box to run function
        # ----- File Name/Directory -----
        self.load_file_analysis_button = tk.Button(left_top_frame,text="Load File",command=self.select_analysis_file) # create button to select file directory for data
        self.load_file_analysis_button.grid(row=1,column=2,sticky="w") # layout load file button
        # ===== Plot Options (right top frame) =====
        # ----- Select Number of Plots and Test Type -----
        tk.Label(right_top_frame,text="Number of Plots:").grid(row=1,column=0,sticky='e') # create number of plots label
        self.num_plots_box_analysis_tab = ttk.Combobox(right_top_frame,
                                                       textvariable=self.number_of_analysis_plots_tk,
                                                       values=[1,2,3,4,5,6,7,8],
                                                       state='readonly',
                                                       width=combo_box_width) # create drop down box to select number of plots
        self.num_plots_box_analysis_tab.grid(row=1,column=1,sticky='w') # layout number of plots box
        self.num_plots_box_analysis_tab.bind("<<ComboboxSelected>>",self.on_selection_change_num_plots_analysis_tab) # bind the drop down box to run function
        self.num_plots_box_analysis_tab.current(0) # make current selection the first value
        self.num_plots_box_analysis_tab.event_generate("<<ComboboxSelected>>") # act as if the first value has been selected i.e. run the selection change function
        ''' List all plot axes and load data buttons'''
        tk.Label(right_top_frame,text="Test Type:").grid(row=2, column=0, sticky="e") # create test type label, stick to the right side
        test_type_options = ["Modulus Check","Tensile","Creep","Fatigue"] # list drop down items under "Test Type"
        self.test_type_box_analysis_tab = ttk.Combobox(right_top_frame,
                                                       textvariable=self.plot_test_type_analysis_tk,
                                                       values=test_type_options,
                                                       state="readonly",width=combo_box_width) # create drop-down box
        self.test_type_box_analysis_tab.grid(row=2, column=1, sticky="w") # layout drop box
        self.test_type_box_analysis_tab.bind("<<ComboboxSelected>>",self.on_selection_change_plot_test_type_analysis_tab) # bind the drop down box to run plotting function
        # ----- Add Check Buttons -----
        self.enable_axes_labels_analysis_tab = tk.Checkbutton(right_top_frame,
                                                              variable=self.enable_axes_labels_analysis_tab_tk,
                                                              command = self.on_selection_change_num_plots_analysis_tab,
                                                              text='Axes Labels') # create checkbox to enable/disable axes labels
        self.enable_axes_labels_analysis_tab.grid(row=1,column=2,sticky='w') # layout checkbutton
        self.enable_labels_analysis_tab = tk.Checkbutton(right_top_frame,
                                                         variable=self.enable_plot_labels_analysis_tab_tk,
                                                         command = self.on_selection_change_num_plots_analysis_tab,
                                                         text='Plot Labels') # create checkbox to enable/disable plot labels
        self.enable_labels_analysis_tab.grid(row=1,column=3,sticky='w') # layout checkbutton
        self.enable_filtering_analysis_tab = tk.Checkbutton(right_top_frame,
                                                            variable=self.enable_filtering_analysis_tab_tk,
                                                            command = self.on_selection_change_num_plots_analysis_tab,
                                                            text='Filtering') # create checkbox to enable/disable axes labels
        self.enable_filtering_analysis_tab.grid(row=1,column=4,sticky='w') # layout checkbutton
        self.enable_snip_analysis_tab = tk.Checkbutton(right_top_frame,
                                                      variable=self.enable_snip_analysis_tab_tk,
                                                      command = self.on_selection_change_num_plots_analysis_tab,
                                                      text='Snip') # create checkbox to enable/disable axes labels
        self.enable_snip_analysis_tab.grid(row=1,column=5,sticky='w') # layout checkbutton
        self.enable_x_shift_analysis_tab = tk.Checkbutton(right_top_frame,
                                                          variable=self.enable_x_shift_analysis_tab_tk,
                                                          command = self.on_selection_change_num_plots_analysis_tab,
                                                          text='X-Shift') # create checkbox to enable/disable x shift labels
        self.enable_x_shift_analysis_tab.grid(row=1,column=6,sticky='w') # layout checkbutton
        self.enable_y_shift_analysis_tab = tk.Checkbutton(right_top_frame,
                                                          variable=self.enable_y_shift_analysis_tab_tk,
                                                          command = self.on_selection_change_num_plots_analysis_tab,
                                                          text='Y-Shift') # create checkbox to enable/disable y shift labels
        self.enable_y_shift_analysis_tab.grid(row=1,column=7,sticky='w') # layout checkbutton
        # ----- Add Toggle Button -----
        self.axes_toggle_btn = tk.Button(right_top_frame,
                                    text="▾",
                                    width=1,
                                    command=self.toggle_axes_selection_frame)
        self.analysis_toggle_btn = tk.Button(left_top_frame,
                                    text="▾",
                                    width=1,
                                    command=self.toggle_analysis_frame)
        # place it just above or to the right of the selection_frame
        self.axes_toggle_btn.grid(row=2, column=8, sticky="ne")
        self.analysis_toggle_btn.grid(row=1, column=4, sticky="ne")
        # ----- Plot/Run Buttons -----
        tk.Button(left_top_frame, text="Run Analysis", command=self.start_analysis_threading).grid(row=1, column=3, pady=5,sticky='w') # create run analysis button
        tk.Button(right_top_frame, text="Plot Data", command=self.plot_test_data).grid(row=2, column=2, pady=5,sticky='w') # create plot button
        # ===== Plotting =====
        # ----- Create Force vs Displacement (fd) Plot -----
        self.analysis_fig, self.analysis_ax = plt.subplots()
        self.analysis_fig.tight_layout(rect=(0, 0.05, 1, 1))
        # ----- Embed Plot Using FigureCanvasTkAgg -----
        self.analysis_plot = FigureCanvasTkAgg(self.analysis_fig,master=self.right_middle_frame_analysis) # Embed Plot
        self.analysis_plot.draw() # draw plot
        self.analysis_plot.get_tk_widget().grid(row=0,column=0,sticky="nsew") # configure plot dimensions
        toolbar_conv = NavigationToolbar2Tk(self.analysis_plot,self.right_middle_frame_analysis, pack_toolbar=False)
        toolbar_conv.update()
        toolbar_conv.grid(row=1, column=0, sticky="ew")
        # ===== Command Window =====
        cmd_frame = tk.LabelFrame(self.analysis_tab,text="Command Log",labelanchor='n') # create cmd_frame
        cmd_frame.grid(row=3,column=0,sticky='nsew')
        self.cmd_text_box_analysis = tk.Text(cmd_frame,height=4,state='disabled') # create text box window
        self.cmd_text_box_analysis.grid(row=0,column=0,sticky="nsew") # layout text box
        vsb = ttk.Scrollbar(cmd_frame, orient="vertical", command=self.cmd_text_box_analysis.yview)
        vsb.grid(row=0, column=0, sticky="nse")
        self.cmd_text_box_analysis.configure(yscrollcommand=vsb.set)
        # ===== Configure Columns/Rows =====
        self.analysis_tab.columnconfigure(0,weight=1)
        self.analysis_tab.rowconfigure(0,weight=0)
        self.analysis_tab.rowconfigure(1,weight=1)
        self.analysis_tab.rowconfigure(2,weight=0)

        top_frame.columnconfigure(0,weight=1) # make column 6 stretch to fill empty space
        top_frame.columnconfigure(1,weight=1)
        top_frame.rowconfigure(0,weight=1)
        left_top_frame.columnconfigure(3,weight=1)
        right_top_frame.columnconfigure(7,weight=1)
        self.middle_frame_analysis.columnconfigure(0,weight=1)
        self.middle_frame_analysis.columnconfigure(1,weight=1)
        self.middle_frame_analysis.rowconfigure(0,weight=1)
        self.right_middle_frame_analysis.columnconfigure(0,weight=1)
        self.right_middle_frame_analysis.rowconfigure(0,weight=1)
        self.plot_axes_frame_analysis_tab.columnconfigure(15,weight=1)
        cmd_frame.columnconfigure(0,weight=1)

    def create_calibration_tab(self):
        # ===== Create Frames =====
        header_frame=tk.Frame(self.calibration_tab,bd=1,relief='solid') # create header frame on calibration tab
        header_frame.grid(row=0,column=0,columnspan=2,sticky='new')
        left_frame = tk.Frame(self.calibration_tab,bd=1,relief='solid') # create left side frame on calibration tab
        left_frame.grid(row=1,column=0,padx=5,pady=5,sticky='new') # define padding and fill of left frame
        right_frame = tk.Frame(self.calibration_tab,bd=1,relief='solid') # create right side frame on calibration tab
        right_frame.grid(row=1,column=1,padx=10,pady=5,sticky='new') # define padding and fill of right frame
        # ===== Create Labels,Entrys =====
        tk.Label(header_frame,text="ATS Calibration",font=('TkDefaultFont',16,'bold'),justify='center').grid(row=0,column=0,sticky='nsew')
        tk.Label(left_frame,text="Device:").grid(row=0,column=0,sticky="e")# create calibration options label
        tk.Label(left_frame,text="File Name:").grid(row=1,column=0,sticky="e") # define file name label
        self.file_name_calibration_tab = tk.Entry(left_frame,textvariable=self.file_name_calibration_tab,text="Enter File Name For Calibration Data",width=21) # define file name entry
        self.file_name_calibration_tab.grid(row=1,column=1,sticky='w')
        tk.Button(left_frame,text="Select File Directory",command=self.select_folder).grid(row=1,column=2,sticky="w") # create button to select file directory for new file
        tk.Label(left_frame,text="Number of Points:").grid(row=0,column=2,sticky='w') # create label for number of calibration points
        self.num_points_entry_calibration_tab = tk.Entry(left_frame,textvariable=self.num_calibration_pts)
        self.num_points_entry_calibration_tab.grid(row=0,column=3,sticky='w') # create entry box for number of calibration points
        # ===== Create Calibration Drop Down Box ====
        calibration_options = ["LVDT","Pressure Transducer","I/P Transducer","Frame Compliance"] # define calibration options
        self.calibration_box_calibration_tab = ttk.Combobox(left_frame,textvariable=self.calibration_method,values=calibration_options,state="readonly") # create drop-down box
        self.calibration_box_calibration_tab.grid(row=0,column=1,sticky="w")
        self.calibration_box_calibration_tab.bind("<<ComboboxSelected>>",self.on_selection_change_calibration_tab) # bind the drop down box to run selection change function
        # ===== Calibration Data Entry =====
        self.param_frame_calibration_tab = tk.Frame(left_frame,bd=1,relief='solid') # create parameter frame in calibration tab
        self.param_frame_calibration_tab.grid(row=2,column=0,padx=0,pady=20,columnspan=4,sticky='new')
        ''' These labels and entrys are bound in on_selection_change function and are found in row 0'''
        # ===== Plotting =====
        # ----- Create Force vs Displacement (fd) Plot (Top) -----
        self.cal_conv_fig, self.cal_conv_ax = plt.subplots()
        self.cal_conv_fig.tight_layout(rect=(.05, 0.05, 1, .95))
        # ----- Create Linear Fit Plot (Bottom) -----
        self.cal_lin_fig, self.cal_lin_ax = plt.subplots()
        self.cal_lin_fig.tight_layout(rect=(.05, 0.05, 1, .95))
        # ----- Embed Plot Using FigureCanvasTkAgg -----
        self.cal_plot_conv = FigureCanvasTkAgg(self.cal_conv_fig,master=right_frame) # Embed Plot
        self.cal_plot_conv.draw() # draw plot
        self.cal_plot_conv.get_tk_widget().grid(row=0,column=0,sticky="nsew") # configure plot dimensions
        toolbar_conv = NavigationToolbar2Tk(self.cal_plot_conv, right_frame, pack_toolbar=False)
        toolbar_conv.update()
        toolbar_conv.grid(row=1, column=0, sticky="ew")

        self.cal_plot_lin = FigureCanvasTkAgg(self.cal_lin_fig,master=right_frame) # Embed Plot
        self.cal_plot_lin.draw() # draw plot
        self.cal_plot_lin.get_tk_widget().grid(row=2,column=0,sticky="nsew") # configure plot dimensions
        toolbar_lin = NavigationToolbar2Tk(self.cal_plot_lin, right_frame, pack_toolbar=False)
        toolbar_lin.update()
        toolbar_lin.grid(row=3, column=0, sticky="ew")
        # ===== Command Window =====
        cmd_frame = tk.LabelFrame(self.calibration_tab,text="Command Log",labelanchor='n') # create cmd_frame
        cmd_frame.grid(row=4,column=0,columnspan=2,sticky='nsew')
        self.cmd_text_box_calibration = tk.Text(cmd_frame,height=4,state='disabled') # create text box window
        self.cmd_text_box_calibration.grid(row=0,column=0,sticky="nsew") # layout text box
        vsb = ttk.Scrollbar(cmd_frame, orient="vertical", command=self.cmd_text_box_test.yview)
        vsb.grid(row=0, column=0, sticky="nse")
        self.cmd_text_box_calibration.configure(yscrollcommand=vsb.set)
        # ===== Configure Columns/Rows =====
        self.calibration_tab.columnconfigure(0,weight=1)
        self.calibration_tab.columnconfigure(1,weight=1)
        self.calibration_tab.rowconfigure(1,weight=1)

        header_frame.columnconfigure(0,weight=1)
        left_frame.columnconfigure(3,weight=1)
        self.param_frame_calibration_tab.columnconfigure(4,weight=1)
        right_frame.columnconfigure(0,weight=1)
        right_frame.rowconfigure(0,weight=1)
        right_frame.rowconfigure(1,weight=0)
        right_frame.rowconfigure(2,weight=1)
        right_frame.rowconfigure(3,weight=0)
        cmd_frame.columnconfigure(0,weight=1)

    def create_functions_tab(self):
        # ===== Define Sizes =====
        button_width = 20 # define button width
        entry_width = 20 # defome entry width
        # ===== Create Frames =====
        header_frame = tk.Frame(self.functions_tab,bd=1,relief='solid') # create header frame
        header_frame.grid(row=0,column=0,sticky='new') # layout header frame
        middle_frame = tk.Frame(self.functions_tab,bd=1,relief='solid') # create middle frame
        middle_frame.grid(row=1,column=0,sticky='new') # layout middle frame
        LVDT_frame = tk.Frame(middle_frame,bd=1,relief='solid') # create LVDT frame
        LVDT_frame.grid(row=0,column=0,sticky='new') # layout LVDT frame
        pressure_transducer_frame = tk.Frame(middle_frame,bd=1,relief='solid') # create pressure transducer frame
        pressure_transducer_frame.grid(row=1,column=0,sticky='new') # layout pressure transducer frame
        ip_transducer_frame = tk.Frame(middle_frame,bd=1,relief='solid') # create I/P transducer frame
        ip_transducer_frame.grid(row=2,column=0,sticky='new') # layout I/P frame
        tk.Label(header_frame,text='ATS Functions',font=('TkDefaultFont',16,'bold'),justify='center').grid(row=0,column=0,sticky='nsew') # create header label
        # ===== LVDT =====
        tk.Label(LVDT_frame,text='LVDT',font=('TkDefaultFont',12,'bold'),justify='center').grid(row=0,column=0,columnspan=3,sticky='nsew') # create LVDT header
        tk.Label(LVDT_frame,text='Current Position (inches):').grid(row=1,column=0,sticky='e') # create current position label
        tk.Label(LVDT_frame,text='Current Voltage (V):').grid(row=2,column=0,sticky='e') # create current voltage label
        tk.Label(LVDT_frame,text='Zero Offset Position (inches):').grid(row=3,column=0,sticky='w') # create zero position offset label
        tk.Button(LVDT_frame,text='Measure',command=lambda: (self.funLVDT.measure(callback=True),self.funLVDT.measure_voltage(callback=True)),width=button_width).grid(row=1,column=2,sticky='w') # create measure button
        tk.Button(LVDT_frame,text='Set Zero Offset Postion',command=self.LVDT_get_zero,width=button_width).grid(row=3,column=2,sticky='w') # create zero offset button
        tk.Entry(LVDT_frame,textvariable=self.LVDT_current_position_tk,state='readonly',width=entry_width).grid(row=1,column=1,sticky='w') # display current position
        tk.Entry(LVDT_frame,textvariable=self.LVDT_current_voltage_tk,state='readonly',width=entry_width).grid(row=2,column=1,sticky='w') # display current voltage
        tk.Entry(LVDT_frame,textvariable=self.LVDT_cal_zero_tk,state='readonly',width=entry_width).grid(row=3,column=1,sticky='w') # display zero offset
        # ===== Pressure Transducer =====
        tk.Label(pressure_transducer_frame,text='Pressure Transducer',font=('TkDefaultFont',12,'bold'),justify='center').grid(row=0,column=0,columnspan=3,sticky='nsew') # create header label
        tk.Label(pressure_transducer_frame,text="Current Pressure (psi):").grid(row=1,column=0,sticky='e') # create current pressure label
        tk.Entry(pressure_transducer_frame,textvariable=self.PT_current_pressure_tk,state='readonly',width=entry_width).grid(row=1,column=1,sticky='w') # display current pressure
        tk.Label(pressure_transducer_frame,text="Current Force (lb):").grid(row=2,column=0,sticky='e') # create current force label
        tk.Entry(pressure_transducer_frame,textvariable=self.PT_current_force_tk,state='readonly',width=entry_width).grid(row=2,column=1,sticky='w') # display current force
        tk.Button(pressure_transducer_frame,text='Measure',command=lambda: (self.funPT.readPSI(callback=True),self.funPT.readForce(callback=True)),width=button_width).grid(row=1,column=2,sticky='w') # create measure button
        tk.Label(pressure_transducer_frame,text="Zero Offset Pressure (psi):").grid(row=3,column=0,sticky='w') # create zero offset pressure label
        tk.Entry(pressure_transducer_frame,textvariable=self.PT_cal_zero_tk,state='readonly',width=entry_width).grid(row=3,column=1,sticky='w') # create zero offset pressure entry
        tk.Button(pressure_transducer_frame,text='Set Zero Offset Pressure',command=self.PT_get_zero,width=button_width).grid(row=3,column=2,sticky='w') # create zero offset button
        # ===== I/P Transducer (DAC)=====
        tk.Label(ip_transducer_frame,text='I/P Transducer',font=('TkDefaultFont',12,'bold'),justify='center').grid(row=0,column=0,columnspan=3,sticky='nsew') # create header label
        tk.Label(ip_transducer_frame,text='Set Pressure (psi):').grid(row=1,column=0,sticky='w') # create set pressure label
        tk.Entry(ip_transducer_frame,textvariable=self.DAC_set_pressure_tk,width=entry_width).grid(row=1,column=1,sticky='w')
        tk.Button(ip_transducer_frame,text='Set Pressure',command=lambda: (self.funDAC.writePSI(self.DAC_set_pressure_tk.get(),callback=True)),width=button_width).grid(row=1,column=2,sticky='w') # create set pressure button
        # ===== Command Window =====
        cmd_frame = tk.LabelFrame(self.functions_tab,text="Command Log",labelanchor='n') # create cmd_frame
        cmd_frame.grid(row=2,column=0,columnspan=2,sticky='nsew')
        self.cmd_text_box_functions = tk.Text(cmd_frame,height=4,state='disabled') # create text box window
        self.cmd_text_box_functions.grid(row=0,column=0,sticky="nsew") # layout text box
        vsb = ttk.Scrollbar(cmd_frame, orient="vertical", command=self.cmd_text_box_test.yview)
        vsb.grid(row=0, column=0, sticky="nse")
        self.cmd_text_box_functions.configure(yscrollcommand=vsb.set)
        # ===== Configure Columns/Rows =====
        self.functions_tab.columnconfigure(0,weight=1)
        self.functions_tab.rowconfigure(1,weight=1)

        header_frame.columnconfigure(0,weight=1)
        middle_frame.columnconfigure(0,weight=1)
        LVDT_frame.columnconfigure(2,weight=1)
        pressure_transducer_frame.columnconfigure(2,weight=1)
        ip_transducer_frame.columnconfigure(2,weight=1)
        cmd_frame.columnconfigure(0,weight=1)

    def create_tuning_tab(self):
        # ===== Create Frame/Labels/Buttons =====
        top_frame = tk.Frame(self.tuning_tab) # create top frame where values, entry boxes, and drop downs are housed on the test tab (notebook)
        top_frame.grid(row=0,column=0,padx=10, pady=0,sticky='ew') # size of top frame
        # ----- Force/Pressure/Displacement -----
        tk.Label(top_frame, text="Force (lb):").grid(row=0, column=0, sticky="e") # create force label, sticking to right side
        tk.Label(top_frame, textvariable=self.force_label_tuning_tab_tk).grid(row=0, column=1, sticky="w") # create force variable label, sticking to left side

        tk.Label(top_frame, text="Pressure (psi):").grid(row=0, column=2, sticky="e") # create pressure label, sticking to right side
        tk.Label(top_frame, textvariable=self.pressure_var).grid(row=0, column=3, sticky="w") # create pressure variable label, sticking to left side

        tk.Label(top_frame, text="Displacement (in):").grid(row=0, column=4, sticky="e") # create displacement label, sticking to right side
        tk.Label(top_frame, textvariable=self.displacement_var).grid(row=0, column=5, sticky="w") # create displacement variable label, sticking to left side
        # ===== Controls =====
        self.middle_frame_tuning = tk.Frame(self.tuning_tab) # create middle frame for test methods and start/stop buttons
        self.middle_frame_tuning.grid(row=1,column=0,padx=10, pady=0,sticky='ew') # add padding in x and y, fill spacing in x direction
        # ----- Test Method -----
        tk.Label(self.middle_frame_tuning, text="Tuning Method:").grid(row=0, column=0, sticky="e") # create test method label, stick to the right side
        tuning_options = ["Stroke Rate"] # list drop down items under "Tuning Method"
        self.tuning_box_tuning_tab = ttk.Combobox(self.middle_frame_tuning, textvariable=self.tuning_method_tuning_tab_tk,values=tuning_options,state="readonly") # create drop-down box
        self.tuning_box_tuning_tab.grid(row=0, column=1, sticky="w") # layout drop box
        self.tuning_box_tuning_tab.bind("<<ComboboxSelected>>",self.on_selection_change_tuning_tab) # bind the drop down box to run selection change function
        # ----- Test Specific Metric ------
        self.param_frame_tuning_tab = tk.Frame(self.middle_frame_tuning) # create test parameter frame - can be destroyed when changing selection
        self.param_frame_tuning_tab.grid(row=1,column=0,sticky="new",columnspan=2)
        ''' These labels and entrys are bound in on_selection_change function and are found in row 0'''
        # ----- File Name/Directory -----
        tk.Label(self.middle_frame_tuning, text="File Name:").grid(row=2, column=0, sticky="e") # create file name label, stick to the right side
        tk.Entry(self.middle_frame_tuning, textvariable=self.file_name_tuning_tab_tk,width=40).grid(row=2, column=1, sticky="w") # create entry box for file name
        tk.Button(self.middle_frame_tuning,text="Select File Directory",command=self.select_folder).grid(row=2,column=2,sticky="w") # create button to select file directory for new file
        # ----- Start/Stop Buttons -----
        tk.Button(self.middle_frame_tuning,text="Start Test",
                  command=self.on_start_button_tuning_tab,
                  bg="green",
                  fg="white").grid(row=3, column=0, pady=5) # create button to start test
        tk.Button(self.middle_frame_tuning,
                  text="Stop Test",
                  command=self.on_test_stop_button,
                  bg="red",
                  fg="white").grid(row=3, column=1, pady=5) # create button to stop test
        # ===== Live Plot =====
        # ----- Bottom Frame -----
        bottom_frame = tk.Frame(self.tuning_tab) # Create bottom frame for plotting
        bottom_frame.grid(row=2,column=0,padx=10, pady=5,sticky='nsew') # add padding to x and y sides, fill both y and x directions
        # ----- Plotting -----
        # ----- Create Force vs Displacement (fd) Plot -----
        self.tuning_fd_fig, self.tuning_fd_ax = plt.subplots()
        self.tuning_fd_fig.tight_layout(rect=(0, 0.05, 1, 1))
        # ----- Embed Plot Using FigureCanvasTkAgg -----
        self.tuning_fd_plot = FigureCanvasTkAgg(self.tuning_fd_fig,master=bottom_frame) # Embed Plot
        self.tuning_fd_plot.draw() # draw plot
        self.tuning_fd_plot.get_tk_widget().grid(row=0,column=0,sticky="nsew") # configure plot dimensions
        toolbar_conv = NavigationToolbar2Tk(self.tuning_fd_plot,bottom_frame,pack_toolbar=False)
        toolbar_conv.update()
        toolbar_conv.grid(row=1, column=0, sticky="ew")
        # ===== Command Window =====
        cmd_frame = tk.LabelFrame(self.tuning_tab,text="Command Log",labelanchor='n') # create cmd_frame
        cmd_frame.grid(row=3,column=0,sticky='nsew')
        self.cmd_text_box_tuning = tk.Text(cmd_frame,height=4,state='disabled') # create text box window
        self.cmd_text_box_tuning.grid(row=0,column=0,sticky="nsew") # layout text box
        vsb = ttk.Scrollbar(cmd_frame, orient="vertical", command=self.cmd_text_box_tuning.yview)
        vsb.grid(row=0, column=0, sticky="nse")
        self.cmd_text_box_tuning.configure(yscrollcommand=vsb.set)
        # ===== Configure Columns/Rows =====
        self.tuning_tab.columnconfigure(0,weight=1)
        self.tuning_tab.rowconfigure(0,weight=0)
        self.tuning_tab.rowconfigure(1,weight=0)
        self.tuning_tab.rowconfigure(2,weight=1)

        top_frame.columnconfigure(5,weight=1) # make column 6 stretch to fill empty space
        top_frame.rowconfigure(0,weight=1)
        bottom_frame.columnconfigure(0,weight=1)
        bottom_frame.rowconfigure(0,weight=1)
        cmd_frame.columnconfigure(0,weight=1)

    def open_settings_menu_analysis(self):
        # ===== Create Settings Window =====
        settings_window = tk.Toplevel(self.root) # create settings window
        settings_window.title('Analysis Settings') # set window title
        settings_window.transient(self.root) # ensures window is always in front of parent window
        settings_window.geometry("400x200") # define size of settings window
        # ===== Get Mod Check Information ======
        file_path = self.folder_path.get() # get selected folder path
        new_path = os.path.join(file_path,self.file_name_pretest_tab_tk.get()+".csv")
        max_load = self.max_load.get() # get max load for mod check
        load_rate = self.load_rate.get() # get load rate for mod check
        # ===== Display test Parameters =====
        header_frame = tk.Frame(confirmation_window) # create header_frame
        header_frame.grid(row=0,column=0,sticky='ew')
        info_frame = tk.Frame(confirmation_window) # create info_frame in confirmation window
        info_frame.grid(row=1,column=0,sticky='we') # layout info_frame
        tk.Label(header_frame,text="Modulus Check Parameters",font=('TkDefaultFont',16,'bold'),justify='center').grid(row=0,column=0,sticky='ew') # create label
        tk.Label(info_frame,text=f"Maximum Load: {max_load}",justify='center').grid(row=1,column=0,sticky='ew') # create label
        tk.Label(info_frame,text=f"Load Rate: {load_rate}",justify='center').grid(row=2,column=0,sticky="ew") # create label
        tk.Label(info_frame,text=f"File Path: {file_path}",justify='center').grid(row=3,column=0,sticky="ew") # create label

        # ===== Continue/Cancel Buttons =====
        button_frame = tk.Frame(confirmation_window) # create button_frame in confirmation window
        button_frame.grid(row=2,column=0,pady=20,sticky='ew') # layout button_frame
        tk.Button(button_frame,text="Start Test",justify='center',bg='green',fg='white',command=lambda:[confirmation_window.destroy(),self.start_modcheck_threading(max_load=max_load,load_rate=load_rate,file_path=new_path)]).grid(row=0,column=0,sticky='e')
        tk.Button(button_frame,text="Cancel",justify='left',bg='red',fg='white',command=confirmation_window.destroy).grid(row=0,column=1,sticky='w')
        # ===== Configure Columns/Rows =====
        confirmation_window.columnconfigure(0,weight=1)
        header_frame.columnconfigure(0,weight=1)
        info_frame.columnconfigure(0,weight=1)
        button_frame.columnconfigure(0,weight=1)
        button_frame.columnconfigure(1,weight=1)

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path.set(path)
            self.log_command(f"File path selected: {self.folder_path.get()}")

    def select_analysis_file(self):
        path = filedialog.askopenfilename(
            title="Select data file for analysis",
            filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if not path:
            return  # user canceled
        self.analysis_file_path = path # store path
        # update the button’s label to show the filename
        fname = os.path.basename(path)
        self.load_file_analysis_button.configure(text=fname)

    def select_plot_file(self,idx):
        path = filedialog.askopenfilename(
            title="Select data file for plot {}".format(idx+1),
            filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if not path:
            return  # user canceled
        self.plot_file_paths[idx] = path # store path
        # update the button’s label to show the filename
        fname = os.path.basename(path)
        self.load_buttons[idx].configure(text=fname)

    def open_calibration_file(self):
        # ===== Open Calibration File =====
        self.filename = filedialog.askopenfilename(
            title="Select a calibration file",
            initialdir=".",                                # start in current working directory
            filetypes=[("CSV files","*.csv"), ("All files","*.*")]
        )
        if self.filename:
            self.log_command(f"Calibration File: {self.filename} selected...") # log file selection
        else:
            self.log_command("File selection canceled...") # log file selection cancelation

        method = self.calibration_method.get() # get current calibration method

        if method=="LVDT":
            # ===== Plot Calibration Data =====
            self.plot_calibration_data(file_path=self.filename,is_file_loaded=True) # plot calibration data,loading file
            # ===== Update Text Variables =====
            self.LVDT_cal_factor_tk.set(round(self.LVDT_cal_factor,9)) # set tk text variable to its new value
            self.LVDT_cal_zero_tk.set(round(self.LVDT_cal_zero,5)) # set tk text variable to its new value
            self.LVDT_cal_std_dev_tk.set(round(self.LVDT_cal_std_dev,5)) # set tk text variable to its new value
            self.LVDT_cal_linearity_tk.set(round(self.LVDT_cal_linearity,4)) # set tk text variable to its new value
            self.LVDT_cal_R2_tk.set(round(self.LVDT_cal_R2,4)) # set tk text variable to its new value
            # ===== Populate Statistics =====
            tk.Label(self.param_frame_calibration_tab,text='Calibration Factor (inches/count):').grid(row=1,column=0,sticky='e') # create cal factor label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.LVDT_cal_factor_tk,state='readonly').grid(row=1,column=1,sticky='w') # display calibration factor
            tk.Label(self.param_frame_calibration_tab,text="Zero Offset (inches):").grid(row=2,column=0,sticky='e') # create zero offset label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.LVDT_cal_zero_tk,state='readonly').grid(row=2,column=1,sticky='w') # display zero offset
            tk.Label(self.param_frame_calibration_tab,text='Standard Deviation (inches):').grid(row=3,column=0,sticky='e') # create standard deviation label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.LVDT_cal_std_dev_tk,state='readonly').grid(row=3,column=1,sticky='w') # display standard deviation
            tk.Label(self.param_frame_calibration_tab,text='Linearity (%FSO):').grid(row=4,column=0,sticky='e') # create linearity label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.LVDT_cal_linearity_tk,state='readonly').grid(row=4,column=1,sticky='w') # display linearity
            tk.Label(self.param_frame_calibration_tab,text='R\u00b2:').grid(row=5,column=0,sticky='e') # create R^2 lable
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.LVDT_cal_R2_tk,state='readonly').grid(row=5,column=1,sticky='w') # display R2 value
        elif method=="Pressure Transducer":
            # ===== Plot Calibration Data =====
            self.plot_calibration_data(file_path=self.filename,is_file_loaded=True) # plot calibration data,loading file
            # ===== Update Text Variables =====
            self.PT_cal_factor_tk.set(round(self.PT_cal_factor,9)) # set tk text variable to its new value
            self.PT_cal_zero_tk.set(round(self.PT_cal_zero,3)) # set tk text variable to its new value
            self.PT_cal_std_dev_tk.set(round(self.PT_cal_std_dev,4)) # set tk text variable to its new value
            self.PT_cal_linearity_tk.set(round(self.PT_cal_linearity,4)) # set tk text variable to its new value
            self.PT_cal_R2_tk.set(round(self.PT_cal_R2,4)) # set tk text variable to its new value
            # ===== Populate Statistics =====
            tk.Label(self.param_frame_calibration_tab,text='Calibration Factor (psi/count):').grid(row=2,column=0,sticky='e') # create cal factor label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.PT_cal_factor_tk,state='readonly').grid(row=2,column=1,sticky='w') # display calibration factor
            tk.Label(self.param_frame_calibration_tab,text="Zero Offset (psi):").grid(row=3,column=0,sticky='e') # create zero offset label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.PT_cal_zero_tk,state='readonly').grid(row=3,column=1,sticky='w') # display zero offset
            tk.Label(self.param_frame_calibration_tab,text='Standard Deviation (psi):').grid(row=4,column=0,sticky='e') # create standard deviation label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.PT_cal_std_dev_tk,state='readonly').grid(row=4,column=1,sticky='w') # display standard deviation
            tk.Label(self.param_frame_calibration_tab,text='Linearity (%FSO):').grid(row=5,column=0,sticky='e') # create linearity label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.PT_cal_linearity_tk,state='readonly').grid(row=5,column=1,sticky='w') # display linearity
            tk.Label(self.param_frame_calibration_tab,text='R\u00b2:').grid(row=6,column=0,sticky='e') # create R^2 lable
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.PT_cal_R2_tk,state='readonly').grid(row=6,column=1,sticky='w') # display R2 value
        elif method=="I/P Transducer":
            # ===== Plot Calibration Data =====
            self.plot_calibration_data(file_path=self.filename,is_file_loaded=True) # plot calibration data,loading file
            # ===== Update Text Variables =====
            self.IP_cal_factor_tk.set(round(self.IP_cal_factor,9)) # set tk text variable to its new value
            self.IP_cal_zero_tk.set(round(self.IP_cal_zero,4)) # set tk text variable to its new value
            self.IP_cal_std_dev_tk.set(round(self.IP_cal_std_dev,4)) # set tk text variable to its new value
            self.IP_cal_linearity_tk.set(round(self.IP_cal_linearity,4)) # set tk text variable to its new value
            self.IP_cal_R2_tk.set(round(self.IP_cal_R2,4)) # set tk text variable to its new value
            # ===== Populate Statistics =====
            tk.Label(self.param_frame_calibration_tab,text='Calibration Factor (input psi/output psi):').grid(row=2,column=0,sticky='e') # create cal factor label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.IP_cal_factor_tk,state='readonly').grid(row=2,column=1,sticky='w') # display calibration factor
            tk.Label(self.param_frame_calibration_tab,text="Zero Offset (psi):").grid(row=3,column=0,sticky='e') # create zero offset label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.IP_cal_zero_tk,state='readonly').grid(row=3,column=1,sticky='w') # display zero offset
            tk.Label(self.param_frame_calibration_tab,text='Standard Deviation (psi):').grid(row=4,column=0,sticky='e') # create standard deviation label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.IP_cal_std_dev_tk,state='readonly').grid(row=4,column=1,sticky='w') # display standard deviation
            tk.Label(self.param_frame_calibration_tab,text='Linearity (%FSO):').grid(row=5,column=0,sticky='e') # create linearity label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.IP_cal_linearity_tk,state='readonly').grid(row=5,column=1,sticky='w') # display linearity
            tk.Label(self.param_frame_calibration_tab,text='R\u00b2:').grid(row=6,column=0,sticky='e') # create R^2 lable
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.IP_cal_R2_tk,state='readonly').grid(row=6,column=1,sticky='w') # display R2 value
        elif method=="Frame Compliance":
            # ===== Plot Calibration Data =====
            self.plot_calibration_data(file_path=self.filename,is_file_loaded=True) # clear existing plot, add old data to group plot
            tk.Label(self.param_frame_calibration_tab,text="Left Snip:").grid(row=3,column=0,sticky='e') # create left snip label
            self.left_snip_entry_FC = tk.Entry(self.param_frame_calibration_tab,textvariable=self.left_snip_FC_tk) # create left snip entry
            self.left_snip_entry_FC.grid(row=3,column=1,sticky='w') # layout left snip entry
            self.left_snip_entry_FC.bind("<Return>",lambda event: self.plot_calibration_data(self.filename,is_file_loaded=True)) # re-plot data after pressing enter
            self.left_snip_entry_FC.bind("<FocusOut>",lambda event: self.plot_calibration_data(self.filename,is_file_loaded=True)) # re-plot data after deselcting entry
            tk.Label(self.param_frame_calibration_tab,text="Right Snip:").grid(row=4,column=0,sticky='e') # create right snip label
            self.right_snip_entry_FC = tk.Entry(self.param_frame_calibration_tab,textvariable=self.right_snip_FC_tk) # create right snip entry
            self.right_snip_entry_FC.grid(row=4,column=1,sticky='w') # layout right snip entry
            self.right_snip_entry_FC.bind("<Return>",lambda event: self.plot_calibration_data(self.filename,is_file_loaded=True)) # re-plot data after pressing enter
            self.right_snip_entry_FC.bind("<FocusOut>",lambda event: self.plot_calibration_data(self.filename,is_file_loaded=True)) # re-plot data after deselcting entry
            tk.Label(self.param_frame_calibration_tab,text='Slope (in/lb):').grid(row=5,column=0,sticky='e') # create slope label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.FC_slope_tk,state='readonly').grid(row=5,column=1,sticky='w') # create slope entry
            tk.Label(self.param_frame_calibration_tab,text='Zero (in):').grid(row=6,column=0,sticky='e') # create zero label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.FC_zero_tk,state='readonly').grid(row=6,column=1,sticky='w') # create zero entry
            tk.Label(self.param_frame_calibration_tab,text='R\u00b2:').grid(row=7,column=0,sticky='e') # create r2 label
            tk.Entry(self.param_frame_calibration_tab,textvariable=self.FC_r2_tk,state='readonly').grid(row=7,column=1,sticky='w') # create r2 entry
            self.record_slope_button_FC = tk.Button(self.param_frame_calibration_tab,text="Record Slope",command=self.save_FC_data,width=18) # create save data button
            self.record_slope_button_FC.grid(row=0,column=3,sticky='w') # layout save data button

    def run_analysis(self):
        #try:
        method = self.analysis_test_type_analysis_tk.get() # define analysis method
        if method=="Modulus Check":
            # ===== Run Analysis =====
            funAnalyze = analyize(path=self.analysis_file_path,
                                thickness=self.gauge_thickness_tk.get(),
                                g_width=self.gauge_width_tk.get(),
                                t_width=None,
                                D1=None,
                                gauge_length_initial=None,
                                CH_hole2mark_initial=None,
                                AC_hole2mark_initial=None,
                                CH_hole2mark_final=None,
                                AC_hole2mark_final=None,
                                base_dir=self.base_dir,
                                log_callback=self.log_command)
            self.log_command("Analysis started...") # log start of data analysis
            funAnalyze.read_data() # read data from file
            elastic_modulus,LR_start,LR_end = funAnalyze.calculate_elastic_modulus() # calculate elastic modulus
            self.elastic_stress,self.elastic_strain = funAnalyze.elastic_conversion() # run elastic conversion
            # ===== Set Values =====
            self.elastic_modulus_tk.set(elastic_modulus*(10**-6)) # set tk variable elastic modulus
            self.linear_regression_elastic_start_tk.set(LR_start) # set linear regression start value
            self.linear_regression_elastic_end_tk.set(LR_end) # set linear regression end value
            self.on_selection_change_analysis_test_type_analysis_tab() # update values
            # ===== Enable Widgets to Save Data =====
            self.file_name_analysis_entry.config(state="normal") # enable file name entry
            self.save_analysis_data_button['command']=lambda: (self.select_folder(),self.save_analysis_data()) # select folder to save data to, and save that data
            self.save_analysis_data_button.config(state='normal') # enable save data button
            self.log_command("Analysis completed...") # log completion of data analysis
        elif method=="Tensile":
            ''' elastic stress and strain will need joined with plastic values before returning to save data for tensile
            they must be the same length as the rest of the data'''
            # ===== Run Analysis =====
            funAnalyze = analyize(path=self.analysis_file_path,
                                thickness=self.gauge_thickness_tk.get(),
                                g_width=self.gauge_width_tk.get(),
                                t_width=self.tab_width_tk.get(),
                                D1=self.hole_diameter_tk.get(),
                                gauge_length_initial=self.gauge_length_tk.get(),
                                CH_hole2mark_initial=self.CH_hole2mark_initial_tk.get(),
                                AC_hole2mark_initial=self.AC_hole2mark_initial_tk.get(),
                                CH_hole2mark_final=self.CH_hole2mark_final_tk.get(),
                                AC_hole2mark_final=self.AC_hole2mark_final_tk.get(),
                                base_dir=self.base_dir,
                                log_callback=self.log_command)
            self.log_command("Analysis started...") # log start of data analysis
            # ===== Run Analysis =====
            funAnalyze.read_data() # read data from file
            elastic_modulus,LR_start,LR_end = funAnalyze.calculate_elastic_modulus() # calculate elastic modulus
            self.stress,self.strain,self.elastic_modulus,self.yield_stress,self.offset_yield_stress,self.UTS,self.UTS_strain = funAnalyze.total_conversion() # run total conversion
            # ===== Set Values =====
            self.elastic_modulus_tk.set(round(elastic_modulus*(10**-6),2)) # set tk variable elastic modulus
            self.yield_strength_tk.set(round(self.yield_stress*(10**-3),2)) # set yield stress variable
            self.offset_yield_strength_tk.set(round(self.offset_yield_stress*(10**-3),2)) # set offset yield stress variable
            self.UTS_tk.set(round(self.UTS*(10**-3),2)) # set UTS variable
            self.UTS_strain_tk.set(round(self.UTS_strain*100,2)) # set UTS strain variable
            self.linear_regression_elastic_start_tk.set(LR_start) # set linear regression start value
            self.linear_regression_elastic_end_tk.set(LR_end) # set linear regression end value
            self.on_selection_change_analysis_test_type_analysis_tab() # update values
            # ===== Enable Widgets to Save Data =====
            self.file_name_analysis_entry.config(state="normal") # enable file name entry
            self.save_analysis_data_button['command']=lambda: (self.select_folder(),self.save_analysis_data()) # select folder to save data to, and save that data
            self.save_analysis_data_button.config(state='normal') # enable save data button
            self.log_command("Analysis completed...") # log completion of data analysis
            pass
        elif method=="Creep":
            pass
        elif method=="Fatigue":
            pass
        # except AttributeError:
        #     self.log_command("Load a file to analyize and try again...")

    def plot_calibration_data(self,file_path,is_file_loaded=False):
        # ===== Get ComboBox Method =====
        method = self.calibration_method.get() # get current calibration method
        # ===== Plot =====
        if method=="LVDT":
            # ===== Read and Format Data =====
            # ----- Plot Raw Data (displacement vs voltage) -----
            data = pd.read_csv(file_path) # data frame
            num_lines = len(data) # number of lines
            displacement_calibration_data = data['displacement'].to_numpy() # convert displacement data to numpy array
            count_calibration_data = data['counts'].to_numpy() # convert displacement data to numpy array
            self.cal_conv_ax.cla() # clear old data
            self.cal_lin_ax.cla() # clear old data

            if num_lines>=2: # plot before and aftercalibration is complete
                m,b = np.polyfit(displacement_calibration_data,count_calibration_data,1) # 1st degree fit
                linear_fit_x = np.linspace(np.min(displacement_calibration_data),np.max(displacement_calibration_data),len(displacement_calibration_data)) # two point x data array for linear fit
                linear_fit_x_counts = np.linspace(np.min(count_calibration_data),np.max(count_calibration_data),len(count_calibration_data)) # two point x data array for linear fit
                linear_fit_y = (m*linear_fit_x)+b # y=mx+b
                self.cal_lin_ax.plot(linear_fit_x, linear_fit_y,color='r',label='Linear Fit') # plot x and y data
                self.cal_lin_ax.set_ylim(np.min([np.min(count_calibration_data),np.min(linear_fit_y)]),np.max([np.max(count_calibration_data),np.max(linear_fit_y)])) # set y limits
                self.cal_lin_ax.set_xlim(np.min([np.min(displacement_calibration_data),np.min(linear_fit_x)]),np.max([np.max(displacement_calibration_data),np.max(linear_fit_x)])) # set y limits
            self.cal_lin_ax.scatter(displacement_calibration_data,count_calibration_data,color='b',label='Measured')
            self.cal_lin_ax.set_title('LVDT Calibration Data') # set title
            self.cal_lin_ax.set_ylabel('Counts') # set x label
            self.cal_lin_ax.set_xlabel('Displacement (in)') # set y label
            self.cal_lin_ax.legend() # enable legend
            self.cal_plot_lin.draw_idle() # redraw canvas
            self.log_command('LVDT calibration data plotted succesfully...') # log LVDT plotting
            try:
                calibration_status = self.calibration_is_complete # check if calibration has been ran
            except AttributeError: # calibration hasn't ran
                calibration_status = True # calibration is already up to date
            if calibration_status or is_file_loaded: # if calibration is complete, plot
                # ===== Statistics =====
                try:
                # ----- Calibration Factor -----
                    LVDT_cal_data = pd.read_csv("LVDT_calibration_log.csv") # read calibration log
                    self.LVDT_cal_factor = float(LVDT_cal_data['slope'].iloc[-1]) # pull most recent cal factor, convert from str to float
                # ----- Zero -----
                    self.LVDT_cal_zero = float(LVDT_cal_data['zero'].iloc[-1]) # pull most recent zero, convert from str to float
                # ----- Convert Counts to Inches -----
                    measured_displacement_calibration_data = (self.LVDT_cal_factor*count_calibration_data) + self.LVDT_cal_zero # convert voltage to displacement (inches)
                    converted_slope = np.polyfit(displacement_calibration_data,measured_displacement_calibration_data,1) # find the slope of ideal vs actual data
                    linear_fit_y_converted = (converted_slope[0]*displacement_calibration_data) + converted_slope[1] # linear fit of converted data (ideal vs actual)
                except FileNotFoundError:
                    self.log_command("No LVDT calibration log available, cannot calculate calibration factor and zero...")
                # ----- R2 -----
                res = measured_displacement_calibration_data-linear_fit_y_converted # calculate residuals
                ss_res = np.sum(res**2) # sum of squared residuals
                ss_tot = np.sum((measured_displacement_calibration_data-measured_displacement_calibration_data.mean())**2) # total sum of squares
                self.LVDT_cal_R2 = 1-(ss_res/ss_tot) # calculate r2
                # ----- Linearity -----
                fsr = displacement_calibration_data.max() - displacement_calibration_data.min() # full scale range
                max_dev = np.max(np.abs(res)) # maximum absolute residual
                self.LVDT_cal_linearity = max_dev / fsr * 100 # as % of FSR
                # ----- Standard Deviation -----
                self.LVDT_cal_std_dev = np.std(res) # calculate standard deviation of residuals
                # ----- Plotting Inches -----
                self.cal_conv_ax.plot(displacement_calibration_data, linear_fit_y_converted,color='r',label='Linear Fit') # plot x and y data
                self.cal_conv_ax.set_ylim(np.min(linear_fit_y_converted),np.max(linear_fit_y_converted)) # set y limits
                self.cal_conv_ax.set_xlim(np.min(displacement_calibration_data),np.max(displacement_calibration_data)) # set y limits
                self.cal_conv_ax.scatter(displacement_calibration_data,measured_displacement_calibration_data,color='b',label='Measured')
                self.cal_conv_ax.set_title('LVDT Calibration Data') # set title
                self.cal_conv_ax.set_xlabel('Input Displacement (in)') # set x label
                self.cal_conv_ax.set_ylabel('Measured Displacement (in)') # set y label
                self.cal_conv_ax.legend() # enable legend
                self.cal_plot_conv.draw_idle() # redraw canvas
            else:
                pass
        elif method=="Pressure Transducer":
            # ===== Read and Format Data =====
            # ----- Plot Raw Data (pressure vs counts) -----
            data = pd.read_csv(file_path) # data frame
            num_lines = len(data) # number of lines
            pressure_calibration_data = data['pressure'].to_numpy() # convert pressure data to numpy array
            count_calibration_data = data['counts'].to_numpy() # convert count data to numpy array
            self.cal_conv_ax.cla() # clear old data
            self.cal_lin_ax.cla() # clear old data

            if num_lines>=2: # plot before and after calibration is complete
                m,b = np.polyfit(pressure_calibration_data,count_calibration_data,1) # 1st degree fit
                linear_fit_x = np.linspace(np.min(pressure_calibration_data),np.max(pressure_calibration_data),len(pressure_calibration_data)) # two point x data array for linear fit
                linear_fit_y = (m*linear_fit_x)+b # y=mx+b
                self.cal_lin_ax.plot(linear_fit_x, linear_fit_y,color='r',label='Linear Fit') # plot x and y data
                self.cal_lin_ax.set_ylim(np.min([np.min(count_calibration_data),np.min(linear_fit_y)]),np.max([np.max(count_calibration_data),np.max(linear_fit_y)])) # set y limits
                self.cal_lin_ax.set_xlim(np.min([np.min(pressure_calibration_data),np.min(linear_fit_x)]),np.max([np.max(pressure_calibration_data),np.max(linear_fit_x)])) # set y limits
            self.cal_lin_ax.scatter(pressure_calibration_data,count_calibration_data,color='b',label='Measured')
            self.cal_lin_ax.set_title('Pressure Transducer Calibration Data') # set title
            self.cal_lin_ax.set_ylabel('Counts') # set y label
            self.cal_lin_ax.set_xlabel('Pressure (psi)') # set x label
            self.cal_lin_ax.legend() # enable legend
            self.cal_plot_lin.draw_idle() # redraw canvas
            self.log_command('Pressure transducer calibration data plotted succesfully...') # log LVDT plotting
            try:
                calibration_status = self.calibration_is_complete # check if calibration has been ran
            except AttributeError: # calibration hasn't ran
                calibration_status = True # calibration is already up to date
            if calibration_status or is_file_loaded: # if calibration is complete, plot
                # ===== Statistics =====
                try:
                # ----- Calibration Factor -----
                    PT_cal_data = pd.read_csv("PT_calibration_log.csv") # read calibration log
                    self.PT_cal_factor = float(PT_cal_data['slope'].iloc[-1]) # pull most recent cal factor, convert from str to float
                # ----- Zero -----
                    self.PT_cal_zero = float(PT_cal_data['zero'].iloc[-1]) # pull most recent zero, convert from str to float
                # ----- Convert Counts to psi -----
                    measured_pressure_calibration_data = (self.PT_cal_factor*count_calibration_data) + self.PT_cal_zero # convert counts(voltage) to pressure (psi)
                    converted_slope = np.polyfit(pressure_calibration_data,measured_pressure_calibration_data,1) # slope of converted data
                    linear_fit_y_converted = (converted_slope[0]*measured_pressure_calibration_data) + converted_slope[1] # linear fit between ideal (x) and measured (y) pressure
                except FileNotFoundError:
                    self.log_command("No pressure transducer calibration log available, cannot calculate calibration factor and zero...")
                # ----- R2 -----
                res = measured_pressure_calibration_data-linear_fit_y_converted # calculate residuals
                ss_res = np.sum(res**2) # sum of squared residuals
                ss_tot = np.sum((measured_pressure_calibration_data-measured_pressure_calibration_data.mean())**2) # total sum of squares
                self.PT_cal_R2 = 1-(ss_res/ss_tot) # calculate r2
                # ----- Linearity -----
                fsr = pressure_calibration_data.max() - pressure_calibration_data.min() # full scale range
                max_dev = np.max(np.abs(res)) # maximum absolute residual
                self.PT_cal_linearity = max_dev / fsr * 100 # as % of FSR
                # ----- Standard Deviation -----
                self.PT_cal_std_dev = np.std(res) # calculate standard deviation of residuals
                # ----- Plotting Pressure -----
                self.cal_conv_ax.plot(pressure_calibration_data, linear_fit_y_converted,color='r',label='Linear Fit') # plot x and y data
                self.cal_conv_ax.set_ylim(np.min(linear_fit_y_converted),np.max(linear_fit_y_converted)) # set y limits
                self.cal_conv_ax.set_xlim(np.min(pressure_calibration_data),np.max(pressure_calibration_data)) # set x limits
                self.cal_conv_ax.scatter(pressure_calibration_data,measured_pressure_calibration_data,color='b',label='Measured')
                self.cal_conv_ax.set_title('Pressure Transducer Calibration Data') # set title
                self.cal_conv_ax.set_xlabel('Input Pressure (psi)') # set x label
                self.cal_conv_ax.set_ylabel('Calibrated Transducer Pressure (psi)') # set y label
                self.cal_conv_ax.legend() # enable legend
                self.cal_plot_conv.draw_idle() # redraw canvas
        elif method=="I/P Transducer":
            # ===== Read and Format Data =====
            # ----- Plot Raw Data (input pressure vs output pressure) -----
            data = pd.read_csv(file_path) # data frame
            num_lines = len(data) # number of lines
            input_pressure_calibration_data = data['input pressure'].to_numpy() # convert input pressure data to numpy array
            output_pressure_calibration_data = data['output pressure'].to_numpy() # convert output pressure data to numpy array
            self.cal_conv_ax.cla() # clear old data
            self.cal_lin_ax.cla() # clear old data

            if num_lines>=2: # plot before and after calibration is complete
                m,b = np.polyfit(input_pressure_calibration_data,output_pressure_calibration_data,1) # 1st degree fit
                linear_fit_x = np.linspace(np.min(input_pressure_calibration_data),np.max(input_pressure_calibration_data),len(input_pressure_calibration_data)) # two point x data array for linear fit
                linear_fit_y = (m*linear_fit_x)+b # y=mx+b
                self.cal_lin_ax.plot(linear_fit_x, linear_fit_y,color='r',label='Linear Fit') # plot x and y data
                self.cal_lin_ax.set_ylim(np.min([np.min(output_pressure_calibration_data),np.min(linear_fit_y)]),np.max([np.max(output_pressure_calibration_data),np.max(linear_fit_y)])) # set y limits
                self.cal_lin_ax.set_xlim(np.min([np.min(input_pressure_calibration_data),np.min(linear_fit_x)]),np.max([np.max(input_pressure_calibration_data),np.max(linear_fit_x)])) # set y limits
            self.cal_lin_ax.scatter(input_pressure_calibration_data,output_pressure_calibration_data,color='b',label='Measured')
            self.cal_lin_ax.set_title('I/P Transducer Calibration Data') # set title
            self.cal_lin_ax.set_ylabel('Output Pressure (psi)') # set y label
            self.cal_lin_ax.set_xlabel('Input Pressure (psi)') # set x label
            self.cal_lin_ax.legend() # enable legend
            self.cal_plot_lin.draw_idle() # redraw canvas
            self.log_command('I/P transducer calibration data plotted succesfully...') # log I/P plotting
            try:
                calibration_status = self.calibration_is_complete # check if calibration has been ran
            except AttributeError: # calibration hasn't ran
                calibration_status = True # calibration is already up to date
            if calibration_status or is_file_loaded: # if calibration is complete, plot
                # ===== Statistics =====
                try:
                # ----- Calibration Factor -----
                    IP_cal_data = pd.read_csv("IP_calibration_log.csv") # read calibration log
                    self.IP_cal_factor = float(IP_cal_data['slope'].iloc[-1]) # pull most recent cal factor, convert from str to float
                # ----- Zero -----
                    self.IP_cal_zero = float(IP_cal_data['zero'].iloc[-1]) # pull most recent zero, convert from str to float
                # ----- Convert output pressure to calibrated output pressure -----
                    calibrated_output_pressure_data = (self.IP_cal_factor*output_pressure_calibration_data) + self.IP_cal_zero # convert counts(voltage) to pressure (psi)
                    converted_slope = np.polyfit(input_pressure_calibration_data,calibrated_output_pressure_data,1) # slope of converted data
                    linear_fit_y_converted = (converted_slope[0]*input_pressure_calibration_data) + converted_slope[1] # linear fit between ideal (x) and measured (y) pressure
                except FileNotFoundError:
                    self.log_command("No I/P calibration log available, cannot calculate calibration factor and zero...")
                # ----- R2 -----
                res = calibrated_output_pressure_data-linear_fit_y_converted # calculate residuals
                ss_res = np.sum(res**2) # sum of squared residuals
                ss_tot = np.sum((calibrated_output_pressure_data-calibrated_output_pressure_data.mean())**2) # total sum of squares
                self.IP_cal_R2 = 1-(ss_res/ss_tot) # calculate r2
                # ----- Linearity -----
                fsr = input_pressure_calibration_data.max() - input_pressure_calibration_data.min() # full scale range
                max_dev = np.max(np.abs(res)) # maximum absolute residual
                self.IP_cal_linearity = max_dev / fsr * 100 # as % of FSR
                # ----- Standard Deviation -----
                self.IP_cal_std_dev = np.std(res) # calculate standard deviation of residuals
                # ----- Plotting Pressure -----
                self.cal_conv_ax.plot(input_pressure_calibration_data, linear_fit_y_converted,color='r',label='Linear Fit') # plot x and y data
                self.cal_conv_ax.set_ylim(np.min(linear_fit_y_converted),np.max(linear_fit_y_converted)) # set y limits
                self.cal_conv_ax.set_xlim(np.min(input_pressure_calibration_data),np.max(input_pressure_calibration_data)) # set x limits
                self.cal_conv_ax.scatter(input_pressure_calibration_data,calibrated_output_pressure_data,color='b',label='Measured')
                self.cal_conv_ax.set_title('I/P Calibration Data') # set title
                self.cal_conv_ax.set_xlabel('Input Pressure (psi)') # set x label
                self.cal_conv_ax.set_ylabel('Calibrated Ouput Pressure (psi)') # set y label
                self.cal_conv_ax.legend() # enable legend
                self.cal_plot_conv.draw_idle() # redraw canvas
        elif method=='Frame Compliance':
            # ===== Read,Format, and Plot Data =====
            data = pd.read_csv(file_path) # data frame
            force = data['force'].to_numpy() # convert force data to numpy array
            displacement = data['displacement'].to_numpy() # convert displacement data to numpy array
            if is_file_loaded==False:
                self.cal_lin_ax.plot(displacement,force,color='r') # plot x and y data
                self.cal_lin_ax.set_ylim(0,max(force)+50) # set y limits
                self.cal_lin_ax.set_xlim(np.min(displacement),max(displacement)+.002) # set x limits
                self.cal_lin_ax.set_title('Compliance') # set title
                self.cal_lin_ax.set_ylabel('Force (lb)') # set y label
                self.cal_lin_ax.set_xlabel('Displacement (in)') # set x label
                self.cal_plot_lin.draw_idle() # redraw canvas
                self.log_command('Compliance curve plotted succesfully...') # log compliance plotting
            # ===== Plot Full Curve =====
            if is_file_loaded==True: # if single test is complete
                self.cal_lin_ax.cla() # clear old data
                self.cal_conv_ax.cla() # clear old data
                # ===== Load Linear Fit Data and plot =====
                # try:
                #     os.chdir(self.base_dir) # change directory to base directory
                #     data = pd.read_csv('frame_compliance_log.csv') # read data from file
                #     loaded_slope = 1/(data['slope'].to_numpy()[-1]) # Get most recent slope, slope is in the form of displacement = F(force)
                #     loaded_zero = -loaded_slope*data['zero'].to_numpy()[-1] # get most recent zero, convert for plotting purposes
                #     linear_fit_y_loaded = (displacement*loaded_slope) + loaded_zero # create array of y values
                #     self.cal_lin_ax.plot(displacement,linear_fit_y_loaded,color='black',label="Previous Linear Fit") # plot linear fit
                #     self.cal_lin_ax.set_ylim(0,max(force)+50) # set y limits
                #     self.cal_lin_ax.set_xlim(np.min(displacement),max(displacement)+.002) # set x limits
                #     self.cal_lin_ax.set_title('Previous Compliance') # set title
                #     self.cal_lin_ax.set_ylabel('Force (lb)') # set y label
                #     self.cal_lin_ax.set_xlabel('Displacement (in)') # set x label
                #     log_exists = True # frame compliance log exists
                # except FileNotFoundError:
                #     log_exists = False # frame compliance log doesnt exists
                l_snip = self.left_snip_FC_tk.get() # get left snip value
                r_snip = self.right_snip_FC_tk.get() # get right snip value
                force_agg = np.array([]) # initialize snipped force aggregate variable
                displacement_agg = np.array([]) # initialize snipped displacement aggregate variable
            # ===== Snip Individual Tests and Plot =====
                start = 0 # define start of testing range
                n = 0 # number of tests counter
                for i in range(len(force)-1):
                    if abs(force[i+1]-force[i])>=100: # if the difference between two points is more than 100 i.e. a new data set
                        end = i # define end of testing range
                        if l_snip>0 or r_snip>0:
                            n += 1 # increase counter
                            temp_force = force[(start+l_snip):(end-r_snip)] # snip force data
                            force_agg = np.append(force_agg,temp_force) # append snipped force data
                            temp_displacement = displacement[(start+l_snip):(end-r_snip)] # snip displacement data
                            displacement_agg = np.append(displacement_agg,temp_displacement) # append snipped displacement data
                            self.cal_conv_ax.plot(temp_displacement,temp_force,color='red',label=f'Test {n}') # plot data
                            # if log_exists:
                            #     self.cal_lin_ax.plot(displacement[start:end],force[start:end],label=f'Test {n}') # plot all data once on load
                        else:
                            n += 1 # increase counter
                            force_agg = np.append(force_agg,force[start:end]) # reassign variable name
                            displacement_agg = np.append(displacement_agg,displacement[start:end]) # reassign variable name
                            self.cal_conv_ax.plot(displacement[start:end],force[start:end],label=f'Test {n}') # plot data
                            # if log_exists:
                            #     self.cal_lin_ax.plot(displacement[start:end],force[start:end],label=f'Test {n}') # plot all data once on load
                        start = i+1 # define start of next testing range
                if n>1:
                    # ===== Plot Last Test Values (no drop observed) =====
                    n+=1 # increase counter
                    if l_snip>0 or r_snip>0:
                        self.cal_conv_ax.plot(displacement[(start+l_snip):(-r_snip)],label=f'Test {n}') # plot data
                        # if log_exists:
                        #     self.cal_lin_ax.plot(displacement[start:],force[start:],label=f'Test {n}') # plot data
                    else:
                        self.cal_conv_ax.plot(displacement[start:],force[start:],label=f'Test {n}') # plot data
                        # if log_exists:
                        #     self.cal_lin_ax.plot(displacement[start:],force[start:],label=f'Test {n}') # plot data
                # ===== Calculate Slope and Statistics =====
                curv = np.polyfit(y=displacement_agg,x=force_agg,deg=1) # calculate linear fit curve
                slope = 1/curv[0] # get slope
                zero = -curv[1]*slope # get zero
                self.FC_slope_tk.set(round(1/slope,10)) # set slope value in entry
                self.FC_zero_tk.set(curv[1]) # set zero value
                # ----- Linear Fit -----
                linear_fit_y = (displacement_agg*slope) + zero # create array of y values
                # ----- R^2 -----
                res = force_agg-linear_fit_y # calculate residuals
                ss_res = np.sum(res**2) # sum of squared residuals
                ss_tot = np.sum((force_agg-force_agg.mean())**2) # total sum of squares
                self.FC_r2_tk.set(round(1-(ss_res/ss_tot),5)) # calculate r2
                # ===== Finish Plotting =====
                self.cal_conv_ax.plot(displacement_agg,linear_fit_y,color='blue',label='Linear Fit')
                self.cal_conv_ax.set_ylim(0,max(force)+50) # set y limits
                self.cal_conv_ax.set_xlim(min(displacement),max(displacement)+.002) # set x limits
                self.cal_conv_ax.set_title('Compliance') # set title
                self.cal_conv_ax.set_ylabel('Force (lb)') # set y label
                self.cal_conv_ax.set_xlabel('Displacement (in)') # set x label
                self.cal_conv_ax.legend(loc="lower right") # display plot legend
                #self.cal_lin_ax.legend(loc="lower right") # display plot legend
                self.cal_plot_conv.draw_idle() # redraw canvas
                self.cal_plot_lin.draw_idle() # redraw canvas
                self.log_command("Compliance curve plotted succesfully...") # log compliance plotting

    def plot_raw_test_data(self,file_path,test_method=None):
        if test_method=="MODcheck":
            # ===== Read and Format Data =====
            # ----- Plot Raw Data (force vs. displacement) -----
            data = pd.read_csv(file_path) # data frame
            force = data['force'].to_numpy() # convert data frame to numpy array
            displacement = data['displacement'].to_numpy() # convert data frame to numpy array
            self.pretest_fd_ax.cla() # clear old data
            self.pretest_fd_ax.plot(displacement,force,color='r') # plot x and y data
            self.pretest_fd_ax.set_ylim(0,np.max(force)+50) # set y limits
            self.pretest_fd_ax.set_xlim(0,np.max(displacement)+.01) # set x limits
            self.pretest_fd_ax.set_title('Modulus Check') # set title
            self.pretest_fd_ax.set_ylabel('Force (lb)') # set y label
            self.pretest_fd_ax.set_xlabel('Displacement (in)') # set x label
            self.pretest_fd_plot.draw_idle() # redraw canvas
            self.log_command('Modulus Check data plotted succesfully...') # log mod check plotting
        elif test_method=="tensile":
            # ===== Read and Format Data =====
            # ----- Plot Raw Data (force vs. displacement) -----
            data = pd.read_csv(file_path) # data frame
            force = data['force'].to_numpy() # convert data frame to numpy array
            displacement = data['displacement'].to_numpy() # convert data frame to numpy array
            self.test_fd_ax.cla() # clear old data
            self.test_fd_ax.plot(displacement,force,color='r') # plot x and y data
            self.test_fd_ax.set_ylim(0,np.max(force)+50) # set y limits
            self.test_fd_ax.set_xlim(0,np.max(displacement)+.01) # set x limits
            self.test_fd_ax.set_title('Tensile Test') # set title
            self.test_fd_ax.set_ylabel('Force (lb)') # set y label
            self.test_fd_ax.set_xlabel('Displacement (in)') # set x label
            self.test_fd_plot.draw_idle() # redraw canvas
            self.log_command('Tensile test data plotted succesfully...') # log tensile test plotting
        elif test_method=="creep":
            pass
        elif test_method=="fatigue":
            pass
        elif test_method=="tuning":
            # ===== Read and Format Data =====
            # ----- Plot Raw Data (force vs. displacement) -----
            data = pd.read_csv(file_path) # data frame
            displacement = data['displacement'].to_numpy() # convert data frame to numpy array
            time = data['time_'].to_numpy() # convert data frame to numpy array
            force = data['force'].to_numpy()[-1] # get last force value
            self.force_label_tuning_tab_tk.set(force) # set current force value
            self.tuning_fd_ax.cla() # clear old data
            self.tuning_fd_ax.plot(time,displacement,color='r') # plot x and y data
            self.tuning_fd_ax.set_ylim(0,np.max(displacement)+.001) # set y limits
            self.tuning_fd_ax.set_xlim(0,np.max(time)+2) # set x limits
            self.tuning_fd_ax.set_title('Stroke Rate Tuning') # set title
            self.tuning_fd_ax.set_ylabel('Displacement(in)') # set y label
            self.tuning_fd_ax.set_xlabel('Time(s)') # set x label
            self.tuning_fd_plot.draw_idle() # redraw canvas
            self.log_command('Tuning data plotted succesfully...') # log tensile test plotting

    def plot_test_data(self):
        # ===== Clear Axes =====
        self.analysis_ax.cla()
        self._col_map = {
                        "Force":              "force",
                        "Pressure":           "pressure",
                        "Displacement":       "displacement",
                        "Time":               "time_",
                        "Setpoint":           "setpoint",
                        "Temperature (CH1)":  "temp1",
                        "Temperature (CH2)":  "temp2",
                        "Temperature (CH3)":  "temp3",
                        "Temperature (CH4)":  "temp4",
                        "Stress":             "stress",
                        "Strain":             "strain",
                        "Cycles":             "cycles",} # map axes to data columns

        # ===== Itterate over each 
        for i, filepath in enumerate(self.plot_file_paths):
            if self.toggled_plots_array[i].get()==True: # if plot is enabled
                if not filepath:
                    continue  # skip empty rows
                file_ext = os.path.splitext(filepath)[1].lower()
                try:
                    if file_ext=='.csv':
                        df = pd.read_csv(filepath) # read new file type .csv
                    elif file_ext=='.txt':
                        df = pd.read_csv(filepath,sep=r'\s+',header=None,names=["force",'pressure','displacement','setpoint','control','temp1','temp2','temp3','temp4','time']) # load old file type
                except Exception as e:
                    self.log_command(f"Failed to load {filepath}: {e}")
                    continue
                # ===== Get Plotting Axes =====
                x_axes_unmapped = self.x_axis_cbs_array[i].get()
                y_axes_unmapped = self.y_axis_cbs_array[i].get()
                x_axes = self._col_map.get(x_axes_unmapped)
                y_axes = self._col_map.get(y_axes_unmapped)
                # ===== Load Data =====
                if x_axes not in df.columns or y_axes not in df.columns:
                    self.log_command(f"Columns {x_axes}/{y_axes} not in {filepath}")
                    continue
                x = df[x_axes].to_numpy() # convert data into numpy array
                y = df[y_axes].to_numpy() # convert data into numpy array
                # ===== Filter Data =====
                if self.enable_filtering_analysis_tab_tk.get()==True: # if filtering is enabled
                    # ----- Check Moving Average Entry -----
                    try:
                        x_moving_avg = int(self.x_filter_entry_array[i].get()) # get size of moving average  
                    except ValueError:
                        x_moving_avg = 1 # set moving average=1 (no moving average) if a non-integer value is entered
                    try:
                        y_moving_avg = int(self.y_filter_entry_array[i].get()) # get size of moving average
                    except ValueError:
                        y_moving_avg = 1 # set moving average=1 (no moving average) if a non-integer value is entered
                    # ----- Execute Moving Average -----
                    x_kernel = np.ones(x_moving_avg) / x_moving_avg # find the average of the given number of points
                    y_kernel = np.ones(y_moving_avg) / y_moving_avg # find the average of the given number of points
                    x = np.convolve(x, x_kernel, mode='same') # perform moving average on data with edge effects
                    y = np.convolve(y, y_kernel, mode='same') # perform moving average on data with edge effects
                # ===== Shift Axes =====
                if self.enable_x_shift_analysis_tab_tk.get()==True: # if x shift is enabled
                    try:
                        x += float(self.x_shift_entry_array[i].get()) # get x shift and adjust
                    except ValueError:
                        pass # nothing has been entered
                if self.enable_y_shift_analysis_tab_tk.get()==True: # if y shift is enabled
                    try:
                        y += float(self.y_shift_entry_array[i].get()) # get y shift and adjust
                    except ValueError:
                        pass # nothing has been entered
                # ===== Plot =====
                # ----- Enable Plot Labels -----
                if self.enable_plot_labels_analysis_tab_tk.get()==True:
                    lbl = self.plot_entry_array[i].get() # assign plot label
                else:
                    lbl = None # label is none type
                # ----- Enable Snipping -----
                if self.enable_snip_analysis_tab_tk.get()==True:
                    try:
                        l_snip = int(self.left_snip_entry_array[i].get()) # define left snip value
                    except ValueError:
                        l_snip = 0 # no left sniping - 0 is first index
                    try:
                        r_snip = int(self.right_snip_entry_array[i].get()) # define right snip value
                    except ValueError:
                        r_snip = 1 # no right snipping - -1 is last index
                    self.analysis_ax.plot(x[l_snip:-r_snip],y[l_snip:-r_snip],label=lbl) # plot snipped figure
                else:
                    self.analysis_ax.plot(x,y,label=lbl) # plot unsnipped figure
            # ===== Finalize Figure =====
            if self.enable_axes_labels_analysis_tab_tk.get()==True: # if axes labels are enabled
                self.analysis_ax.set_xlabel(self.x_label.get()) # set x label
                self.analysis_ax.set_ylabel(self.y_label.get()) # set y label
                self.analysis_ax.set_title(self.title.get())
            if self.enable_plot_labels_analysis_tab_tk.get()==True:
                self.analysis_ax.legend() # create legend if labels are applied
            self.analysis_ax.grid(True)
            self.analysis_plot.draw_idle()
        self.log_command("Data plotted succesfully...")

    def toggle_axes_selection_frame(self):
        if self.plot_axes_frame_analysis_tab.winfo_ismapped():
            # hide it
            self.plot_axes_frame_analysis_tab.grid_remove()
            self.axes_toggle_btn.configure(text="▸")  # right‐arrow = “expand”
        else:
            # show it again
            self.plot_axes_frame_analysis_tab.grid()
            self.axes_toggle_btn.configure(text="▾")
    
    def toggle_analysis_frame(self):
        if self.left_middle_frame_analysis.winfo_ismapped():
            # hide it
            self.left_middle_frame_analysis.grid_remove()
            self.analysis_toggle_btn.configure(text="▸")  # right‐arrow = “expand”
            self.middle_frame_analysis.columnconfigure(0,weight=0)
        else:
            # show it again
            self.left_middle_frame_analysis.grid()
            self.analysis_toggle_btn.configure(text="▾")
            self.middle_frame_analysis.columnconfigure(0,weight=1)

    def on_selection_change_pre_test_tab(self,event=None):
        #clear out old widgets (labels)
        for child in self.param_frame_pre_test_tab.winfo_children():
            child.destroy()
        # ===== Get ComboBox Method =====
        method = self.test_box_pretest_tab.get() # get current test method
        # ===== Calibration Tab =====
        # ----- Layout Sizes -----
        #button_width = 18 # define button width
        entry_width = 40 # define entry width
        if method=="Modulus Check":
            # ----- Maximum Load ------
            tk.Label(self.middle_frame_pretest, text='Maximum Load (lb):').grid(row=1,column=0,sticky='e') # create label for maximum load input
            self.max_load_entry_pretest_tab = tk.Entry(self.middle_frame_pretest, textvariable=self.max_load,width=entry_width) # create entry box for file name
            self.max_load_entry_pretest_tab.grid(row=1, column=1, sticky="w") # layout max load entry box
            # ----- Load Rate -----
            tk.Label(self.middle_frame_pretest, text='Load Rate (lb/s):').grid(row=2,column=0,sticky='e') # create label for maximum load input
            self.load_rate_entry_pretest_tab = tk.Entry(self.middle_frame_pretest, textvariable=self.load_rate,width=entry_width) # create entry box for file name
            self.load_rate_entry_pretest_tab.grid(row=2, column=1, sticky="w") # layout load rate entry box

    def on_selection_change_test_tab(self,event=None):
        
        #clear out old widgets (labels)
        for child in self.param_frame_test_tab.winfo_children():
            child.destroy()
        # ===== ComboBox Methods =====
        method = self.test_box_test_tab.get()
        # ===== Define Text Variables =====
        self.waveform = tk.StringVar(value="Sinusoidal") # define waveform as a string variable
        self.frequency = tk.DoubleVar() # define frequency as a float variable
        # ===== Test Tab =====
        #----- Test Specific Metric -----
        if method =="Tensile":
            # ----- Tensile Label & Entry -----
            tk.Label(self.param_frame_test_tab, text="Stroke Rate (in/min):").grid(row=0, column=2, sticky="e") # create stroke rate label
            tk.Entry(self.param_frame_test_tab, textvariable=self.stroke_rate_tk,width=40).grid(row=0, column=3, sticky="w") # create entry box for stroke rate
        elif method=="Creep":
            # ----- Creep Label & Entry -----
            tk.Label(self.param_frame_test_tab, text="Applied Constant Stress:").grid(row=0, column=2, sticky="e") # create stroke rate label
            tk.Entry(self.param_frame_test_tab, textvariable=self.stroke_rate_tk,width=40).grid(row=0, column=3, sticky="w") # create entry box for applied constant stress
        elif method=="Fatigue":
            # ----- Fatigue Label, Entry and Drop-Down -----
            tk.Label(self.param_frame_test_tab, text="Frequency:").grid(row=0, column=2, sticky="e") # create frequency label
            tk.Entry(self.param_frame_test_tab, textvariable=self.frequency,width=40).grid(row=0, column=3, sticky="w") # create entry box for waveform

            tk.Label(self.param_frame_test_tab, text="Waveform:").grid(row=1, column=2, sticky="e") # create test method label, stick to the right side
            test_options_fatigue = ["Sinusoidal", "Triangular", "Square"] # list drop down items under "Test Method"
            self.test_box_test_tab_fatigue = ttk.Combobox(self.param_frame_test_tab, textvariable=self.waveform, values=test_options_fatigue, state="readonly") # create drop-down box
            self.test_box_test_tab_fatigue.grid(row=1, column=3, sticky="w") # layout drop box

    def on_selection_change_analysis_test_type_analysis_tab(self,event=None):
        combo_box_width = 15
        entry_width = 20
        button_width = 15
        # ===== Clear Old Widgets =====
        for child in self.left_middle_frame_analysis.winfo_children():
            child.destroy()
        # ===== Get Current Analysis Method =====
        method = self.analysis_test_type_analysis_tk.get() # define analysis method
        if method=="Modulus Check":
            # ===== Inputs =====
            tk.Label(self.left_middle_frame_analysis,text='Inputs',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=0,column=0,columnspan=4,sticky='ew') # create and layout header
            tk.Label(self.left_middle_frame_analysis,text='Gauge Width (in):').grid(row=1,column=0,sticky='e') # create gauge width label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.gauge_width_tk,width=entry_width).grid(row=1, column=1, sticky="w") # create entry box for gauge width
            tk.Label(self.left_middle_frame_analysis,text='Gauge Thickness (in):').grid(row=2,column=0,sticky='e') # create gauge thickness label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.gauge_thickness_tk,width=entry_width).grid(row=2,column=1,sticky='w') # create entry box for gauge thickness
            # ===== Outputs =====
            tk.Label(self.left_middle_frame_analysis,text='Results',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=3,column=0,columnspan=4,sticky='ew') # create and layout header
            tk.Label(self.left_middle_frame_analysis,text="Elastic Modulus (Msi):").grid(row=4,column=0,sticky='e') # create elastic modulus label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.elastic_modulus_tk,state='readonly',width=entry_width).grid(row=4, column=1, sticky="w") # create entry box for elastic modulus
            # ===== Statistics =====
            tk.Label(self.left_middle_frame_analysis,text='Linear Fit',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=5,column=0,columnspan=4,sticky='ew') # create and layout header
            tk.Label(self.left_middle_frame_analysis,text='R\u00b2:').grid(row=6,column=0,sticky='e') # create R^2 label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.linear_fit_R2_tk,state='readonly',width=entry_width).grid(row=6, column=1, sticky="w") # create entry box for elastic modulus
            tk.Label(self.left_middle_frame_analysis,text='Standard Deviation:').grid(row=7,column=0,sticky='e') # create and layout standard deviation label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.linear_fit_std_dev_tk,state='readonly',width=entry_width).grid(row=7, column=1, sticky="w") # create entry box for elastic modulus
            tk.Label(self.left_middle_frame_analysis,text='Linear Regression Start:').grid(row=8,column=0,sticky='e') # create linear regression start label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.linear_regression_elastic_start_tk,state='readonly',width=entry_width).grid(row=8,column=1,sticky='w') # create linear regression start entry
            tk.Label(self.left_middle_frame_analysis,text='Linear Regression End:').grid(row=9,column=0,sticky='e') # create linear regression start label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.linear_regression_elastic_end_tk,state='readonly',width=entry_width).grid(row=9,column=1,sticky='w') # create linear regression start entry
            # ===== Export Data =====
            tk.Label(self.left_middle_frame_analysis,text='File Name:').grid(row=10,column=0,sticky='e') # create and layout file name label
            self.file_name_analysis_entry = tk.Entry(self.left_middle_frame_analysis,textvariable=self.file_name_analysis_tab_tk,width=entry_width,state='disabled') # create file name entry
            self.file_name_analysis_entry.grid(row=10,column=1,sticky='w') # layout file name entry
            self.save_analysis_data_button = tk.Button(self.left_middle_frame_analysis,command=None,text='Export Data',state='disabled',width=button_width) # create export data button
            self.save_analysis_data_button.grid(row=10,column=2,sticky='w') # layout button
        elif method=="Tensile":
            # ===== Inputs =====
            tk.Label(self.left_middle_frame_analysis,text='Inputs',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=0,column=0,columnspan=4,sticky='ew') # create and layout header
            tk.Label(self.left_middle_frame_analysis,text='Gauge Width (in):').grid(row=1,column=0,sticky='e') # create gauge width label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.gauge_width_tk,width=entry_width).grid(row=1, column=1, sticky="w") # create entry box for gauge width
            tk.Label(self.left_middle_frame_analysis,text='Gauge Thickness (in):').grid(row=2,column=0,sticky='e') # create gauge thickness label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.gauge_thickness_tk,width=entry_width).grid(row=2,column=1,sticky='w') # create entry box for gauge thickness
            tk.Label(self.left_middle_frame_analysis,text='Tab Width (in):').grid(row=3,column=0,sticky='e') # create tab width label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.tab_width_tk,width=entry_width).grid(row=3,column=1,sticky='w') # create entry box for tab width
            tk.Label(self.left_middle_frame_analysis,text='Hole Diameter (in):').grid(row=4,column=0,sticky='e') # create hole diameter label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.hole_diameter_tk,width=entry_width).grid(row=4,column=1,sticky='w') # create hole diameter entry
            tk.Label(self.left_middle_frame_analysis,text='Marked Gauge Length(in):').grid(row=5,column=0,sticky='e') # create gauge lenth label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.gauge_length_tk,width=entry_width).grid(row=5,column=1,sticky='w') # create gauge length entry
            tk.Label(self.left_middle_frame_analysis,text='Initial (CH) - Hole-to-Mark (in):').grid(row=6,column=0,sticky='e') # create crosshead hole to mark label initial
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.CH_hole2mark_initial_tk,width=entry_width).grid(row=6,column=1,sticky='w') # create crosshead hole to mark initial length input
            tk.Label(self.left_middle_frame_analysis,text='Initial (AC) - Hole-to-Mark (in):').grid(row=7,column=0,sticky='e') # create actuator hole to mark label initial
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.AC_hole2mark_initial_tk,width=entry_width).grid(row=7,column=1,sticky='w') # create actuator hole to mark initial length input
            tk.Label(self.left_middle_frame_analysis,text='Final (CH) - Hole-to-Mark (in):').grid(row=8,column=0,sticky='e') # create crosshead hole to mark label final
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.CH_hole2mark_final_tk,width=entry_width).grid(row=8,column=1,sticky='w') # create crosshead hole to mark final length input
            tk.Label(self.left_middle_frame_analysis,text='Final (AC) - Hole-to-Mark (in):').grid(row=9,column=0,sticky='e') # create actuator hole to mark label final
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.AC_hole2mark_final_tk,width=entry_width).grid(row=9,column=1,sticky='w') # create actuator hole to mark final length input
            # ===== Outputs =====
            tk.Label(self.left_middle_frame_analysis,text='Results',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=10,column=0,columnspan=4,sticky='ew') # create and layout header
            tk.Label(self.left_middle_frame_analysis,text="Elastic Modulus (Msi):").grid(row=11,column=0,sticky='e') # create elastic modulus label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.elastic_modulus_tk,state='readonly',width=entry_width).grid(row=11, column=1, sticky="w") # create entry box for elastic modulus
            tk.Label(self.left_middle_frame_analysis,text="Yield Strength (ksi):").grid(row=12,column=0,sticky='e') # create yield strength label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.yield_strength_tk,state='readonly',width=entry_width).grid(row=12, column=1, sticky="w") # create entry box for yield strength
            tk.Label(self.left_middle_frame_analysis,text="0.2% Yield Strength (ksi):").grid(row=13,column=0,sticky='e') # create 0.2% yield strength label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.offset_yield_strength_tk,state='readonly',width=entry_width).grid(row=13, column=1, sticky="w") # create entry box for 0.2% yield strength
            tk.Label(self.left_middle_frame_analysis,text="Ultimate Tensile Strength (ksi):").grid(row=14,column=0,sticky='e') # create ultimate tensile strength label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.UTS_tk,state='readonly',width=entry_width).grid(row=14, column=1, sticky="w") # create entry box for ultimate tensile strength
            tk.Label(self.left_middle_frame_analysis,text="Strain at UTS (%):").grid(row=15,column=0,sticky='e') # create strain at UTS label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.UTS_strain_tk,state='readonly',width=entry_width).grid(row=15, column=1, sticky="w") # create entry box for strain at UTS
            # ===== Statistics =====
            tk.Label(self.left_middle_frame_analysis,text='Statistics',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=16,column=0,columnspan=4,sticky='ew') # create and layout header
            tk.Label(self.left_middle_frame_analysis,text='R\u00b2:').grid(row=17,column=0,sticky='e') # create R^2 label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.linear_fit_R2_tk,state='readonly',width=entry_width).grid(row=17, column=1, sticky="w") # create entry box for R2
            tk.Label(self.left_middle_frame_analysis,text='Standard Deviation:').grid(row=18,column=0,sticky='e') # create and layout standard deviation label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.linear_fit_std_dev_tk,state='readonly',width=entry_width).grid(row=18, column=1, sticky="w") # create entry box for standard deviation
            tk.Label(self.left_middle_frame_analysis,text='Linear Regression Start:').grid(row=19,column=0,sticky='e') # create linear regression start label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.linear_regression_elastic_start_tk,state='readonly',width=entry_width).grid(row=19,column=1,sticky='w') # create linear regression start entry
            tk.Label(self.left_middle_frame_analysis,text='Linear Regression End:').grid(row=20,column=0,sticky='e') # create linear regression start label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.linear_regression_elastic_end_tk,state='readonly',width=entry_width).grid(row=20,column=1,sticky='w') # create linear regression start entry
            tk.Label(self.left_middle_frame_analysis,text='Sample Rate (SPS):').grid(row=21,column=0,sticky='e') # create sample rate label
            tk.Entry(self.left_middle_frame_analysis,textvariable=self.sample_rate_tk,state='readonly',width=entry_width).grid(row=19, column=1, sticky="w") # create entry box for elastic modulus
            # ===== Export Data =====
            tk.Label(self.left_middle_frame_analysis,text='File Name:').grid(row=22,column=0,sticky='e') # create and layout file name label
            self.file_name_analysis_entry = tk.Entry(self.left_middle_frame_analysis,textvariable=self.file_name_analysis_tab_tk,width=entry_width,state='disabled') # create file name entry
            self.file_name_analysis_entry.grid(row=22,column=1,sticky='w') # layout file name entry
            self.save_analysis_data_button = tk.Button(self.left_middle_frame_analysis,command=None,text='Export Data',state='disabled',width=button_width) # create export data button
            self.save_analysis_data_button.grid(row=22,column=2,sticky='w') # layout button
        elif method=="Creep":
            pass
        elif method=="Fatigue":
            pass

    def on_selection_change_num_plots_analysis_tab(self,event=None):
        combo_box_width = 15
        entry_width = 16
        entry_width_small = 4
        self.plot_options_analysis_tab = [""] # create empty drop down box - updated through "on_selection_change_analysis_tab"
        # ===== Clear Old Widgets =====
        for child in self.plot_axes_frame_analysis_tab.winfo_children():
            child.destroy()
        # ===== Initialize Variables =====
        num_plots = self.number_of_analysis_plots_tk.get() # get number of plots
        self.plot_file_location_array = [] # create array to house plot file locations
        self.x_axis_cbs_array = [] # create array to house combo boxes
        self.y_axis_cbs_array = [] # create array to house combo boxes
        self.plot_file_paths = [None]*num_plots # create array to store file paths for each plot
        self.load_buttons = [] # create array to configure button text
        self.plot_entry_array = [] # create array to store entrys for plot labels
        self.x_filter_entry_array = [] # create array to store entrys for filter values
        self.y_filter_entry_array = [] # create array to store entrys for filter values
        self.left_snip_entry_array = [] # create array to store snipping values for left side
        self.right_snip_entry_array = [] # create array to store snipping values for right side
        self.x_shift_entry_array = [] # create array to store x shift values
        self.y_shift_entry_array = [] # create array to store y shift values
        self.toggled_plots_array = [] # create array to store toggled plots
        # ===== Layout ComboBoxes,Labels, and Buttons =====
        for i in range(num_plots):
            # ----- Axes Combo Boxes -----
            tk.Label(self.plot_axes_frame_analysis_tab,text="Y Axis:").grid(row=i,column=0,sticky='e') # create x axis label
            y_axis_cbs = ttk.Combobox(self.plot_axes_frame_analysis_tab,
                                      values=self.plot_options_analysis_tab,
                                      state='readonly',
                                      width=combo_box_width) # create drop down box for x axis plot selection
            y_axis_cbs.grid(row=i,column=1,sticky='w') # layout x axis selection
            self.y_axis_cbs_array.append(y_axis_cbs) # append combobox to array

            tk.Label(self.plot_axes_frame_analysis_tab,text='X Axis:').grid(row=i,column=2,sticky='e') # create x axis label
            x_axis_cbs = ttk.Combobox(self.plot_axes_frame_analysis_tab,
                                      values=self.plot_options_analysis_tab,
                                      state='readonly',
                                      width=combo_box_width) # create drop down box for y axis plot selection
            x_axis_cbs.grid(row=i,column=3,sticky='w')
            self.x_axis_cbs_array.append(x_axis_cbs) # append combobox to array
            # ----- Load File Button -----
            btn = tk.Button(self.plot_axes_frame_analysis_tab,
                            text="Load File…",
                            width=12,
                            command=lambda idx=i: self.select_plot_file(idx))
            self.load_buttons.append(btn)
            # ===== Enable Plot Labels =====
            if self.enable_plot_labels_analysis_tab_tk.get()==True: # if enable plot labels
                plot_label = tk.Label(self.plot_axes_frame_analysis_tab,text='Label:') # create plot label
                plot_entry = tk.Entry(self.plot_axes_frame_analysis_tab,width=entry_width) # create temporary variable to store plot label
                self.plot_entry_array.append(plot_entry) # append entry to plot entry array
            # ===== Enable Filtering =====
            if self.enable_filtering_analysis_tab_tk.get()==True: # if filtering is enabled
                filter_label_x = tk.Label(self.plot_axes_frame_analysis_tab,text='Moving Average (X):') # create x axis filter label
                filter_entry_x = tk.Entry(self.plot_axes_frame_analysis_tab,width=entry_width_small) # create temporary variable to store filter value
                self.x_filter_entry_array.append(filter_entry_x) # append filter entry to filter entry array
                filter_label_y = tk.Label(self.plot_axes_frame_analysis_tab,text='Moving Average (Y):') # create y axis filter label
                filter_entry_y = tk.Entry(self.plot_axes_frame_analysis_tab,width=entry_width_small) # create temporary variable to store filter value
                self.y_filter_entry_array.append(filter_entry_y) # append filter entry to filter entry array
            # ===== Enable Snipping =====
            if self.enable_snip_analysis_tab_tk.get()==True: # if snipping is enabled
                snip_left_label = tk.Label(self.plot_axes_frame_analysis_tab,text='Snip Left:') # create left snip label
                snip_left_entry = tk.Entry(self.plot_axes_frame_analysis_tab,width=entry_width_small) # create left snip entry box
                self.left_snip_entry_array.append(snip_left_entry) # append snip entry to array (store value)
                snip_right_label = tk.Label(self.plot_axes_frame_analysis_tab,text='Snip Right:') # create right snip label
                snip_right_entry = tk.Entry(self.plot_axes_frame_analysis_tab,width=entry_width_small) # create right snip entry box
                self.right_snip_entry_array.append(snip_right_entry) # append snip entry to array (store value)
            # ===== Enable x Shift =====
            if self.enable_x_shift_analysis_tab_tk.get()==True: # if x shift is enabled
                x_shift_label = tk.Label(self.plot_axes_frame_analysis_tab,text='X Shift:') # create x shift label
                x_shift_entry = tk.Entry(self.plot_axes_frame_analysis_tab,width=entry_width_small) # create x shift entry box
                self.x_shift_entry_array.append(x_shift_entry) # append x shift entry to array (store shift value)
            # ===== Enable y Shift =====
            if self.enable_y_shift_analysis_tab_tk.get()==True: # if y shift is enabled
                y_shift_label = tk.Label(self.plot_axes_frame_analysis_tab,text='Y Shift:') # create y shift label
                y_shift_entry = tk.Entry(self.plot_axes_frame_analysis_tab,width=entry_width_small) # create y shift entry box
                self.y_shift_entry_array.append(y_shift_entry) # append y shift entry to array (store shift value)
            # ===== Create Toggle Plot Buttons =====
            toggle_var = tk.IntVar(value=1) # define integer variable to store toggle value
            toggle_plot_button = tk.Checkbutton(self.plot_axes_frame_analysis_tab,variable=toggle_var)# create checkbox to enable/disable plot
            self.toggled_plots_array.append(toggle_var) # append array to store toggled plots
            # ----- Determine Widget Placement -----
            widgets = [] # allocate widget array
            if self.enable_plot_labels_analysis_tab_tk.get()==True: # if enable plot labels is true
                widgets.append(plot_label) # add plot label to widget array
                widgets.append(plot_entry) # add plot entry to widget array
            if self.enable_filtering_analysis_tab_tk.get()==True: # if enable filtering is true
                widgets.append(filter_label_x) # add filter label to widget array
                widgets.append(filter_entry_x) # add filter entry to widget array
                widgets.append(filter_label_y) # add filter label to widget array
                widgets.append(filter_entry_y) # add filter entry to widget array
            if self.enable_snip_analysis_tab_tk.get()==True: # if enable snip is true
                widgets.append(snip_left_label) # add left snip label to widget array
                widgets.append(snip_left_entry) # add left snip entry to widget array
                widgets.append(snip_right_label) # add right snip label to widget array
                widgets.append(snip_right_entry) # add right snip entry to widget array
            if self.enable_x_shift_analysis_tab_tk.get()==True: # if enable x shift is true
                widgets.append(x_shift_label) # add x shift label to widget array
                widgets.append(x_shift_entry) # add x shift entry to widget array
            if self.enable_y_shift_analysis_tab_tk.get()==True: # if enable y shift is true
                widgets.append(y_shift_label) # add y shift label to widget array
                widgets.append(y_shift_entry) # add y shift entry to widget array
            widgets.append(btn) # add load data button to widget array
            widgets.append(toggle_plot_button) # add toggle plot button to widget array
            start_column = 4 # define start column for enable/disable widgets
            for offset, w in enumerate(widgets):
                w.grid(row=i, column=start_column+offset, sticky="w")
        # ===== Enable Axes Labels =====
        if self.enable_axes_labels_analysis_tab_tk.get()==True: # if enable axes labels
            last_row = num_plots+1 # define last row
            # ----- Create Axes Label Frame -----
            axes_labels_frame = tk.Frame(self.plot_axes_frame_analysis_tab) # create frame to house axes labels
            axes_labels_frame.grid(row=last_row,column=0,columnspan=7,sticky='ew') # layout frame
            # ----- Set Y Label -----
            tk.Label(axes_labels_frame,text="Y Label:").grid(row=0,column=0,sticky='e') # create y label label
            self.y_label = tk.Entry(axes_labels_frame,width=entry_width) # create y label entry
            self.y_label.grid(row=0,column=1,sticky='w') # layout y label entry
            # ----- Set X Label -----
            tk.Label(axes_labels_frame,text="X Label:").grid(row=0,column=2,sticky='e') # create x label label
            self.x_label = tk.Entry(axes_labels_frame,width=entry_width) # create x label entry
            self.x_label.grid(row=0,column=3,sticky='w') # layout x label entry
            # ----- Set Title -----
            tk.Label(axes_labels_frame,text="Title:").grid(row=0,column=4,sticky='w') # create title label
            self.title = tk.Entry(axes_labels_frame,width=entry_width) # create title entry
            self.title.grid(row=0,column=5,sticky='w') # layout title entry
        current_method = self.plot_test_type_analysis_tk.get() # check to see if there is already a test method selected
        if current_method: # if the user has already selected a test method
            self.on_selection_change_plot_test_type_analysis_tab() # update the options for the given test method - accounts for changing the number of plots
    
    def on_selection_change_plot_test_type_analysis_tab(self,event=None):
        # ===== Get Current Plotting Method =====
        method = self.plot_test_type_analysis_tk.get() # define plotting method
        for x_cb, y_cb in zip(self.x_axis_cbs_array, self.y_axis_cbs_array): # clear values if test type has been changed
            x_cb.set('')
            y_cb.set('')

        # ===== Update ComboBox Values/Options =====
        if method=="Modulus Check":
            plot_options = ["Force",
                            "Stress",
                            "Pressure",
                            "Displacement",
                            'Strain',
                            "Time",
                            "Setpoint",
                            "Temperature (CH1)",
                            "Temperature (CH2)",
                            "Temperature (CH3)",
                            "Temperature (CH4)",
                            "Yield Line (True)",
                            "Yield Point (True)",
                            "Yield Line (0.2%)",
                            "Yield Point (0.2%)",
                            "UTS Point"]
        elif method=="Tensile":
            plot_options = ["Force",
                            "Stress",
                            "Pressure",
                            "Displacement",
                            'Strain',
                            "Time",
                            "Setpoint",
                            "Temperature (CH1)",
                            "Temperature (CH2)",
                            "Temperature (CH3)",
                            "Temperature (CH4)",
                            "Yield Line (True)",
                            "Yield Point (True)",
                            "Yield Line (0.2%)",
                            "Yield Point (0.2%)",
                            "UTS Point"]
        elif method=="Creep":
            pass
        elif method=="Fatigue":
            pass

        for x_cb, y_cb in zip(self.x_axis_cbs_array, self.y_axis_cbs_array): # configure combo box values after selection has been made
            x_cb.configure(values=plot_options, state='readonly')
            y_cb.configure(values=plot_options, state='readonly')
            if not plot_options: # if plot options doesnt exist
                x_cb.set('')
                y_cb.set('')
            
    def on_selection_change_calibration_tab(self,event=None):
        
        #clear out old widgets and plots
        for child in self.param_frame_calibration_tab.winfo_children():
            child.destroy()
        self.cal_lin_ax.cla() # clear old data
        self.cal_conv_ax.cla() # clear old data
        # ===== Get ComboBox Method =====
        method = self.calibration_method.get() # get current calibration method
        # ===== Calibration Tab =====
        # ----- Layout Sizes -----
        button_width = 18 # define button width
        entry_width = 30 # define entry width
        #----- Calibration Specific Metric -----
        if method =="LVDT":
            # ----- Label & Entry -----
            tk.Label(self.param_frame_calibration_tab, text=f"Distance:").grid(row=0, column=0, sticky="e") # create  distance label
            self.LVDT_displacement_entry = tk.Entry(self.param_frame_calibration_tab, textvariable=self.LVDT_cal_input_displacement_tk,width=entry_width) # create entry box for distance
            self.LVDT_displacement_entry.grid(row=0, column=1, sticky="w") # layout entry
            self.LVDT_record_button = tk.Button(self.param_frame_calibration_tab,command=lambda: (self.LVDT_calibration_call(displacement=self.LVDT_cal_input_displacement_tk.get())),text='Record Measurement',width=button_width) # create record button for calibration
            self.LVDT_record_button.grid(row=0,column=2,sticky='w') # layout button
            self.LVDT_load_cal_data_button = tk.Button(self.param_frame_calibration_tab,command=self.open_calibration_file,text='Load Calibration Data',width=button_width) # load calibration data button
            self.LVDT_load_cal_data_button.grid(row=0,column=3,sticky='w') # layout button
        elif method=="Pressure Transducer":
            # ----- Label & Entry -----
            tk.Label(self.param_frame_calibration_tab, text=f"Set Pressure:").grid(row=0, column=0, sticky="e") # create set pressure label
            self.PT_set_pressure_entry = tk.Entry(self.param_frame_calibration_tab, textvariable=self.PT_cal_input_pressure_tk,width=entry_width) # create entry box for set pressure
            self.PT_set_pressure_entry.grid(row=0, column=1, sticky="w") # layout entry
            self.PT_set_pressure_button = tk.Button(self.param_frame_calibration_tab,command=lambda: (self.funDAC.writePSI(self.PT_cal_input_pressure_tk.get())),text="Set Pressure",width=button_width) # create set pressure button
            self.PT_set_pressure_button.grid(row=0,column=2,sticky='w') # layout button
            tk.Label(self.param_frame_calibration_tab,text='Measured Pressure (external):').grid(row=1,column=0,sticky='e') # create measured pressure label
            self.PT_measured_pressure_entry = tk.Entry(self.param_frame_calibration_tab,textvariable=self.PT_cal_measured_pressure_gauge_tk,width=entry_width) # create measured pressure entry box
            self.PT_measured_pressure_entry.grid(row=1,column=1,sticky='w') # layout entry
            self.PT_record_button = tk.Button(self.param_frame_calibration_tab,command=lambda: (self.PT_calibration_call(pressure=self.PT_cal_measured_pressure_gauge_tk.get())),text='Record Measurement',width=button_width) # create record button for calibration
            self.PT_record_button.grid(row=1,column=2,sticky='w') # layout button
            self.PT_load_cal_data_button = tk.Button(self.param_frame_calibration_tab,command=self.open_calibration_file,text='Load Calibration Data',width=button_width) # load calibration data button
            self.PT_load_cal_data_button.grid(row=0,column=3,sticky='w') # layout button
        elif method=="I/P Transducer":
            # ----- Label & Entry -----
            tk.Label(self.param_frame_calibration_tab,text=f"Set Pressure:").grid(row=0, column=0, sticky="e") # create set pressure label
            self.IP_set_pressure_entry = tk.Entry(self.param_frame_calibration_tab, textvariable=self.IP_cal_input_pressure_tk,width=entry_width) # create entry box for set pressure
            self.IP_set_pressure_entry.grid(row=0, column=1, sticky="w") # layout entry
            self.IP_set_pressure_button = tk.Button(self.param_frame_calibration_tab,command=lambda: (self.funDAC.writePSI(self.IP_cal_input_pressure_tk.get(),callback=True)),text="Set Pressure",width=button_width) # create set pressure button
            self.IP_set_pressure_button.grid(row=0,column=2,sticky='w') # layout button
            tk.Label(self.param_frame_calibration_tab,text='Measured Pressure:').grid(row=1,column=0,sticky='e') # create measured pressure label
            self.IP_measured_pressure_entry = tk.Entry(self.param_frame_calibration_tab,textvariable=self.IP_cal_output_pressure_tk,state='disabled',width=entry_width) # create measured pressure entry box
            self.IP_measured_pressure_entry.grid(row=1,column=1,sticky='w') # layout entry
            self.IP_measure_method_checkbutton = tk.Checkbutton(self.param_frame_calibration_tab,variable=self.IP_measure_method_use_external_gauge,command=self.on_IP_cal_method_checkbutton,text='Measure Pressure Externally') # create checkbox to determine pressure measurement method
            self.IP_measure_method_checkbutton.grid(row=1,column=3,sticky='w') # layout checkbutton
            self.IP_record_button = tk.Button(self.param_frame_calibration_tab,command=lambda: (self.IP_calibration_call(input_pressure=self.IP_cal_input_pressure_tk.get(),output_pressure=None,measurement_method_external=False)),text='Record Measurement',width=button_width) # create record button for calibration in default configuration
            self.IP_record_button.grid(row=1,column=2,sticky='w') # layout button
            self.IP_load_cal_data_button = tk.Button(self.param_frame_calibration_tab,command=self.open_calibration_file,text='Load Calibration Data',width=button_width) # load calibration data button
            self.IP_load_cal_data_button.grid(row=0,column=3,sticky='w') # layout button
        elif method=="Frame Compliance":
            tk.Label(self.param_frame_calibration_tab,text="Max Load (lb):").grid(row=0,column=0,sticky='e') # create max load label
            self.FC_max_load_entry = tk.Entry(self.param_frame_calibration_tab,textvariable=self.FC_max_load_tk,width=entry_width) # create max load entry
            self.FC_max_load_entry.grid(row=0,column=1,sticky='w') # layout max load entry
            tk.Label(self.param_frame_calibration_tab,text="Known Specimen Modulus (psi)").grid(row=1,column=0,sticky='e') # create known sample modulus label
            self.FC_known_modulus_entry = tk.Entry(self.param_frame_calibration_tab,textvariable=self.FC_known_modulus_tk,width=entry_width) # create known modulus entry
            self.FC_known_modulus_entry.grid(row=1,column=1,sticky='w') # layout known specimen modulus entry
            self.start_FC_test_button = tk.Button(self.param_frame_calibration_tab,command=lambda: (self.start_FC_threading(file_path=self.file_name_calibration_tab.get(),
                                                                                                                            max_load=self.FC_max_load_tk.get(),
                                                                                                                            num_tests=self.num_calibration_pts.get())),
                                                                                                                            text="Start Test",
                                                                                                                            width=button_width,
                                                                                                                            bg='green',
                                                                                                                            fg='white') # create start test button
            self.start_FC_test_button.grid(row=1,column=2,sticky='w') # layout start button
            self.stop_FC_test_button = tk.Button(self.param_frame_calibration_tab,
                                                 command=self.on_test_stop_button,
                                                 text="Stop Test",
                                                 width=button_width,
                                                 bg='red',
                                                 fg='white') # create stop test button
            self.stop_FC_test_button.grid(row=1,column=3,sticky='w') # layout start button
            self.load_data_button = tk.Button(self.param_frame_calibration_tab,command=self.open_calibration_file,text='Load Aggregate Data',width=button_width) # create load data button
            self.load_data_button.grid(row=0,column=2,sticky='w') # layout button

        self.num_points_entry_calibration_tab.configure(state='normal') # enable on change after calibration is complete
        self.file_name_calibration_tab.configure(state='normal') # enable on change after calibration is complete

    def on_selection_change_tuning_tab(self,event=None):
        
        #clear out old widgets (labels)
        for child in self.param_frame_tuning_tab.winfo_children():
            child.destroy()
        # ===== ComboBox Methods =====
        method = self.tuning_box_tuning_tab.get()
        # ===== Tuning Tab =====
        #----- Test Specific Metric -----
        if method =="Stroke Rate":
            # ----- Tensile Label & Entry -----
            tk.Label(self.param_frame_tuning_tab, text="Kp:").grid(row=0, column=0, sticky="e") # create Kp label
            tk.Entry(self.param_frame_tuning_tab, textvariable=self.kp_tk,width=40).grid(row=0, column=1, sticky="w") # create entry box for kp
            tk.Label(self.param_frame_tuning_tab, text="Maxiumum Load (lb):").grid(row=1, column=0, sticky="e") # create maximum load label
            tk.Entry(self.param_frame_tuning_tab, textvariable=self.tuning_max_load_tk,width=40).grid(row=1, column=1, sticky="w") # create entry box for maximum load
            tk.Label(self.param_frame_tuning_tab, text="Stroke Rate (in/min):").grid(row=2, column=0, sticky="e") # create stroke rate label
            tk.Entry(self.param_frame_tuning_tab, textvariable=self.stroke_rate_tk,width=40).grid(row=2, column=1, sticky="w") # create entry box for stroke rate
        elif method=="Creep":
            pass
        elif method=="Fatigue":
            pass

    def on_IP_cal_method_checkbutton(self,event=None):
        button_width=18
        if self.IP_measure_method_use_external_gauge.get()==True: # box checked - measure pressure manually
            self.log_command("true")
            self.IP_measured_pressure_entry.configure(state='normal') # enable measured pressure entry if measuring externally
            self.IP_record_button = tk.Button(self.param_frame_calibration_tab,command=lambda: (self.IP_calibration_call(input_pressure=self.IP_cal_input_pressure_tk.get(),output_pressure=self.IP_cal_output_pressure_tk.get(),measurement_method_external=True)),text='Record Measurement',width=button_width) # create record button for calibration
        elif self.IP_measure_method_use_external_gauge.get()==False: # box unchecked - measure presure with PT
            self.log_command("false")
            self.IP_measured_pressure_entry.configure(state='disabled') # disable measured pressure entry if using transducer
            self.IP_record_button = tk.Button(self.param_frame_calibration_tab,command=lambda: (self.IP_calibration_call(input_pressure=self.IP_cal_input_pressure_tk.get(),output_pressure=False,measurement_method_external=False)),text='Record Measurement',width=button_width) # create record button for calibration
        self.IP_record_button.grid(row=1,column=2,sticky='w') # layout button

    def on_start_button_pretest_tab(self,event=None):

        if self.max_load.get()<=0 or self.load_rate.get()<=0:
            self.log_command("Please enter a positive non-zero value for maximum load and load rate...")
        else:
            self.modcheck_confirmation()

    def on_start_button_test_tab(self,event=None):
        # ===== Get Test Method =====
        method = self.test_box_test_tab.get() # get current test method
        if method=="Tensile":
            if self.stroke_rate_tk.get()<=0 or self.kp_tk.get()<=0:
                self.log_command("Please enter a positive non-zero value for stroke rate and Kp...")
            else:
                self.test_confirmation()
        elif method=="Creep":
            pass
        elif method=="Fatigue":
            pass

    def on_start_button_tuning_tab(self,event=None):
        # ===== Get Test Method =====
        method = self.tuning_box_tuning_tab.get() # get current test method
        # ===== Get File Path and Name ======
        file_path = self.folder_path.get() # get selected folder path
        new_path = os.path.join(file_path,self.file_name_tuning_tab_tk.get()+".csv")
        if method=="Stroke Rate":
            stroke_rate = self.stroke_rate_tk.get() # get stroke rate for tuning
            kp = self.kp_tk.get() # get kp for PID
            max_load = self.tuning_max_load_tk.get() # get max load for tuning
            if stroke_rate<=0 or kp<=0 or max_load<=0:
                self.log_command("Please enter a positive non-zero value for stroke rate,Kp, and maximum load...")
            else:
                self.start_tuning_threading(file_path=new_path,stroke_rate=stroke_rate,kp=kp,max_load=max_load) # start threading for tuning operation

    def on_test_stop_button(self,event=None):
        # ===== Stop Test =====
        self.funtest.stop_test() # Run stop_test method of funtest class (from main.py)

    def modcheck_confirmation(self):
        # ===== Create Confirmation Window =====
        confirmation_window = tk.Toplevel(self.root) # create confirmation window
        confirmation_window.title('Confirm Modulus Check') # set window title
        confirmation_window.transient(self.root) # ensures window is always in front of parent window
        confirmation_window.geometry("400x200") # define size of confirmation window
        # ===== Get Mod Check Information ======
        file_path = self.folder_path.get() # get selected folder path
        new_path = os.path.join(file_path,self.file_name_pretest_tab_tk.get()+".csv")
        max_load = self.max_load.get() # get max load for mod check
        load_rate = self.load_rate.get() # get load rate for mod check
        # ===== Display test Parameters =====
        header_frame = tk.Frame(confirmation_window) # create header_frame
        header_frame.grid(row=0,column=0,sticky='ew')
        info_frame = tk.Frame(confirmation_window) # create info_frame in confirmation window
        info_frame.grid(row=1,column=0,sticky='we') # layout info_frame
        tk.Label(header_frame,text="Modulus Check Parameters",font=('TkDefaultFont',16,'bold'),justify='center').grid(row=0,column=0,sticky='ew') # create label
        tk.Label(info_frame,text=f"Maximum Load: {max_load}",justify='center').grid(row=1,column=0,sticky='ew') # create label
        tk.Label(info_frame,text=f"Load Rate: {load_rate}",justify='center').grid(row=2,column=0,sticky="ew") # create label
        tk.Label(info_frame,text=f"File Path: {file_path}",justify='center').grid(row=3,column=0,sticky="ew") # create label

        # ===== Continue/Cancel Buttons =====
        button_frame = tk.Frame(confirmation_window) # create button_frame in confirmation window
        button_frame.grid(row=2,column=0,pady=20,sticky='ew') # layout button_frame
        tk.Button(button_frame,text="Start Test",justify='center',bg='green',fg='white',command=lambda:[confirmation_window.destroy(),self.start_modcheck_threading(max_load=max_load,load_rate=load_rate,file_path=new_path)]).grid(row=0,column=0,sticky='e')
        tk.Button(button_frame,text="Cancel",justify='left',bg='red',fg='white',command=confirmation_window.destroy).grid(row=0,column=1,sticky='w')
        # ===== Configure Columns/Rows =====
        confirmation_window.columnconfigure(0,weight=1)
        header_frame.columnconfigure(0,weight=1)
        info_frame.columnconfigure(0,weight=1)
        button_frame.columnconfigure(0,weight=1)
        button_frame.columnconfigure(1,weight=1)

    def test_confirmation(self):
        # ===== Get Test Method =====
        method = self.test_box_test_tab.get() # get test method
        # ===== Create Confirmation Window =====
        confirmation_window = tk.Toplevel(self.root) # create confirmation window
        confirmation_window.title('Confirm Test Parameters') # set window title
        confirmation_window.transient(self.root) # ensures window is always in front of parent window
        confirmation_window.geometry("400x200") # define size of confirmation window
        # ===== Get File Path and Name ======
        file_path = self.folder_path.get() # get selected folder path
        new_path = os.path.join(file_path,self.file_name_test_tab_tk.get()+".csv")
        stroke_rate = self.stroke_rate_tk.get() # get stroke rate for tensile test
        kp = self.kp_tk.get() # get kp for PID
        # ===== Create Frames =====
        header_frame = tk.Frame(confirmation_window) # create header_frame
        header_frame.grid(row=0,column=0,sticky='ew')
        info_frame = tk.Frame(confirmation_window) # create info_frame in confirmation window
        info_frame.grid(row=1,column=0,sticky='we') # layout info_frame
        button_frame = tk.Frame(confirmation_window) # create button_frame in confirmation window
        button_frame.grid(row=2,column=0,pady=20,sticky='ew') # layout button_frame
        # ===== Test Specific Parameters =====
        tk.Label(header_frame,text="Test Parameters",font=('TkDefaultFont',16,'bold'),justify='center').grid(row=0,column=0,sticky='ew') # create label
        if method=='Tensile':
            tk.Label(info_frame,text=f"Stroke Rate (in/min): {stroke_rate}",justify='center').grid(row=1,column=0,sticky='ew') # create label
            tk.Label(info_frame,text=f"Kp: {kp}",justify='center').grid(row=2,column=0,sticky="ew") # create label
            tk.Label(info_frame,text=f"File Path: {file_path}",justify='center').grid(row=3,column=0,sticky="ew") # create label
            tk.Button(button_frame,text="Start Test",justify='center',bg='green',fg='white',command=lambda:[confirmation_window.destroy(),self.start_test_threading(file_path=new_path,kp=kp,stroke_rate=stroke_rate)]).grid(row=0,column=0,sticky='e')
            tk.Button(button_frame,text="Cancel",justify='left',bg='red',fg='white',command=confirmation_window.destroy).grid(row=0,column=1,sticky='w')
        elif method=='Creep':
            pass
        elif method=='Fatigue':
            pass
        # ===== Configure Columns/Rows =====
        confirmation_window.columnconfigure(0,weight=1)
        header_frame.columnconfigure(0,weight=1)
        info_frame.columnconfigure(0,weight=1)
        button_frame.columnconfigure(0,weight=1)
        button_frame.columnconfigure(1,weight=1)

    def start_modcheck_threading(self,max_load,load_rate,file_path):
        self.modcheck_is_running = True # define variable to determine if modcheck is running
        t = threading.Thread(target=self.funtest.MODcheck,args=(max_load,load_rate,file_path),daemon=True) # start modcheck as a background thread
        t.start()

    def start_test_threading(self,file_path,kp,stroke_rate):
        # ===== Get Test Method =====
        method = self.test_box_test_tab.get() # get test method
        # ===== Start Threading =====
        if method=='Tensile':
            t = threading.Thread(target=self.funtest.tensile,args=(kp,stroke_rate,file_path),daemon=True) # start tensile test as a background thread
        elif method=='Creep':
            pass
        elif method=='Fatigue':
            pass
        self.test_is_running = True # define variable to determine if test is running
        t.start()
    
    def start_tuning_threading(self,file_path,kp,stroke_rate,max_load):
        # ===== Get Test Method =====
        method = self.tuning_box_tuning_tab.get() # get test method
        # ===== Start Threading =====
        if method=='Stroke Rate':
            t = threading.Thread(target=self.funtest.PIDtuning,args=(kp,stroke_rate,max_load,file_path),daemon=True) # start tensile test as a background thread
        self.tuning_is_running = True # define variable to determine if test is running
        t.start()

    def start_analysis_threading(self):
        t = threading.Thread(target=self.run_analysis,args=(),daemon=True) # start modcheck as a background thread
        t.start()

    def start_FC_threading(self,file_path,max_load,num_tests):
        # ===== Empyty Old Values and Plots =====
        self.FC_slope_tk.set(0) # set slope back to zero
        self.FC_zero_tk.set(0) # set zero back to zero
        self.FC_r2_tk.set(0) # set r2 back to zero
        self.cal_lin_ax.cla() # clear old data
        self.cal_conv_ax.cla() # clear old data
        # ===== Start Threading =====
        new_path = os.path.join(self.folder_path.get(),file_path) # join directory with folder name
        t = threading.Thread(target=self.funtest.frame_compliance,args=(new_path,max_load,num_tests),daemon=True) # start modcheck as a background thread
        t.start()

    def save_FC_data(self):
        if self.FC_max_load_tk.get()==0 or self.FC_known_modulus_tk.get()==0:
            self.log_command("Enter a value greater than zero for Max Load and Known Modulus to save data...")
        else:
            wdir = os.path.dirname(self.filename) # change directory to loaded file location
            funSolver = solver(path=os.path.join(wdir,'FC_test_aggregate.csv'),
                               log_callback=self.log_command,
                               base_dir=self.base_dir) # create instance of solver class
            specimen_elastic_deformation_function = funSolver.calculate_elastic_deformation(elastic_modulus=self.FC_known_modulus_tk.get(),max_load=self.FC_max_load_tk.get()) # calculate total elastic deformation in the specimen
            frame_displacement_function = abs(self.FC_slope_tk.get()-specimen_elastic_deformation_function) # calculate frame displacement function - absolute value for testing purposes, not actually necessary
            print(f"specimen elastic deformation function: {specimen_elastic_deformation_function}")
            print(self.FC_slope_tk.get())
            print(f"Frame displacement function: {frame_displacement_function}")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df = pd.DataFrame({'date':[timestamp],'slope':[frame_displacement_function],'zero':[self.FC_zero_tk.get()]}) # create data frame with these values
            write_header = not os.path.exists('frame_compliance_log.csv') # check to see if the file exists, if so, define as false
            df.to_csv('frame_compliance_log.csv',mode='a',header=write_header,index=False) # append data frame to csv
            self.log_command("Compliance logged succesfully...")

    def save_analysis_data(self):
        method = self.analysis_test_type_analysis_tk.get() # define analysis method
        loaded_data = self.analysis_file_path # define file path of loaded data
        new_path = os.path.join(self.folder_path.get(),self.file_name_analysis_tab_tk.get()+'.csv') # get complete file path
        df = pd.read_csv(loaded_data) # read csv file
        if method=='Modulus Check':
            try:
                df.insert(0,'stress',self.elastic_stress) # insert stress column at the begining
                df.insert(1,'strain',self.elastic_strain) # insert strain column in front of stress column
            except ValueError: # stress/strain already exists
                df.drop('stress',axis=1) # delete existing stress column
                df.drop('strain',axis=1) # delete existing strain column
                df.insert(0,'stress',self.elastic_stress) # insert stress column at the begining
                df.insert(1,'strain',self.elastic_strain) # insert strain column in front of stress column
            pass
        elif method=='Tensile':
            try:
                df.insert(0,'stress',self.stress) # insert stress column at the begining
                df.insert(1,'strain',self.strain) # insert strain column in front of stress column
            except ValueError: # stress/strain already exists
                df.drop('stress',axis=1) # delete existing stress column
                df.drop('strain',axis=1) # delete existing strain column
                df.insert(0,'stress',self.stress) # insert stress column at the begining
                df.insert(1,'strain',self.strain) # insert strain column in front of stress column
        elif method=='Creep':
            pass
        elif method=='Fatigue':
            pass
        df.to_csv(new_path,index=False) # create new file with inserted values
        self.log_command("Data exported succesfully...")

    def log_command(self,message: str):
        # ===== Log Command =====
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}]: {message}\n"
        # ===== Log to Pre-Test Tab =====
        self.cmd_text_box_pretest.configure(state="normal") # make it writable
        self.cmd_text_box_pretest.insert("end", line) # insert command at the end
        self.cmd_text_box_pretest.see("end")    # scroll to bottom
        self.cmd_text_box_pretest.configure(state="disabled") # make it read-only
        # ===== Log to Test Tab =====
        self.cmd_text_box_test.configure(state="normal") # make it writable
        self.cmd_text_box_test.insert("end", line) # insert command at the end
        self.cmd_text_box_test.see("end")    # scroll to bottom
        self.cmd_text_box_test.configure(state="disabled") # make it read-only
        # ===== Log to Analysis Tab =====
        self.cmd_text_box_analysis.configure(state="normal") # make it writable
        self.cmd_text_box_analysis.insert("end", line) # insert command at the end
        self.cmd_text_box_analysis.see("end")    # scroll to bottom
        self.cmd_text_box_analysis.configure(state="disabled") # make it read-only
        # ===== Log to Calibration Tab =====
        self.cmd_text_box_calibration.configure(state="normal") # make it writable
        self.cmd_text_box_calibration.insert("end", line) # insert command at the end
        self.cmd_text_box_calibration.see("end")    # scroll to bottom
        self.cmd_text_box_calibration.configure(state="disabled") # make it read-only
        # ===== Log to Functions Tab =====
        self.cmd_text_box_functions.configure(state="normal") # make it writable
        self.cmd_text_box_functions.insert("end", line) # insert command at the end
        self.cmd_text_box_functions.see("end")    # scroll to bottom
        self.cmd_text_box_functions.configure(state="disabled") # make it read-only
        # ===== Log to Tuning Tab =====
        self.cmd_text_box_tuning.configure(state="normal") # make it writable
        self.cmd_text_box_tuning.insert("end", line) # insert command at the end
        self.cmd_text_box_tuning.see("end")    # scroll to bottom
        self.cmd_text_box_tuning.configure(state="disabled") # make it read-only

    def rehash(self,event=None):
        os.chdir(self.base_dir) # resest working directory to base directory
        # ===== Rehash Classes =====
        # allows classes to load most recent calibration data
        ''' refreshing is done to avoid different instances bound to multiple widgets'''
        self.funtest.refresh(log_callback=self.log_command,
                            test_status_callback=self.test_status)
        self.funLVDT.refresh(log_callback=self.log_command,
                            status_callback=self.calibration_status,
                            current_position_callback=self.LVDT_get_current_position,
                            current_voltage_callback=self.LVDT_get_current_voltage)
        self.funPT.refresh(log_callback=self.log_command,
                        status_callback=self.calibration_status,
                        current_pressure_callback=self.PT_get_current_pressure,
                        current_force_callback=self.PT_get_current_force)
        self.funDAC.refresh(log_callback=self.log_command,
                          status_callback=self.calibration_status)

    def LVDT_calibration_call(self,displacement):
        self.funLVDT.record_calibration_point(displacement=displacement,num_points=self.num_calibration_pts.get()) # record calibration point

    def LVDT_get_zero(self):
        os.chdir(self.base_dir) # ensure directory is base directory
        self.funLVDT.zero_position() # zero LVDT position
        df = pd.read_csv('LVDT_calibration_log.csv') # read calibration data
        LVDT_zero_offset = df['zero'].to_numpy()[-1] # convert zero to numpy array, use last value
        self.LVDT_cal_zero_tk.set(round(LVDT_zero_offset,5)) # update zero offset text variable

    def LVDT_get_current_position(self,current_position: float):
        self.LVDT_current_position_tk.set(round(current_position,5)) # update text variable for current position
    
    def LVDT_get_current_voltage(self,current_voltage: float):
        self.LVDT_current_voltage_tk.set(round(current_voltage,4)) # update text variable for current voltage

    def PT_calibration_call(self,pressure):
        self.funPT.record_calibration_point(pressure=pressure,num_points=self.num_calibration_pts.get()) # record calibration point

    def PT_get_zero(self):
        os.chdir(self.base_dir) # ensure directory is base directory
        self.funPT.zero_reading() # zero PT reading
        df = pd.read_csv('PT_calibration_log.csv') # read calibration data
        PT_zero_offset = df['zero'].to_numpy()[-1] # convert zero to numpy array, use last value
        self.PT_cal_zero_tk.set(round(PT_zero_offset,3)) # update zero offset text variable

    def PT_get_current_pressure(self,current_pressure: float):
        self.PT_current_pressure_tk.set(round(current_pressure,2)) # update text variable for current pressure

    def PT_get_current_force(self,current_force: float):
        self.PT_current_force_tk.set(round(current_force,2)) # update text variable for current pressure

    def IP_calibration_call(self,input_pressure,output_pressure,measurement_method_external=False):
        self.funDAC.record_calibration_point(input_pressure=input_pressure,output_pressure=output_pressure,measurement_method_external=measurement_method_external,num_points=self.num_calibration_pts.get()) # record calibration point

    def IP_get_zero(self):
        os.chdir(self.base_dir) # ensure directory is base directory
        self.funDAC.zero_reading() # zero PT reading
        df = pd.read_csv('IP_calibration_log.csv') # read calibration data
        IP_zero_offset = df['zero'].to_numpy()[-1] # convert zero to numpy array, use last value
        self.IP_cal_zero_tk.set(round(IP_zero_offset,3)) # update zero offset text variable

    def test_status(self,method,is_complete):
        
        if method=='MODcheck':
            path = os.path.join(self.folder_path.get(),self.file_name_pretest_tab_tk.get()+'.csv') # define file path
            if is_complete=='default-True' or is_complete=="default-updated": # plot data on pretest (default) tab
                self.plot_raw_test_data(file_path=path,
                                        test_method='MODcheck')
            elif is_complete=='calibration-True' or is_complete=='calibration-updated': # plot data on calibration tab
                files = glob.glob(os.path.join(self.file_name_calibration_tab.get(), "FC_test_*.csv")) # get list of matching files
                files.sort(key=lambda f: int(os.path.splitext(f)[0].split("_")[-1])) # extract numeric part and sort by it
                recent_file = files[-1] # get most recent file
                if is_complete=='calibration-updated':
                    self.plot_calibration_data(file_path=recent_file) # plot data
                elif is_complete=='calibration-True':
                    #self.plot_calibration_data(file_path=recent_file,is_file_loaded=True) # clear existing plot, add old data to group plot
                    self.plot_calibration_data(file_path=recent_file,is_file_loaded=False) # clear existing plot, add old data to group plot
        elif method=='tensile':
            path = os.path.join(self.folder_path.get(),self.file_name_test_tab_tk.get()+'.csv') # define file path
            if is_complete=='default-True' or is_complete=='default-updated':
                self.plot_raw_test_data(file_path=path,
                                        test_method='tensile')
        elif method=='tuning':
            path = os.path.join(self.folder_path.get(),self.file_name_tuning_tab_tk.get()+'.csv') # define file path
            if is_complete=='default-True' or is_complete=='default-updated':
                self.plot_raw_test_data(file_path=path,
                                        test_method='tuning')

    def calibration_status(self,is_complete: bool):

        method = self.calibration_method.get() # get current calibration method
        self.calibration_is_complete = is_complete # define attribute
        if method=="LVDT":
            if self.calibration_is_complete==True: # if calibration is complete, disable buttons, then plot
                self.num_points_entry_calibration_tab.configure(state='disabled') # disable number of calibration points box after calibration
                self.file_name_calibration_tab.configure(state='disabled') # disable file name box after calibration
                self.LVDT_displacement_entry.configure(state='disabled') # disable entry box after calibration
                self.LVDT_record_button.configure(state='disabled') # disable button after calibration
                self.LVDT_load_cal_data_button.configure(state='normal') # enable button after calibrating
                new_path = os.path.join(self.folder_path.get(),self.file_name_calibration_tab.get()+".csv")
                os.rename("LVDT_temp.csv",new_path) # rename temp file to save cal data
                self.log_command(f"Calibration data saved... [{new_path}]")
                self.plot_calibration_data(file_path=new_path) # plot cal data after temp file is removed
            else: # if calibration is not complete, plot temp data
                self.plot_calibration_data(file_path='LVDT_temp.csv')
                self.LVDT_load_cal_data_button.configure(state='disabled') # disable button while calibrating
        elif method=="Pressure Transducer":
            if self.calibration_is_complete==True: # if calibration is complete, disable buttons, set pressure to min, then plot
                self.num_points_entry_calibration_tab.configure(state='disabled') # disable number of calibration points box after calibration
                self.file_name_calibration_tab.configure(state='disabled') # disable file name box after calibration
                self.PT_set_pressure_entry.configure(state='disabled') # disable set pressure entry
                self.PT_set_pressure_button.configure(state='disabled') # dissable set pressure button
                self.PT_measured_pressure_entry.configure(state='disabled') # disable entry box after calibration
                self.PT_record_button.configure(state='disabled') # disable button after calibration
                self.PT_load_cal_data_button.configure(state='normal') # enable button after calibrating
                new_path = os.path.join(self.folder_path.get(),self.file_name_calibration_tab.get()+".csv")
                os.rename("PT_temp.csv",new_path) # rename temp file to save cal data
                self.log_command(f"Calibration data saved... [{new_path}]")
                self.funDAC.writeVoltage(0) # set pressure back to minimum - write voltage in case calibration is out of wack, will write high pressure if it is
                self.plot_calibration_data(file_path=new_path) # plot cal data after temp file is removed
            else: # if calibration is not complete, plot temp data
                self.plot_calibration_data(file_path='PT_temp.csv')
                self.PT_load_cal_data_button.configure(state='disabled') # disable button while calibrating
        elif method=="I/P Transducer":
            if self.calibration_is_complete==True: # if calibration is complete, disable buttons, set pressure to min, then plot
                self.num_points_entry_calibration_tab.configure(state='disabled') # disable number of calibration points box after calibration
                self.file_name_calibration_tab.configure(state='disabled') # disable file name box after calibration
                self.IP_set_pressure_entry.configure(state='disabled') # disable set pressure entry
                self.IP_set_pressure_button.configure(state='disabled') # dissable set pressure button
                self.IP_measured_pressure_entry.configure(state='disabled') # disable entry box after calibration
                self.IP_record_button.configure(state='disabled') # disable button after calibration
                self.IP_measure_method_checkbutton.configure(state='disabled') # disable button after calibration
                self.IP_load_cal_data_button.configure(state='normal') # enable button after calibrating
                new_path = os.path.join(self.folder_path.get(),self.file_name_calibration_tab.get()+".csv")
                os.rename("IP_temp.csv",new_path) # rename temp file to save cal data
                self.log_command(f"Calibration data saved... [{new_path}]")
                self.funDAC.writePSI(3) # set pressure back to minimum
                self.plot_calibration_data(file_path=new_path) # plot cal data after temp file is removed
            else: # if calibration is not complete, plot temp data
                self.plot_calibration_data(file_path='IP_temp.csv')
                self.IP_load_cal_data_button.configure(state='disabled') # disable button while calibrating
        return self.calibration_is_complete # return calibration status

    def exit_program(self):
        self.root.quit()

# ===== Tkinter GUI setup =====
if __name__=="__main__":
    app = GUI()
    app.root.protocol("WM_DELETE_WINDOW",app.exit_program)
    app.root.mainloop()
    
def main():
    app = GUI()
    app.root.protocol("WM_DELETE_WINDOW",app.exit_program)
    app.root.mainloop()
    
