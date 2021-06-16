#!/usr/bin/env python
# coding: utf-8

# References
# Useful docs / articles / etc
#   
#   1 - [A Python wrapper around AHK](https://pypi.org/project/ahk/)
# 
#   2 - [OpenCV on Wheels](https://pypi.org/project/opencv-python/)
#
#   3 - [Autopilot for Elite Dangerous using OpenCV and thoughts on CV enabled bots in visual-to-keyboard loop]
#       (https://networkgeekstuff.com/projects/autopilot-for-elite-dangerous-using-opencv-and-thoughts-on-cv-enabled-bots-in-visual-to-keyboard-loop/)
#   
#   5 - [Direct Input to a Game - Python Plays GTA V]
#       (https://pythonprogramming.net/direct-input-game-python-plays-gta-v/)
#   
#   6 - [Cross-platform GUI automation for human beings](https://pyautogui.readthedocs.io/en/latest/index.html)

from random import random
from PIL import ImageGrab
from mss import mss
from pyautogui import countdown, size
from time import sleep, time
from datetime import datetime
from math import degrees, atan
from json import load, loads, dump
from numpy import array, sum, where, asarray
from os import environ, listdir, system
from xml.etree.ElementTree import parse
from discord_webhook import DiscordWebhook
from colorlog import getLogger, ColoredFormatter
from src.directinput import SCANCODE, PressKey, ReleaseKey
from os.path import join, isfile, getmtime, getsize, abspath, exists
from logging import basicConfig, INFO, DEBUG, StreamHandler, info, debug, warning, error, critical, exception
from cv2 import cvtColor, COLOR_RGB2BGR, COLOR_BGR2GRAY, createCLAHE, imshow, waitKey, destroyAllWindows, imwrite,  \
    COLOR_GRAY2BGR, COLOR_BGR2HSV, inRange, imread, IMREAD_GRAYSCALE, TM_CCOEFF_NORMED, matchTemplate, minMaxLoc, \
    rectangle, circle

""" ################################# """
""" Constant and Variable declaration """
"""       Basic Initialization        """
""" ################################# """

# Constants
RELEASE = '2021-6-16-0 203Null'
PATH_LOG_FILES, PATH_KEYBINDINGS = None, None
KEY_MOD_DELAY = 0.010
KEY_REPEAT_DELAY = 0.100
KEY_DEFAULT_DELAY = 0.200
FUNCTION_DEFAULT_DELAY = 0.500
SCREEN_WIDTH, SCREEN_HEIGHT = size()
keys_to_obtain = [
    'YawLeftButton',
    'YawRightButton',
    'RollLeftButton',
    'RollRightButton',
    'PitchUpButton',
    'PitchDownButton',
    'SetSpeedZero',
    # 'SetSpeed25',
    'SetSpeed75',
    'SetSpeed100',
    'HyperSuperCombination',
    'UIFocus',
    'UI_Up',
    'UI_Down',
    'UI_Left',
    'UI_Right',
    'UI_Select',
    'UI_Back',
    'CycleNextPanel',
    'HeadLookReset',
    'PrimaryFire',
    'SecondaryFire',
    'MouseReset'
]
config = dict(DiscoveryScan="Primary",
              SafeNet=True,
              # AutoFSS=False,
              PrepJump=True,
              # StartKey='home',
              # EndKey='end',
              JumpTries=5,
              RefuelThreshold=30,
              TerminationCountdown=120,
              # JournalPath="",
              # BindingsPath="",
              # GraphicsConfigPath="",
              DiscordWebhook=False,
              DiscordWebhookURL="",
              DiscordUserID="",
              DebugLog=True,
              )

# Variable Declaration
statusCache = None
statusCacheSize = None
keys = [None]
autopilot_start_time = datetime.max
prep_engaged = datetime.min

# def get_config():
if exists('config.json'):
    with open('config.json') as json_file:
        config = load(json_file)
else:
    with open('config.json', 'w') as json_file:
        dump(config, json_file)

# Logging

basicConfig(filename='autopilot.log', level=DEBUG)
logger = getLogger()
logger.setLevel((INFO, DEBUG)[config["DebugLog"]])
handler = StreamHandler()
handler.setLevel((INFO, DEBUG)[config["DebugLog"]])
handler.setFormatter(
    ColoredFormatter('%(log_color)s%(levelname)-8s%(reset)s %(white)s%(message)s',
                     log_colors={
                         'DEBUG': 'fg_bold_cyan',
                         'INFO': 'fg_bold_green',
                         'WARNING': 'bg_bold_yellow,fg_bold_blue',
                         'ERROR': 'bg_bold_red,fg_bold_white',
                         'CRITICAL': 'bg_bold_red,fg_bold_yellow',
                     }, secondary_log_colors={}
                     )
)
logger.addHandler(handler)

logger.debug('This is a DEBUG message. These information is usually used for troubleshooting')
logger.info('This is an INFO message. These information is usually used for conveying information')
logger.warning('some warning message. These information is usually used for warning')
logger.error('some error message. These information is usually used for errors and should not happen')
logger.critical(
    'some critical message. These information is usually used for critical error and usually results in an exception')

info('\n' + 20 * '-' + '\n' + 'AUTOPILOT DATA ' + '\n' + 20 * '-' + '\n')

info('RELEASE=' + str(RELEASE))
info('PATH_LOG_FILES=' + str(PATH_LOG_FILES))
info('PATH_KEYBINDINGS=' + str(PATH_KEYBINDINGS))
info('KEY_MOD_DELAY=' + str(KEY_MOD_DELAY))
info('KEY_DEFAULT_DELAY=' + str(KEY_DEFAULT_DELAY))
info('KEY_REPEAT_DELAY=' + str(KEY_REPEAT_DELAY))
info('FUNCTION_DEFAULT_DELAY=' + str(FUNCTION_DEFAULT_DELAY))
info('SCREEN_WIDTH=' + str(SCREEN_WIDTH))
info('SCREEN_HEIGHT=' + str(SCREEN_HEIGHT))


def times_stamp_to_local_time(timestamp):
    dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    return dt


""" ############################################# """
""" Acquire and parse Elite Dangerous journal log """
""" ############################################# """


def get_latest_log(path_logs=None):
    """Returns the full path of the latest (most recent) elite log file (journal) from specified path"""
    if not path_logs:
        path_logs = environ['USERPROFILE'] + '\\Saved Games\\Frontier Developments\\Elite Dangerous'
    list_of_logs = [join(path_logs, f) for f in listdir(path_logs) if
                    isfile(join(path_logs, f)) and f.startswith('Journal.')]
    if not list_of_logs:
        return None
    latest_log = max(list_of_logs, key=getmtime)

    return latest_log


# Extract ship info from log
def ship():
    """Returns a 'status' dict containing relevant game status information (state, fuel, ...)"""
    latest_log = get_latest_log(PATH_LOG_FILES)
    global statusCache
    global statusCacheSize

    statussize = getsize(latest_log)
    if statusCacheSize == statussize:
        return statusCache

    ship_status = {
        'time': (datetime.now() - datetime.fromtimestamp(getmtime(latest_log))).seconds,
        'status': None,
        'type': None,
        'location': None,
        'star_class': None,
        'target': None,
        'fuel_capacity': None,
        'fuel_level': None,
        'fuel_percent': None,
        'is_scooping': False,
        'damaged': False,
        'dist_jumped': 0,
        'jumps_remains': 0,
        'speed': 0,
    }
    jumps_lasthr = []
    # Read log line by line and parse data
    with open(latest_log, encoding="utf-8") as f:
        for line in f:
            log = loads(line)

            # parse data
            try:
                # parse ship status
                log_event = log['event']

                if log_event == 'StartJump':
                    ship_status['status'] = str('starting_' + log['JumpType']).lower()

                elif log_event == 'SupercruiseEntry' or log_event == 'FSDJump':
                    ship_status['status'] = 'in_supercruise'

                elif log_event == 'SupercruiseExit' or log_event == 'DockingCancelled' or (
                        log_event == 'Music' and ship_status['status'] == 'in_undocking') or (
                        log_event == 'Location' and log['Docked'] is False):
                    ship_status['status'] = 'in_space'

                elif log_event == 'Undocked':
                    ship_status['status'] = 'in_space'

                elif log_event == 'DockingRequested':
                    ship_status['status'] = 'starting_docking'

                elif log_event == "Music" and log['MusicTrack'] == "DockingComputer":
                    if ship_status['status'] == 'starting_undocking':
                        ship_status['status'] = 'in_undocking'
                    elif ship_status['status'] == 'starting_docking':
                        ship_status['status'] = 'in_docking'

                elif log_event == 'Docked':
                    ship_status['status'] = 'in_station'

                # parse ship type
                if log_event == 'LoadGame' or log_event == 'Loadout':
                    ship_status['type'] = log['Ship']

                # parse fuel
                if 'FuelLevel' in log and ship_status['type'] != 'TestBuggy':
                    ship_status['fuel_level'] = log['FuelLevel']
                if 'FuelCapacity' in log and ship_status['type'] != 'TestBuggy':
                    try:
                        ship_status['fuel_capacity'] = log['FuelCapacity']['Main']
                    except:
                        ship_status['fuel_capacity'] = log['FuelCapacity']
                if log_event == 'FuelScoop' and 'Total' in log:
                    ship_status['fuel_level'] = log['Total']
                if ship_status['fuel_level'] and ship_status['fuel_capacity']:
                    ship_status['fuel_percent'] = round(
                        (ship_status['fuel_level'] / ship_status['fuel_capacity']) * 100)
                else:
                    ship_status['fuel_percent'] = 10

                # parse scoop
                if log_event == 'FuelScoop' and (
                        datetime.utcnow() - times_stamp_to_local_time(log['timestamp'])).seconds < 10 and \
                        ship_status['fuel_percent'] < 100:
                    ship_status['is_scooping'] = True
                else:
                    ship_status['is_scooping'] = False

                # parse location
                if (log_event == 'Location' or log_event == 'StartJump') and 'StarSystem' in log:
                    ship_status['location'] = log['StarSystem']
                if 'StarClass' in log:
                    ship_status['star_class'] = log['StarClass']

                # parse target
                if log_event == 'FSDTarget':
                    if log['Name'] == ship_status['location']:
                        ship_status['target'] = None
                        ship_status['jumps_remains'] = 0
                    else:
                        ship_status['target'] = log['Name']
                        try:
                            ship_status['jumps_remains'] = log['RemainingJumpsInRoute']
                        except:
                            try:
                                ship_status['jumps_remains'] = statusCache['jumps_remains'] - 1
                            except:
                                ship_status['jumps_remains'] = 0
                                warning(
                                    'Log did not have jumps remaining. This happens most if you have less than .' +
                                    '3 jumps remaining. Jumps remaining will be inaccurate for this jump.')

                elif log_event == 'FSDJump':
                    timestamp = times_stamp_to_local_time(log['timestamp'])
                    if timestamp > autopilot_start_time:
                        seconds_ago = (datetime.utcnow() - timestamp).seconds
                        if seconds_ago < 900:  # 15min
                            jumps_lasthr.append(seconds_ago)

                    if ship_status['location'] == ship_status['target']:
                        ship_status['target'] = None
                    ship_status['dist_jumped'] = log["JumpDist"]

                # Damage
                if (log_event == 'HeatDamage' or log_event == 'HullDamage') and (
                        datetime.utcnow() - times_stamp_to_local_time(log['timestamp'])).seconds < 10:
                    # log_event == 'HeatWarning' or
                    ship_status['damaged'] = True

            # exceptions
            except Exception as trace:
                exception("Exception occurred")
                print(trace)
    # warning(jumps_lasthr)
    if len(jumps_lasthr) > 1:
        ship_status['speed'] = len(jumps_lasthr) / (max(jumps_lasthr) / 3600)
    statusCache = ship_status
    statusCacheSize = statussize
    # debug('ship=' + str(ship()))
    return ship_status


""" ############################################# """
""" Keybinding acquisition and binding assignment """
""" ############################################# """


def get_latest_keybinds(path_bindings=None):
    if not path_bindings:
        path_bindings = environ['LOCALAPPDATA'] + "\\Frontier Developments\\Elite Dangerous\\Options\\Bindings"
    list_of_bindings = [join(path_bindings, f) for f in listdir(path_bindings) if
                        (isfile(join(path_bindings, f)) and join(path_bindings, f).endswith("binds"))]
    if not list_of_bindings:
        return None
    latest_bindings = max(list_of_bindings, key=getmtime)
    debug("Current Keybinds: " + str(latest_bindings))
    return latest_bindings


def get_bindings(obtain_keys=None):
    """Returns a dict struct with the direct input equivalent of the necessary elite keybindings"""
    if obtain_keys is None:
        obtain_keys = keys_to_obtain
    direct_input_keys = {}
    convert_to_direct_keys = {
        'Key_LeftShift': 'LShift',
        'Key_RightShift': 'RShift',
        'Key_LeftAlt': 'LAlt',
        'Key_RightAlt': 'RAlt',
        'Key_LeftControl': 'LControl',
        'Key_RightControl': 'RControl',
        'Key_RightBracket': 'RBracket',
        'Key_LeftBracket': 'LBracket'
    }

    latest_bindings = get_latest_keybinds()
    bindings_tree = parse(latest_bindings)
    bindings_root = bindings_tree.getroot()

    for item in bindings_root:
        if item.tag in obtain_keys:
            new_key = None
            mod = None
            # Check primary
            if item[0].attrib['Device'].strip() == "Keyboard":
                new_key = item[0].attrib['Key']
                if len(item[0]) > 0:
                    mod = item[0][0].attrib['Key']
            # Check secondary (and prefer secondary)
            if item[1].attrib['Device'].strip() == "Keyboard":
                new_key = item[1].attrib['Key']
                if len(item[1]) > 0:
                    mod = item[1][0].attrib['Key']
                else:
                    mod = None
            # Adequate key to SCANCODE dict standard
            if new_key in convert_to_direct_keys:
                new_key = convert_to_direct_keys[new_key]
            elif new_key is not None:
                new_key = new_key[4:]
            # Adequate mod to SCANCODE dict standard
            if mod in convert_to_direct_keys:
                mod = convert_to_direct_keys[mod]
            elif mod is not None:
                mod = mod[4:]
            # Prepare final binding
            binding = None
            try:
                if new_key is not None:
                    binding = {'pre_key': 'DIK_' + new_key.upper()}
                    binding['key'] = SCANCODE[binding['pre_key']]
                    if mod is not None:
                        binding['pre_mod'] = 'DIK_' + mod.upper()
                        binding['mod'] = SCANCODE[binding['pre_mod']]
                if binding is not None:
                    direct_input_keys[item.tag] = binding
            except Exception as e:
                error('<' + new_key + '> is most likely an unusable keybind. Please rebind and restart the script.')
                error(e)

    if len(list(direct_input_keys.keys())) < 1:
        return None
    else:
        return direct_input_keys


keys = get_bindings()
for key in keys_to_obtain:
    try:
        info('Binding <' + str(key) + '>: ' + str(keys[key]))
    except Exception:
        warning(
            str("<" + key + "> does not appear to have a valid keybind. This could cause issues with the script." +
                "Please bind the key and restart the script.").upper())

""" ############# """
""" Input Control """
""" ############# """


def send(key_to_send, hold=None, repeat=1, repeat_delay=None, state=None):
    global KEY_MOD_DELAY, KEY_DEFAULT_DELAY, KEY_REPEAT_DELAY

    if key_to_send is None:
        warning('Attempted to send key press, but no key was provided.')
        return

    # debug(
    #     'Sending key:' + str(key_to_send) + ', Hold:' + str(hold) + ', Repeat:' + str(repeat) + ', Repeat Delay:' + str(
    #         repeat_delay) + ', State:' + str(state))
    for i in range(repeat):

        if state is None or state == 1:
            if 'mod' in key_to_send:
                PressKey(key_to_send['mod'])
                sleep(KEY_MOD_DELAY)

            PressKey(key_to_send['key'])

        if state is None:
            if hold:
                sleep(hold)
            else:
                sleep(KEY_DEFAULT_DELAY)

        if state is None or state == 0:
            ReleaseKey(key_to_send['key'])

            if 'mod' in key_to_send:
                sleep(KEY_MOD_DELAY)
                ReleaseKey(key_to_send['mod'])

        if repeat_delay:
            sleep(repeat_delay)
        else:
            sleep(KEY_REPEAT_DELAY)


# Clear input
def clear_input(to_clear=None):
    info('\n' + 20 * '-' + '\n' + ' CLEAR INPUT ' + '\n' + 20 * '-' + '\n')
    send(to_clear['SetSpeedZero'])
    send(to_clear['MouseReset'])
    for key_to_clear in to_clear.keys():
        if key_to_clear in keys:
            send(to_clear[key_to_clear], state=0)
    debug('clear_input')


""" ############################################# """
""" Open Computer Vision Processing """
""" ############################################# """


# Get screen
def get_screen(x_left, y_top, x_right, y_bot):
    # t1 = time()
    # screen = ImageGrab.grab(bbox=(x_left, y_top, x_right, y_bot))
    # t2 = time()
    # screen = array(screen)
    # t3 = time()
    # screen = cvtColor(screen, COLOR_RGB2BGR)
    # # print("get_screen performance: " + str([t2-t1, t3-t2, time()-t3]))
    # return screen
    with mss() as sct:
        img = sct.grab((int(x_left), int(y_top), int(x_right), int(y_bot)))
        return asarray(img)


# Equalization
def equalize(image=None, testing=False):
    while 1:
        if testing:
            img = get_screen((5 / 16) * SCREEN_WIDTH, (5 / 8) * SCREEN_HEIGHT, (2 / 4) * SCREEN_WIDTH,
                             (15 / 16) * SCREEN_HEIGHT)
        else:
            img = image.copy()
        # Load the image in greyscale
        img_gray = cvtColor(img, COLOR_BGR2GRAY)
        # create a CLAHE object (Arguments are optional).
        clahe = createCLAHE(clipLimit=2.0, tileGridSize=(16, 16))
        img_out = clahe.apply(img_gray)
        if testing:
            imshow('Equalized', img_out)
            if waitKey(25) & 0xFF == ord('q'):
                destroyAllWindows()
                break
        else:
            break
    return img_out

# Filter bright
def filter_bright(image=None, testing=False):
    while 1:
        if testing:
            img = get_screen((5 / 16) * SCREEN_WIDTH, (5 / 8) * SCREEN_HEIGHT, (2 / 4) * SCREEN_WIDTH,
                             (15 / 16) * SCREEN_HEIGHT)
        else:
            img = image.copy()
        equalized = equalize(img)
        equalized = cvtColor(equalized, COLOR_GRAY2BGR)
        equalized = cvtColor(equalized, COLOR_BGR2HSV)
        filtered = inRange(equalized, array([0, 0, 215]), array([0, 0, 255]))
        if testing:
            imshow('Filtered', filtered)
            if waitKey(25) & 0xFF == ord('q'):
                destroyAllWindows()
                break
        else:
            break
    return filtered


# Filter sun
def filter_sun(image=None, testing=False):
    while 1:
        if testing:
            hsv = get_screen((1 / 3) * SCREEN_WIDTH, (1 / 4) * SCREEN_HEIGHT, (2 / 3) * SCREEN_WIDTH,
                             (3 / 4) * SCREEN_HEIGHT)
        else:
            hsv = image.copy()
        # converting from BGR to HSV color space
        hsv = cvtColor(hsv, COLOR_BGR2HSV)
        # filter Elite UI orange
        filtered = inRange(hsv, array([0, 100, 240]), array([180, 255, 255]))
        if testing:
            imshow('Filtered', filtered)
            if waitKey(25) & 0xFF == ord('q'):
                destroyAllWindows()
                break
        else:
            break
    return filtered


# Get sun
def sun_percent():
    screen = get_screen((1 / 3) * SCREEN_WIDTH, (1 / 4) * SCREEN_HEIGHT, (2 / 3) * SCREEN_WIDTH,
                        (3 / 4) * SCREEN_HEIGHT)
    filtered = filter_sun(screen)
    white = sum(filtered == 255)
    black = sum(filtered != 255)
    result = white / black
    return result * 100


# Get compass image
def get_compass_image(testing=False):
    t1 = time()
    while 1:
        if SCREEN_WIDTH == 3840:
            compass_template = imread(join(abspath("."), "templates/compass_3840.png"), IMREAD_GRAYSCALE)
        elif SCREEN_WIDTH == 2560 or SCREEN_WIDTH == 3440:
            compass_template = imread(join(abspath("."), "templates/compass_2560.png"), IMREAD_GRAYSCALE)
        else:
            compass_template = imread(join(abspath("."), "templates/compass_1920.png"), IMREAD_GRAYSCALE)
        compass_width, compass_height = compass_template.shape[::-1]
        doubt = 10
        # t2 = time()
        screen = get_screen((5 / 16) * SCREEN_WIDTH, (5 / 8) * SCREEN_HEIGHT, (2 / 4) * SCREEN_WIDTH,
                            (15 / 16) * SCREEN_HEIGHT)
        # t3 = time()
        # filtered = filter_orange(screen)
        equalized = equalize(screen)
        # t4 = time()
        match = matchTemplate(equalized, compass_template, TM_CCOEFF_NORMED)
        # t5 = time()
        threshold = 0.3
        min_val, max_val, min_loc, max_loc = minMaxLoc(match)
        # t6 = time()
        if max_val < threshold:
            continue
        pt = max_loc

        compass_image = screen[pt[1]-doubt: pt[1]+compass_height+doubt, pt[0]-doubt: pt[0]+compass_width+doubt].copy()
        if compass_image.size == 0:
            # Something has gone seriously wrong, we need to try again.
            # debug("get_compass_image] pt=" + str(pt))
            # debug("get_compass_image] doubt=" + str(doubt))
            # debug("get_compass_image] screen-tentative=" + str(
            #     screen[pt[1] - doubt: pt[1] + compass_height + doubt, pt[0] - doubt: pt[0] + compass_width + doubt]))
            # debug("get_compass_image(b)]                      pt[1]=" + str(pt[1]))
            # debug("get_compass_image(b)]                pt[1]-doubt=" + str(pt[1] - doubt))
            # debug("get_compass_image(b)]             compass_height=" + str(compass_height))
            # debug("get_compass_image(b)] pt[1]+compass_height+doubt=" + str(pt[1] + compass_height + doubt))
            # debug("get_compass_image(b)]                      pt[0]=" + str(pt[0]))
            # debug("get_compass_image(b)]                pt[0]-doubt=" + str(pt[0] - doubt))
            # debug("get_compass_image(b)]              compass_width=" + str(compass_width))
            # debug("get_compass_image(b)]  pt[0]+compass_width+doubt=" + str(pt[0] + compass_height + doubt))
            continue
        break

    if testing:
        rectangle(screen, (pt[0] - doubt, pt[1] - doubt),
                  (pt[0] + (compass_width + doubt), pt[1] + (compass_height + doubt)), (0, 0, 255), 2)
        loc = where(match >= threshold)
        pts = tuple(zip(*loc[::-1]))
        match = cvtColor(match, COLOR_GRAY2BGR)
        for p in pts:
            circle(match, p, 1, (0, 0, 255), 1)
        circle(match, pt, 5, (0, 255, 0), 3)
        imshow('Compass Found', screen)
        imshow('Compass Mask', equalized)
        imshow('Compass Match', match)
        if compass_image.shape[0] > 0 and compass_image.shape[1] > 0:
            imshow('Compass', compass_image)
        waitKey(1)
    # debug("Get compass execution time is: %.2f millseconds" % ((time() - t1) * 1000))
    # print([t2-t1, t3-t2, t4-t3, t5-t4, t6-t5])
    result = {'x': compass_width, 'y': compass_height}
    # debug('Compass Location: ' + str(result) + " (confidence %.2f)" % max_val + " (Acquisition time: %.2f ms)" % ((time() - t1) * 1000))
    return compass_image, compass_width + (2 * doubt), compass_height + (2 * doubt)


# Get navpoint offset
same_last_count = 0
last_last = {'x': 1, 'y': 100}


def get_navpoint_offset(testing=False, last=None):
    t1 = time()
    global same_last_count, last_last
    if SCREEN_WIDTH == 3840:
        navpoint_template = imread(join(abspath("."), "templates/navpoint_3840.png"), IMREAD_GRAYSCALE)
    elif SCREEN_WIDTH == 2560 or SCREEN_WIDTH == 3440:
        navpoint_template = imread(join(abspath("."), "templates/navpoint_2560.png"), IMREAD_GRAYSCALE)
    else:
        navpoint_template = imread(join(abspath("."), "templates/navpoint_1920.png"), IMREAD_GRAYSCALE)
    navpoint_width, navpoint_height = navpoint_template.shape[::-1]
    compass_image, compass_width, compass_height = get_compass_image()
    # filtered = filter_blue(compass_image)
    filtered = filter_bright(compass_image)
    match = matchTemplate(filtered, navpoint_template, TM_CCOEFF_NORMED)
    threshold = 0.3
    min_val, max_val, min_loc, max_loc = minMaxLoc(match)
    pt = (0, 0)
    if max_val >= threshold:
        pt = max_loc
    # else:
        # debug("Navpoint ignored, confidence %.2f" % max_val)
    final_x = (pt[0] + ((1 / 2) * navpoint_width)) - ((1 / 2) * compass_width)
    final_y = ((1 / 2) * compass_height) - (pt[1] + ((1 / 2) * navpoint_height))
    if testing:
        rectangle(compass_image, pt, (pt[0] + navpoint_width, pt[1] + navpoint_height), (0, 0, 255), 2)
        imshow('Navpoint Found', compass_image)
        imshow('Navpoint Mask', filtered)
        waitKey(1)
    if pt == (0, 0):
        if last:
            if last == last_last:
                same_last_count = same_last_count + 1
            else:
                last_last = last
                same_last_count = 0
            if same_last_count > 5:
                same_last_count = 0
                if random() < .9:
                    result = {'x': 1, 'y': 100}
                else:
                    result = {'x': 100, 'y': 1}
            else:
                result = last
        else:
            result = None
    else:
        result = {'x': final_x, 'y': final_y}
    debug('Nav Compass Point Offset: ' + str(result) + " (confidence %.2f)" % max_val + " (Acquisition time: %.2f ms)" % ((time() - t1) * 1000))
    return result

image_id = 0
def get_destination_offset(testing=True, last=None):
    t1 = time()
    global same_last_count, last_last, image_id
    if SCREEN_WIDTH == 3840:
        destination_template = imread(join(abspath("."), "templates/destination_3840.png"), IMREAD_GRAYSCALE)
    elif SCREEN_WIDTH == 2560 or SCREEN_WIDTH == 3440:
        destination_template = imread(join(abspath("."), "templates/destination_2560.png"), IMREAD_GRAYSCALE)
    else:
        destination_template = imread(join(abspath("."), "templates/destination_1920.png"), IMREAD_GRAYSCALE)
    destination_width, destination_height = destination_template.shape[::-1]
    screen = get_screen((1 / 4) * SCREEN_WIDTH, (1 / 4) * SCREEN_HEIGHT, (3 / 4) * SCREEN_WIDTH,
                        (3 / 4) * SCREEN_HEIGHT)
    # mask_orange = filter_cyan(screen) #Custom color 203Null
    equalized = equalize(screen)
    # filtered = filter_bright(screen)
    match = matchTemplate(equalized, destination_template, TM_CCOEFF_NORMED)
    threshold = 0.3
    min_val, max_val, min_loc, max_loc = minMaxLoc(match)
    pt = (0, 0)
    if max_val >= threshold:
        pt = max_loc

    width = (1 / 2) * SCREEN_WIDTH
    height = (1 / 2) * SCREEN_HEIGHT

    final_x = pt[0] + ((1 / 2) * destination_width) - (1 / 2) * width
    final_y = pt[1] + ((1 / 2) * destination_height) - (1 / 2) * height
    if testing:
        br = (max_loc[0] + destination_width, max_loc[1] + destination_height)
        rectangle(screen, pt, br, (0, 0, 255), 2)
        # imwrite("destination_%i (%.2f).jpg" % (image_id, max_val ), screen, )
        # image_id += 1
        imshow('Destination Found', screen)
        imshow('Destination Mask', equalized)
        waitKey(1)
    if pt == (0, 0):
        if last:
            if last == last_last:
                same_last_count = same_last_count + 1
            else:
                last_last = last
                same_last_count = 0
            if same_last_count > 5:
                same_last_count = 0
                if random() < .9:
                    result = {'x': 1, 'y': 100}
                else:
                    result = {'x': 100, 'y': 1}
            else:
                result = last
        else:
            result = None
    else:
        result = {'x': final_x, 'y': final_y}
    t2 = time()
    t = t2 - t1
    debug('Destination Offset: ' + str(result) + " (confidence %.2f)" % max_val + " (Acquisition time: %.2f ms)" % ((time() - t1) * 1000))
    debug(pt)
    return result


# Angle Offset from Center
def x_angle(point=None):
    if not point or point['x'] == 0:
        return None
    result = degrees(atan(point['y'] / point['x']))
    if point['x'] > 0:
        return +90 - result
    else:
        return -90 - result


""" ############################## """
""" Auto ship navigation functions """
""" ############################## """


# Undock
def undock():
    info('\n' + 20 * '-' + '\n' + 'Waiting for undock' + '\n' + 20 * '-' + '\n')
    if ship()['status'] != "in_station":
        error('Undock function called while not in a station')
        raise Exception('Undock function called while not in a station')
    send(keys['UI_Back'], repeat=10)
    send(keys['HeadLookReset'])
    send(keys['UI_Down'], hold=3)
    send(keys['UI_Select'])
    sleep(1)
    if not (ship()['status'] == "starting_undock" or ship()['status'] == "in_undock"):
        error('Attempted to undock, but failed to execute properly.')
        raise Exception("Attempted to undock, but failed to execute properly.")
    send(keys['HeadLookReset'])
    send(keys['SetSpeedZero'], repeat=2)
    wait = 120
    for i in range(wait):
        sleep(1)
        if i > wait - 1:
            error('Undocking took longer than 2 minutes, possible error with undocking.')
            raise Exception('Undocking took longer than 2 minutes, possible error with undocking.')
        if ship()['status'] == "in_space":
            break
    info('\n' + 20 * '-' + '\n' + 'Undocked successfully.' + '\n' + 20 * '-' + '\n')
    return True


# Dock
def dock():
    info('\n' + 20 * '-' + '\n' + 'Waiting to dock.' + '\n' + 20 * '-' + '\n')
    if ship()['status'] != "in_space":
        error('Attempting to dock while not in space. This is unadvised!')
        raise Exception('Attempting to dock while not in space. This is unadvised!')
    tries = 3
    for i in range(tries):
        send(keys['UI_Back'], repeat=10)
        send(keys['HeadLookReset'])
        send(keys['UIFocus'], state=1)
        send(keys['UI_Left'])
        send(keys['UIFocus'], state=0)
        send(keys['CycleNextPanel'], repeat=2)
        send(keys['UI_Up'], hold=3)
        send(keys['UI_Right'])
        send(keys['UI_Select'])
        sleep(1)
        if ship()['status'] == "starting_dock" or ship()['status'] == "in_dock":
            break
        if i > tries - 1:
            error('Docking sequence was unable to be started.')
            raise Exception("Docking sequence was unable to be started.")
    send(keys['UI_Back'])
    send(keys['HeadLookReset'])
    send(keys['SetSpeedZero'], repeat=2)
    wait = 120
    for i in range(wait):
        sleep(1)
        if i > wait - 1:
            error('Docking took longer than 2 minutes. Possible error with docking.')
            raise Exception('Docking took longer than 2 minutes. Possible error with docking.')
        if ship()['status'] == "in_station":
            break
    send(keys['UI_Up'], hold=3)
    send(keys['UI_Down'])
    send(keys['UI_Select'])
    debug('\n' + 20 * '-' + '\n' + 'Docking complete!' + '\n' + 20 * '-' + '\n')
    return True


def align(override_prepjump = False):
    info('ALIGN: Starting Align Sequence')
    if not (ship()['status'] == 'in_supercruise' or ship()['status'] == 'in_space' or
            ship()['status'] == 'starting_supercruise'):
        error('Ship align failed.')
        send_discord_webhook("❌ Ship align failed.", True)
        raise Exception('align failed.')

    info('ALIGN: Executing star avoidance maneuver')
    while sun_percent() > 3:
        send(keys['PitchUpButton'], state=1)
    send(keys['PitchUpButton'], state=0)

    info('ALIGN: Setting speed to 100%')
    send(keys['SetSpeed100'])

    # left = False
    # right = False
    # up = False
    # down = False
    if config['PrepJump'] and override_prepjump == False :
        global prep_engaged
        prep_engaged = datetime.now()
        send(keys['HyperSuperCombination'], hold=0.2)  # prep

    crude_align()

    if ship()['status'] == 'starting_hyperspace':
        return

    fine_align()

# Crude Align
def crude_align():
    close = 3
    close_a = 10

    off = get_navpoint_offset()
    while off is None:  # Until NavPoint Found
        send(keys['PitchUpButton'], state=1)
        off = get_navpoint_offset(last=off)
    send(keys['PitchUpButton'], state=0)

    ang = x_angle(off)

    info('ALIGN: Executing crude jump alignment.')
    while ((off['x'] > close and ang > close_a) or (off['x'] < -close and ang < -close_a) or
           (off['y'] > close) or (off['y'] < -close)):
        ReleaseKey(keys['RollRightButton']['key'])
        ReleaseKey(keys['RollLeftButton']['key'])
        ReleaseKey(keys['PitchUpButton']['key'])
        ReleaseKey(keys['PitchDownButton']['key'])

        while (off['x'] > close and ang > close_a) or (off['x'] < -close and ang < -close_a):
            debug("Roll aligning")
            if off['x'] > close and ang > close_a:
                PressKey(keys['RollRightButton']['key'])
            else:
                ReleaseKey(keys['RollRightButton']['key'])

            if off['x'] < -close and ang < -close_a:
                PressKey(keys['RollLeftButton']['key'])
            else:
                ReleaseKey(keys['RollLeftButton']['key'])

            if ship()['status'] == 'starting_hyperspace':
                ReleaseKey(keys['RollRightButton']['key'])
                ReleaseKey(keys['RollLeftButton']['key'])
                return

            off = get_navpoint_offset(last=off)
            ang = x_angle(off)

        ReleaseKey(keys['RollRightButton']['key'])
        ReleaseKey(keys['RollLeftButton']['key'])
        ReleaseKey(keys['PitchUpButton']['key'])
        ReleaseKey(keys['PitchDownButton']['key'])

        while (off['y'] > close) or (off['y'] < -close):
            debug("Pitch aligning")

            if off['y'] > close:
                PressKey(keys['PitchUpButton']['key'])
            else:
                ReleaseKey(keys['PitchUpButton']['key'])

            if off['y'] < -close:
                PressKey(keys['PitchDownButton']['key'])
            else:
                ReleaseKey(keys['PitchDownButton']['key'])

            if ship()['status'] == 'starting_hyperspace':
                ReleaseKey(keys['PitchUpButton']['key'])
                ReleaseKey(keys['PitchDownButton']['key'])
                return

            off = get_navpoint_offset(last=off)
            ang = x_angle(off)

    ReleaseKey(keys['RollRightButton']['key'])
    ReleaseKey(keys['RollLeftButton']['key'])
    ReleaseKey(keys['PitchUpButton']['key'])
    ReleaseKey(keys['PitchDownButton']['key'])

    return


# Fine Align
def fine_align():
    new = None
    info('ALIGN: Executing fine jump alignment')
    sleep(0.5)
    close = 40
    hold_pitch = 0.200
    hold_yaw = 0.400
    off = get_destination_offset()
    for i in range(3):
        new = get_destination_offset()
        if new:
            off = new
            break
        else:
            crude_align()
    if new is None:
        return False

    while (off['x'] > close) or (off['x'] < -close) or (off['y'] > close) or (off['y'] < -close):
        if off['x'] > close:
            PressKey(keys['YawRightButton']['key'])
        elif off['x'] < -close:
            PressKey(keys['YawLeftButton']['key'])
        else:
            ReleaseKey(keys['YawRightButton']['key'])
            ReleaseKey(keys['YawLeftButton']['key'])

        if off['y'] > close:
            PressKey(keys['PitchUpButton']['key'])
        elif off['y'] < -close:
            PressKey(keys['PitchDownButton']['key'])
        else:
            ReleaseKey(keys['PitchDownButton']['key'])
            ReleaseKey(keys['PitchUpButton']['key'])


        if ship()['status'] == 'starting_hyperspace':
            return True

        for i in range(3):
            new = get_destination_offset()
            if new:
                off = new
                break
            else:
                ReleaseKey(keys['YawRightButton']['key'])
                ReleaseKey(keys['YawLeftButton']['key'])
                ReleaseKey(keys['PitchDownButton']['key'])
                ReleaseKey(keys['PitchUpButton']['key'])
                crude_align()
        if new is None:
            return False

        if (off['x'] <= close) and (off['x'] >= -close) and (off['y'] <= close) and (off['y'] >= -close):
            debug('ALIGN: Jump alignment complete')
            ReleaseKey(keys['YawRightButton']['key'])
            ReleaseKey(keys['YawLeftButton']['key'])
            ReleaseKey(keys['PitchDownButton']['key'])
            ReleaseKey(keys['PitchUpButton']['key'])
            return True


# Jump
def jump():
    info('JUMP: Executing Hyperspace Jump')
    # global prep_engaged

    if (datetime.now() - prep_engaged).seconds < 20:
        info("JUMP: Preped jump detected. %d seconds remaining" % (datetime.now() - prep_engaged).seconds)

    while (datetime.now() - prep_engaged).seconds < 20 and ship()['status'] != 'starting_hyperspace':
        sleep(1)

    # sleep(8)

    if ship()['status'] == 'starting_hyperspace':
        info('JUMP: Hyperspace Jump in Progress')
        while ship()['status'] != 'in_supercruise':
            sleep(1)
        debug('jump=speed 0')
        send(keys['SetSpeedZero'])
        info('JUMP: Jump Complete')
        return True

    # send(keys['HyperSuperCombination'], hold=1) #Cancel the prepjump
    for i in range(config['JumpTries']):
        info('JUMP: Hyperspace Jump attempt #' + str(i + 1))
        if not (ship()['status'] == 'in_supercruise' or ship()['status'] == 'in_space' or
                ship()['status'] == 'starting_supercruise'):
            error('FSD Jump Failed')
            send_discord_webhook("❌ FSD Jump Failed", True)
            raise Exception('FSD Jump Failed')
        # sleep(0.5)
        debug('jump=start fsd')
        send(keys['HyperSuperCombination'], hold=1)
        sleep(20)
        if ship()['status'] != 'starting_hyperspace':
            debug('jump=misaligned stop fsd')
            send(keys['HyperSuperCombination'], hold=1)
            sleep(2)
            align()
        else:
            debug('jump=in jump')
            while ship()['status'] != 'in_supercruise':
                sleep(1)
            debug('jump=speed 0')
            send(keys['SetSpeedZero'])
            debug('jump=complete')
            return True
    error('jump=err2')
    send_discord_webhook("❌ FSD Jump Failed", True)
    raise Exception("jump failure")


# Refuel
def refuel(refuel_threshold=config['RefuelThreshold']):
    info('Executing fuel scooping maneuvers')
    scoopable_stars = ['F', 'O', 'G', 'K', 'B', 'A', 'M']
    if ship()['status'] != 'in_supercruise':
        error('refuel=err1')
        return False
    elif ship()['fuel_percent'] < refuel_threshold and ship()['star_class'] in scoopable_stars:
        debug('refuel=start refuel')
        debug('Star Class: ' + ship()['star_class'])
        send(keys['SetSpeed100'])
        send_discord_webhook("⛽⌛ Fuel Scooping")
        debug('refuel=wait for refuel')
        sleep(4)
        send(keys['SetSpeedZero'], repeat=3)
        refuel_time = time()
        while ship()['is_scooping'] is False or time() - refuel_time < 10: #Wait for journal to report on scooping
            continue
        while ship()['is_scooping'] is False:
            send(keys['SetSpeed100'])
            sleep(1)
            send(keys['SetSpeedZero'], repeat=3)
            sleep(10)
        debug('refuel=scooping detected')

        while not ship()['fuel_percent'] == 100:
            sleep(1)
        send_discord_webhook("⛽✔️ Fuel Scoop Complete")
        debug('refuel=complete')
        return True
    elif ship()['fuel_percent'] >= refuel_threshold:
        debug('refuel=not needed')
        return False
    elif ship()['star_class'] not in scoopable_stars:
        debug('refuel=needed, unsuitable star')
        return False
    else:
        return False


# Position
def position(refueled_multiplier=1):
    # info('POSIT: Waiting to enter system')
    # while sun_percent() < 10:
    #     print(sun_percent())
    #     # continue
    # sleep(2)
    info('POSIT: Starting system entry positioning maneuver')
    if config['DiscoveryScan'] == "Primary":
        info('POSIT: Scanning system.')
        send(keys['PrimaryFire'], state=1)
    elif config['DiscoveryScan'] == "Secondary":
        info('POSIT: Scanning system.')
        send(keys['SecondaryFire'], state=1)

    if refueled_multiplier <= 1:
        send(keys['SetSpeed75'])
    send(keys['PitchUpButton'], state=1)
    sleep(4)
    # send(keys['PitchUpButton'], state=0)
    send(keys['SetSpeed100'])
    # send(keys['PitchUpButton'], state=1)
    # while sun_percent() > 3:
    #     sleep(1)
    sleep(4)
    send(keys['PitchUpButton'], state=0)
    sleep(5*refueled_multiplier)
    info('POSIT: System entry positioning complete')

    if config['DiscoveryScan'] == "Primary":
        debug('position=scanning1')
        send(keys['PrimaryFire'], state=0)
    elif config['DiscoveryScan'] == "Secondary":
        debug('position=scanning2')
        send(keys['SecondaryFire'], state=0)
    return True


# Autopilot main

# status reference
#
# 'in-station'
# 
# 'in-supercruise'
# 
# 'in-space'
# 
# 'starting-undocking'
# 
# 'in-undocking'
# 
# 'starting-docking'
# 
# 'in-docking'


""" ###################### """
""" SAFE NET FUNCTIONALITY """
""" ###################### """


def safe_net(callback):
    try:
        if config['SafeNet']:
            info('SAFENET: Ship Damage Safenet Activated!')
            last_ship_status = ship()['status']
            while 1:
                # error('Ship Damage Safenet Running!')
                # error(ship()['status'])
                if ship()['damaged']:
                    critical("Ship Damage Detected, Exiting Game.")
                    send_discord_webhook("🔥🔥🔥 Damage Detected, Exiting Game 🔥🔥🔥", True)
                    kill_ed()
                    callback()
                    return
                if ship()['status'] == "in_space" and last_ship_status == "in_supercruise":
                    critical("Ship dropped from supercurise")
                    send_discord_webhook("❌ Ship dropped from supercurise. Action required", True)
                    callback()
                last_ship_status = ship()['status']
                sleep(1)
    finally:
        if config['SafeNet']:
            info('SAFENET: Ship Damage Safenet Deactivated!')


def kill_ed():
    critical("Trying to terminate Elite Dangerous!!")
    send_discord_webhook("🛑 Trying to terminate Elite Dangerous!! 🛑", True)
    for i in range(10):
        system("TASKKILL /F /IM EliteDangerous64.exe")


jump_count = 0
total_dist_jumped = 0

""" ############################## """
""" Main Function """
""" ############################## """


def autopilot(callback):
    # while True:
    #     # fine_align()
    #     get_destination_offset()
    autopilot_completed = False

    try:
        global jump_count, total_dist_jumped, autopilot_start_time

        jump_count, total_dist_jumped = 0, 0
        autopilot_start_time = datetime.utcnow()

        send_discord_webhook("▶️ Autopilot Engaged!")

        while ship()['target']:
            if ship()['status'] == 'in_space' or ship()['status'] == 'in_supercruise':
                t1 = time()

                info('\n' + 20 * '-' + '\n' + 'AUTOPILOT ALIGN' + '\n' + 20 * '-' + '\n')

                align()
                info('\n' + 20 * '-' + '\n' + 'AUTOPILOT JUMP' + '\n' + 20 * '-' + '\n')

                jump()

                ship_status = ship()
                total_dist_jumped += ship_status['dist_jumped']
                jump_count += 1
                if ship_status['target']:
                    send_discord_webhook(
                        "🚦 Jump #%d completed, arriving at %s. Average speed of %.2f jumps/hr. " % (
                            jump_count,
                            ship_status['location'],
                            ship_status['speed']
                        ) +
                        "%.2f LYs covered and %d jumps left to go." % (
                            total_dist_jumped,
                            ship_status['jumps_remains']
                        )
                    )
                else:
                    time_token = (datetime.utcnow() - autopilot_start_time).seconds
                    hours = time_token // 3600
                    minutes = time_token % 3600 // 60
                    seconds = time_token % 60
                    send_discord_webhook(
                        "🏁 Jump #%d completed, arriving at %s. %2f LYs covered over %d hours" % (
                            jump_count,
                            ship_status['location'],
                            total_dist_jumped,
                            hours
                        ) +
                        " %d minutes and %d seconds ( %.2f jumps per hour)" % (
                            minutes,
                            seconds,
                            jump_count / (time_token / 3600)
                        )
                    )

                info('\n' + 20 * '-' + '\n' + 'AUTOPILOT REFUEL' + '\n' + 20 * '-' + '\n')

                refueled = refuel()

                info('\n' + 20 * '-' + '\n' + 'AUTOPILOT POSIT' + '\n' + 20 * '-' + '\n')
                if refueled:
                    position(refueled_multiplier=3)
                else:
                    position(refueled_multiplier=1)

                t2 = time()
                t = t2 - t1
                print("Complete Nav Cycle execution time: ", t, " seconds")
        send(keys['SetSpeedZero'])
        info('\n' + 20 * '-' + '\n' + 'AUTOPILOT END' + '\n' + 20 * '-' + '\n')
        clear_input(get_bindings())
        critical("Disable Autopilot now or it will exit in 120 seconds")
        send_discord_webhook("⏹️ Autopilot Disengaged! Disable Autopilot now or it will exit in 120 seconds")
        for i in range(1, 120):
            sleep(1)
        kill_ed()
        autopilot_completed = True
        autopilot_start_time = datetime.max
        callback()
    finally:
        if autopilot_completed is False:
            info('\n' + 20 * '-' + '\n' + 'AUTOPILOT DISENGAGED' + '\n' + 20 * '-' + '\n')
            send_discord_webhook("⏹️ Autopilot Disengaged!")


def send_discord_webhook(content, at_owner=False):
    if config['DiscordWebhook']:
        if at_owner:
            content = "<@%s> %s" % (config["DiscordUserID"], content)
        webhook = DiscordWebhook(url=config["DiscordWebhookURL"], content=content)
        webhook.execute()
