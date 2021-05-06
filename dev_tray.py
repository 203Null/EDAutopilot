import threading

import keyboard
import kthread
from PIL import Image
from pystray import Icon, MenuItem, Menu
from os.path import join, abspath

from dev_autopilot import autopilot, get_bindings, clear_input, set_scanner, safe_net, kill_ed

STATE = 1


def setup(icon):
    icon.visible = True


def exit_action():
    stop_action()
    icon.visible = False
    icon.stop()


main_thread = None
safeNet_thread = None


def start_action():
    # stop_action()
    
    global main_thread
    main_thread = kthread.KThread(target=autopilot, name="EDAutopilot")
    main_thread.isAlive = main_thread.is_alive  # KThread workaround
    main_thread.start()

    global safeNet_thread
    safeNet_thread = kthread.KThread(target=safe_net, name="EDAutopilot_SafeNet")
    safeNet_thread.isAlive = safeNet_thread.is_alive
    safeNet_thread.start()


def stop_action():
    print("Tring to abort")
    while main_thread and main_thread.is_alive():
        main_thread.kill()
    while safeNet_thread and safeNet_thread.is_alive():
        safeNet_thread.kill()

    clear_input(get_bindings())


def set_state(v):
    def inner(icon, item):
        global STATE
        STATE = v
        set_scanner(STATE)

    return inner


def get_state(v):
    def inner(item):
        return STATE == v

    return inner


def tray():
    global icon, thread
    icon = None
    thread = None

    name = 'ED - Autopilot'
    icon = Icon(name=name, title=name)
    logo = Image.open(join(abspath("."), 'src/logo.png'))
    icon.icon = logo

    icon.menu = Menu(
        MenuItem(
            'Scan Off',
            set_state(0),
            checked=get_state(0),
            radio=True
        ),
        MenuItem(
            'Scan on Primary Fire',
            set_state(1),
            checked=get_state(1), 
            radio=True
        ),
        MenuItem(
            'Scan on Secondary Fire',
            set_state(2),
            checked=get_state(2),
            radio=True
        ),
        MenuItem('Exit', lambda: exit_action())
    )

    keyboard.add_hotkey('page up', start_action)
    keyboard.add_hotkey('page down', stop_action)
    keyboard.add_hotkey('end', kill_ed)

    # keyboard.wait()
    icon.run(setup)


if __name__ == '__main__':
    tray()
