
'''
A wxPython GUI to Functional Test Returns
Copyright (c) 2016 EnerNOC, Inc. All rights reserved.

In addition to Python2.6, YOU NEED WXPYTHON TO RUN THIS (AND PYSERIAL)

If you are using a Zebra Printer for MAC Labels, you must use Windows and the 
    Zebra Printer must be the Default Printer for the PC (requires win32print)

NOT DESIGNED FOR USE WITH OUT A FUNCTIONAL TEST FIXTURE
'''
#----------------------------------------------------------------------
# GUI/Threading Setup Stuff
#----------------------------------------------------------------------
import sys, os, time, getopt, logging
from threading import Thread
import serial, wx                   #Non-Core Packages (NEED win32print for Labels too)
import keygen                       #For Key Write
import decimal as DEC
from subprocess import Popen
import win32print
import string



#----------------------------------------------------------------------
# Tester Globals (UPDATE THIS STUFF TO RUN THE TEST (or use arguments))
#----------------------------------------------------------------------
MFG = True                         # Production using it?

# Where is it running?
if MFG:
    DIR = 'C:\Users\shawn.pate\Documents\Tester Files\BTL_FT\CommandApp_USBRelay.exe ' 
    ZEBRA_LC    = 5     # Zebra MAC Label Count (how many labels print)

    # ['G20_TTY','RX_TTY','LIL_TTY','METER_TTY','MUX_TTY']
    S2_COMMS    = ['COM29',  None,   'COM28',  None,   None]
    S2_C_COMMS  = ['COM78',  None,   'COM77', 'COM16', 'COM76' ]
    M2_COMMS    = ['COM86', 'COM77',  None,   'COM16', 'COM76' ]     
    M2_B_COMMS  = ['COM91', 'COM77',  None,   'COM16', 'COM76' ]

    
else:   # Engineering 
    DIR = 'C:\WorkSpace\M341P_FunctionalTest\M341P_FT\CommandApp_USBRelay.exe ' 
    ZEBRA_LC    = 0     # Zebra MAC Label Count (how many labels print)
    
    # ['G20_TTY','RX_TTY','LIL_TTY','METER_TTY','MUX_TTY']
    S2_COMMS    = ['COM87',  None,   'COM80',  None,   None]
    S2_C_COMMS  = ['COM92',  None,   'COM91', 'COM6', 'COM76' ]
    M2_COMMS    = ['COM86', 'COM77',  None,   'COM6', 'COM76' ]     
    M2_B_COMMS  = ['COM91', 'COM77',  None,   'COM6', 'COM76' ]

VER = '1.03'                        # returns.py Version number. 
M2commish = "M2_Commish.py"         # setup to load the Button1 test on the SD-CARD.
M2_485 = "M2_485.py"                #setup to load the Button1 test on the SD-CARD.
TEST_COUNT = 1                      # Count of total test loops without a restart.
FREQ = 2500
SOUNDTIME = 1000
FIRST_TEST_PASS = True              # When the test is started/restarted we need to wait for the Start button to be pressed.
SECOND_PASS_PLUS = False            # after the first pass don't reload the test list.
ZEBRA_DV    = None                  # Zebra Device (opened)

S2_PWR_ON   = "open 1"              # Turn on power to the S2.
S2_PWR_OFF  = "close 255"           # Turn off all relay.
S2_USB_ON   = "open 2"              # Turn on S2 USB power.
S2_USB_OFF  = "close 2"             # Turn off S2 USB power.


            
DEVICE_TYPE = 'S2_C'                # S2, M2, S2_C, M2_B 

G20_TTY     = S2_C_COMMS[0]         # G20_TTY
RX_TTY      = S2_C_COMMS[1]         # RX_TTY
LIL_TTY     = S2_C_COMMS[2]         # LIL_TTY
METER_TTY   = S2_C_COMMS[3]         # Hp Multimeter Com port.
MUX_TTY     = S2_C_COMMS[4]         # 2 Tracker2's wire as a Mux & several relay for power & ...
CAN_SKIP    = True                  # Set true to Enable FLASH_RX & KEY-PAIR Checkboxes
FLASH_COPRO = True                  # Skips Coprocessor Programming if False (CAN_SKIP must be True if not using CL)
WRITE_KP    = True                  # Skips MAC Key-Pair Association if False (CAN_SKIP must be True)
CUST_TEST   = False                 # start with Custom Tests disabled.


PWR_BIT     = '20'                  # Power on Bit.
PWR_ON      = True                  # Assume the State of Power is ON so it will turn OFF first pass.
MUX_VALUE   = PWR_BIT               # Set the state as if the power only is on.
UNITS       = ""                    # Meter units VAC OHMS...
METER_INIT  = False                 # the first time the Program is run init the meter.

S2_M3_VERS  = None                  # S2 M3 Version
Tests       = []                    # Global Test list.
TestNames   = []                    # Global Test names list
RequiredTests = [0,1,2,3]           # these tests always need to be Run prior to other tests
SelectedTests = RequiredTests
CustomTests = []                  # in custom tests if this test index is true the test will be run.
#----------------------------------------------------------------------
# GUI/Thread Globals
#----------------------------------------------------------------------
errStr = None                       # errors returned from self.run
TEST_START_TIME = None              # saves the start of the test.
CURRENT_LOG = None                  #File Handler for DUT Test Log
TEMP_LOG    = ""                    #File Handler used until we get a MAC.
TEST_STEP   = 0                     #0 for Init or Testing

G_PAN_ID    = 0                     #Global Panel (GUI Window) ID has the following stuff:
T_TXT_ID    = wx.NewId()            #GUI Window has this Static Text at the Top,
B_TXT_ID    = wx.NewId()            #GUI Window has this Static Text Under that,
P_TXT_ID    = wx.NewId()            # Label count listbox text.
LB_ID       = wx.NewId()            #GUI Window has this Button on the Left,
RB_ID       = wx.NewId()            #and GUI Window has this Button on the Right
# PIC1_ID     = wx.NewId()            #and GUI Window has this Image on the Left
PIC2_ID     = wx.NewId()            #and GUI Window has this Image on the Right
IM_DONE_ID  = wx.NewId()            #NotifiCAUTION Event for Worker Thread Completion
RX_CB_ID    = wx.NewId()            #Program  Checkbox ID
KP_CB_ID    = wx.NewId()            #Program Key-Pair Checkbox ID
CH_LB_ID    = wx.NewId()            # CheckBoxList ID
CT_CB_ID    = wx.NewId()            # Custom Test CheckBox show or hide tests list. 
DT_S2_ID    = wx.NewId()            # Device Type S2 CheckBox ID.
DT_S2_C_ID  = wx.NewId()            # Device Type S2_C CheckBox ID.
DT_M2_ID    = wx.NewId()            # Device Type M2 CheckBox ID.
DT_M2_B_ID  = wx.NewId()            # Device Type M2_B CheckBox ID.
LB_CNT_ID   = wx.NewId()            # Barcode Labels wanted listbox.
BTN_PRT_ID  = wx.NewId()            # Print a Barcode label from scanded of entered MAC.
TXT_BX_ID   = wx.NewId()            # MAC Text input box.

USB_PWR_ON  = '30'                  # power on the USB Devices Thumb drive, & RS-485... Leaving power on.
           

BOOT_T      = 0                     #Time of BTL Boot 2 Linux
BOOTLOG     = ""                    #Bootlog of DUT
DUT_MAC     = ""                    #MAC of DUT
EOT_STR = "\nPowering Down DUT...\n\rUSE CAUTION when removing PCA caps still CHARGED!!!"

#------------------------------------------------------Test Globals
DUT_LOG = logging.getLogger('dutLogger')    #Get a Logger for the DUT
DUT_MAC = ""                                #MAC of DUT
LIL_C       = None                          #Init M3 Console Invalid
RX_C        = None                          #Init RX Console Invalid
G20_C       = None                          #Init G20 Console Invalid
MUX_C       = None                          #Init the MUX Console Invalid
METER_C     = None                          #Init the Meter Console Invalid.

# ---------------------- M2 Rev B2 -------------------------------------------
M2_B_LEDMAX = 3
M2_B_LEDMIN = 2
M2_B_LEDMAX1 = 0.8
M2_B_LEDMIN1 = -0.1

M2_B_TestsEnabled = [True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False ]

M2_B_TEST_SIGNAL = ['+Supply','+52VDC','+12VDC','+3.3VDC','+5VDC','+1VDC','LED1','LED2','LED3','D20_GREEN_LED','D19_RED_LED','VREF','D9_PWR_LED']

M2_B_LIMIT_SHORTS = {'+Supply':350,'+52VDC':800,'+12VDC':700,'+3.3VDC':100000,\
                '+5VDC':20000,'VREF':5000}

M2_B_MUX_ADDR_SHORTS = {'+Supply':'00', '+52VDC':'01', '+12VDC':'02','+3.3VDC':'03',\
                '+5VDC':'04','+1VDC':'05','VREF':'0B'}

M2_B_MUX_ADDR_PWR = {'+Supply':'20', '+52VDC':'21', '+12VDC':'22','+3.3VDC':'23',\
                '+5VDC':'24','+1VDC':'25','LED1':'26','LED2':'27','LED3':'28','D20_GREEN_LED':'29','D19_RED_LED':'2A','VREF':'2B','D9_PWR_LED':'2C'}

M2_B_LIMIT_PWR_HI = {'+Supply':35, '+52VDC':54, '+12VDC':12.4,'+3.3VDC':3.4,\
                '+5VDC':5.2,'+1VDC':1.05,'LED1':M2_B_LEDMAX1,'LED2':M2_B_LEDMAX1,'LED3':M2_B_LEDMAX1,'D20_GREEN_LED':M2_B_LEDMAX,'D19_RED_LED':M2_B_LEDMAX,'VREF':3.4,'D9_PWR_LED':M2_B_LEDMAX}
                
M2_B_LIMIT_PWR_LO = {'+Supply':30, '+52VDC':50, '+12VDC':11.8,'+3.3VDC':3.2,\
                '+5VDC':4.9,'+1VDC':0.95,'LED1':M2_B_LEDMIN1,'LED2':M2_B_LEDMIN1,'LED3':M2_B_LEDMIN1,'D20_GREEN_LED':M2_B_LEDMIN,'D19_RED_LED':M2_B_LEDMIN,'VREF':3.2,'D9_PWR_LED':M2_B_LEDMIN}


# ---------------------- M2 Rev B2 -------------------------------------------

# ---------------------- M2 (M341P)--------------------------------------------

M2_TestsEnabled = [True, True, True, True, False, False, False, False, False, False, False, False, \
            False, False, False, False, False, False, False, False, False, False, False, False]

M2_TEST_SIGNAL = ['T1-8','T2-5','+Supply','+12VDC','+5VDC','+3.3VDC','+24VDC','+12V OUT','+1VDC','VREF']

M2_LIMIT_SHORTS = {'T1-8':15000, 'T2-5':100000, '+Supply':1000, '+BATT':2000, '+12VDC':700,'+ModemVDC':10000,'+3.3VDC':100000,\
                '+24VDC':4000,'+12V OUT':2000,'+5VDC':20000,'+1VDC':80,'VREF':5000}

M2_UX_ADDR_SHORTS = {'T1-8':'00', 'T2-5':'01', '+Supply':'02', '+BATT':'03', '+12VDC':'04','+ModemVDC':'05','+3.3VDC':'06',\
                '+24VDC':'07','+12V OUT':'08','+5VDC':'09','+1VDC':'0A','VREF':'0B'}

M2_MUX_ADDR_PWR = {'T1-8':'20', 'T2-5':'21', '+Supply':'22', '+BATT':'23', '+12VDC':'24','+ModemVDC':'25','+3.3VDC':'26',\
                '+24VDC':'27','+12V OUT':'28','+5VDC':'29','+1VDC':'2A','VREF':'2B'}

M2_LIMIT_PWR_HI = {'T1-8':0, 'T2-5':0, '+Supply':30, '+BATT':13.9, '+12VDC':14.9,'+ModemVDC':5.1,'+3.3VDC':3.4,\
                '+24VDC':25.8,'+12V OUT':12.4,'+5VDC':5.2,'+1VDC':1.05,'VREF':3.4}

M2_LIMIT_PWR_LO = {'T1-8':0, 'T2-5':0, '+Supply':20, '+BATT':13.5, '+12VDC':14.5,'+ModemVDC':4.9,'+3.3VDC':3.2,\
                '+24VDC':23.9,'+12V OUT':11.8,'+5VDC':4.9,'+1VDC':0.95,'VREF':3.2}

M2_LEDMAX = 3.6
M2_LEDMIN = 1.8

# ---------------------- M2 (M341P) -------------------------------------------

# ---------------------- S2 Rev C2 -------------------------------------------
S2_C_LEDMAX = 2.2
S2_C_LEDMAX1 = 3.1
S2_C_LEDMIN = 1.7

S2_C_TestsEnabled = [True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False ]
        
S2_C_TEST_SIGNAL = ['+52VDC','+5VDC','+3.3VDC','+1VDC','PowerLED','PulseLED1','PulseLED2',\
               'M3_HeartbeatLED','G20_HeartbeatLED','CellLED','LED801','RelayLED1','RelayLED2','GreenLanLED','YellowLanLED']

S2_C_LIMIT_SHORTS = {'+52VDC':500,'+3.3VDC':100000,'+5VDC':20000}

S2_C_MUX_ADDR_SHORTS = {'+52VDC':'00', '+5VDC':'01', '+3.3VDC':'02'}

S2_C_MUX_ADDR_PWR = {'+52VDC':'20', '+5VDC':'21', '+3.3VDC':'22', '+1VDC':'23', 'PowerLED':'24','PulseLED1':'25','PulseLED2':'26',\
                'M3_HeartbeatLED':'27','G20_HeartbeatLED':'28','CellLED':'29','LED801':'2A','RelayLED1':'2B','RelayLED2':'2C','GreenLanLED':'2D','YellowLanLED':'2E'}

S2_C_LIMIT_PWR_HI = {'+52VDC':54,'+5VDC':5.2,'+3.3VDC':3.4,'+1VDC':1.05,'PowerLED':S2_C_LEDMAX1,'PulseLED1':S2_C_LEDMAX,'PulseLED2':S2_C_LEDMAX,\
                'M3_HeartbeatLED':S2_C_LEDMAX,'G20_HeartbeatLED':S2_C_LEDMAX,'CellLED':S2_C_LEDMAX,'LED801':2.5,'RelayLED1':S2_C_LEDMAX,'RelayLED2':S2_C_LEDMAX,'GreenLanLED':0.8,'YellowLanLED':0.8}

S2_C_LIMIT_PWR_LO = {'+52VDC':50,'+5VDC':4.9,'+3.3VDC':3.2,'+1VDC':0.95,'PowerLED':S2_C_LEDMIN,'PulseLED1':S2_C_LEDMIN,'PulseLED2':S2_C_LEDMIN,\
                'M3_HeartbeatLED':S2_C_LEDMIN,'G20_HeartbeatLED':S2_C_LEDMIN,'CellLED':S2_C_LEDMIN,'LED801':S2_C_LEDMIN,'RelayLED1':S2_C_LEDMIN,'RelayLED2':S2_C_LEDMIN,'GreenLanLED':0.5,'YellowLanLED':0.5}

# ---------------------- S2 Rev C2 -------------------------------------------

S2_TestsEnabled = [True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False ]


MK_PANEL = {'TstDone':'Shorts Test Good!!', 'TstStart':'Testing Power Supplies...', 'Botton1':'NADA', 'Button2':'NADA'}



#----------------------------------------------------------------------
# Argument Handling: G20_TTY RX_TTY ZEBRA_LC NoFlash
#                ex: -b COM1 -l COM9 -z 4     -n
#----------------------------------------------------------------------
try:
    (opts, args) = getopt.getopt(sys.argv[1:], "b:l:z:fk")
except getopt.GetoptError, err:
    print str(err) # will print something like "option -a not recognized"
    print "Usage: -b G20-TTY -l RX-TTY -z LabelPrintNumber -f(NO RX flash) -k(NO Write Key)"
    sys.exit(1)
for (o, a) in opts:
    if o == "-b":
        G20_TTY = a
    elif o == "-l":
        RX_TTY = a
    elif o == "-f":
        FLASH_RX = False
    elif o == "-k":
        WRITE_KP = False
    elif o == "-z":
        ZEBRA_LC = int(a, 10)
    else:
        assert False, "unhandled option"
if DEVICE_TYPE == 'M2' or DEVICE_TYPE == 'M2_B':
    print "Returns Functional Test Starting with G20-TTY %s, RX-TTY %s, and \nwill" % (G20_TTY, RX_TTY),
elif DEVICE_TYPE == 'S2' or DEVICE_TYPE == 'S2_C':
    print "Returns Functional Test Starting with G20-TTY %s, LIL-TTY %s, and \nwill" % (G20_TTY, LIL_TTY),
    
if(FLASH_COPRO == False):
    print "NOT",
print "program the Coprocessor and \nwill",
if(WRITE_KP == False):
    print "NOT",
print "Write rsa_key.pem; \n%d MAC Label(s) to be printed\n" % ZEBRA_LC
#----------------------------------------------------------------------
# Thread Event Handler Stuff
#--------------------------------------------------Defines Result Event
def EVT_RESULT(win, func):
    win.Connect(-1, -1, IM_DONE_ID, func)
#------------------------Simple Event to Return Test Result (PASS/FAIL)
class ResultEvent(wx.PyEvent):
    def __init__(self, data):
        wx.PyEvent.__init__(self)   #Init Result Event
        self.SetEventType(IM_DONE_ID)
        self.data = data
#---------------------------------Thread class that Does [Testing] Work
class WorkerThread(Thread):
    
   

    def __init__(self, notify_window):
        Thread.__init__(self)       #Init Worker Thread Class
        self._notify_window = notify_window
        self._want_abort = 0 
        
        self.M2_B_Tests = [self.Shorts, self.PwrSuppliesTest, self.LinuxLogin, self.MacId, self.UsbBounce, self.ProgramRx, self.VisualLED, self.RxG20Comms, \
                      self.RS485, self.M2_B_RelayContact, self.Rx_EE_Data, self.Rx_Temp, self.Rx_AcReadBrownOut, \
                      self.M2_B_LED, self.M2_B_Button1, self.Rx_ResetButton, self.EncryptKey, self.WatchDog, self.G20_Reset, self.PrintZebraLabels ]
        
        self.M2_Tests = [self.Shorts, self.PwrSuppliesTest, self.LinuxLogin, self.MacId, self.UsbBounce, self.ProgramRx, self.VisualLED, self.RxG20Comms, \
                      self.Rx_ResetButton, self.EncryptKey, self.WatchDog, self.G20_Reset, self.M2_PowerModem, self.M2_Rx_Hv_InOut, self.M2_Rx_DigInOut, \
                      self.M2_AnalogIns, self.Rx_EE_Data, self.Rx_Temp, self.Rx_AcReadBrownOut, \
                      self.M2_Battery, self.M2_RxRedLED, self.M2_RxGreenLED, self.M2_RxPwrLED, self.PrintZebraLabels ]
        
        self.S2_C_Tests = [self.Shorts, self.PwrSuppliesTest, self.LinuxLogin, self.MacId, self.UsbBounce, self.ProgramM3, self.S2_C_Pulse, \
                      self.RS485, self.S2_C_AutoLed, self.S2_Relay, self.S2_Button1, self.S2_M3_Reset, \
                      self.EncryptKey, self.WatchDog, self.G20_Reset, self.S2_BrownOut, self.PrintZebraLabels ]
        
        self.S2_Tests = [self.S2_Pwr_RomBoot, self.LinuxLogin, self.MacId, self.UsbBounce, self.ProgramM3, self.S2_Pulse, \
                      self.RS485, self.VisualLED, self.S2_Relay, self.S2_Button1, self.S2_M3_Reset, \
                      self.EncryptKey, self.WatchDog, self.G20_Reset, self.S2_BrownOut, self.PrintZebraLabels ]
        
        
        
        # This starts the thread running on creation
        self.start()
       
    
        
        
       
    #-------------------------------------------------Run Worker Thread
    def run(self):
        global TEST_STEP, CURRENT_LOG, BOOTLOG, BOOT_T, DUT_MAC, S1_RX_VERS, S2_RX_VERS, RX_C, G20_C, MUX_C, METER_C
        global ZEBRA_LC, ZEBRA_DV, FLASH_RX, WRITE_KP, TEST_START_TIME, TEMP_LOG, errStr, TEST_COUNT, DUT_LOG
        global DEVICE_TYPE, Tests, TestNames, CustomTests, CUST_TEST, M2_B_TestsEnabled
        global S2_TestsEnabled, S2_C_TestsEnabled, M2_TestsEnabled
        
        self._want_abort = 0                    #TODO? Don't want to Abort Yet
        errStr = None                           # clear the error string
                                  
        
        
        if DEVICE_TYPE == 'S2':
            Tests = self.S2_Tests
            CustomTests = S2_TestsEnabled
        elif DEVICE_TYPE == 'S2_C':
            Tests = self.S2_C_Tests
            CustomTests = S2_C_TestsEnabled
        elif DEVICE_TYPE == 'M2':
            Tests = self.M2_Tests
            CustomTests = M2_TestsEnabled
        elif DEVICE_TYPE == 'M2_B':
            Tests = self.M2_B_Tests
            CustomTests = M2_B_TestsEnabled
            
        #+++++++++++++++++++++++++++++++++++++++
        TestNames = []
        
       
        for test in Tests:
            # Get the test name string and build a list to populate the custom tests CheckBoxList
            tmp = str(test)
            start = tmp.index('WorkerThread.' ) + 13
            end = tmp.index('of') - 1
            TestNames.append(tmp[start:end])

        if TEST_STEP == 0:                      #TEST_STEP = 0 => Initialize GUI
            print "GUI Initialization ERROR"
            errStr = "FAIL GUI Initialization ERROR"
            return
        
        if errStr == None and TEST_STEP <= len(Tests):  
            
            #if not FIRST_TEST_PASS:
            print "Doing Test Step %d" % TEST_STEP
            
            tmp = str(Tests[(TEST_STEP - 1)])
            start = tmp.index('WorkerThread.' ) + 13
            end = tmp.index('of') - 1
            TestName = tmp[start:end]
            #else: #Debug lines
                #pass
                #time.sleep(3)
                #print "lenght of Test: " + str(len(Tests))
                #print "Lenght of CustomTests: " + str(len(CustomTests))
            
            if not CUST_TEST:
                Tests[(TEST_STEP - 1)]()
            elif CustomTests[TEST_STEP -1]:
                
                Tests[(TEST_STEP - 1)]()
                MK_PANEL['TstStart'] = "Custom Test Mode!!"
                
                if TEST_STEP <= (len(Tests) - 1): 
                    # if the next test is M2_B_Button1 & the test is enabled.
                    if TestNames[TEST_STEP] == 'M2_B_Button1' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release RX_Button1 Button SW4 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL" 
                        
                    # if the next test is S2_Button1 & the test is enabled.
                    elif TestNames[TEST_STEP] == 'S2_Button1' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release Button1 Button SW1 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL" 
                        
                    # if the next test is S2_M3_Reset & the test is enabled.
                    elif TestNames[TEST_STEP] == 'S2_M3_Reset' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release M3_RESET Button SW600 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL" 
                    
                    # if the next test is Rx_ResetButton & the test is enabled.
                    elif TestNames[TEST_STEP] == 'Rx_ResetButton' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release RX_RESET Button SW3 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL" 
                    
                    # if the next test is G20_RESET & the test is enabled.
                    elif TestNames[TEST_STEP] == 'G20_RESET' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release G20_RESET Button SW100 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL"
                    
            else:
                print '\nSkipping --> ' + TestName 
                
                if TEST_STEP <= (len(Tests) - 1):
                    # if the next test is M2_B_Button1 & the test is enabled.
                    if TestNames[TEST_STEP] == 'M2_B_Button1' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release RX_Button1 Button SW4 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL" 
                        
                    # if the next test is S2_Button1 & the test is enabled.
                    elif TestNames[TEST_STEP] == 'S2_Button1' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release Button1 Button SW1 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL" 
                        
                    # if the next test is S2_M3_Reset & the test is enabled.
                    elif TestNames[TEST_STEP] == 'S2_M3_Reset' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release M3_RESET Button SW600 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL" 
                    
                    # if the next test is Rx_ResetButton & the test is enabled.
                    elif TestNames[TEST_STEP] == 'Rx_ResetButton' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release RX_RESET Button SW3 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL" 
                    
                    # if the next test is G20_RESET & the test is enabled.
                    elif TestNames[TEST_STEP] == 'G20_Reset' and CustomTests[TEST_STEP]:
                        MK_PANEL['TstDone'] = "Press/Release G20_RESET Button SW100 \n\r Click FAIL if Screen doesn't Change in 5s"
                        MK_PANEL['Button1'] = "NADA"
                        MK_PANEL['Button2'] = "FAIL"
        
        #+++++++++++++++++++++++++++++++++++++++
        elif TEST_STEP == len(Tests) + 1:    
            self.PrintZebraLabels
         
         
        #+++++++++++++++++++++++++++++++++++++++
        elif TEST_STEP >= len(Tests) + 2 or TEST_STEP <= len(Tests) + 3: #or TEST_STEP == len(Test) + 1:          #Last Step :~)
            if TEST_STEP == len(Tests) + 2:
                print "Test is DONE!!!"
                DUT_LOG.info("------------ALL TESTS PASSED!!!------------")
                if DEVICE_TYPE != 'S2':
                    self.switchMux('00')    # Power OFF the DUT
                else:
                    self.S2_Power(S2_PWR_OFF)
                
        #+++++++++++++++++++++++++++++++++++++++
        else:
            print "never see this in run"
            wx.PostEvent(self._notify_window, ResultEvent('FAIL ON BAD TEST_STEP'))
            print "Restarting test Program!"
            python = sys.executable
            os.execl(python, python, *sys.argv)
            
        #--------------------- check for a fail ------------------    
        if errStr != None:                  # Automantic FAIL
            
            if DEVICE_TYPE != 'S2':
                self.switchMux('00')        # Power OFF the DUT
            else:
                self.S2_Power(S2_PWR_OFF)
                
            wx.PostEvent(self._notify_window, ResultEvent(errStr))
            DUT_LOG.error( errStr )
                
        else:   # the test passed.
            wx.PostEvent(self._notify_window, ResultEvent("%d" % TEST_STEP))
            
    #------------------Method for use by main thread to signal an abort
    def abort(self):
        self._want_abort = 1
    #----------------------------------------------------------------------
    # Test Thread Functions
    #----------------------------------------------------------------------
    
    def BigRomBoot(self, timeOut = 0):
        global  G20_C
        forever = False
        bootlog = ""
        if timeOut == 0:
            forever = True
        bootTime = time.time()
        bootTimeOut = bootTime + timeOut        #90 Second Timeout For Linux Boot (120s watchdog reboot)
        while bootlog.find("RomBOOT") == -1:    #Wait for userFAIL for RomBOOT
            G20_Cgot = G20_C.read()
            bootlog = bootlog + G20_Cgot    
            if self._want_abort:                  #FAIL Clicked by User
                print "Aborting RomBOOT Hang..."
                return -2
            elif (not forever) and (time.time() >= bootTimeOut):
                return -1
        return 1
    
    #---------------------------------------------------------------------
    #  Shorts Test
    def Shorts(self):
        global TEST_STEP
        global TEMP_LOG, errStr, DEVICE_TYPE, M2_B_TEST_SIGNAL, M2_B_LIMIT_SHORTS, M2_B_MUX_ADDR_SHORTS, \
               M2_TEST_SIGNAL, M2_LIMIT_SHORTS, M2_UX_ADDR_SHORTS, S2_C_TEST_SIGNAL, S2_C_LIMIT_SHORTS, S2_C_MUX_ADDR_SHORTS

       

        #+++++++++++++++++++++++++++++++++++++++  
        if self.switchMux('00') == 1:               #Make sure the DUT is Powered OFF
            time.sleep(2)
        else:
            errStr = "FAIL MUX SWITCH POWER OFF " + \
              "\nTEST FIXTURE USB MAY NEED to be POWER CYCLED!!!"   #Wait for the power to go OFF.
           
        if errStr == None:  
            while FIRST_TEST_PASS:                      # wait for the start button to be pressed.
                time.sleep(1)
            #'''    
            
            #+++++++++++++++++++++++++++++++++++++++ 
            if DEVICE_TYPE == 'S2_C':
                TEST_SIGNAL = S2_C_TEST_SIGNAL 
                LIMIT_SHORTS = S2_C_LIMIT_SHORTS
                MUX_ADDR_SHORTS = S2_C_MUX_ADDR_SHORTS 
            elif DEVICE_TYPE == 'M2':   
                TEST_SIGNAL = M2_TEST_SIGNAL
                LIMIT_SHORTS = M2_LIMIT_SHORTS
                MUX_ADDR_SHORTS = M2_UX_ADDR_SHORTS
            elif DEVICE_TYPE == 'M2_B':
                TEST_SIGNAL = M2_B_TEST_SIGNAL
                LIMIT_SHORTS = M2_B_LIMIT_SHORTS
                MUX_ADDR_SHORTS = M2_B_MUX_ADDR_SHORTS
            else:
                errStr = 'FAIL Wrong Device Type For Shorts Test: ' + str(DEVICE_TYPE)
                return 1
        
            TEST_START_TIME = time.time()               # Save the start time.
            TEMP_LOG = "\n-----Test Start Time----> " + time.asctime() + "\n"       #Log start Time
            
            #-------TEST FOR SHORTS--------------
            for Signal in TEST_SIGNAL:
                if Signal != '+1VDC' and Signal.rfind("LED") == -1:       #Don't test 1VDC because the meter puts out 7.2VDC for ohms
                    print "Testing for Shorts on " + Signal + "..."            
                    self.switchMux(MUX_ADDR_SHORTS[Signal])
                    Reading = self.ReadMeter('KOHMS')
                    
                    if Reading == "---":                         # No reading was received.
                        errStr = "FAIL Shorts " + Signal + " No Meter Reading: ---"
                        break
                    elif float(Reading) >= LIMIT_SHORTS[Signal]:
                        TEMP_LOG += Signal + " Shorts Test Pass Reading: " + Reading + UNITS + "\n"
                        print Signal + " Shorts Test Pass Reading: " + Reading + UNITS
                    else:
                        errStr = 'FAIL ' + Signal + ' Shorts Reading: ' + Reading + UNITS + \
                                 '\nLimit:  ' + ">= " + str(LIMIT_SHORTS[Signal]) + UNITS 
                        break    
            #'''
            MK_PANEL['TstDone'] = "Shorts Test Good!!"    
            MK_PANEL['TstStart'] = "Testing Power Supplies..."
            MK_PANEL['Button1'] = "NADA"
            MK_PANEL['Button2'] = "NADA"
            
    #---------------------------------------------------------------------
    #  Power Supplies Test
    def PwrSuppliesTest(self):
        global TEMP_LOG, errStr, DEVICE_TYPE, M2_B_TEST_SIGNAL, M2_B_MUX_ADDR_PWR, M2_B_LIMIT_PWR_HI, M2_B_LIMIT_PWR_LO, \
               M2_TEST_SIGNAL, M2_MUX_ADDR_PWR, M2_LIMIT_PWR_HI, M2_LIMIT_PWR_LO, S2_C_TEST_SIGNAL, S2_C_MUX_ADDR_PWR, \
               S2_C_LIMIT_PWR_HI, S2_C_LIMIT_PWR_LO
               
        #+++++++++++++++++++++++++++++++++++++++ 
        if DEVICE_TYPE == 'S2_C':  
            TEST_SIGNAL = S2_C_TEST_SIGNAL 
            MUX_ADDR_PWR = S2_C_MUX_ADDR_PWR
            LIMIT_PWR_HI = S2_C_LIMIT_PWR_HI   
            LIMIT_PWR_LO = S2_C_LIMIT_PWR_LO 
        elif DEVICE_TYPE == 'M2':
            TEST_SIGNAL = M2_TEST_SIGNAL 
            MUX_ADDR_PWR = M2_MUX_ADDR_PWR
            LIMIT_PWR_HI = M2_LIMIT_PWR_HI   
            LIMIT_PWR_LO = M2_LIMIT_PWR_LO 
        elif DEVICE_TYPE == 'M2_B':
            TEST_SIGNAL = M2_B_TEST_SIGNAL 
            MUX_ADDR_PWR = M2_B_MUX_ADDR_PWR
            LIMIT_PWR_HI = M2_B_LIMIT_PWR_HI   
            LIMIT_PWR_LO = M2_B_LIMIT_PWR_LO 
        else:
            errStr = 'FAIL Wrong Device Type For Power Supplies Test: ' + str(DEVICE_TYPE)
            return 1
        #++++++++++++++++++++++++++++++++++++++++++++++                                 
        print "Powering DUT on!"
        
        if self.switchMux('20') != 1:
            errStr = 'FAIL MUX SWITCH POWER ON'
        #'''
        if errStr == None:
            time.sleep(4)
            #------------TEST POWER--------
            for Signal in TEST_SIGNAL:    
                    if Signal.rfind("LED") == -1:
                        print "Testing Power on " + Signal + "..."            
                        self.switchMux(MUX_ADDR_PWR[Signal])
                    
                        Reading = self.ReadMeter('DC')
                    
                        if Reading == "---":                         # No reading was received.
                            errStr = "FAIL Power " + Signal + " No Meter Reading: ---"
                            break
                        elif float(Reading) >= LIMIT_PWR_LO[Signal] and float(Reading) <= LIMIT_PWR_HI[Signal]:
                            TEMP_LOG += Signal + " Power Test Pass Reading: " + Reading + UNITS + "\n"
                            print Signal + " Power Test Pass Reading: " + Reading + UNITS
                        else:
                            errStr = 'FAIL ' + Signal + ' Power Reading: ' + Reading + UNITS + \
                                     '\nLimit:  ' + str(LIMIT_PWR_LO[Signal]) + "-"  + str(LIMIT_PWR_HI[Signal]) + UNITS
                            break    
            #'''     "Power Supplies Good!! Device Booting!!", "Waiting to Login...", "NADA", "NADA"
            MK_PANEL['TstDone'] = "Power Supplies Good!! Device Booting!!"    
            MK_PANEL['TstStart'] = "Waiting to Login..."
            MK_PANEL['Button1'] = "NADA"
            MK_PANEL['Button2'] = "NADA"
    
    #---------------------------------------------------------------------
    def S2_Pwr_RomBoot(self):
        global  errStr, FIRST_TEST_PASS, S2_PWR_ON
        
        
        
        if not FIRST_TEST_PASS:
            return
        
        while FIRST_TEST_PASS:                      # wait for the start button to be pressed.
                time.sleep(1)
                
        print "Waiting ENDLESSLY for RomBOOT..."
        print 'Test step = ' + str(TEST_STEP)
        
        print 'Turning on S2 power'
        Rtrn = self.S2_Power(S2_PWR_ON)
        if Rtrn:
            errStr = "Fail S2 Power On Failed! \n Try Unplugging & Replugging USB."
            return 1
            
        time.sleep(2)
        bootStat = self.BigRomBoot(0)
        if bootStat != 1:
            if bootStat != -2:              #USER ABORT IS -2
                wx.PostEvent(self._notify_window, ResultEvent('FAIL ON RomBOOT'))
            return 1
         
        MK_PANEL['TstDone'] = "RomBoot Good!! Device Booting!!"    
        MK_PANEL['TstStart'] = "Waiting to Login..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"
    #---------------------------------------------------------------------
    def RomBoot(self):                    #TEST_STEP = 1 => Wait for RomBOOT
        global  errStr
        print "Waiting for RomBOOT..."
        bootStat = self.BigRomBoot(5)
        if bootStat != 1:
            errStr = 'FAIL ON RomBOOT Timeout!'            #Timeout
    
    #---------------------------------------------------------------------
    def S2_Power(self, Action = None):
        global DIR
        result = 1      # set fail to start
        
        # Two possible device Id's
        UnitId1 = ' IGEUN '
        UnitId2 = ' CNVEJ '
        
        cmd = DIR + UnitId1 + Action
        
        if Action != None:
            p = Popen(cmd) #, stdout=PIPE, stderr=PIPE)
            p.communicate()
            result = p.returncode
            
            # if the first failed try the next device.
            if result:
                cmd = DIR + UnitId2 + Action
                p = Popen(cmd) #, stdout=PIPE, stderr=PIPE)
                p.communicate()
                result = p.returncode
                
                
        return result
    
    #---------------------------------------------------------------------
    #   Linux Login
    def LinuxLogin(self):
        global BOOTLOG, BOOT_T, errStr, S2_USB_ON, DEVICE_TYPE
        
        if DEVICE_TYPE != 'S2':
            print "Waiting for RomBOOT..."
            bootStat = self.BigRomBoot(5)
            if bootStat != 1:
                errStr = 'FAIL ON RomBOOT Timeout!'            #Timeout
                return 1
            print "RomBOOT received!!"
        
        timeout = 125
        print "Booting; Waiting " + str(timeout) + "s for Login.."
        BOOTLOG = "RomBOOT" 
        bootTime = time.time()
        bootTimeOut = bootTime + timeout    #125 Second Timeout For Linux Boot (125s watchdog reboot)
        while time.time() < bootTimeOut:
            G20_Cgot = G20_C.read()
            #print G20_Cgot + "\n\n"    #Debug Only
            BOOTLOG = BOOTLOG + G20_Cgot
            if BOOTLOG.rfind("at91sam9g20ek login:") != -1:
                bootDone = time.time()
                break
        else:
            #TODO SAVE BIGTOE BOOTLOG?
            try:
                if time.time() > bootTimeOut:
                    print "Timeout on RomBOOT time: "  + str(time.time())
                    
                print "[%d]:\n%s" % (len(BOOTLOG), BOOTLOG)
            except:
                print "NOTE THIS:  Bootlog NOT Printable"
            errStr = 'FAIL ON RomBOOT'
            
        if errStr == None:  # No ERRORS??
            #print "[%d]:\n%s" % (len(BOOTLOG), BOOTLOG)    #Debug Only
            BOOT_T = bootDone - (bootTime + 2)  #+2 for RomBOOT
            print "Got Login Prompt in %d seconds" % BOOT_T
           
            G20_Cgot = self.SerialPortWrite(G20_C, "root\n")    # UserId: root
            
            #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
            if G20_Cgot.find("Password:") == -1:
                #TODO SAVE BIGTOE BOOTLOG?
                errStr = 'FAIL ON LOGIN USER'
            
            if errStr == None:   # No ERRORS??  
                G20_Cgot = self.SerialPortWrite(G20_C, "!enadmin1\n", 2)   # send the password.
                
                #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
                if G20_Cgot.rfind("root@at91sam9g20ek:~#") == -1:       #24 for "\r\nroot@at91sam9g20ek:~# "
                    #TODO SAVE BIGTOE BOOTLOG?
                    errStr = 'FAIL ON LOGIN PASSWORD'
                    
                if errStr == None:  # No ERRORS??
                    print "Moving to smallfoot-app..."
                    
                    G20_Cgot = self.SerialPortWrite(G20_C, "cd /var/smallfoot/smallfoot-app\n")
                    #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
                    #82 "cd /var/small...+root@at91sa...mallfoot-app#"
                    if G20_Cgot.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app#") == -1:
                        #TODO SAVE BIGTOE BOOTLOG?
                        errStr = 'FAIL ON SD FS 1 (REPLACE CARD?)'
                    elif DEVICE_TYPE != 'S2':
                        print 'Turning on ' + DEVICE_TYPE + ' USB power'
                        if self.switchMux(USB_PWR_ON) != 1:
                            errStr = 'FAIL MUX SWITCH POWER ON'
                    else:   # S2 Only!
                        print 'Turning on S2 USB power'
                        Rtrn = self.S2_Power(S2_USB_ON)
                        if Rtrn:
                            errStr = "Fail USB Power Failed! \n Try Unplugging & Replugging USB."
                            return 1
                              
                            
                    
                    time.sleep(3)   # Wait for the USB connect messages to happen.
                    # Add USB power on to Boot log
                    BOOTLOG += G20_C.readall()
            
                    
        if errStr != None:
            return 1
        
        #"Logged In!! Please Wait...", "Verifying Bootlog and MAC...", "NADA", "NADA"
        MK_PANEL['TstDone'] = "Logged In!! Please Wait..."    
        MK_PANEL['TstStart'] = "Verifying Bootlog and MAC..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"
        
    #---------------------------------------------------------------------
    #       Get MAC ID 
    def MacId(self):
        global CURRENT_LOG, BOOTLOG, BOOT_T, DUT_MAC
        global DUT_LOG, TEMP_LOG, errStr, G20_C, DEVICE_TYPE
        
        #TEST_STEP = 3 => MAC & Bootlog Verification
        #MAC Test
        print "Getting MAC..."
        testTimeOut = time.time() + 5
        G20_Cgot = ""
        G20_C.flushInput()
        G20_C.write("python test/MAC_Read.py\n")
        G20_C.flush()
        
        while time.time() < testTimeOut:
            time.sleep(1)
            G20_Cgot = G20_C.readline()
            if G20_Cgot.rfind("00-") != -1:
                start = G20_Cgot.index("00")
                DUT_MAC = G20_Cgot[start:start+17]
                break
    
            if G20_Cgot.rfind("D8-") != -1:
                start = G20_Cgot.index("D8")
                DUT_MAC = G20_Cgot[start:start+17]
                break
            
        #print "Debug 2 [%d]:%s" % (len(DUT_MAC), DUT_MAC)    #Debug Only
        if (DUT_MAC.rfind("D8-80-39") != -1 or DUT_MAC.rfind("00-04-A3") != -1 or DUT_MAC.rfind("00-1E-C0") != -1) and len(DUT_MAC) == 17:
            #Start Logging to File (if not doing so already)
            if CURRENT_LOG is None:
                DUT_LOG.setLevel(logging.INFO)
                FILENAME = DEVICE_TYPE + "_" + DUT_MAC
                CURRENT_LOG = logging.FileHandler( "ReturnsTestLogs/%s.log" % FILENAME )
                CURRENT_LOG.formatter = logging.Formatter("%(asctime)s  %(message)s")
                DUT_LOG.addHandler( CURRENT_LOG )
                print "Got A MAC started logging to M2_TestLogs/%s.log" % DUT_MAC
                DUT_LOG.info(TEMP_LOG)                          # put the Shorts & Power tests in first
                DUT_LOG.info( "%s TEST LOG" % DUT_MAC )
                DUT_LOG.info( "Device Type: %s" % DEVICE_TYPE )
                DUT_LOG.info( "Linux Boot Time: %d seconds" % BOOT_T)
            else:
                print "STILL LOGGING WTF?? NO LOG FOR DUT!!!!!!"
        else:
            errStr = 'FAIL ON INVALID MAC'
            return 1
        #-------------  Check LAN if S2 ---------
        if DEVICE_TYPE == 'S2' or DEVICE_TYPE == 'S2_C':
            self.EtherNet()
        
        #------------- Check USBs registered -------------
        if BOOTLOG.rfind("usb 1-1: new full speed USB device") == -1:
            errStr = 'FAIL ON USB 1-1'
            DUT_LOG.error( "Bootlog:\n%s" %BOOTLOG )    #Save Bootlog
        else: 
            DUT_LOG.info( "USB 1-1 Test: Pass" )
            
        if errStr == None:  # No ERRORS??
            #USB 2 TEST
            if BOOTLOG.rfind("usb 1-2: new full speed USB device") == -1:
                errStr = 'FAIL ON USB 1-2'
                DUT_LOG.error( "Bootlog:\n%s" %BOOTLOG )    #Save Bootlog
            else: 
                DUT_LOG.info( "USB 1-2 Test: Pass" )
        else:
            return 1
        
                    
        BOOTLOG = ""
        TEMP_LOG = ""
        #"Verified!! Please Wait...", "Testing USB Ports...", "NADA", "NADA"
        MK_PANEL['TstDone'] = "Verified!! Please Wait..."   
        MK_PANEL['TstStart'] = "Testing USB Ports..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"
            
    
    #---------------------------------------------------------------------
    #     Ethernet Test
    def EtherNet(self):
        global errStr, DUT_LOG, BOOTLOG
        
        print "Testing Ethernet..."
        if BOOTLOG.rfind("No lease") != -1:
            wx.PostEvent(self._notify_window, ResultEvent('FAIL ON ETHERNET (NO LEASE)'))
            DUT_LOG.error( "Bootlog:\n%s" %BOOTLOG )    #Save Bootlog
            errStr = 'FAIL ON ETHERNET (NO LEASE)'
            return 1
        print'Ethernet Test Passed'
        
    #---------------------------------------------------------------------
    #    TEST_STEP = 4 => TPS USB Bounce
    def UsbBounce(self):                    
        global errStr, DUT_LOG, G20_C, BOOTLOG
        
        print "Testing USB Disconnect/Reconnect..."
        
        G20_Cgot = self.SerialPortWrite(G20_C, "echo 0 > /sys/class/gpio/tps_enable/value\n")
        #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
        if G20_Cgot.rfind("usb 1-1: USB disconnect") == -1 or G20_Cgot.rfind("usb 1-2: USB disconnect") == -1:
            errStr = 'FAIL ON USB DISCONNECT'
            
        if errStr == None:  # No ERRORS??
            
            G20_Cgot = self.SerialPortWrite(G20_C, "echo 1 > /sys/class/gpio/tps_enable/value\n")
            #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
            if G20_Cgot.rfind("usb 1-1: new full speed USB device") == -1 or G20_Cgot.rfind("usb 1-2: new full speed USB device") == -1:
                errStr = 'FAIL ON USB RECONNECT'
            
            if errStr == None:  # No ERRORS??
                DUT_LOG.info( "USB Test: Pass" )
                
        #"USB Ports Good!! Please Wait...", "Programming RX...", "NADA", "NADA"
        MK_PANEL['TstDone'] = "USB Ports Good!! Please Wait..."   
        MK_PANEL['TstStart'] = "Programming Coprocessor..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"
    
    #---------------------------------------------------------------------
    # Program the Coprocessor on the S2 
    def ProgramM3(self):
        global errStr, DUT_LOG, G20_C, LIL_C
        if FLASH_COPRO:
            print "Checking M3 Version..."
            G20_Cgot = self.SerialPortWrite(G20_C, "cd /var/smallfoot/smallfoot-app\n")
            #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
            if G20_Cgot.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app#") == -1:
                errStr = 'FAIL ON SD FS moving to smallfoot-app (REPLACE CARD?)'
            if errStr == None:
                #Identify M3 Binary & version
                G20_Cgot = self.SerialPortWrite(G20_C, "ls /var/smallfoot/littletoe\n")
                #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
                m3BinIndex = G20_Cgot.rfind( "btl_combo" )
                if ( m3BinIndex ) == -1:
                    errStr = 'FAIL ON M3 find btl_comboXXX.BIN'
                    DUT_LOG.error( "No M3 Combo Bin Found:\n%s" % G20_Cgot )
                    return 1
                binName = G20_Cgot[ (m3BinIndex) : (m3BinIndex + 18) ] #btl_combo_NNNN.bin
                S2_M3_VERS = G20_Cgot[ (m3BinIndex + 10) : (m3BinIndex + 14) ] # NNNN
                print "SD-CARD M3 Version: " + S2_M3_VERS
            
#                # Check the Version on the processor before we do anything.
#                G20_Cgot = self.SerialPortWrite(G20_C, "python test/FuncTest/BTL/btlGetHwVersion-FT.py\n", 5)
#                VerIndex = G20_Cgot.rfind("Ver ")
#                versStr = G20_Cgot[ (VerIndex + 4) : (VerIndex + 8) ]
#                print "Version CMD = " + versStr
#                print "File Version = " + S2_M3_VERS
                # if the version isn't right reprogram it.
#               if S2_M3_VERS != versStr:
                print "Moving to utils..."
                G20_Cgot = self.SerialPortWrite(G20_C, "cd utils\n")
                if G20_Cgot.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app/utils#") == -1:
                    errStr = 'FAIL ON SD FS moving to utils (REPLACE CARD?)'
            
                DUT_LOG.info( "Erasing M3..." )
                #print "Doing Erase..."
                timeOut = time.time() + 20
                G20_Cgot = self.SerialPortWrite(G20_C,"python m3loader.py -e\n",1)
                while time.time() < timeOut:
                    G20_Cgot += G20_C.read()
                    #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
                    if G20_Cgot.find( "root@at91sam9g20ek:/var/smallfoot/smallfoot-app/utils#" ) != -1:
                        break
                else:
                    errStr = 'FAIL ON M3 ERASE TIMEOUT'
                    DUT_LOG.error( "Erase M3 Timeout:\n%s" % G20_Cgot )
                    return 1
                    
                DUT_LOG.info( "Erase M3 took %d seconds" % (time.time() - (timeOut - 20)) )

                DUT_LOG.info( "Programming M3..." )
                #print "Doing Program..."
                LIL_C.flushInput()
                G20_C.flushInput()
                timeOut = time.time() + 60
                G20_Cgot = self.SerialPortWrite(G20_C,"python m3loader.py -a 0x08000000 -f /var/smallfoot/littletoe/" + binName + "\n", 1)
                while time.time() < timeOut:
                    G20_Cgot += G20_C.read()
                    #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
                    if G20_Cgot.find( "root@at91sam9g20ek:/var/smallfoot/smallfoot-app/utils#" ) != -1:
                        break
                else:
                    errStr =  'FAIL ON PROGRAM M3 TIMEOUT'
                    DUT_LOG.error( "Prog M3 Timeout:\n%s" % G20_Cgot )
                    return 1
                #print "[%d]:%s" % (len(output), output)
                if G20_Cgot.rfind("Errno") != -1 or G20_Cgot.rfind("Traceback") != -1:
                    errStr = 'FAIL ON PROGRAM M3 ERROR'
                    DUT_LOG.error( "Prog M3 FAIL:\n%s" % G20_Cgot )
                    return 1
                DUT_LOG.info( "M3 Programming took %d seconds" % (time.time() - (timeOut - 60)) )
                
                lilCgot = LIL_C.readall()   #Read enough to get version and ID
                #print "[%d]:%s" % (len(lilCgot), lilCgot)
                m3IdIndex = lilCgot.rfind( "Image 1 is a good image" )
                if ( m3IdIndex ) == -1:
                    errStr = 'FAIL ON M3 message IMAGE 1 GOOD'
                    DUT_LOG.error( "No Image 1 Good Message:\n%s" % lilCgot )
                    return 1
                else:
                    #m3IdStr = lilCgot[ (m3IdIndex+6) : (m3IdIndex+6+8) ]    #+6 for "ID: 0x" +8 for HHHHHHHH
                    DUT_LOG.info( "Got M3 Image 1 Good Message!")
                    
                #lilCgot = LIL_C.read(650)   #Read enough to get version and ID
                if lilCgot.find( S2_M3_VERS) == -1:
                    errStr = 'FAIL ON M3 VERSION'
                    DUT_LOG.error( "FAIL Bad M3 Version: %s" % lilCgot )
                    return 1
                
                print "Moving back to smallfoot-app..."
                G20_C.write("cd ..\n")
                G20_C.flush()
                MK_PANEL['TstDone'] = "Program M3 Good!! Please Wait..."
                    
#                # M3 Firmware version is current  
#                else:
#                    MK_PANEL['TstDone'] = "M3 Version is " + versStr + " skipping program!"
                
        else:
            #print "DANGER DANGER Skipping Programming M3 Step!!"
            DUT_LOG.warning( "DANGER DANGER Skipping Programming M3 Step!!" )
            print "Getting Hardware Version..."
            G20_Cgot = self.SerialPortWrite(G20_C, "python test/FuncTest/BTL/btlGetHwVersion-FT.py\n")
            print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
            MK_PANEL['TstDone'] = "Skipping Program M3 !!..."
        
           
        MK_PANEL['TstStart'] = "Testing Pulse Inputs..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"
    
    #---------------------------------------------------------------------
    #    TEST_STEP = 5 => Program RX
    def ProgramRx(self):                    
        global errStr, DUT_LOG, G20_C
        print "Moving to utils..."
        
        if FLASH_COPRO:
            G20_Cgot = self.SerialPortWrite(G20_C, "cd utils\n")
            #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
            if G20_Cgot.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app/utils#") == -1:
                errStr = 'FAIL ON SD FS 2 (REPLACE CARD?)'
                
            if errStr == None:  # No ERRORS??
                output = ""
                DUT_LOG.info( "Programming RX..." )
                #print "Doing Programming..."
                G20_C.write("python RXLoader.py ../../m2m/M341P\t\n")
                G20_C.flush()
                timeOut = time.time() + 70
                while time.time() < timeOut:
                    G20_Cgot = G20_C.read()
                    #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
                    output = output + G20_Cgot
                    if output.find( "Chip is ready for programming" ) != -1 and \
                       output.find( "Programming Block ffff0000" ) != -1 and \
                       output.find( "root@at91sam9g20ek:" ) != -1:
                        break
                else:
                    errStr = 'FAIL ON RX PROGRAMMING TIMEOUT'
                    DUT_LOG.error( "Programming RX Timeout:\n%s" % output )
                    return 1
                
                if errStr == None:  # No ERRORS??
                    #print "[%d]:%s" % (len(output), output)    #Debug Only
                    if output.rfind("Errno") != -1 or output.rfind("Traceback") != -1:
                        errStr = 'FAIL ON RX PROGRAMMING ERROR'
                        DUT_LOG.error( "Programming RX FAIL:\n%s" % output )
                        return 1
                    
                    if errStr == None:  # No ERRORS??
                        DUT_LOG.info( "Programming RX took %d seconds" % (time.time() - (timeOut - 40)) )
                        print "Moving back to smallfoot-app..."                        
                        G20_Cgot = self.SerialPortWrite(G20_C, "cd ..\n")
                        
                MK_PANEL['TstDone'] = "Program RX Good!! Please Wait..." 
                
        else:
            # KGB??? 
            print "DANGER DANGER Skipping Programming RX Step!!"
            DUT_LOG.warning( "DANGER DANGER Skipping Programming RX Step!!" )
            MK_PANEL['TstDone'] = "Skipping Program RX!!..." 
          
        MK_PANEL['TstStart'] = "Setup G20 LEDs test..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"   
        
        
    #---------------------------------------------------------------------
    #      old S2 Visual Blink LEDS Test
    def VisualLED(self):      
        global errStr, G20_C
        print "Cell and App LEDs On (no Blink)..."
                 
        G20_C.write("echo 255 > /sys/class/leds/wangood/brightness\n")
        G20_C.flush()
        G20_C.write("echo 255 > /sys/class/leds/appheartbeat/brightness\n")
        G20_C.flush()
        G20_C.write("echo 255 > /sys/class/leds/heartbeat/brightness\n")
        G20_C.flush()
        
        
        #"Inspect G20 LEDs 1, 2, 3 close to U1/G20", "(ALL On or Bliking PASS)", "PASS", "FAIL"
        MK_PANEL['TstDone'] = "Inspect ALL 9 LEDs"   
        MK_PANEL['TstStart'] = "(ALL On or Bliking PASS)"
        MK_PANEL['Button1'] = "PASS"
        MK_PANEL['Button2'] = "FAIL" 
        
        
    #---------------------------------------------------------------------
    #    test transaction RX <-> G20
    def RxG20Comms(self):
        global errStr, DUT_LOG, G20_C
        print "Testing RX<-->G20 Communications..."               # previous step to clear before starting test.
        G20_Cgot = self.SerialPortWrite(G20_C, "python test/RXCommTest.py\n", 2)
        #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
        if G20_Cgot.rfind("ERROR") != -1 or G20_Cgot.rfind("PASS") == -1:
            errStr = 'FAIL RX<-->G20 COM'
            DUT_LOG.error( "Bad RX<-->G20 COMs Test:\n%s" % G20_Cgot )
            
        else: 
            DUT_LOG.info( "RX<-->G20 COMs: Pass" )
            
        #"RX<-->G20 COM Test Good!! Please Wait...", " Testing RS485...", "NADA", "NADA"
        MK_PANEL['TstDone'] = "RX<-->G20 COM Test Good!! Please Wait..."   
        MK_PANEL['TstStart'] = " Testing RS485..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"    
        
    #---------------------------------------------------------------------
    # 
    def S2_Pulse(self):
        global errStr, DUT_LOG, G20_C
        
        # --- Shawn's comment --- fixes pre 2.5 pulse2 test for old S2s
        G20_C.write("sed -i 's/time.sleep(1)/time.sleep(4)\\1/'  test/FuncTest/BTL/btlGet2Pulse-FT.py\n")
        G20_Cgot = ""
        while G20_Cgot.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app# ") == -1:
            G20_Cgot += G20_C.readall()
            
        print "Waiting for 2 Pulse Input test..."
        G20_C.flushInput()
        G20_Cgot = G20_C.readall()            #Try to read (cd ..\r\nroot@at91sam9g20ek:/var/smallfoot/smallfoot-app# ) for Flash
        #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
        G20_C.write("python test/FuncTest/BTL/btlGet2Pulse-FT.py\n")
        G20_C.flush()
        #313 for success w/flash (errors should be less) but about 622 with usb from TPS if no flash so just read till Prompt
        while G20_Cgot.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app# ") == -1:
            G20_Cgot += G20_C.readall()
        #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
        if G20_Cgot.rfind("ERROR") != -1 or G20_Cgot.rfind("SUCCESS: PC1") == -1 or G20_Cgot.rfind("SUCCESS: PC2") == -1 :
            errStr = 'FAIL ON LOW SPEED PULSE COUNT'
            DUT_LOG.error( "Bad Low Speed Pulse:\n%s" % G20_Cgot )
            return 1
        else: DUT_LOG.info( "Low Speed 2 Pulse Counters Test: Pass" )
        
        MK_PANEL['TstDone'] = "S2 2 Pulse Test Good!!..."   
        MK_PANEL['TstStart'] = " Testing RS485..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"    
    #---------------------------------------------------------------------
    # 
    def S2_C_Pulse(self):
        global errStr, DUT_LOG, G20_C
        print "Waiting for 6 Pulse Input test..."
        G20_C.flushInput()
        G20_Cgot = G20_C.read(56)            #Try to read (cd ..\r\nroot@at91sam9g20ek:/var/smallfoot/smallfoot-app# ) for Flash
        #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
        G20_C.write("python test/FuncTest/BTL/btlGet6Pulse-FT.py\n")
        G20_C.flush()
        Cout = ""
        #313 for success w/flash (errors should be less) but about 622 with usb from TPS if no flash so just read till Prompt
        while Cout.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app# ") == -1:
            G20_Cgot = G20_C.read()
            #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
            Cout = Cout + G20_Cgot
        #print "[%d]:%s" % (len(Cout), Cout)
        if Cout.rfind("ERROR") != -1 or Cout.rfind("SUCCESS: PC1") == -1 or Cout.rfind("SUCCESS: PC2") == -1 \
                                     or Cout.rfind("SUCCESS: PC3") == -1 or Cout.rfind("SUCCESS: PC4") == -1 \
                                     or Cout.rfind("SUCCESS: PC5") == -1 or Cout.rfind("SUCCESS: PC6") == -1:
            
            wx.PostEvent(self._notify_window, ResultEvent('FAIL ON LOW SPEED PULSE COUNT'))
            DUT_LOG.error( "Bad Low Speed Pulse:\n%s" % Cout )
            return
        else: DUT_LOG.info( "Low Speed Pulse Counters Test: Pass" )
        
        #-------------- TEST Hi Speed Pulse inputs. ---------------
        # get the command prompt  
        
        while Cout.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app# ") == -1:
            G20_C.write("\n")
            G20_Cgot = G20_C.read()
        
        print "Waiting for Hi Speed Pulse Counters test..."
        G20_C.flushInput()
        #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
        G20_C.write("python test/FuncTest/BTL/btlGetHiSpeedPulses-FT.py\n")
        G20_C.flush()
        Cout = ""
        while Cout.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app# ") == -1:
            G20_Cgot = G20_C.read()
            Cout = Cout + G20_Cgot
        
        Cout_list = Cout.split()

        print Cout_list[4] + "  " + Cout_list[7]
        
        K5_pulse1_1 = int(Cout_list[4])
        K5_pulse2_1 = int(Cout_list[7])
         
        retry_count = 3
        Hi_Speed_Retry = True
        while(Hi_Speed_Retry and retry_count > 0 ):
            self.switchMux('70')                            # Trigger the Hi Speed pulse generator.
            time.sleep(3.3)
            self.switchMux('30')                            # clear the trigger.
            #time.sleep(1)                                   # wait for the pulses to complete.
            
            G20_C.readall() 
            G20_C.write("python test/FuncTest/BTL/btlGetHiSpeedPulses-FT.py\n") 
            G20_C.flush()
            Cout1 = ""
            while Cout1.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app# ") == -1:
                G20_Cgot = G20_C.read()
                Cout1 = Cout1 + G20_Cgot
                
            Cout1_list = Cout1.split()

            print Cout1_list[4] + "  " + Cout1_list[7]
            
            K5_pulse1_2 = int(Cout1_list[4])
            K5_pulse2_2 = int(Cout1_list[7])
            
            if Cout.rfind("ERROR") != -1 or Cout1.rfind("ERROR") != -1 \
               or (K5_pulse1_2 - K5_pulse1_1) != 200 or (K5_pulse2_2 - K5_pulse2_1) != 200:
                K5_pulse1_1 = K5_pulse1_2
                K5_pulse2_1 = K5_pulse2_2
                retry_count -= 1
                if(retry_count == 0):
                    wx.PostEvent(self._notify_window, ResultEvent('FAIL ON Hi SPEED PULSE COUNT'))
                    DUT_LOG.error( "Errors in Hi Speed Pulse Test:\n Pulse1: %s \n Pulse2: " % Cout + str(Cout1) )
                    return
                else:
                    print "Retrying Hi Speed Pulses!! Retrys left = " + str(retry_count)
                    
            elif (K5_pulse1_2 - K5_pulse1_1) != 200:
                K5_pulse1_1 = K5_pulse1_2
                K5_pulse2_1 = K5_pulse2_2
                retry_count -= 1
                if(retry_count == 0):
                    wx.PostEvent(self._notify_window, ResultEvent('FAIL ON Hi SPEED PULSE1 COUNT'))
                    DUT_LOG.error( "Fail on Hi Speed Pulse1 Count Not = 200 was %i" % (K5_pulse1_2 - K5_pulse1_1))
                    return
                else:
                    print "Retrying Hi Speed Pulse1!! Retrys left = " + str(retry_count)
                    
            elif (K5_pulse2_2 - K5_pulse2_1) != 200:
                K5_pulse1_1 = K5_pulse1_2
                K5_pulse2_1 = K5_pulse2_2
                retry_count -= 1
                if(retry_count == 0):
                    wx.PostEvent(self._notify_window, ResultEvent('FAIL ON Hi SPEED PULSE2 COUNT'))
                    DUT_LOG.error( "Fail on Hi Speed Pulse2 Count Not = 200 was %i" % (K5_pulse2_2 - K5_pulse2_1))
                    return 1
                else:
                    print "Retrying Hi Speed Pulse2!! Retrys left = " + str(retry_count)
                    
            else:
                DUT_LOG.info( "Hi Speed Pulse Counters Test: Pass" )
                Hi_Speed_Retry = False
        
    #---------------------------------------------------------------------
    #
    def RS485(self):
        global errStr, DUT_LOG, G20_C, DEVICE_TYPE
        
        print "Waiting for MODBUS echo..."
            
        G20_Cgot = self.SerialPortWrite(G20_C, "python test/FuncTest/BTL/btl485-FT.py\n\r", 2)
        
        
        #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
        if G20_Cgot.rfind("ERROR") != -1 or G20_Cgot.rfind("SUCCESS") == -1:
            #wx.PostEvent(self._notify_window, ResultEvent('FAIL ON RS485'))
            DUT_LOG.error( "Bad RS485:\n%s" % G20_Cgot )
            errStr = "FAIL ON Bad RS485: " + G20_Cgot
            return 1
        else: DUT_LOG.info( "RS485 Test: Pass" )
        
        #"RS485 Test Good!!", " Starting Relay & Inputs 1 & 2 test...", "NADA", "NADA"
        MK_PANEL['TstDone'] = "RS485 Test Good!!"   
        if DEVICE_TYPE == "M2_B":
            MK_PANEL['TstStart'] = " Testing Relay, Inputs 1, and 2..."
        elif DEVICE_TYPE == "S2_C":
            MK_PANEL['TstStart'] = "Auto Testing LEDs.."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"    
    
    
    #---------------------------------------------------------------------
    #         Rx Temperature test
    def Rx_Temp(self):
        global errStr, DUT_LOG, RX_C
        timeStrt = time.time()
        
        print "Testing RX Temperature Sensor..."
        RX_Cgot = self.SerialPortWrite(RX_C, "4")         # Run Test.
        
        if int(RX_Cgot) >= 200 and int(RX_Cgot) <= 400 :
            DUT_LOG.info( "RX Temperature Sensor Test Pass" )
        else:
            errStr = 'FAIL RX TEMPERATURE SENSOR'
            return 1
        
        print "RX Temperature Sensor test took %d seconds" % (time.time() - timeStrt)
    
        MK_PANEL['TstDone'] = "RX Temperature Sensor Test Good!!"   
        MK_PANEL['TstStart'] = "Testing RX AC Power Reading..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"  
        
        
    #---------------------------------------------------------------------
    #       RX AC Power Reading On & Off Backup CAP test
    def Rx_AcReadBrownOut(self): 
        global errStr, DUT_LOG, RX_C  
        timeStrt = time.time()
        print "Testing RX AC Power Reading AC On..."
        RX_Cgot = self.SerialPortWrite(RX_C, "5")         # Run Test. assume the power is on.
        
        if int(RX_Cgot) >= 600 and int(RX_Cgot) <= 800 :
            DUT_LOG.info( "RX AC Power On Reading Test Pass counts = " + RX_Cgot)
        else:
            errStr = 'FAIL RX AC POWER READING ON READING = '  + RX_Cgot
            return 1
        
        if errStr == None:
            print "Testing RX AC Power Reading AC Off..."
            print "Turning Off AC Power!! Testing capacitor power"
            self.switchMux('40')                            # Turn the AC power off
            time.sleep(2)                                   # Wait for the Power to drop.
            RX_Cgot = self.SerialPortWrite(RX_C, "5",3)     # Run Test. power is off.
        
            if len(RX_Cgot) >= 1:        # Did we get a response??
                if int(RX_Cgot) >= 100  and int(RX_Cgot) <= 170 :
                    DUT_LOG.info( "RX AC Power Off Reading Test Pass counts = " + RX_Cgot )
                    self.switchMux('20')                        # Turn the power back on.
                else:
                    errStr = 'FAIL RX AC POWER READING OFF READING = '  + RX_Cgot
                    return 1
            else:   # No Reading received.
                DUT_LOG.info( "Check that capacitors power keeps DUT on!")
                errStr = 'FAIL RX AC POWER READING GOT NO RESPONSE'
                return 1
        
        print "RX AC Power Reading test took %d seconds" % (time.time() - timeStrt) 
        
        MK_PANEL['TstDone'] = "RX AC Power Reading Test Good!!"   
        MK_PANEL['TstStart'] = "Testing LEDs Please Wait..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"           
        
    #---------------------------------------------------------------------
    #       RX LED test
    def M2_B_LED(self): 
        global errStr, DUT_LOG, TEMP_LOG   

        print "Testing LEDs on DUT!"

        TEST_SIGNAL = M2_B_TEST_SIGNAL 
        MUX_ADDR_PWR = M2_B_MUX_ADDR_PWR
        LIMIT_PWR_HI = M2_B_LIMIT_PWR_HI   
        LIMIT_PWR_LO = M2_B_LIMIT_PWR_LO 
        
        if errStr == None:
            #------------Read LED Voltages--------
            for Signal in TEST_SIGNAL:    
                    if Signal.rfind("LED") != -1:  # and Signal.rfind("LED1") == -1 and Signal.rfind("LED2") == -1 and Signal.rfind("LED3") == -1:
                        print "Testing voltage on " + Signal + "..."            
                        self.switchMux(MUX_ADDR_PWR[Signal])
                      
                        retryRead = 0
                        Reading = self.ReadMeter('DC')
                        while retryRead < 3 and Reading == "---":
                            Reading = self.ReadMeter('DC')
                            print "retrying LED reading..."
                            retryRead = retryRead + 1
                            
                        if Reading == "---":                         # No reading was received.
                            errStr = "FAIL First Reading " + Signal + " No Meter Reading: ---"
                            break
                        
                        #print "First Reading = " + str(Reading)
                        MaxRead = 6
                        while (float(Reading) < LIMIT_PWR_LO[Signal] or float(Reading) > LIMIT_PWR_HI[Signal]) and MaxRead > 0:
                            Reading = self.ReadMeter('DC')
                            MaxRead = MaxRead - 1
                            print "Retry Reading = " + str(Reading)
                            time.sleep(0.7)
                    
                        if Reading == "---":                         # No reading was received.
                            errStr = "FAIL Reading " + Signal + " No Meter Reading: ---"
                            break
                        elif float(Reading) >= LIMIT_PWR_LO[Signal] and float(Reading) <= LIMIT_PWR_HI[Signal]:
                            TEMP_LOG += Signal + " Test Pass Reading: " + Reading + UNITS + "\n"
                            print Signal + " LED Test Pass Reading: " + Reading + UNITS
                        else:
                            errStr = 'FAIL ' + Signal + ' Voltage Reading: ' + Reading + UNITS + \
                                     '\nLimit:  ' + str(LIMIT_PWR_LO[Signal]) + "-"  + str(LIMIT_PWR_HI[Signal]) + UNITS
                            DUT_LOG.error( errStr )
                            break    
             
            if errStr != None:
                return 1
            else: DUT_LOG.info( TEMP_LOG )     
        
        MK_PANEL['TstDone'] = "LEDs Test Good!!"    
        MK_PANEL['TstStart'] = "Press/Release RX_Button1 Button SW4 \n\r Click FAIL if Screen doesn't Change in 5s"
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "FAIL" 
        
        
    #---------------------------------------------------------------------
    # 
    def M2_B_Button1(self):
        global errStr, DUT_LOG, G20_C
        print "Testing Button1..."
        
        #print "SKipping M2_B_Button1!!! KGB"
        #return
        G20_Cgot = self.SerialPortWrite(G20_C, "ls /var/smallfoot/smallfoot-app/test/FuncTest/BTL/M2_Commish.py\n", 1)
        # do we need to write the file?
        if G20_Cgot.find("No such file or directory") != -1:
            print "Moving to BTl..."
            G20_C.write("cd /var/smallfoot/smallfoot-app/test/FuncTest/BTL\n")
            G20_C.flush()
            
            #open the test file.
            ins = open( M2commish, "r" )
            
            print "Copying test file to the SD-CARD"
            G20_C.write("vi M2_Commish.py\n")       # open the new file.
            G20_C.write("i\n")                      # put vi in insert mode.
            # write the test file to the SD-CARD one line at a time.    
            for line in ins:
                G20_C.write(line)                # Write the lines in.
                 
            G20_C.write(chr(27) + ":x\n")               # get out of input mode, save, and exit.
            time.sleep(2)
            G20_C.write("chmod +x M2_Commish.py\n")     # make it executable.
            
            print "Moving to smallfoot-app..."
            G20_C.write("cd /var/smallfoot/smallfoot-app\n")
            G20_C.flush()
        
        # run the test!!!
        print "Waiting for M2_B_Button1 Press..."
        G20_C.flushInput()
        G20_C.write("python test/FuncTest/BTL/M2_Commish.py&\n")
        G20_C.flush()
        Cout = ""
        while Cout.rfind("SUCCESS: Got BUTTON1 Asynch RPC") == -1 and \
              Cout.rfind("ASYNC: RPC Response srcAddr=00000000 seq=0 status=00 cmdId=80 attribClass=10 attribIndex=80 data=[00]") == -1:
            G20_Cgot = G20_C.read()
            Cout = Cout + G20_Cgot
            if self._want_abort:            #FAIL Clicked by User
                print "Aborting BUTTON1 Hang..."
                errStr = "FAIL BUTTON1 User Abort!!"
                return 1
        else: DUT_LOG.info( "BUTTON1 Test: Pass" )
          
        
        MK_PANEL['TstDone'] = "Button1 Test Good!!"   
        MK_PANEL['TstStart'] = "Press/Release RX_RESET Button SW3 \n\r Click FAIL if Screen doesn't Change in 5s"
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "FAIL" 
    #---------------------------------------------------------------------
    # 
    def S2_Button1(self):  
        global errStr, DUT_LOG, G20_C
        
        #print "SKipping S2_Button1!!! KGB"
        #return
        #print "Waiting for Config Button Asynch on RPC..."
        print "Waiting for BUTTON1 Press..."
        G20_C.flushInput()
        G20_C.write("python test/FuncTest/BTL/btlCommish-FT.py&\n")
        G20_C.flush()
        G20_Cgot = ""
        while G20_Cgot.rfind("SUCCESS: Got BUTTON1 Asynch RPC") == -1 and \
              G20_Cgot.rfind("ASYNC: RPC Response srcAddr=00000000 seq=0 status=00 cmdId=80 attribClass=10 attribIndex=80 data=[00]") == -1:
            G20_Cgot += G20_C.read()
            if self._want_abort:            #FAIL Clicked by User
                print "Aborting BUTTON1 Hang..."
                return 1
        else: DUT_LOG.info( "BUTTON1 Test: Pass" )
        
        MK_PANEL['TstDone'] = "Button1 Test Good!!"   
        MK_PANEL['TstStart'] = "Press/Release M3_RESET Button SW600 \n\r Click FAIL if Screen doesn't Change in 5s"
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "FAIL"    
    
    #---------------------------------------------------------------------
    # 
    def S2_M3_Reset(self):
        global errStr, DUT_LOG, LIL_C
        
        #print "SKipping S2_M3_Reset!!! KGB"
        #return
        #print "Waiting for a byte from M3..."
        print "Waiting for M3_RESET Press..."
        LIL_C.flushInput()
        lilCgot = ""
        while len(lilCgot) == 0:            #[TODO test char?? '-'] Wait for userFAIL for M3_RESET Button
            lilCgot = LIL_C.read()
            if self._want_abort:            #FAIL Clicked by User
                print "Aborting M3_RESET Hang..."
                return 1
        else: DUT_LOG.info( "M3_RESET Button Test: Pass" )
            
        MK_PANEL['TstDone'] = "M3_RESET Button Test Good!!"   
        MK_PANEL['TstStart'] = "Encrypting SD Card..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"    
        
    #---------------------------------------------------------------------
    # 
    def Rx_ResetButton(self): 
        global errStr, DUT_LOG, RX_C   
        # RX_RESET Button
        print "Waiting for a byte from RX..."
        
        #print "SKipping RX Reset Button!!! KGB"
        #return
        #'''
        RX_C.flushInput()
        rxCgot = ""
        resetTimeOut = time.time() + 100
        while len(rxCgot) == 0:            #[TODO test char?? '-'] Wait for userFAIL for M3_RESET Button
            rxCgot = RX_C.read()
            if self._want_abort:            #FAIL Clicked by User
                print "Aborting RX_RESET Hang..."
                errStr = 'FAIL BUTTON Rx_Reset'
                return 1
            elif time.time() >= resetTimeOut:
                errStr = "FAIL ON RX_RESET TIMEOUT"
                return 1
            
        else: 
            DUT_LOG.info( "RX_RESET Button Test: Pass" )
        #'''
        
        MK_PANEL['TstDone'] = "RX_RESET Button Test Good!!"   
        MK_PANEL['TstStart'] = "Encrypting SD Card..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"    
    
    #---------------------------------------------------------------------
    #   M2 B  Relay and  Dry contacts test.
    def M2_B_RelayContact(self):
        global errStr, DUT_LOG, G20_C
        
        G20_Cgot = self.SerialPortWrite(G20_C, "python test/Read_M2_Inputs.py 1\n\r", 1)
        if G20_Cgot.find("Low") != -1:
            G20_Cgot = self.SerialPortWrite(G20_C, "python test/Read_M2_Inputs.py 2\n\r", 1) 
            
            # test contact #2  then Turn on the Relay
            if G20_Cgot.find("High") != -1:
                G20_C.write("python test/M2_Relay_Control.py 1\n\r")
                time.sleep(6) # wait for the input to be read.
                
                G20_Cgot = self.SerialPortWrite(G20_C, "python test/Read_M2_Inputs.py 1\n\r", 1)
                if G20_Cgot.find("High") != -1:
                    G20_Cgot = self.SerialPortWrite(G20_C, "python test/Read_M2_Inputs.py 2\n\r", 1) 
                    
                    if G20_Cgot.find("Low") != -1:
                        DUT_LOG.info( "Relay, Inputs 1, & 2 Test: Pass" )
                    else:
                        errStr = 'FAIL Input2 Not Low Relay K1'
                else:  
                    errStr = 'FAIL Input1 Not High Relay K1'
            else:
                errStr = 'FAIL Input2 Not High Relay K1'      
        else:
            errStr = 'FAIL Input1 Not Low Relay K1'
            
        if errStr != None:
            return 1
       
        MK_PANEL['TstDone'] = "Relay, Inputs 1, \& 2 Good!!"   
        MK_PANEL['TstStart'] = "Testing RX EE Data..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"    

    #---------------------------------------------------------------------
    #   RX EE Data test 
    def Rx_EE_Data(self):
        global errStr, DUT_LOG, RX_C
        
        timeStrt = time.time()
        
        print "Testing RX EE Data..."
        RX_Cgot = self.SerialPortWrite(RX_C, "\r")        # Clear first String.
        RX_Cgot = self.SerialPortWrite(RX_C, "3")         # Run Test.
        
        if RX_Cgot.rfind("Ok") != -1 :
            DUT_LOG.info( "RX EE Data test Pass" )
        else:
            errStr = 'FAIL RX RX EE Data'
            
        print "RX EE Data test took %d seconds" % (time.time() - timeStrt) 
    
        MK_PANEL['TstDone'] = "RX EE Data Test Good!!"   
        MK_PANEL['TstStart'] = "Testing RX Temperature Sensor..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"  
    
    
    #---------------------------------------------------------------------
    #
    def S2_C_AutoLed(self):
        global errStr, DUT_LOG, TEMP_LOG, G20_C, S2_C_TEST_SIGNAL, S2_C_MUX_ADDR_PWR, S2_C_LIMIT_PWR_HI, S2_C_LIMIT_PWR_LO
        
        
        TEST_SIGNAL = S2_C_TEST_SIGNAL 
        MUX_ADDR_PWR = S2_C_MUX_ADDR_PWR
        LIMIT_PWR_HI = S2_C_LIMIT_PWR_HI   
        LIMIT_PWR_LO = S2_C_LIMIT_PWR_LO 
        
        print "Cell and App LEDs On (no Blink)..."

        # Turn off Self Stimulation it makes the LEDs flash.
        G20_C.write("python test/FuncTest/BTL/btlGetHiSpeedPulses-FT.py\n") 
        G20_C.flush()
        
        Cout = ""
        while Cout.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app# ") == -1:
            G20_Cgot = G20_C.read()
            Cout = Cout + G20_Cgot
            
        G20_C.write("echo 255 > /sys/class/leds/wangood/brightness\n")
        G20_C.flush()
        G20_C.write("echo 255 > /sys/class/leds/appheartbeat/brightness\n")
        G20_C.flush()
        G20_C.write("echo 255 > /sys/class/leds/heartbeat/brightness\n")
        G20_C.flush()
        
        # wait for the prompt.
        Cout = ""
        while Cout.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app# ") == -1:
            G20_Cgot = G20_C.read()
            Cout = Cout + G20_Cgot
            
        G20_C.write("python test/FuncTest/bigLedsOn-FT.py\n")
        G20_C.flush()
       
        print "Testing LEDs on DUT!"
       
        #'''
        if errStr == None:
            #------------Read LED Voltages--------
            for Signal in TEST_SIGNAL:    
                    if Signal.rfind("LED") != -1:
                        print "Testing voltage on " + Signal + "..."            
                        self.switchMux(MUX_ADDR_PWR[Signal])
                    
                        retryRead = 0
                        Reading = self.ReadMeter('DC')
                        while retryRead < 3 and Reading == "---":
                            Reading = self.ReadMeter('DC')
                            print "retrying LED reading..."
                            retryRead = retryRead + 1
                            
                        if Reading == "---":                         # No reading was received.
                            errStr = "FAIL First Reading " + Signal + " No Meter Reading: ---"
                            break
                    
                        MaxRead = 6
                        while (float(Reading) < LIMIT_PWR_LO[Signal] or float(Reading) > LIMIT_PWR_HI[Signal]) and MaxRead > 0:
                            Reading = self.ReadMeter('DC')
                            MaxRead = MaxRead - 1
                            print "Retry Reading = " + str(Reading)
                            time.sleep(0.7)
                    
                        if Reading == "---":                         # No reading was received.
                            errStr = "FAIL Power " + Signal + " No Meter Reading: ---"
                            break
                        elif float(Reading) >= LIMIT_PWR_LO[Signal] and float(Reading) <= LIMIT_PWR_HI[Signal]:
                            TEMP_LOG += Signal + " Test Pass Reading: " + Reading + UNITS + "\n"
                            print Signal + " LED Test Pass Reading: " + Reading + UNITS
                        else:
                            errStr = 'FAIL ' + Signal + ' Voltage Reading: ' + Reading + UNITS + \
                                     '\nLimit:  ' + str(LIMIT_PWR_LO[Signal]) + "-"  + str(LIMIT_PWR_HI[Signal]) + UNITS
                            DUT_LOG.error( errStr )
                            break    
            #'''  
            if errStr != None:
                wx.PostEvent(self._notify_window, ResultEvent(errStr))
                return
            else: DUT_LOG.info( TEMP_LOG )
        
        
        MK_PANEL['TstDone'] = "LEDs Test Good!!"    
        MK_PANEL['TstStart'] = "Testing S2 Relays..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"
    
    #---------------------------------------------------------------------
    #
    def S2_Relay(self):
        global errStr, DUT_LOG, G20_C
        print "Testing S2 Relays..."
        retry_count = 4
        while(retry_count > 0 ):
            G20_C.flushInput()
            G20_C.write("python test/FuncTest/BTL/btl2Relays-FT.py\n")
            G20_C.flush()
            Cout = ""
            while Cout.rfind("root@at91sam9g20ek:/var/smallfoot/smallfoot-app# ") == -1:
                G20_Cgot = G20_C.read()
                Cout = Cout + G20_Cgot

            #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)
            if Cout.rfind("ERROR") != -1 or Cout.rfind("SUCCESS") == -1:
                retry_count -= 1
                if(retry_count == 0):
                    wx.PostEvent(self._notify_window, ResultEvent('FAIL ON RELAYS'))
                    DUT_LOG.error( "Bad Relay Test:\n%s" % Cout )
                    return 1
                else:
                    print "Retrying Relay Test!! Retrys left = " + str(retry_count)
                
            else: 
                DUT_LOG.info( "Relay Test: Pass" )
                retry_count = 0
    
        MK_PANEL['TstDone'] = "Relays Test Good!!"    
        MK_PANEL['TstStart'] = "Press/Release Button1 Button SW1 \n\r Click FAIL if Screen doesn't Change in 5s"
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "FAIL" 
    
    
    #---------------------------------------------------------------------
    #    Encryption & Public Key
    def EncryptKey(self):
        global errStr, DUT_LOG, G20_C
        print "Moving back home..."

        G20_Cgot = self.SerialPortWrite(G20_C, "cd /home/root\n")
        if WRITE_KP:
            print "Writting Key..."
            id_= None
            key = None
            id_, key = keygen.issue_private_key( DUT_MAC )
            if key is None:
                errStr = 'FAIL ON KEYGEN (call EnerNOC!!)'
                
            if errStr == None:  # No ERRORS??
                #print key   #TODO 
                if key.find("-----BEGIN RSA PRIVATE KEY-----") == -1 or key.rfind("-----END RSA PRIVATE KEY-----") == -1:
                    errStr = 'FAIL ON KEYGEN (call EnerNOC!!)'
                    
                if errStr == None:  # No ERRORS??    
                    G20_C.write("echo \"%s\" > /var/smallfoot/smallfoot-app/rsa_key.pem\n" % key)
                    G20_C.flush()
                    keygen.record_key_used(id_, DUT_MAC)
                    print "Key&MAC Associated!!"
                    
        else:
            DUT_LOG.warning( "DANGER DANGER Skipping Key&MAC Association Step!!" )
            
        print "Encrypting..."
        encST = time.time()
        G20_C.flushInput()
        G20_Cgot = G20_C.readall()   #TODO (70, 291, 341??)
        #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)     #Debug Only
        G20_C.write("/etc/init.d/cryptfs-mount init\n")
        G20_C.flush()
        Cout = ""
        bootTimeOut = time.time() + 125
        #TODO long timeout??
        while Cout.rfind("root@at91sam9g20ek:~# ") == -1:
            if Cout.rfind("RomBOOT") != -1:
                errStr = 'FAIL ON CRYPT FS (RomBOOT fail)'  
                DUT_LOG.error( "cryptfs-mount init:\n%s" % Cout )
                break
            elif time.time() >= bootTimeOut:
                errStr = 'FAIL ON CRYPT FS (RomBOOT) TIMEOUT'
                break
            
            G20_Cgot = G20_C.read() #all()
            #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
            Cout = Cout + G20_Cgot
            
        if errStr == None:  # No ERRORS??    
            if Cout.rfind("enc1 is already mounted at /var/smallfoot/smallfoot-app") != -1:
                print "CARD ALLREADY ENCRYPTED?? sync-ing..."
                syncST = time.time()
                G20_C.write("sync\n")
                G20_C.flush()
                Cout = ""
                PromtTimeOut = time.time() + 125
                while Cout.rfind("root@at91sam9g20ek:~# ") == -1:
                    G20_Cgot = G20_C.read() #all()
                    #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
                    Cout = Cout + G20_Cgot
                    if time.time() >= PromtTimeOut:
                        errStr = 'FAIL ON CRYPT FS Promt not received TIMEOUT'
                        break
                    
                #print "[%d]:%s" % (len(Cout), Cout)     #Debug Only
                DUT_LOG.warning("CARD ALLREADY ENCYPTED?? Sync took %d seconds" % ( time.time() - syncST ) )
            else:
                #print "[%d]:%s" % (len(Cout), Cout)
                DUT_LOG.info( "cryptfs-mount init took %d seconds" % ( time.time() - encST ) )
                #G20_C.write("echo $?\n")
                #G20_Cgot = G20_C.read(10)    #10 for "echo $?\nXX"
                G20_Cgot = self.SerialPortWrite(G20_C, "echo $?\n")
                #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
                if G20_Cgot.find("0") == -1:
                    errStr = 'FAIL ON CRYPT FS (SE)'
                    DUT_LOG.error( "cryptfs-mount init:\n%s" % Cout )
                    
        if errStr == None:  # No ERRORS??        
            print "Checking encryted image size..."
            G20_C.write("ls -la /var/smallfoot/cryptfs.img\n")
            G20_C.flush()
            G20_Cgot = G20_C.read(125) 
            
            if G20_Cgot.find(" 15728640 ") == -1:
                errStr = 'FAIL ON CRYPT FS (File SIZE)\nPlease replace the SD-CARD!'
                DUT_LOG.error( "cryptfs incorrect file size:\n%s" % G20_Cgot )
        
        if errStr == None:  # No ERRORS??
            DUT_LOG.info( "cryptfs image size: 15728640 bytes" )
            DUT_LOG.info( "Encrytion and Key: Pass" )
            
        MK_PANEL['TstDone'] = "SD Card Encryption Good!!"   
        MK_PANEL['TstStart'] = "Testing Supervisor..."
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"   
        
        
    #---------------------------------------------------------------------
    #     Supervisor
    def WatchDog(self):  
        global errStr, DUT_LOG, G20_C   
        print "killing the mfgpetter..."
        
        G20_Cgot = self.SerialPortWrite(G20_C, "killall mfgpetter\n")
        #print "[%d]:%s" % (len(G20_Cgot), G20_Cgot)    #Debug Only
        print "Waiting 13s for RomBOOT..."
        
        
        bootStat = self.BigRomBoot(13)
        if bootStat != 1:
            if bootStat != -2:              #USER ABORT IS -2
                errStr = 'FAIL ON SUPERVISOR' 
                 
        else: 
            DUT_LOG.info( "G20-Watchdog Test: Pass" )
            
        MK_PANEL['TstDone'] = "Supervisor Test Good!!"   
        MK_PANEL['TstStart'] = "Press/Release G20_RESET Button SW100 \n\r Click FAIL if Screen doesn't Change in 5s"
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "FAIL"
   

    #---------------------------------------------------------------------
    #       G20 RESET Button
    def G20_Reset(self):
        global errStr, DUT_LOG, DEVICE_TYPE
        print "Waiting ENDLESSLY for RomBOOT..."
        print "Press/Release G20_RESET Button SW1"
        
        #print "KGB --> Skipping G20_Reset test <--KGB"
        #return
        
        bootStat = self.BigRomBoot(0)
        if bootStat != 1:
            if bootStat != -2:              #USER ABORT IS -2
                errStr = 'FAIL ON RESET BUTTON'
                 
        else: 
            DUT_LOG.info( "RESET Button Test: Pass" )
        
        MK_PANEL['TstDone'] = "G20_RESET Button Test Good!!"  
        if DEVICE_TYPE == "S2" or DEVICE_TYPE == "S2_C":
            MK_PANEL['TstStart'] = "Brown Out Test..."
        elif DEVICE_TYPE == "M2":
            MK_PANEL['TstStart'] = "Modem Power Test..."
        elif DEVICE_TYPE == "M2_B":
            MK_PANEL['TstStart'] = "Print MAC Labels!"
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "NADA"

    #---------------------------------------------------------------------
    #
    def M2_PowerModem(self):
        global errStr, DUT_LOG, RX_C, M2_MUX_ADDR_PWR, M2_LIMIT_PWR_LO, M2_LIMIT_PWR_HI
        global M2_Signal
        TEMP_LOG = ""
        Rx_Supply = ['+ModemVDC','+BATT']
        for M2_Signal in Rx_Supply:
            print "Testing Power on " + M2_Signal + "..."            
            self.switchMux(M2_MUX_ADDR_PWR[M2_Signal])
        
            Reading = self.ReadMeter('DC')
        
            if Reading == "---":                         # No reading was received.
                errStr = "FAIL Power " + M2_Signal + " No Meter Reading: ---"
                return 1
            elif float(Reading) >= M2_LIMIT_PWR_LO[M2_Signal] and float(Reading) <= M2_LIMIT_PWR_HI[M2_Signal]:
                DUT_LOG.info(M2_Signal + " Power Test Pass Reading: " + Reading + UNITS + "\n")
                print M2_Signal + " Power Test Pass Reading: " + Reading + UNITS
            else:
                errStr = 'FAIL ' + M2_Signal + ' Power Reading: ' + Reading + UNITS + \
                         '\nLimit:  ' + str(M2_LIMIT_PWR_LO[M2_Signal]) + "-"  + str(M2_LIMIT_PWR_HI[M2_Signal]) + UNITS
                return 1
                
    #---------------------------------------------------------------------
    #
    def M2_Rx_Hv_InOut(self):
        global errStr, DUT_LOG, RX_C
        timeStrt = time.time()
        print "Testing RX HV input and output..."
        RX_Cgot = self.SerialPortWrite(RX_C, "\r")          # Clear first String.
        RX_Cgot = self.SerialPortWrite(RX_C, "0")         # Run the HV Out/In test.
        InOutTimeOut = time.time() + 12
        RxRpnse = ""
        
        while RxRpnse.rfind("\r") == -1:
            time.sleep(1)
            RxRpnse += RX_C.readall()
            if time.time() > InOutTimeOut:
                errStr = "FAIL INPUT/OUTPUT READ TIMEOUT"
                return 1
        if errStr == None:
            hv_Off, hv_On = RxRpnse.split(',')
            
            if int(hv_Off) <= 10 and int(hv_On) <= 900 and int(hv_On) >= 700:
                DUT_LOG.info( "RX HV input/output test Pass" )
            else:
                errStr = 'FAIL RX HV IN/OUT'
                return 1
            print "RX HV input and output test took %d seconds" % (time.time() - timeStrt)
    
        
    #---------------------------------------------------------------------
    #
    def M2_Rx_DigInOut(self):
        global errStr, DUT_LOG, RX_C
        timeStrt = time.time()
        print "Testing RX Out2 and Dig Inputs 1, 2..."
        RX_Cgot = self.SerialPortWrite(RX_C, "1", 2)         # Run the Output2 and Digital Inputs test.
      
        if RX_Cgot.rfind("Off, On, On, Off") != -1:
            DUT_LOG.info("RX Out2 & Dig Inputs 1 & 2 test Pass")
        else:
            errStr = 'FAIL RX OUT2 and DIG IN 1, 2 the States = ' + RX_Cgot
         
        print "RX Out2 and Dig Inputs 1, 2 test took %d seconds" % (time.time() - timeStrt)    
            
        
    #---------------------------------------------------------------------
    #
    def M2_AnalogIns(self):
        global errStr, DUT_LOG, RX_C
        timeStrt = time.time()
        print "Testing RX Analog inputs 1-4..."
    
        RX_Cgot = self.SerialPortWrite(RX_C, "2")         # Run the Analog inputs 1-4v test.                                                      
        An1, An2, An3, An4 = RX_Cgot.split(',')             # Assume Zero on analog inputs.

        if int(An1) <= 10 and int(An2) <= 10 and \
           int(An3) <= 10 and int(An4) <= 10:
            self.switchMux('30')                            # Put +5VDC on analog inputs.
            time.sleep(2)                                   # give the inputs time to see +5V.
            LoLimit = 400 
            HiLimit = 430
            RX_Cgot = self.SerialPortWrite(RX_C, "2")         # Run the Analog inputs 1-4v test Again.                                                      
            An1, An2, An3, An4 = RX_Cgot.split(',')             
        
            if int(An1) >= LoLimit and int(An1) <= HiLimit and \
               int(An2) >= LoLimit and int(An2) <= HiLimit and \
               int(An3) >= LoLimit and int(An3) <= HiLimit and \
               int(An3) >= LoLimit and int(An4) <= HiLimit:
                DUT_LOG.info( "RX HV Analog inputs 1-4 test Pass" )
                self.switchMux('20')                        # Take +5VDC off the analog inputs.
            else:
                errStr = 'FAIL RX ANALOG INs AT 5VDC READ: ' + RX_Cgot + 'COUNT LIMITS: ' + str(LoLimit) + ', ' + str(HiLimit)
        else:
            errStr = 'FAIL RX ANALOG INs AT 0VDC READ: ' + RX_Cgot + 'COUNT LIMIT: 10'
            
        print "RX Analog inputs 1-4 test took %d seconds" % (time.time() - timeStrt) 
        
    #---------------------------------------------------------------------
    #
    def M2_Battery(self):
        global errStr, DUT_LOG, RX_C
        
        timeStrt = time.time()
            
        self.switchMux("70")                                # Turn on the battery voltage
        print "Testing RX Battery System Test..."
        BatteryTimeOut = time.time() + 12
        RxResponse = ""
        RX_Cgot = self.SerialPortWrite(RX_C, "6")
        
        while RxResponse.rfind("\r") == -1: 
            time.sleep(1)     
            RxResponse += RX_C.readall() 
            RxResponse.strip()
            if time.time() >= BatteryTimeOut:
                errStr= "FAIL BATTERY SYSTEM READ TIMEOUT"       
                break
               
        if errStr == None:
            try:
                batt1, batt2, batt3, batt4 = RxResponse.split(',')
                
                if int(batt1) >= 10 and int(batt1) <= 120 and \
                   int(batt2) >= 830 and int(batt2) <= 870 and \
                   int(batt3) >= 810 and int(batt3) <= 845 and \
                   int(batt4) >= 500 and int(batt4) <= 560:
                    DUT_LOG.info( "RX Battery System Test Pass" )
                else:
                    errStr = 'FAIL RX BATTERY SYSTEM READINGS: ' + RX_Cgot + \
                            '\nLimits: 10-100, 830-870, 810-845, 500-560'
            
                print "RX Battery System test took %d seconds" % (time.time() - timeStrt)
        
            except:
                
                errStr = "FAIL Incorrect response on Battery test" 
        
    #---------------------------------------------------------------------
    #
    def M2_RxRedLED(self):
        global errStr, DUT_LOG, RX_C, M2_LEDMIN, M2_LEDMAX
        timeStrt = time.time()
        print "Testing RX Red LED Test..."
        
        #'''
        self.switchMux("2D")                            # Hook to the LED Junction D19
        
        RX_Cgot = self.SerialPortWrite(RX_C, "7")         # Run Test.
        
        if RX_Cgot.rfind('Ok') != -1 :
            Reading = self.ReadMeter("DC")               # Read the DC Volts.
            
            if Reading == "---":                         # No reading was recieved.
                errStr = "FAIL RX Red LED No Meter Reading: ---"
            elif float(Reading) >= M2_LEDMIN and float(Reading) <= M2_LEDMAX:
                DUT_LOG.info( "RX Red LED Test Pass" )
            else:
                errStr = 'FAIL RX Red LED Test Reading: ' + Reading + UNITS + \
                         '\nLimits: ' + str(M2_LEDMIN) + "-" + str(M2_LEDMAX) + UNITS  
        else:
            errStr = 'FAIL RX Red LED Test RX Bad Response' 
        #'''
        print "RX Red LED test took %d seconds" % (time.time() - timeStrt)            
            
    #---------------------------------------------------------------------
    #
    def M2_RxGreenLED(self):
        global errStr, DUT_LOG, RX_C, M2_LEDMIN, M2_LEDMAX
        
        timeStrt = time.time()
        print "Testing RX Green LED Test..."
        #'''
        self.switchMux("2E")                            # Hook to the LED Junction D20
        
        RX_Cgot = self.SerialPortWrite(RX_C, "8")       # Run Test.
        
        if RX_Cgot.rfind('Ok') != -1 :
            Reading = self.ReadMeter("DC")              # Read the DC Volts.
            
            if Reading == "---":                         # No reading was recieved.
                errStr = "FAIL RX Green LED No Meter Reading: ---"
            elif float(Reading) >= M2_LEDMIN and float(Reading) <= M2_LEDMAX:
                DUT_LOG.info( "RX Green LED Test Pass" )
            else:
                errStr = 'FAIL RX Green LED Reading: ' + Reading + UNITS + \
                         '\nLimits:  ' + str(M2_LEDMIN) + "-" + str(M2_LEDMAX) + UNITS               
        else:
            errStr = 'FAIL RX Green LED Test RX Bad Response'
        #'''
        print "RX Green LED Test test took %d seconds" % (time.time() - timeStrt) 
       
    #---------------------------------------------------------------------
    #
    def M2_RxPwrLED(self):
        global errStr, DUT_LOG, RX_C, M2_LEDMIN, M2_LEDMAX
        timeStrt = time.time()                            # Hook to the LED Junction D20
            
        print "Testing RX Power LED Test..."
        #'''
        self.switchMux("2C")
      
        Reading = self.ReadMeter("DC")               # Read the DC Volts.
        
        if Reading == "---":                         # No reading was recieved.
            errStr = "FAIL RX Power LED No Meter Reading: ---"
        elif float(Reading) >= M2_LEDMIN and float(Reading) <= M2_LEDMAX:
            DUT_LOG.info( "RX Power LED Test Pass" )
        else:
            errStr = 'FAIL RX Power LED Reading: ' + Reading + UNITS + \
                     '\nLimits:  ' + str(M2_LEDMIN) + "-" + str(M2_LEDMAX) + UNITS                
        
        print "RX Power LED Test test took %d seconds" % (time.time() - timeStrt) 
        
        print "TOTAL TEST TIME: %d seconds" % (time.time() - TEST_START_TIME) 
        
        #'''           

    #---------------------------------------------------------------------
    #
    def S2_BrownOut(self):
        global errStr, DUT_LOG, LIL_C, DEVICE_TYPE, S2_PWR_OFF, FIRST_TEST_PASS
        
#        if FIRST_TEST_PASS:
#            return
#        
        print "Turning OFF UUT Power for UV Supply"
        if DEVICE_TYPE == "S2_C": 
            #turn OFF the power
            if self.switchMux('01') != 1:
                errStr = 'FAIL MUX SWITCH POWER OFF in UV Supply Test'
                return 1
        else:
            Rtrn = self.S2_Power(S2_PWR_OFF)
            if Rtrn:
                errStr = "Fail S2 Power Off Failed! \n Try Unplugging & Replugging USB."
                return 1
   
        print "Waiting ENDLESSLY for UV Supply"
               
        Cout = ""
        LIL_C.flushInput()
        LIL_C.flushOutput()
        LIL_C.flush()
        while Cout.find("UV Supply") == -1: #Wait for userFAIL for M3_RESET Button
            lilCgot = LIL_C.read()          #TODO FASTER?? HERE DOTHIS
            Cout = Cout + lilCgot
            if self._want_abort:            #FAIL Clicked by User
                print "Aborting UV Supply Hang..."
                return 1
        else:
            #print "[%d]:%s" % (len(Cout), Cout)
            DUT_LOG.info( "Brownout Test: Pass" )    
        
        MK_PANEL['TstDone'] = "Power Down UUT..."   
        MK_PANEL['TstStart'] = "Click FAIL if Screen doesn't Change in 10s"
        MK_PANEL['Button1'] = "NADA"
        MK_PANEL['Button2'] = "FAIL"

      
        
    #---------------------------------------------------------------------
    #    Print MAC ID Labels
    def PrintZebraLabels(self):
        global DUT_LOG, DUT_MAC, ZEBRA_LC, ZEBRA_DV, errStr, MFG
        if ZEBRA_LC:
            print "ZEBRA GO!!"
            macNoSepSTR = ""
            for i in range(0,17):
                if DUT_MAC[i] != '-':
                    macNoSepSTR = macNoSepSTR + DUT_MAC[i]
            if MFG:
                labelStr = "^XA^FO038,15^BY2^BCN,61,N,N,N^FD%s^FS^FO110,80^ADN36,20^FD%s^FS^XZ" % (macNoSepSTR, DUT_MAC)
            else:
                labelStr = "^XA^FO140,15^BY2^BCN,61,N,N,N^FD%s^FS^FO200,80^ADN36,20^FD%s^FS^XZ" % (macNoSepSTR, DUT_MAC)
            printStr = ""
            
            if ZEBRA_DV == None:
                zebra_name   = win32print.GetDefaultPrinter()
                ZEBRA_DV = win32print.OpenPrinter(zebra_name)
                
            for i in range(ZEBRA_LC):
                printStr = printStr + labelStr
            #print printStr
            try:
                zJob = win32print.StartDocPrinter(ZEBRA_DV, 1, ("MAC Labels", None, "RAW"))
                win32print.WritePrinter(ZEBRA_DV, printStr)
                win32print.EndDocPrinter(ZEBRA_DV)
                DUT_LOG.info( "%d MAC LABELS PRINTED" % ZEBRA_LC)
            except:
                errStr = "FAIL BAR CODE LABEL PRINT"
                wx.PostEvent(self._notify_window, ResultEvent('FAIL ON ZEBRA (call EnerNOC!!)'))
                return
            
        else:
            DUT_LOG.warning( "USER SELECTED NO LABELS" )

    
  


    #------------------------- Mux address routine
    def switchMux(self, newMuxValue):
        global MUX_VALUE, MUX_C, MUX_TTY, TEST_STEP, EOT_STR

        #Save the new Mux state.   
        MUX_VALUE = newMuxValue
        try:
            MUX_C.flushInput()
            MUX_C.write(newMuxValue + "\r")
            MUX_C.flush()
            newMuxValue = MUX_C.read(3)             #get the echo 
            
            if newMuxValue.rfind(MUX_VALUE) == -1:
                wx.PostEvent(self._notify_window, ResultEvent('FAILED MUX SWITCH UNPLUG & REPLUG USB CABLE'))
                return -1
            return 1
        except:
            print "FAILED MUX SWITCH COM Port TestStep: "  + str(TEST_STEP) + \
                  "\nTEST FIXTURE USB MAY NEED to be POWER CYCLED!!!"
            
       
    #---------- Serial Write to port the message in sendMsg and return what is read.
    def SerialPortWrite(self, port, sendMsg, sDelay = 0):
        global TEST_STEP, EOT_STR
        
        try:
            port.flushInput()
            port.write(sendMsg)
            port.flush()
            if sDelay > 0:
                time.sleep(sDelay)
                
            rettrn =  port.readall()
            
            if rettrn == None:
                return ""
            else: 
                return rettrn
       
        except:
            print "FAILED SerialPortWrite TestStep: " + str(TEST_STEP) + \
                  "\nTEST FIXTURE USB MAY NEED to be POWER CYCLED!!!"
            
          
        
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def ReadMeter(self, MeasType):
        global UNITS, METER_INIT
        
        # Agilent Multimeter Commands
        ClrStatus = "*CLS"
            
        ResetUnit = "*RST"
        
        #SysError = "SYST:ERR?"
           
        SystemRemote = "SYST:REM"
        
        #ReadResults = "READ?"
        
        #Initiate = "INIT "
        
        #Fetch = "FETC?"
        
        #NumbOfReads = "DATA:POIN?"
           
        MeshRequestAC = "MEAS:VOLT:AC? DEF, DEF"
        
        MeshRequestAClow = "MEAS:VOLT:AC? .1, DEF"
          
        MeshRequestDC = "MEAS:VOLT:DC? DEF, DEF"
           
        MeshReqResist = "MEAS:RES? DEF, DEF"
        
        MeshResist100K = "MEAS:RES? 900000, DEF"
        
        #MeshResistNplCycles = "RES:NPLC 100"
        
        MeshReqFreq = "MEAS:FREQ? DEF, DEF"
        
        #ConfigDcv = "CONF:VOLT:DC DEF, DEF"
        
        #ConfigRes = "CONF:RES DEF, DEF"
        
        #TrigSrc = "TRIG:SOUR IMM"
        
        #TrigDelay = "TRIG:DEL 0"
        
        #TrigCntInf = "TRIG:COUN INF"
        
        #TrigCntOne = "TRIG:COUN 1"
        
        #SampCnt500 = "SAMP:COUN 10"
        
        #SampCnt10 = "SAMP:COUN 10"
        
        #SampCntX = "SAMP:COUN "
        
        BeeperOff = "SYST:BEEP:STAT OFF"
        
        LF = "\n"

        if not METER_INIT:
            #put the meter in remote mode.
            TmpStr = SystemRemote + LF
            self.SerialPortWrite(METER_C, TmpStr) 
            
            #clear any errors.
            TmpStr = ClrStatus + LF
            self.SerialPortWrite(METER_C, TmpStr)
    
            TmpStr = ResetUnit + LF
            self.SerialPortWrite(METER_C, TmpStr)
            
            
            self.SerialPortWrite(METER_C, BeeperOff + LF)
            
            METER_INIT = True
    
        
          
        
            

        
        if MeasType == "AC":
            TmpStr = MeshRequestAC + LF
            UNITS = "VAC"
           
        elif MeasType == "ACLOW":
            TmpStr = MeshRequestAClow + LF
            UNITS = "mVAC"

        elif MeasType == "DC":
            TmpStr = MeshRequestDC + LF
            UNITS = "VDC"

        elif MeasType == "OHMS":
            TmpStr = MeshReqResist + LF
            UNITS = "OHMs"

        elif MeasType == "KOHMS":
            TmpStr = MeshResist100K + LF
            UNITS = "OHMs"
            
        else: # MeasType == "FREQ":
            TmpStr = MeshReqFreq + LF
            UNITS = "HZ"

        if UNITS == "VAC":
            MeshResponse = self.SerialPortWrite(METER_C, TmpStr, 2)
        else:
            # Send the command to the meter.
            MeshResponse = self.SerialPortWrite(METER_C, TmpStr,0.1)
            retry = 3
            while retry > 0 and (MeshResponse == None or len(MeshResponse) < 17):
                MeshResponse = self.SerialPortWrite(METER_C, TmpStr,1)
                retry = retry - 1
                
        
        if MeshResponse == None or len(MeshResponse) < 17:
            MeshResponse = "---"
            METER_INIT  = False
        else:
            try:
                # Convert the Scientific notation to decimal. 
                Reading = DEC.Decimal(MeshResponse) 
                round(Reading, 3)
                
                MeshResponse = str(Reading)   
        
            
                # Greater than 10M set max 10M.
                if float(MeshResponse) > 10000000:
                    MeshResponse = "10000000"
      
            except:
                MeshResponse = "---"
                METER_INIT  = False
        #return the value
        return MeshResponse
     
        
        
        
#----------------------------------------------------------------------
# theFrame is [more or less] the GUI:
#   It has a wxPanel with 2 Static Text Lines and 2 Button Controls,
#   and kicks off WorkerThreads to do Programming and Test
#----------------------------------------------------------------------
class theFrame(wx.Frame):
    def __init__(self, parent, id):
        global TEST_STEP, DEVICE_TYPE, DONE_BUTTON, VER, MFG
        
        if MFG:
            wx.Frame.__init__(self, parent, id, ' EnerNOC Returns Tester Version ' + VER + ' Production', pos=(-1250, 0), size=(500, 200)) #size=(620, 180))
        else:
            wx.Frame.__init__(self, parent, id, ' EnerNOC Returns Tester Version ' + VER + ' ENG', pos=(0, 0), size=(500, 200)) #size=(620, 180))
        
        # Set up event handler for any worker thread results
#        EVT_RESULT(self,self.OnResult)
#        # And indicate we don't have a worker thread yet
#        
#        self.worker = None
        
        self.selectDeviceType()

    #-----------------------------------------------------------------
    def selectDeviceType(self):
        global DT_S2_ID, DT_S2_C_ID, DT_M2_ID, DT_M2_B_ID, T_TXT_ID, B_TXT_ID
        global G_PAN_ID, DONE_BUTTON
        
        DONE_BUTTON = False
        
        if G_PAN_ID != 0:
            G_PAN_ID.Destroy()                  #Destroy the old before creating new
        G_PAN_ID = wx.Panel(self, size=self.GetClientSize())
        wx.EVT_CLOSE(self, self.OnQuit)         #Might Want to Abort Worker Thread When Quitting...
       
        G_PAN_ID.SetBackgroundColour('#DCDCDC')
        
        self.sTxt1 = wx.StaticText(G_PAN_ID, T_TXT_ID, 'Please Select Device Type', style=wx.ALIGN_CENTRE)
        self.sTxt1.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sTxt1.SetSize(self.sTxt1.GetBestSize())
        
        self.sTxt2 = wx.StaticText(G_PAN_ID, B_TXT_ID, "(Check Device Type checkbox to continue)", style=wx.ALIGN_CENTRE)
        self.sTxt2.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sTxt2.SetSize(self.sTxt2.GetBestSize())
        
        font = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)
        
        S2_DT = wx.CheckBox(G_PAN_ID, DT_S2_ID, label="S2")
        S2_DT.SetValue(False)
        #Bind Device Type Check
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckDone, S2_DT)
        self.S2_DT = S2_DT
        
        S2_C_DT = wx.CheckBox(G_PAN_ID, DT_S2_C_ID, label="S2_C")
        S2_C_DT.SetValue(False)
        #Bind Device Type Check
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckDone, S2_C_DT)
        self.S2_C_DT = S2_C_DT
        
        M2_DT = wx.CheckBox(G_PAN_ID, DT_M2_ID, label="M2")
        M2_DT.SetValue(False)
        #Bind Device Type Check
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckDone, M2_DT)
        self.M2_DT = M2_DT
        
        M2_B_DT = wx.CheckBox(G_PAN_ID, DT_M2_B_ID, label="M2_B")
        M2_B_DT.SetValue(False)
        #Bind Device Type Check
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckDone, M2_B_DT)
        self.M2_B_DT = M2_B_DT
        
        
        vSizer = wx.BoxSizer(wx.VERTICAL)
        
        
        hSizer = wx.BoxSizer(wx.HORIZONTAL)
       
        # add vertical space pixels.
        vSizer.Add(self.sTxt1 , flag=wx.CENTER, border=10)
        vSizer.Add(self.sTxt2 , flag=wx.CENTER, border=10)
        vSizer.Add((-1, 20))
        
        S2_DT.SetFont(font)
        hSizer.Add(S2_DT)
        
        self.S2_C_DT.SetFont(font)
        hSizer.Add(self.S2_C_DT, flag=wx.CENTER, border=10)
       
        M2_DT.SetFont(font)
        hSizer.Add(M2_DT, flag=wx.CENTER, border=10)
        
        M2_B_DT.SetFont(font)
        hSizer.Add(M2_B_DT, flag=wx.CENTER, border=10)
        
        vSizer.Add(hSizer, flag=wx.CENTER, border=10)
        
        
        
        G_PAN_ID.SetSizer(vSizer)
        G_PAN_ID.Centre()
        G_PAN_ID.Layout()
        G_PAN_ID.Show()
        G_PAN_ID.Refresh()
            
    
    #------------------------------------------------------------------
    def makePanel(self, staticTxt1, staticTxt2, b1txt, b2txt):
        global G_PAN_ID, T_TXT_ID, B_TXT_ID, LB_ID, RB_ID, RX_CB_ID, KP_CB_ID, CH_LB_ID
        global FLASH_COPRO, WRITE_KP, TEST_STEP, CURRENT_LOG, CAN_SKIP, DUT_MAC, TestNames
        global CustomTests, FIRST_TEST_PASS, SECOND_PASS_PLUS, SelectedTests
        global DT_S2_ID, DT_S2_C_ID, DT_M2_ID, DT_M2_B_ID, LB_CNT_ID, P_TXT_ID, DEVICE_TYPE
        global ZEBRA_LC, BTN_PRT_ID
    
        font = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)
        
        cantClick1 = False
        cantClick2 = False
        #self.GetSize()
        if G_PAN_ID != 0:
            G_PAN_ID.Destroy()                  #Destroy the old before creating new
        G_PAN_ID = wx.Panel(self, size=self.GetClientSize())
        wx.EVT_CLOSE(self, self.OnQuit)         #Might Want to Abort Worker Thread When Quitting...
       
        #Set Text Controls
        self.sTxt1 = wx.StaticText(G_PAN_ID, T_TXT_ID, staticTxt1, style=wx.ALIGN_CENTRE)
        self.sTxt1.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sTxt1.SetSize(self.sTxt1.GetBestSize())
        self.sTxt2 = wx.StaticText(G_PAN_ID, B_TXT_ID, staticTxt2, style=wx.ALIGN_CENTRE)
        self.sTxt2.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sTxt2.SetSize(self.sTxt2.GetBestSize())
        
        if staticTxt1.find('BUTTON1') != -1:
            self.sTxt1.SetForegroundColour('#FF00FF') # PINK wx.CYAN)  #Set Text 2 Color For Button1 USER ACTIONs
        elif staticTxt1.find('M3_RESET') != -1:
            self.sTxt1.SetForegroundColour('#FF9900') # ORANGE wx.BLACK)  #Set Text 2 Color For RX_RESET USER ACTIONs
        elif staticTxt1.find('RESET') != -1:
            self.sTxt1.SetForegroundColour(wx.BLUE)  #Set Text 2 Color For G20_RESET USER ACTIONs
        elif staticTxt1.find('Inspect') != -1 or staticTxt1.find('Press') != -1 or staticTxt1.find('Un-Power') != -1 :
            self.sTxt1.SetForegroundColour('#0000FF')  #Set Text 1 Color Blue For USER ACTIONs
        elif staticTxt1.find('FAIL') != -1:
            self.sTxt1.SetForegroundColour(wx.RED)   #Set Text 1 Color RED For Failures
        elif staticTxt1.find('PASSED') != -1:
            self.sTxt1.SetForegroundColour('#44a344' )  #33CC33') #Set Text 1 Color GREEN For good DUTs
        
        
        if staticTxt2.find('Button1') != -1 or staticTxt1.find('BUTTON1') != -1:
            self.sTxt2.SetForegroundColour('#FF00FF') # PINK   #Set Text 2 Color For Button1 USER ACTIONs
        elif staticTxt2.find('RX_RESET') != -1 or staticTxt1.find('M3_RESET') != -1:
            self.sTxt2.SetForegroundColour('#FF9900') # ORANGE  #Set Text 2 Color For RX_RESET USER ACTIONs
        elif staticTxt2.find('G20_RESET') != -1:
            self.sTxt2.SetForegroundColour(wx.BLUE)  #Set Text 2 Color For G20_RESET USER ACTIONs
        elif staticTxt2.find('Powering Down') != -1:
            self.sTxt2.SetForegroundColour('#FF9900')  #Set Text 2 Color For power down USER ACTIONs
        
        
        G_PAN_ID.SetBackgroundColour('#DCDCDC')                         # bright pink '#DD3388'
        
        
            
        #Add Program RX & Write Key Checkboxes if Screen1
        if TEST_STEP == 1:
#            
            Prt_Btn = wx.Button(G_PAN_ID, BTN_PRT_ID, 'Print Label', (380, 118), (65, -1))
  
            self.Bind(wx.EVT_BUTTON, self.OnPrintAnyMac, Prt_Btn)
            
            self.MacInput = wx.TextCtrl(G_PAN_ID, TXT_BX_ID, "MAC_ID_NO_DASHES", (365, 90), size=(114, -1))
          
            progRX = wx.CheckBox(G_PAN_ID, RX_CB_ID, label="Program Coprocessor?")
            progRX.SetValue(FLASH_COPRO)
            #Bind Program Check
            self.Bind(wx.EVT_CHECKBOX, self.OnProgChck, progRX)
            
            
            writeKP = wx.CheckBox(G_PAN_ID, KP_CB_ID, label="Write Key?")
            writeKP.SetValue(WRITE_KP)
            #Bind Kep-Pair Check
            self.Bind(wx.EVT_CHECKBOX, self.OnKeyPChck, writeKP)

            if not CAN_SKIP:
                progRX.Disable()
                writeKP.Disable()
                
            S2_DT = wx.CheckBox(G_PAN_ID, DT_S2_ID, label="S2")
            if DEVICE_TYPE == 'S2':
                S2_DT.SetValue(True)
            #Bind Device Type Check
            self.Bind(wx.EVT_CHECKBOX, self.OnDeviceTypeChck, S2_DT)
            self.S2_DT = S2_DT
            
            S2_C_DT = wx.CheckBox(G_PAN_ID, DT_S2_C_ID, label="S2_C")
            if DEVICE_TYPE == 'S2_C':
                S2_C_DT.SetValue(True)
            #Bind Device Type Check
            self.Bind(wx.EVT_CHECKBOX, self.OnDeviceTypeChck, S2_C_DT)
            self.S2_C_DT = S2_C_DT
            
            M2_DT = wx.CheckBox(G_PAN_ID, DT_M2_ID, label="M2")
            if DEVICE_TYPE == 'M2':
                M2_DT.SetValue(True)
            #Bind Device Type Check
            self.Bind(wx.EVT_CHECKBOX, self.OnDeviceTypeChck, M2_DT)
            self.M2_DT = M2_DT
            
            M2_B_DT = wx.CheckBox(G_PAN_ID, DT_M2_B_ID, label="M2_B")
            if DEVICE_TYPE == 'M2_B':
                M2_B_DT.SetValue(True)
            #Bind Device Type Check
            self.Bind(wx.EVT_CHECKBOX, self.OnDeviceTypeChck, M2_B_DT)
            self.M2_B_DT = M2_B_DT
            
            self.sTxt3 = wx.StaticText(G_PAN_ID, P_TXT_ID, "Labels", (430, 0), style=wx.ALIGN_RIGHT)
            self.sTxt3.SetFont(wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL))
            
            Lb_Cnt = ['0','1','2','3','4','5']
            self.LABEL_LIST = wx.ListBox(G_PAN_ID, LB_CNT_ID, (430, 20), (40, 20), Lb_Cnt, wx.LB_SINGLE )
            self.Bind(wx.EVT_LISTBOX, self.OnLabelCountChange, self.LABEL_LIST)
            print 'MAC labels to print = ' + str(ZEBRA_LC)
            self.LABEL_LIST.SetSelection(ZEBRA_LC, True) 
            
            
            
        #    (self, parent, id, pos, size, choices, style, validator, name)
        # Set Button Controls
        if b1txt == "NADA":
            cantClick1 = True
            b1txt = ""
        if b2txt == "NADA":
            cantClick2 = True
            b2txt = ""
        self.lBut = wx.Button(G_PAN_ID, LB_ID, b1txt)
        self.rBut = wx.Button(G_PAN_ID, RB_ID, b2txt)
        self.lBut.Show()
        self.rBut.Show()
        if cantClick1:
            self.lBut.Hide()
            self.lBut.Disable()
        if cantClick2:
            self.rBut.Hide()
            self.rBut.Disable()
            
        # bind the button events to handlers
        if b1txt == "RESTART" and b2txt == "Re-Print1":
            self.Bind(wx.EVT_BUTTON, self.OnRestartBtn, self.lBut)
            self.Bind(wx.EVT_BUTTON, self.OnPrintLabel, self.rBut)
        elif b1txt == "RESTART" and b2txt == "":
            self.Bind(wx.EVT_BUTTON, self.OnRestartBtn, self.lBut)
        elif b1txt == "PASS":
            self.Bind(wx.EVT_BUTTON, self.OnPassBtn, self.lBut)
       
            
            
        if b2txt == "START":
            self.Bind(wx.EVT_BUTTON, self.OnStartBtn, self.rBut)
        elif b2txt == "FAIL":
            self.Bind(wx.EVT_BUTTON, self.OnFailBtn, self.rBut)
            
        # Layout the Controls with Sizers
        vSizer = wx.BoxSizer(wx.VERTICAL)
        vSizer.Add(self.sTxt1, 0, wx.TOP | wx.ALIGN_CENTER, 5)
        vSizer.Add(self.sTxt2, 0, wx.TOP | wx.ALIGN_CENTER, 5)
        
        if TEST_STEP == 1:
            hSizer = wx.BoxSizer(wx.HORIZONTAL)
#            vSizer.Add(updateFile, 0, wx.TOP | wx.ALIGN_CENTER, 5)
            vSizer.Add(progRX, 0, wx.TOP | wx.ALIGN_CENTER, 5)
            vSizer.Add(writeKP, 0, wx.TOP | wx.ALIGN_CENTER, 5)
            # add vertical space 5 pixels.
            vSizer.Add((-1, 5))
            
            S2_DT.SetFont(font)
            hSizer.Add(S2_DT)
            
            self.S2_C_DT.SetFont(font)
            hSizer.Add(self.S2_C_DT, flag=wx.CENTER, border=10)
           
            M2_DT.SetFont(font)
            hSizer.Add(M2_DT, flag=wx.CENTER, border=10)
            
            M2_B_DT.SetFont(font)
            hSizer.Add(M2_B_DT, flag=wx.CENTER, border=10)
            
            vSizer.Add(hSizer, flag=wx.CENTER, border=10)
            
            
        bSizer = wx.BoxSizer(wx.HORIZONTAL)
        bSizer.Add(self.lBut, 0, wx.ALL, 10)
        bSizer.Add(self.rBut, 0, wx.ALL, 10)
        vSizer.Add(bSizer, 0, wx.BOTTOM | wx.ALIGN_CENTER, 10)
        #sizer = wx.BoxSizer(wx.HORIZONTAL)
        #sizer.Add(self.pic1, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        #sizer.Add(vSizer, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        #sizer.Add(self.pic2, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        #G_PAN_ID.SevSizer(sizer)
        G_PAN_ID.SetSizer(vSizer)
        G_PAN_ID.Centre()
        G_PAN_ID.Layout()
        G_PAN_ID.Show()
        if TEST_STEP == 1:
            if CURRENT_LOG is not None:         #Remove any Old Log for ReStart)
                CURRENT_LOG.close()
                DUT_LOG.removeHandler( CURRENT_LOG )
                CURRENT_LOG = None
            DUT_MAC = ""
            
            
            # wait for the start Button every time
            FIRST_TEST_PASS = True
              
            self.worker = WorkerThread(self)    #Start Worker Thread
            
            # wait for the Test Names list to be populated.
            while not TestNames:
                time.sleep(.1)
                
            # Has to be here so that the tests list gets inited.
            CustTests = wx.CheckBox(G_PAN_ID, CT_CB_ID, label="Custom Tests")
                
            #Bind Custom Tests Check
            self.Bind(wx.EVT_CHECKBOX, self.OnCustTest, CustTests)
            
            
                
            ChBxLb = wx.CheckListBox(G_PAN_ID, CH_LB_ID, (0, 20), wx.Size(100, 140), TestNames)
                
            self.Bind(wx.EVT_CHECKLISTBOX, self.EvtCheckListBox, ChBxLb)
            
            self.ChBxLb = ChBxLb
            
            self.ChBxLb.SetChecked(SelectedTests)
            
                     
            if CUST_TEST:
                CustTests.SetValue(True)
            else:
                CustTests.SetValue(False)
                self.ChBxLb.Hide()
    
    def OnPrintAnyMac(self, evt):
        global ZEBRA_LC, DUT_MAC, TXT_BX_ID
        
        
        Copy_MAC = DUT_MAC
        Tmp = self.MacInput.GetValue()
        
        
        # Hex Numbers only.
        if all(c in string.hexdigits for c in Tmp) and len(Tmp) == 12:
            Tmp1 = Tmp.upper()
            Tmp1 = "-".join(Tmp1[i:i+2] for i in range(0, len(Tmp), 2))
            print "Printing one Barcode Label..."
            DUT_MAC = str(Tmp1)
            
            
            labelCnt = ZEBRA_LC
            ZEBRA_LC = 1
            
            self.Frame_PrintZebraLabels()
            
            DUT_MAC = Copy_MAC
            ZEBRA_LC = labelCnt
        else:
            print "Hex Numbers Only!!"
            self.MacInput.SetValue('')
            self.MacInput.SetFocus()
        
       
    def OnLabelCountChange(self, evt):
        global ZEBRA_LC
        
        ListObj = evt.GetEventObject()
        ZEBRA_LC = ListObj.GetSelection()
        
        print "You selected to print " + str(ZEBRA_LC) + " Labels."
        
    
    #--------------------------------------
    #  Reprint the one label.  
    def OnPrintLabel(self, evt): 
        global ZEBRA_LC  
        
        print "Printing one Barcode Label..."
        
        labelCnt = ZEBRA_LC
        ZEBRA_LC = 1
        
        self.Frame_PrintZebraLabels()
        
        ZEBRA_LC = labelCnt
        
         
    #--------------------------------------
    # Select Device Type  done event
    def OnCheckDone(self, evt):
        global DEVICE_TYPE, TEST_STEP, G_PAN_ID
        global G20_TTY, RX_TTY, LIL_TTY, METER_TTY, MUX_TTY
        global S2_COMMS, S2_C_COMMS, M2_COMMS, M2_B_COMMS
        
        

        ChBx = evt.GetEventObject()
        DT = ChBx.GetLabel()
        
        PortList = []
        
        # Clear all checks but the one selected.
        if DT != 'S2':
            self.S2_DT.SetValue(False)
        if DT != 'S2_C':
            self.S2_C_DT.SetValue(False)
        if DT != 'M2':
            self.M2_DT.SetValue(False)
        if DT != 'M2_B':
            self.M2_B_DT.SetValue(False)
        
       
        # pick the com ports based on the Device Type.   
        if DT == 'S2':
            PortList = S2_COMMS       
        elif DT == 'S2_C':
            PortList = S2_C_COMMS 
        elif DT == 'M2':
            PortList = M2_COMMS
        elif DT == 'M2_B':
            PortList = M2_B_COMMS
             
        G20_TTY     =  PortList[0]
        RX_TTY      =  PortList[1]
        LIL_TTY     =  PortList[2]
        METER_TTY   =  PortList[3]
        MUX_TTY     =  PortList[4]
            
        
        
        DEVICE_TYPE = DT
        print 'Selected Device Type: ' + DEVICE_TYPE
        
        
        TEST_STEP = 1
        
        ERR_STR = self.InitCommPorts()

        # Set up event handler for any worker thread results
        EVT_RESULT(self,self.OnResult)
        # And indicate we don't have a worker thread yet
        
        self.worker = None
        
        if ERR_STR is not None:
            TEST_STEP = 0
            self.makePanel("PROGRAM ERROR", ERR_STR, "NADA", "NADA")
        else:
            
            self.makePanel("Waiting for Start Button.", "(Click Start button to start test)", "NADA", "START")
    

    #--------------------------------------
    #  Device Check Box events
    def OnDeviceTypeChck(self, evt):
        global DEVICE_TYPE, TestNames
        global G20_TTY, RX_TTY, LIL_TTY, METER_TTY, MUX_TTY
        global S2_COMMS, S2_C_COMMS, M2_COMMS, M2_B_COMMS
        
        ChBx = evt.GetEventObject()
        DT = ChBx.GetLabel()
        
        PortList = []
        
        # Clear all checks but the one selected.
        if DT != 'S2':
            self.S2_DT.SetValue(False)
        if DT != 'S2_C':
            self.S2_C_DT.SetValue(False)
        if DT != 'M2':
            self.M2_DT.SetValue(False)
        if DT != 'M2_B':
            self.M2_B_DT.SetValue(False)
        
        # pick the com ports based on the Device Type.   
        if DT == 'S2':
            PortList = S2_COMMS       
        elif DT == 'S2_C':
            PortList = S2_C_COMMS 
        elif DT == 'M2':
            PortList = M2_COMMS
        elif DT == 'M2_B':
            PortList = M2_B_COMMS
             
        G20_TTY     =  PortList[0]
        RX_TTY      =  PortList[1]
        LIL_TTY     =  PortList[2]
        METER_TTY   =  PortList[3]
        MUX_TTY     =  PortList[4]
            
        
        
        DEVICE_TYPE = DT
        
        TestNames = []
        self.worker = None
        self.ChBxLb.Clear() 
        self.worker = WorkerThread(self)    #ReStart Worker Thread
        
       
        # wait for the Test Names list to be populated.
        while not TestNames:
            time.sleep(.1)
        # the testnames for the new device type selected.    
        self.ChBxLb.AppendItems(TestNames)
                                
        self.ChBxLb.SetChecked(SelectedTests)

    #--------------------------------------
    # show or don't show CheckBoxList
    def OnCustTest(self, evt):
        global CUST_TEST, RequiredTests, DEVICE_TYPE
        
        DT = DEVICE_TYPE
        
        if DT == 'S2':
            ReqTests = S2_TestsEnabled       
        elif DT == 'S2_C':
            ReqTests = S2_C_TestsEnabled 
        elif DT == 'M2':
            ReqTests = M2_TestsEnabled
        elif DT == 'M2_B':
            ReqTests = M2_B_TestsEnabled
            
        RequiredTests = [] 
        cnt = 0
        for tests in ReqTests:
            if tests:
                RequiredTests.append(cnt)
            cnt += 1
            
        CUST_TEST = evt.Checked()
        print "You Clicked the Custom Tests.",
        if(CUST_TEST == False):
            self.ChBxLb.Hide()
            print "Don't ",
        else:
            self.ChBxLb.SetChecked(RequiredTests)
            self.ChBxLb.Show()
            
        print "Use Custom Tests..."
        
        
        
    def EvtCheckListBox(self, event):
        global DEVICE_TYPE, CustomTests, SelectedTests
        index = event.GetSelection()
        label = self.ChBxLb.GetString(index)
        status = ' not'
        
        DT = DEVICE_TYPE
        ReqTests = []
        
        if DT == 'S2':
            ReqTests = 3   
        elif DT == 'S2_C':
            ReqTests = 4
        elif DT == 'M2':
            ReqTests = 4
        elif DT == 'M2_B':
            ReqTests = 4
        
        if index < ReqTests:   # is this a Legal test to disable?
            print 'This is a required setup test!\n'
            print 'Selection denied!\n'
            #self.ChBxLb.SetChecked(RequiredTests)
            self.ChBxLb.Check(index)
            return 1
        # Enable this test.
        elif self.ChBxLb.IsChecked(index) and index > 3:
            status = ''
            CustomTests[index] = True
            SelectedTests.append(index)
        # Disable this test.
        elif not self.ChBxLb.IsChecked(index):
            CustomTests[index] = False
            SelectedTests.remove(index)
        
        #self.log.WriteText('Box %s is %schecked \n' % (label, status))
        print '%s test is%s selected \n' % (label, status)
        self.ChBxLb.SetSelection(index)    # so that (un)checking also selects (moves the highlight)
    
    
    
    #----------------------------------Handler for Start Button
    def OnStartBtn(self, evt):
        global FIRST_TEST_PASS
        global G_PAN_ID, T_TXT_ID, B_TXT_ID, LB_ID, RB_ID, RX_CB_ID, KP_CB_ID
       
        #Set Text Controls
        
        self.sTxt1.SetLabel("START OF TEST") 
        #self.sTxt2.SetLabel("Testing...")
        
        tSizer = wx.BoxSizer(wx.HORIZONTAL)
        tSizer.Add(self.sTxt1, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        tSizer.Add(self.sTxt2, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        self.rBut.SetLabel("")
        self.rBut.Hide()
        self.rBut.Disable()
        
        
        FIRST_TEST_PASS = False
           
    #----------------------------------Handler for Programming Checkbox
    def OnQuit(self, evt):
        if self.worker:
            print "aborting for Quit"
            self.worker.abort()                 #Flag the worker thread to stop if running
        self.Destroy()
    #----------------------------------Handler for Programming Checkbox
    def OnProgChck(self, evt):
        global FLASH_COPRO
        FLASH_COPRO = evt.Checked()
        print "You Clicked the Program Checkbox so FT will",
        if(FLASH_COPRO == False):
            print "NOT",
        print "program the Coprocessor..."
    #-------------------------------------Handler for Key-Pair Checkbox
    def OnKeyPChck(self, evt):
        global WRITE_KP
        WRITE_KP = evt.Checked()
        print "You Clicked the Key-Pair Checkbox so FT will",
        if(WRITE_KP == False):
            print "NOT",
        print "write to rsa_key.pem..."
        
    #----------------------------------------Handler for Restart Button
    def OnRestartBtn(self, evt):
        global TEST_STEP, G20_C, G20_TTY, RX_C, RX_TTY,MUX_C, MUX_TTY,METER_C, METER_TTY, SECOND_PASS_PLUS
        print "You Clicked the (RESTART) Button; Restarting"
        if self.worker:
            print "Sleeping for worker abort @ Step %d" % TEST_STEP
            time.sleep(2)   #TODO?? wait for abort (from userFAIL)
        TEST_STEP = 0
       
        print "Re-Opening COMs..."
        

        errSt = self.InitCommPorts()
        
        
        if(errSt == None):
            print "COM Re-Open Okay..."

            TEST_STEP = 1
            SECOND_PASS_PLUS = True
            self.makePanel("Waiting for Start Button.", "(Click Start button to start test)", "NADA", "START")
            #self.makePanel("START OF TEST", "Testing for Shorts...", "NADA", "NADA")
            
        else:
            if errSt != None:
                print errSt
                self.makePanel("PROGRAM ERROR", errSt, "RESTART", "NADA")
            else:
                self.makePanel("PROGRAM ERROR", "Unkwon Error!", "RESTART", "NADA")
            
            DUT_LOG.error( errStr )
                
        
        
                 
    #-------------------------------------------Handler for Fail Button
    def OnFailBtn(self, evt):
        global TEST_STEP, DUT_MAC, EOT_STR, errStr, MUX_C, MUX_VALUE 
        global TestNames, MK_PANEL, CUST_TEST, DEVICE_TYPE, S2_PWR_OFF
        
        print "You Clicked the Right (FAIL) Button"
        if self.worker:
            print "Aborting Worker @ Step %d" % TEST_STEP
            self.worker.abort()     #Flag the worker thread to stop if running
            
        if TestNames[TEST_STEP - 1] == 'VisualLED':
            errStr = "FAIL ON LEDs"
        elif TestNames[TEST_STEP - 1] == 'S2_Button1' or \
             TestNames[TEST_STEP - 1] == 'M2_B_Button1':
            errStr = "FAIL BUTTON1"
        elif TestNames[TEST_STEP - 1] == 'S2_M3_Reset' or \
             TestNames[TEST_STEP - 1] == 'Rx_ResetButton':
            errStr = "FAIL ON Coprocessor RESET Button"
        elif TestNames[TEST_STEP - 1] == 'G20_Reset':
            errStr = "FAIL ON G20 RESET Button"
        else:
            print "Test name: " + TestNames[TEST_STEP - 1]
            errStr = "FAIL for Test " + TestNames[TEST_STEP - 1]
            
        DUT_LOG.error( errStr )
            
        TEST_STEP = 0
        
        if DUT_MAC != "":
            self.makePanel("Test FAILED for %s:" % DUT_MAC, "\n " + errStr + EOT_STR, "RESTART", "NADA")
        else:
            self.makePanel("Test FAILED: ", errStr + EOT_STR, "RESTART", "NADA")
       
        if DEVICE_TYPE != 'S2':
            # Turn off the Power.     
            MUX_C.flushInput()
            MUX_C.write("00\r")
            MUX_C.flush()
            MUX_VALUE = "00"
            time.sleep(2)   # Make sure the power is OFF.
        else:
            print 'Turning off S2 power'
            Rtrn =  self.Frame_S2_Power(S2_PWR_OFF)
            if Rtrn:
                errStr = "Fail S2 Power off Failed! \n Try Unplugging & Replugging USB."
                return 1
    #-------------------------------------------Handler for Pass Button
    def OnPassBtn(self, evt):
        global TEST_STEP, TestNames, MK_PANEL, CUST_TEST
        print "You Clicked the Left (PASS) Button"
        if not self.worker:
            if TestNames[TEST_STEP - 1] == 'VisualLED':
                DUT_LOG.info( "G20 LEDs Test: Passed" )
                TEST_STEP += 1
                if CUST_TEST:
                    MK_PANEL['TstStart'] = "Custom Test Mode!!"
                elif DEVICE_TYPE == 'S2':
                    MK_PANEL['TstStart'] = "Testing Relays..."
                else:
                    MK_PANEL['TstStart'] = "Testing RX<-->G20 COMs..."
                    
                MK_PANEL['TstDone'] = "G20 LEDs Test Good"
                MK_PANEL['Button1'] = "NADA"
                MK_PANEL['Button2'] = "NADA" 
                
            else: 
                print "never see this"
                print "Restarting test Program!"
                python = sys.executable
                os.execl(python, python, *sys.argv)
                return 1
            
            self.makePanel(MK_PANEL['TstDone'], MK_PANEL['TstStart'], MK_PANEL['Button1'], MK_PANEL['Button2'])
            self.worker = WorkerThread(self)
        else:
            TEST_STEP = 0
            self.makePanel("SOFTWARE MALFUNCTION", "ERROR: WORKER BUSY", "RESTART", "Next")
            
    #------------------------------------------------------------------
    def OnResult(self, event):
        global TEST_STEP, CURRENT_LOG, ZEBRA_LC, DUT_MAC, EOT_STR, G20_C, RX_C, MUX_C, METER_C, Tests, DEVICE_TYPE, errStr
        self.worker = None
        print "Got Result: %s!!" % event.data
        TESTS = len(Tests)
        
        # make sure it is an int.
        if event.data.isdigit():
            TestStep = int(event.data)
        else:
            TestStep = TEST_STEP
        
        if event.data.rfind("FAIL") != -1 or errStr != None:
            TEST_STEP = 0       #TEST_STEP = 0 => Initialize GUI
            
            #self.CloseCommPorts()
            
            
            print event.data
            if CURRENT_LOG is not None:
                DUT_LOG.error( event.data )
            if DUT_MAC != "":
                self.makePanel("Test FAILED for %s:" % DUT_MAC, event.data + EOT_STR, "RESTART", "NADA")
            else:
                self.makePanel("Test FAILED:", event.data + EOT_STR, "RESTART", "NADA")
        elif TestStep >= 1 and TestStep <= TESTS:    
            if MK_PANEL['Button1'] == "NADA":
                TEST_STEP += 1
            self.makePanel(MK_PANEL['TstDone'], MK_PANEL['TstStart'], MK_PANEL['Button1'], MK_PANEL['Button2'])
            
            # if we have to wait for pass 
            if MK_PANEL['Button1'] == "NADA":
                self.worker = WorkerThread(self)
            
        elif TestStep == TESTS + 2:    
            TEST_STEP += 1
            self.worker = WorkerThread(self)
            
            self.makePanel("ALL TESTS PASSED!!!", "Powering Down DUT...\n\rUSE CAUTION when removing PCA caps still CHARGED!!!", "NADA", "NADA")
        elif TestStep == TESTS + 1:    
            sX = DEVICE_TYPE

            if ZEBRA_LC:
                self.makePanel("%s TEST PASSED for %s!!" % (sX, DUT_MAC), "MAC Labels Printing; Please Wait...", "NADA", "NADA")
                TEST_STEP += 1
                self.worker = WorkerThread(self)

            else:
                self.makePanel("%s TEST PASSED for %s!!" % (sX, DUT_MAC), "User Selected No MAC Labels." + EOT_STR, "RESTART", "Re-Print1")
        elif TestStep == TESTS + 3:  #TEST_STEP = 16 => MAC Labels Printed
            sX = DEVICE_TYPE
            # self.OnRestartBtn(self)      # TEST ONLY KGB
            
            self.makePanel("%s TEST PASSED for %s!!" % (sX, DUT_MAC), "MAC Labels Printed." + EOT_STR, "RESTART", "Re-Print1")
        else:
            print "Unhandled step %d" % TEST_STEP
            self.makePanel("SOFTWARE MALFUNCTION", "ERROR: UNKNOWN STEP", "RESTART", "Next")
            print "Restarting test Program!"
            python = sys.executable
            os.execl(python, python, *sys.argv)
            
            
    #---------------------------------------------------------------------
    #    Print MAC ID Labels
    def Frame_PrintZebraLabels(self):
        global  DUT_MAC, ZEBRA_DV, ZEBRA_LC, MFG
        
        
        if ZEBRA_LC:
            print "ZEBRA GO!! " + DUT_MAC
            macNoSepSTR = ""
            for i in range(0,17):
                if DUT_MAC[i] != '-':
                    macNoSepSTR = macNoSepSTR + DUT_MAC[i]
            if MFG:
                labelStr = "^XA^FO038,15^BY2^BCN,61,N,N,N^FD%s^FS^FO110,80^ADN36,20^FD%s^FS^XZ" % (macNoSepSTR, DUT_MAC)
            else:
                labelStr = "^XA^FO140,15^BY2^BCN,61,N,N,N^FD%s^FS^FO200,80^ADN36,20^FD%s^FS^XZ" % (macNoSepSTR, DUT_MAC)
            
            printStr = ""
            
            if ZEBRA_DV == None:
                zebra_name   = win32print.GetDefaultPrinter()
                ZEBRA_DV = win32print.OpenPrinter(zebra_name)
            
            for i in range(ZEBRA_LC):
                printStr = printStr + labelStr
            #print printStr
            try:
                zJob = win32print.StartDocPrinter(ZEBRA_DV, 1, ("MAC Labels", None, "RAW"))
                win32print.WritePrinter(ZEBRA_DV, printStr)
                win32print.EndDocPrinter(ZEBRA_DV)
                print "%d MAC LABEL PRINTED" % ZEBRA_LC
            except:
                print 'FAIL ON ZEBRA (call EnerNOC!!)'
                errStr = "FAIL BAR CODE LABEL PRINT"
                return
            
        else:
            print "USER SELECTED NO LABELS" 
            
    #---------------------------------------------------------------------
    def Frame_S2_Power(self, Action = None):
        global DIR
        
        result = 1      # set fail to start
        
        # Two possible device Id's
        UnitId1 = ' IGEUN '
        UnitId2 = ' CNVEJ '
        
        cmd = DIR + UnitId1 + Action
        
        if Action != None:
            p = Popen(cmd) #, stdout=PIPE, stderr=PIPE)
            p.communicate()
            result = p.returncode
            
            # if the first failed try the next device.
            if result:
                cmd = DIR + UnitId2 + Action
                p = Popen(cmd) #, stdout=PIPE, stderr=PIPE)
                p.communicate()
                result = p.returncode
                
                
        return result
        
    #---------------------------------------
    def CloseCommPorts(self):
        global TEST_STEP, G20_C, G20_TTY, RX_C, RX_TTY,MUX_C, MUX_TTY,METER_C, METER_TTY, LIL_C, LIL_TTY
        print "Closing COMs..."
        if G20_C != None: 
            G20_C.close()
        
        if RX_C != None: 
            RX_C.close()
            
        if LIL_C != None:
            LIL_C.close()
            
        if MUX_C != None: 
            MUX_C.close()
            
        if METER_C != None: 
            METER_C.close()
        
    #------------------------------------------------------------------
    def InitCommPorts(self): 
        global TEST_STEP, G20_C, G20_TTY, RX_C, RX_TTY,MUX_C, MUX_TTY,METER_C, METER_TTY, LIL_C, LIL_TTY, DEVICE_TYPE
        ERR_STR     = None      
        
        self.CloseCommPorts()
        
        G20_C   = None
        RX_C    = None
        LIL_C   = None
        MUX_C   = None                          #Init the MUX Console Invalid
        METER_C = None                          #Init the Meter Console Invalid.
        
        if(DEVICE_TYPE != 'S2'):
            try:                    #Check for FTDI  Availability
                MUX_C = serial.Serial(port=MUX_TTY, baudrate=38400, timeout=0.1)     #TODO None for waiting forever
            except:
                ERR_STR = "ERROR:MUX  %s NOT Available for Use with Console" % MUX_TTY + \
                          "\nTEST FIXTURE USB MAY NEED to be \r\nPOWERED ON or POWER CYCLED!!!"
            
        if(MUX_C is not None):  #Check for FTDI Availability if MUX_C ok   
            try:                    #Check for FTDI  Availability
                METER_C = serial.Serial(port=METER_TTY, baudrate=9600, timeout=0.5 )     #TODO None for waiting forever
            except:
                ERR_STR = "ERROR:Meter  %s NOT Available for Use with Console" % METER_TTY + \
                      "\nTEST METER USB MAY NEED to be \r\nPOWERED ON or POWER CYCLED!!!"
        
        if(METER_C is None and DEVICE_TYPE == 'S2'):  
            #Check for FTDI Availability if METER_C ok                    #Check for FTDI to J603 Availability
            try:
                LIL_C = serial.Serial(port=LIL_TTY, baudrate=115200, timeout=2)     #TODO None for waiting forever
            except:
                ERR_STR = "ERROR:M3  %s NOT Available for Use with Console" % LIL_TTY + \
                      "\nTEST FIXTURE USB MAY NEED to be \r\nPOWERED ON or POWER CYCLED!!!" 
        elif(METER_C is not None and DEVICE_TYPE == 'S2_C'):  
            #Check for FTDI Availability if METER_C ok                    #Check for FTDI to J603 Availability
            try:
                LIL_C = serial.Serial(port=LIL_TTY, baudrate=115200, timeout=2)     #TODO None for waiting forever
            except:
                ERR_STR = "ERROR:M3  %s NOT Available for Use with Console" % LIL_TTY + \
                      "\nTEST FIXTURE USB MAY NEED to be \r\nPOWERED ON or POWER CYCLED!!!"
                      
        elif(METER_C is not None and DEVICE_TYPE == 'M2' or DEVICE_TYPE == 'M2_B'):  
            #Check for FTDI Availability if METER_C ok  
            try:                    #Check for FTDI  Availability
                RX_C = serial.Serial(port=RX_TTY, baudrate=38400, timeout=0.1)     #TODO None for waiting forever
            except:
                ERR_STR = "ERROR:RX  %s NOT Available for Use with Console" % RX_TTY + \
                      "\nTEST FIXTURE USB MAY NEED to be \r\nPOWERED ON or POWER CYCLED!!!"
                
        if(RX_C is not None) or (LIL_C is not None):  #Check for FTDI Availability if RX_C ok
            try:
                G20_C = serial.Serial(port=G20_TTY, baudrate=115200, timeout=1) #TODO None for waiting forever
            except:
                ERR_STR = "ERROR:G20 %s NOT Available for Use with Console" % G20_TTY + \
                      "\nTEST FIXTURE USB MAY NEED to be \r\nPOWERED ON or POWER CYCLED!!!"
        if (RX_C is not None) or (LIL_C is not None) and (G20_C is not None) and ZEBRA_LC:
            try:
                
                zebra_name   = win32print.GetDefaultPrinter()
                ZEBRA_DV = win32print.OpenPrinter(zebra_name)
                
                print "Using %s to Print MAC Labels" % zebra_name
            except:
                ERR_STR = "ERROR: Could NOT connect to Label Printer"
                
        if ERR_STR == None:
            print "COM & Print Initialization Okay..."
            
            # If this is not an S2.
            if(MUX_C is not None and DEVICE_TYPE != 'S2'):
                # Turn off the Power.     
                MUX_C.flushInput()
                MUX_C.write("00\r")
                MUX_C.flush()
                MUX_VALUE = "00"
                time.sleep(2)   # Make sure the power is OFF.
            else:
                print 'Turning off S2 power'
                Rtrn =  self.Frame_S2_Power(S2_PWR_OFF)
                if Rtrn:
                    ERR_STR = "Fail S2 Power Off Failed! \nTry Unplugging & Replugging USB."
                   
        else:
            print "COM PORT SETUP FAILD: %s" % ERR_STR
                      
        return ERR_STR
        
#----------------------------------------------------------------------
# Here's The Program
#----------------------------------------------------------------------
if __name__ == '__main__':
    
    ERR_STR     = None   
    #-----------------------------------------------------------The GUI
    app = wx.App(False)                             #Create a new app
    frame = theFrame(None, -1)                      #Put theFrame into it (Init trys to Opens COMs)
    #  frame.SetIcon(wx.Icon('PICS\BT-Icon.ico', wx.BITMAP_TYPE_ICO))
    #frame.SetIcon(wx.Icon('PICS\sandwich.ico', wx.BITMAP_TYPE_ICO))
    frame.Show(True)                                #Show theFrame
    app.SetTopWindow(frame)                         #put it on top
    app.MainLoop()                                  #run the App
    #-----------------------------------------------------------On Exit
    print "Done.  Closing COMs, Log, and Printer..."
    if G20_C != None: 
        G20_C.close()
        
    if RX_C != None: 
        RX_C.close()
        
    if LIL_C != None:
        LIL_C.close()
        
    if MUX_C != None: 
        MUX_C.close()
        
    if METER_C != None: 
        METER_C.close()
        
    
    if CURRENT_LOG is not None:
        CURRENT_LOG.close()
    if ZEBRA_DV is not None:
        win32print.ClosePrinter(ZEBRA_DV)
        
    try: sys.exit(0)
    except: pass
    
