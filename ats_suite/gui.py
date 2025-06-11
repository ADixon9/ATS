import tkinter as tk
from tkinter import ttk, filedialog, PhotoImage
from main import *
import matplotlib
import random
import pandas as pd
import os
import threading
import webbrowser
import datetime

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


'''
# Use TkAgg backend
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tensile Testing Machine")

        self.base_dir = os.path.dirname(__file__) # directory of current script
        self.parent_dir = os.path.abspath(os.path.join(self.base_dir,'..'))
        # ===== General =====
        self.force_var = tk.StringVar(value="0")
        self.pressure_var = tk.StringVar(value="0")
        self.displacement_var = tk.StringVar(value="0")
        self.test_method_pretest = tk.StringVar(value="") # define string variable such that test_method can be updated
        self.test_method_test = tk.StringVar(value="") # define string variable such that test_method can be updated
        self.plot_test_type_analysis_tk = tk.StringVar(value='') # define string variable for plotting - define test type to be plotted
        self.x_axis_selection_analysis_tab_tk = tk.StringVar(value='') # define string variable for x axis selection on analysis tab plot
        self.y_axis_selection_analysis_tab_tk = tk.StringVar(value='') # define string variable for y axis selection on analysis tab plot
        self.number_of_analysis_plots_tk = tk.IntVar(value=1) # define integer variable to select number of plots
        self.calibration_method = tk.StringVar(value="") # define string variable such that calibration_method can be updates
        self.IP_measure_method_use_external_gauge = tk.IntVar(value=0) # define integer variable to determine measurement method for I/P calibration
        self.enable_plot_labels_analysis_tab_tk = tk.IntVar(value=0) # define integer variable to enable/disable plot labels
        self.enable_axes_labels_analysis_tab_tk = tk.IntVar(value=0) # define integer variable to enable/disable axes labels
        self.enable_filtering_analysis_tab_tk = tk.IntVar(value=0) # define integer variable to enable/disable data filtering
        self.num_calibration_pts = tk.IntVar(value=10) # define integer variable for number of calibration points
        # ===== LVDT =====
        self.LVDT_cal_input_displacement_tk = tk.DoubleVar(value=0) # define LVDT Displacement variable
        self.LVDT_current_position_tk = tk.DoubleVar(value=0) # define current LVDT displacement variable
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
        # ===== I/P Transducer =====
        self.IP_cal_input_pressure_tk = tk.DoubleVar(value=3) # define IP Displacement variable
        self.IP_cal_output_pressure_tk = tk.DoubleVar(value=0) # define measured pressure variable
        self.IP_cal_factor_tk = tk.DoubleVar(value=0) # define IP cal factor variable
        self.IP_cal_zero_tk = tk.DoubleVar(value=0) # define IP zero variable
        self.IP_cal_std_dev_tk = tk.DoubleVar(value=0) # define IP standard deviation variable
        self.IP_cal_linearity_tk = tk.DoubleVar(value=0) # define IP linearity variable
        self.IP_cal_R2_tk = tk.DoubleVar(value=0) # define IP R^2 calibration variable
        # ===== DAC =====
        self.DAC_set_pressure_tk = tk.DoubleVar(value=3)# define set pressure variable
        # ===== Files =====
        self.file_name_pretest_tab_tk = tk.StringVar(value="") # define file name tk string variable for pretest tab
        self.file_name_test_tab = tk.StringVar(value="") # define file name tk string variable for test tab
        self.file_name_calibration_tab = tk.StringVar(value="") # define file name tk string variable for calibration tab
        self.folder_path = tk.StringVar(value=os.getcwd())
        self.running = False
        # ===== Setup Tabs =====
        self.setup_tabs()
        # ===== Instantiate classes =====
        self.funtest = test(log_callback=self.log_command,
                            test_status_callback=self.test_status)
        self.funLVDT = LVDT(log_callback=self.log_command,
                            status_callback=self.calibration_status,
                            current_position_callback=self.LVDT_get_current_position)
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
        # ===== Help Menu =====
        help_menu = tk.Menu(self.menu, tearoff=False)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation",command=lambda: webbrowser.open("https://github.com/ADixon9/ATS"))
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
        # ------ Browse/Select Folder/File Path -----
        tk.Label(self.middle_frame_pretest, text="Folder:").grid(row=4, column=0, sticky="e") # create folder label, stick to the right side
        tk.Entry(self.middle_frame_pretest, textvariable=self.folder_path, width=40).grid(row=4, column=1, sticky="w") # create folder entry box
        tk.Button(self.middle_frame_pretest, text="Browse", command=self.select_folder).grid(row=4, column=2, sticky="w") # create button to select folder, runs select_folder function
        # ----- Start/Stop Buttons -----
        self.start_button_pretest_tab = tk.Button(self.middle_frame_pretest, text="Start Test", command=None, bg="green", fg="white") # create start test button
        self.start_button_pretest_tab.grid(row=5, column=0, pady=5) # layout start button
        self.stop_button_pretest_tab = tk.Button(self.middle_frame_pretest, text="Stop Test", command=None, bg="red", fg="white") # create button to stop test
        self.stop_button_pretest_tab.grid(row=5, column=1, pady=5) # layout stop button
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

        # ===== Define Text Variables =====
        self.stroke_rate = tk.DoubleVar() # define stroke rate as a floating value
        self.kp = tk.DoubleVar() # define Kp as a floating value

        # ===== Create Frame/Labels/Buttons =====
        top_frame = tk.Frame(self.test_tab) # create top frame where values, entry boxes, and drop downs are housed on the test tab (notebook)
        top_frame.grid(row=0,column=0,padx=10, pady=0,sticky='ew') # size of top frame
        # ----- Force/Pressure/Displacement -----
        tk.Label(top_frame, text="Force (N):").grid(row=0, column=0, sticky="e") # create force label, sticking to right side
        tk.Label(top_frame, textvariable=self.force_var).grid(row=0, column=1, sticky="w") # create force variable label, sticking to left side

        tk.Label(top_frame, text="Pressure (psi):").grid(row=0, column=2, sticky="e") # create pressure label, sticking to right side
        tk.Label(top_frame, textvariable=self.pressure_var).grid(row=0, column=3, sticky="w") # create pressure variable label, sticking to left side

        tk.Label(top_frame, text="Displacement (mm):").grid(row=0, column=4, sticky="e") # create displacement label, sticking to right side
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
        tk.Entry(self.middle_frame_test, textvariable=self.kp,width=40).grid(row=2, column=1, sticky="w") # create entry box for file name
        # ----- File Name/Directory -----
        tk.Label(self.middle_frame_test, text="File Name:").grid(row=3, column=0, sticky="e") # create file name label, stick to the right side
        tk.Entry(self.middle_frame_test, textvariable=self.file_name_test_tab,width=40).grid(row=3, column=1, sticky="w") # create entry box for file name
        tk.Button(self.middle_frame_test,text="Select File Directory",command=self.select_folder).grid(row=3,column=2,sticky="w") # create button to select file directory for new file
        # ------ Browse/Select Folder/File Path -----
        tk.Label(self.middle_frame_test, text="Folder:").grid(row=4, column=0, sticky="e") # create folder label, stick to the right side
        tk.Entry(self.middle_frame_test, textvariable=self.folder_path, width=40).grid(row=4, column=1, sticky="w") # create folder entry box
        tk.Button(self.middle_frame_test, text="Browse", command=self.select_folder).grid(row=4, column=2, sticky="w") # create button to select folder, runs select_folder function
        # ----- Start/Stop Buttons -----
        tk.Button(self.middle_frame_test, text="Start Test", command=None, bg="green", fg="white").grid(row=5, column=0, pady=5) # create button to start test
        tk.Button(self.middle_frame_test, text="Stop Test", command=None, bg="red", fg="white").grid(row=5, column=1, pady=5) # create button to stop test
        # ===== Live Plot =====
        bottom_frame = tk.Frame(self.test_tab) # Create bottom frame for plotting
        bottom_frame.grid(row=2,column=0,padx=10, pady=5,sticky='nsew') # add padding to x and y sides, fill both y and x directions

        self.fig_test, self.ax_test = plt.subplots(figsize=(6,4))
        self.ax_test.set_title("Live Data")
        self.ax_test.set_xlabel("Time (s)")
        self.ax_test.set_ylabel("Force (N)")
        self.line_test, = self.ax_test.plot([], [], 'r-')

        self.canvas_test = FigureCanvasTkAgg(self.fig_test, master=bottom_frame)
        self.canvas_test.draw()
        self.canvas_test.get_tk_widget().grid(row=0,column=0,sticky='nsew')

        self.xdata = []
        self.ydata = []
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
        right_top_frame = tk.Frame(top_frame,bd=1,relief='solid') # create right frame inside top frame
        right_top_frame.grid(row=1,column=1,sticky='nsew') # layout right frame in top frame
        self.plot_axes_frame_analysis_tab = tk.Frame(right_top_frame,bd=1,relief='solid') # create frame to display plot axes selection
        self.plot_axes_frame_analysis_tab.grid(row=4,column=0,columnspan=6,sticky='ew') # layout plot axes frame
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
        #tk.Label(top_frame,text='Analysis',font=('TkDefaultFont',16,'bold'),justify='center').grid(row=0,column=0,columnspan=4) # create and layout header
        tk.Label(left_top_frame,text='Analysis',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=0,column=0,columnspan=4,sticky='ew') # create and layout header
        tk.Label(right_top_frame,text='Plot',font=('TkDefaultFont',10,'bold'),justify='center').grid(row=0,column=0,columnspan=4,sticky='ew') # create and layout header
        # ----- File Name/Directory -----
        tk.Label(left_top_frame, text="Load Analysis Data:").grid(row=1, column=0, sticky="w") # create file name label, stick to the right side
        tk.Button(left_top_frame,text="Browse",command=self.select_folder).grid(row=1,column=1,sticky="w") # create button to select file directory for data
        # ===== Analysis Results (left top frame)=====
        '''
        On analysis side, create a selection to run analysis on mod check and tensile
            - mod check analysis will convert force and displacement to stress vs strain and output elastic modulus
            - tensile will do the same but for plastic region
        allow user to manually or automatically set axis limits
        allow user to set title and labels
        allow user to set legend location
        '''
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
        self.test_type_box_analysis_tab.bind("<<ComboboxSelected>>",self.on_selection_change_test_type_analysis_tab) # bind the drop down box to run plotting function
        # ----- Add Check Buttons -----
        self.enable_labels_analysis_tab = tk.Checkbutton(right_top_frame,
                                                         variable=self.enable_plot_labels_analysis_tab_tk,
                                                         command = self.on_selection_change_num_plots_analysis_tab,
                                                         text='Enable Plot Labels') # create checkbox to enable/disable plot labels
        self.enable_labels_analysis_tab.grid(row=1,column=2,sticky='w') # layout checkbutton
        self.enable_axes_labels_analysis_tab = tk.Checkbutton(right_top_frame,
                                                              variable=self.enable_axes_labels_analysis_tab_tk,
                                                              command = self.on_selection_change_num_plots_analysis_tab,
                                                              text='Enable Axes Labels') # create checkbox to enable/disable axes labels
        self.enable_axes_labels_analysis_tab.grid(row=1,column=3,sticky='w') # layout checkbutton
        self.enable_filtering_analysis_tab = tk.Checkbutton(right_top_frame,
                                                            variable=self.enable_filtering_analysis_tab_tk,
                                                            command = self.on_selection_change_num_plots_analysis_tab,
                                                            text='Enable Filtering') # create checkbox to enable/disable axes labels
        self.enable_filtering_analysis_tab.grid(row=1,column=4,sticky='w') # layout checkbutton
        # ----- Add Toggle Button -----
        self.toggle_btn = tk.Button(right_top_frame,
                                    text="▾",
                                    width=1,
                                    command=self.toggle_axes_selection_frame)
        # place it just above or to the right of the selection_frame
        self.toggle_btn.grid(row=2, column=4, sticky="ne")
        # ----- Plot/Run Buttons -----
        tk.Button(top_frame, text="Run Analysis", command=None).grid(row=2, column=0, pady=5,sticky='w') # create run analysis button
        tk.Button(top_frame, text="Plot Data", command=self.plot_test_data).grid(row=2, column=1, pady=5,sticky='w') # create plot button
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
        left_top_frame.columnconfigure(1,weight=1)
        right_top_frame.columnconfigure(4,weight=1)
        self.middle_frame_analysis.columnconfigure(0,weight=1)
        self.middle_frame_analysis.columnconfigure(1,weight=1)
        self.middle_frame_analysis.rowconfigure(0,weight=1)
        self.right_middle_frame_analysis.columnconfigure(0,weight=1)
        self.right_middle_frame_analysis.rowconfigure(0,weight=1)
        self.plot_axes_frame_analysis_tab.columnconfigure(9,weight=1)
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
        tk.Label(left_frame,text="Calibration Options:").grid(row=0,column=0,sticky="e")# create calibration options label
        tk.Label(left_frame,text="File Name:").grid(row=1,column=0,sticky="e") # define file name label
        self.file_name_calibration_tab = tk.Entry(left_frame,textvariable=self.file_name_calibration_tab,text="Enter File Name For Calibration Data",width=21) # define file name entry
        self.file_name_calibration_tab.grid(row=1,column=1,sticky='w')
        tk.Button(left_frame,text="Select File Directory",command=self.select_folder).grid(row=1,column=2,sticky="w") # create button to select file directory for new file
        tk.Label(left_frame,text="Number of Points for Calibration:").grid(row=0,column=2,sticky='w') # create label for number of calibration points
        self.num_points_entry_calibration_tab = tk.Entry(left_frame,textvariable=self.num_calibration_pts)
        self.num_points_entry_calibration_tab.grid(row=0,column=3,sticky='w') # create entry box for number of calibration points
        # ===== Create Calibration Drop Down Box ====
        calibration_options = ["LVDT","Pressure Transducer","I/P Transducer"] # define calibration options
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
        tk.Label(LVDT_frame,text='Zero Offset Position (inches):').grid(row=2,column=0,sticky='w') # create zero position offset label
        tk.Button(LVDT_frame,text='Measure',command=lambda: (self.funLVDT.measure(callback=True)),width=button_width).grid(row=1,column=2,sticky='w') # create measure button
        tk.Button(LVDT_frame,text='Set Zero Offset Postion',command=self.LVDT_get_zero,width=button_width).grid(row=2,column=2,sticky='w') # create zero offset button
        tk.Entry(LVDT_frame,textvariable=self.LVDT_current_position_tk,state='readonly',width=entry_width).grid(row=1,column=1,sticky='w') # display current position
        tk.Entry(LVDT_frame,textvariable=self.LVDT_cal_zero_tk,state='readonly',width=entry_width).grid(row=2,column=1,sticky='w') # display zero offset
        # ===== Pressure Transducer =====
        tk.Label(pressure_transducer_frame,text='Pressure Transducer',font=('TkDefaultFont',12,'bold'),justify='center').grid(row=0,column=0,columnspan=3,sticky='nsew') # create header label
        tk.Label(pressure_transducer_frame,text="Current Pressure (psi):").grid(row=1,column=0,sticky='e') # create current pressure label
        tk.Entry(pressure_transducer_frame,textvariable=self.PT_current_pressure_tk,state='readonly',width=entry_width).grid(row=1,column=1,sticky='w') # display current pressure
        tk.Button(pressure_transducer_frame,text='Measure',command=lambda: (self.funPT.readPSI(callback=True)),width=button_width).grid(row=1,column=2,sticky='w') # create measure button
        tk.Label(pressure_transducer_frame,text="Zero Offset Pressure (psi):").grid(row=2,column=0,sticky='w') # create zero offset pressure label
        tk.Entry(pressure_transducer_frame,textvariable=self.PT_cal_zero_tk,state='readonly',width=entry_width).grid(row=2,column=1,sticky='w') # create zero offset pressure entry
        tk.Button(pressure_transducer_frame,text='Set Zero Offset Pressure',command=self.PT_get_zero,width=button_width).grid(row=2,column=2,sticky='w') # create zero offset button
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
        left_frame = tk.Frame(self.tuning_tab) # create left side frame on tuning tab

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path.set(path)
            self.log_command(f"File path selected: {self.folder_path.get()}")

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
        # optionally: enable that row’s X/Y comboboxes now that data exists
        self.x_axis_cbs_array[idx].configure(state='readonly')
        self.y_axis_cbs_array[idx].configure(state='readonly')

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
            #print("made it here")
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

    def update_live_data(self):
        if self.running:
            force = random.uniform(0, 1000)
            pressure = random.uniform(0, 150)
            displacement = random.uniform(0, 10)

            self.force_var.set(f"{force:.2f}")
            self.pressure_var.set(f"{pressure:.2f}")
            self.displacement_var.set(f"{displacement:.2f}")

            self.xdata.append(len(self.xdata) * 0.5)
            self.ydata.append(force)
            self.line_test.set_data(self.xdata, self.ydata)
            self.ax_test.relim()
            self.ax_test.autoscale_view()

            self.canvas_test.draw()

            self.root.after(500, self.update_live_data)

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

    def plot_raw_test_data(self,file_path,test_method=None):
        if test_method=="MODcheck":
            # ===== Read and Format Data =====
            # ----- Plot Raw Data (force vs. displacement) -----
            data = pd.read_csv(file_path) # data frame
            force = data['force'].to_numpy() # convert data frame to numpy array
            position = data['position'].to_numpy() # convert data frame to numpy array
            self.pretest_fd_ax.cla() # clear old data
            self.pretest_fd_ax.plot(position,force,color='r') # plot x and y data
            self.pretest_fd_ax.set_ylim(0,np.max(force)+50) # set y limits
            self.pretest_fd_ax.set_xlim(0,np.max(position)+.01) # set x limits
            self.pretest_fd_ax.set_title('Modulus Check') # set title
            self.pretest_fd_ax.set_ylabel('Force (lb)') # set y label
            self.pretest_fd_ax.set_xlabel('Displacement (in)') # set x label
            self.pretest_fd_plot.draw_idle() # redraw canvas
            self.log_command('Modulus Check data plotted succesfully...') # log mod check plotting
        elif test_method=="tensile":
            pass
        elif test_method=="creep":
            pass
        elif test_method=="fatigue":
            pass

    def plot_test_data(self):
        # ===== Clear Axes =====
        self.analysis_ax.cla()
        self._col_map = {
                        "Force":              "force",
                        "Pressure":           "pressure",
                        "Position":           "position",
                        "Time":               "time_",
                        "Setpoint":           "setpoint",
                        "Temperature (CH1)":  "temp1",
                        "Temperature (CH2)":  "temp2",
                        "Temperature (CH3)":  "temp3",
                        "Temperature (CH4)":  "temp4",
                        "Stress":             "stress",
                        "Strain":             "strain",
                        "Cycles":             "cycles"} # map axes to data columns

        # ===== Itterate over each 
        for i, filepath in enumerate(self.plot_file_paths):
            if self.toggled_plots_array[i].get()==True: # if plot is enabled
                if not filepath:
                    continue  # skip empty rows
                try:
                    df = pd.read_csv(filepath)
                except Exception as e:
                    self.log_command(f"Failed to load {filepath}: {e}")
                    continue

                # ===== Get Plotting Axes =====
                x_axes_unmapped = self.x_axis_cbs_array[i].get()
                y_axes_unmapped = self.y_axis_cbs_array[i].get()
                x_axes = self._col_map.get(x_axes_unmapped)
                y_axes = self._col_map.get(y_axes_unmapped)
                if x_axes not in df.columns or y_axes not in df.columns:
                    self.log_command(f"Columns {x_axes}/{y_axes} not in {filepath}")
                    continue
                x = df[x_axes].to_numpy() # convert data into numpy array
                y = df[y_axes].to_numpy() # convert data into numpy array
                if self.enable_filtering_analysis_tab_tk.get()==True: # if filtering is enabled
                    try:
                        moving_avg_size = int(self.filter_entry_array[i].get()) # get size of moving average
                    except TypeError: # if a value other than a number is entered
                        self.log_command("Please enter a positive integer value for Moving Average...")
                    if moving_avg_size>0:
                        kernel = np.ones(moving_avg_size) / moving_avg_size # find the average of the given number of points
                        y = np.convolve(y, kernel, mode='same') # perform moving average on data with edge effects
                    elif moving_avg_size==0:
                        pass # pass if zero is entered, continues as if no moving average
                    else:
                        self.log_command("Please enter a positive integer value for Moving Average...")

                # ===== Plot =====
                if self.enable_plot_labels_analysis_tab_tk.get()==True:
                    lbl = self.plot_entry_array[i].get() # assign plot label
                else:
                    lbl = None # label is none type
                self.analysis_ax.plot(x,y,label=lbl) # plot figure

            # ===== Finalize Figure =====
            if self.enable_axes_labels_analysis_tab_tk.get()==True: # if axes labels are enabled
                self.analysis_ax.set_xlabel(self.x_label.get()) # set x label
                self.analysis_ax.set_ylabel(self.y_label.get()) # set y label
                self.analysis_ax.set_title(self.title.get())
            if self.enable_plot_labels_analysis_tab_tk.get()==True:
                self.analysis_ax.legend() # create legend if labels are applied
            self.analysis_ax.grid(True)
            self.analysis_plot.draw_idle()
            self.log_command("All series plotted.")

    def toggle_axes_selection_frame(self):
        if self.plot_axes_frame_analysis_tab.winfo_ismapped():
            # hide it
            self.plot_axes_frame_analysis_tab.grid_remove()
            self.toggle_btn.configure(text="▸")  # right‐arrow = “expand”
        else:
            # show it again
            self.plot_axes_frame_analysis_tab.grid()
            self.toggle_btn.configure(text="▾")

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
            # ----- Update Button Commands -----
            self.start_button_pretest_tab.configure(command=self.on_start_button_pretest_tab) # configure start button to start mod check
            self.stop_button_pretest_tab.configure(command=None) # configure stop button to stop mod check

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
            tk.Label(self.param_frame_test_tab, text="Stroke Rate:").grid(row=0, column=2, sticky="e") # create stroke rate label
            tk.Entry(self.param_frame_test_tab, textvariable=self.stroke_rate,width=40).grid(row=0, column=3, sticky="w") # create entry box for stroke rate
        elif method=="Creep":
            # ----- Creep Label & Entry -----
            tk.Label(self.param_frame_test_tab, text="Applied Constant Stress:").grid(row=0, column=2, sticky="e") # create stroke rate label
            tk.Entry(self.param_frame_test_tab, textvariable=self.stroke_rate,width=40).grid(row=0, column=3, sticky="w") # create entry box for applied constant stress
        elif method=="Fatigue":
            # ----- Fatigue Label, Entry and Drop-Down -----
            tk.Label(self.param_frame_test_tab, text="Frequency:").grid(row=0, column=2, sticky="e") # create frequency label
            tk.Entry(self.param_frame_test_tab, textvariable=self.frequency,width=40).grid(row=0, column=3, sticky="w") # create entry box for waveform

            tk.Label(self.param_frame_test_tab, text="Waveform:").grid(row=1, column=2, sticky="e") # create test method label, stick to the right side
            test_options_fatigue = ["Sinusoidal", "Triangular", "Square"] # list drop down items under "Test Method"
            self.test_box_test_tab_fatigue = ttk.Combobox(self.param_frame_test_tab, textvariable=self.waveform, values=test_options_fatigue, state="readonly") # create drop-down box
            self.test_box_test_tab_fatigue.grid(row=1, column=3, sticky="w") # layout drop box

    def on_selection_change_num_plots_analysis_tab(self,event=None):
        combo_box_width = 15
        entry_width = 16
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
        self.filter_entry_array = [] # create array to store entrys for filter values
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
            plot_labels = self.enable_plot_labels_analysis_tab_tk.get() # determine if plot labels are enabled
            filtering = self.enable_filtering_analysis_tab_tk.get() # determine if filtering is enabled
            if plot_labels==True and filtering==True:
                plot_label_column = 4 # define plot label column to be 4 when plot label and filtering is enabled
                filter_label_column = 6 # define filter label column to be 6 when plot label and filtering is enabled
                button_column = 8 # define button column to be 6 when plot label and filtering is enabled
                toggle_button_column = 9 # define toggle button column to be 9 when plot label and filtering is enabled
            if (plot_labels==True and filtering==False) or (plot_labels==False and filtering==True): # determine if one or both are enabled
                plot_label_column = 4 # define plot label column to be 4 when plot label or filtering is enabled
                filter_label_column = 4 # define filter label column to be 4 when plot label or filtering is enabled
                button_column = 6 # define button column to be 6 when plot label or filtering is enabled
                toggle_button_column = 7 # define toggle button column to be 7 when plot label or filtering is enabled
            if plot_labels==False and filtering==False: # if none are enabled
                button_column = 5 # define button column to be 5 when plot label is inactive
                toggle_button_column = 6 # define button column to be 6 when plot label is inactive

            btn = tk.Button(self.plot_axes_frame_analysis_tab,
                            text="Load File…",
                            width=12,
                            command=lambda idx=i: self.select_plot_file(idx))
            btn.grid(row=i, column=button_column,sticky='w')
            self.load_buttons.append(btn)
            # ===== Enable Plot Labels =====
            if self.enable_plot_labels_analysis_tab_tk.get()==True: # if enable plot labels
                tk.Label(self.plot_axes_frame_analysis_tab,text='Label:').grid(row=i,column=plot_label_column,sticky='w')
                plot_entry = tk.Entry(self.plot_axes_frame_analysis_tab,width=entry_width) # create temporary variable to store plot label
                plot_entry.grid(row=i,column=plot_label_column+1,sticky='w') # layout plot label entry
                self.plot_entry_array.append(plot_entry) # append entry to plot entry array
            # ===== Enable Filtering =====
            if self.enable_filtering_analysis_tab_tk.get()==True: # if filtering is enabled
                tk.Label(self.plot_axes_frame_analysis_tab,text='Moving Average:').grid(row=i,column=filter_label_column,sticky='w')
                filter_entry = tk.Entry(self.plot_axes_frame_analysis_tab,width=entry_width) # create temporary variable to store filter value
                filter_entry.grid(row=i,column=filter_label_column+1,sticky='w') # layout filter entry
                self.filter_entry_array.append(filter_entry) # append filter entry to filter entry array
            # ===== Create Toggle Buttons =====
            toggle_var = tk.IntVar(value=1) # define integer variable to store toggle value
            toggle_plot_button = tk.Checkbutton(self.plot_axes_frame_analysis_tab,
                                                variable=toggle_var)# create checkbox to enable/disable plot
            toggle_plot_button.grid(row=i,column=toggle_button_column,sticky='w') # layout checkbutton
            self.toggled_plots_array.append(toggle_var) # append array to store toggled plots
        # ===== Toggle Plots =====

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
            self.on_selection_change_test_type_analysis_tab() # update the options for the given test method - accounts for changing the number of plots
    
    def on_selection_change_test_type_analysis_tab(self,event=None):
        # ===== Get Current Plotting Method =====
        method = self.plot_test_type_analysis_tk.get() # define plotting method
        for x_cb, y_cb in zip(self.x_axis_cbs_array, self.y_axis_cbs_array): # clear values if test type has been changed
            x_cb.set('')
            y_cb.set('')

        # ===== Update ComboBox Values/Options =====
        if method=="Modulus Check":
            plot_options = ["Force",
                            "Pressure",
                            "Position",
                            "Time",
                            "Setpoint",
                            "Temperature (CH1)",
                            "Temperature (CH2)",
                            "Temperature (CH3)",
                            "Temperature (CH4)"]
        elif method=="Tensile":
            plot_options = ["Force",
                            "Stress",
                            "Pressure",
                            "Position",
                            "Strain",
                            "Time",
                            "Setpoint",
                            "Temperature (CH1)",
                            "Temperature (CH2)",
                            "Temperature (CH3)",
                            "Temperature (CH4)"]
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
        
        #clear out old widgets (labels)
        for child in self.param_frame_calibration_tab.winfo_children():
            child.destroy()
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
            tk.Label(self.param_frame_calibration_tab, text=f"Set Pressure:").grid(row=0, column=0, sticky="e") # create set pressure label
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

        self.num_points_entry_calibration_tab.configure(state='normal') # enable on change after calibration is complete
        self.file_name_calibration_tab.configure(state='normal') # enable on change after calibration is complete

    def on_click(self, event):
        # ===== Querying the clicked point =====
        if event.inaxes:
            x, y = event.xdata, event.ydata
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Point clicked at x={x:.4f}, y={y:.4f}\n")

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

    def start_modcheck_threading(self,max_load,load_rate,file_path):
        self.modcheck_is_running = True # define variable to determine if modcheck is running
        t = threading.Thread(target=self.funtest.MODcheck,args=(max_load,load_rate,file_path),daemon=True) # start modcheck as a background thread
        t.start()

    def log_command(self,message: str):
        # ===== Log Command =====
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

    def LVDT_calibration_call(self,displacement):
        self.funLVDT.record_calibration_point(displacement=displacement,num_points=self.num_calibration_pts.get()) # record calibration point

    def LVDT_get_zero(self):
        self.funLVDT.zero_position() # zero LVDT position
        df = pd.read_csv('LVDT_calibration_log.csv') # read calibration data
        LVDT_zero_offset = df['zero'].to_numpy()[-1] # convert zero to numpy array, use last value
        self.LVDT_cal_zero_tk.set(round(LVDT_zero_offset,5)) # update zero offset text variable

    def LVDT_get_current_position(self,current_position: float):
        self.LVDT_current_position_tk.set(round(current_position,5)) # update text variable for current position

    def PT_calibration_call(self,pressure):
        self.funPT.record_calibration_point(pressure=pressure,num_points=self.num_calibration_pts.get()) # record calibration point

    def PT_get_zero(self):
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
        self.funDAC.zero_reading() # zero PT reading
        df = pd.read_csv('IP_calibration_log.csv') # read calibration data
        IP_zero_offset = df['zero'].to_numpy()[-1] # convert zero to numpy array, use last value
        self.IP_cal_zero_tk.set(round(IP_zero_offset,3)) # update zero offset text variable

    def test_status(self,method,is_complete):
        path = os.path.join(self.folder_path.get(),self.file_name_pretest_tab_tk.get()+'.csv') # define file path
        if method=='MODcheck':
            if is_complete==True or is_complete=="updated":
                self.plot_raw_test_data(file_path=path,
                                        test_method='MODcheck')
                self.file_name_pretest_tab_entry.configure(state="disabled") # disable file name entry box after test is complete
                self.max_load_entry_pretest_tab.configure(state="disabled") # disable max load entry box after test is complete
                self.load_rate_entry_pretest_tab.configure(state="disabled") # disable load rate entry box after test is complete
                self.start_button_pretest_tab.configure(state="disabled") # disable start button after test is complete
        elif method=='tensile':
            if is_complete==True or is_complete=='updated':
                self.plot_raw_test_data(file_path=path,
                                        test_method='tensile')
        ''' Make this a callback in the main script for mod check, tensile and other tests.
        If modcheck is running and is complete, plot the whole thing, otherwise just update the plot.
        if running, read only all the buttons/ entrys'''

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
    
