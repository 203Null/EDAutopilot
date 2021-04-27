import threading

import keyboard
import kthread
from PIL import Image
from pystray import Icon, MenuItem, Menu

from dev_autopilot import autopilot, resource_path, get_bindings, clear_input, set_scanner, safeNet, killED

STATE = 1

def setup(icon):
    icon.visible = True


def exit_action():
    stop_action()
    icon.visible = False
    icon.stop()

threads = []
def start_action():
    stop_action()
    
    t1 = kthread.KThread(target=autopilot, name="EDAutopilot")
    t1.start()
    threads.append(t1)
    t2 = kthread.KThread(target=checkDamage, name="EDAutopilot_SafeNet")
    t2.start()
    threads.append(t2)


def stop_action():
    global threads
    for thread in threads:
        # print(thread.getName())
        # print(("Dead", "Alive")[thread.is_alive()])
        while(thread.is_alive()):
            thread.terminate()
            # print(("Dead", "Alive")[thread.is_alive()])
        # print("-----------------------")
    clear_input(get_bindings())
    threads = []


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
    logo = Image.open(resource_path('src/logo.png'))
    icon.icon = logo

    # icon.menu = Menu(
    #     MenuItem(
    #         'Scan Off',
    #         set_state(0),
    #         checked=get_state(0),
    #         radio=True
    #     ),
    #     MenuItem(
    #         'Scan on Primary Fire',
    #         set_state(1),
    #         checked=get_state(1), 
    #         radio=True
    #     ),
    #     MenuItem(
    #         'Scan on Secondary Fire',
    #         set_state(2),
    #         checked=get_state(2),
    #         radio=True
    #     ),
    #     MenuItem('Exit', lambda: exit_action())
    # )

    keyboard.add_hotkey('page up', start_action)
    keyboard.add_hotkey('page down', stop_action)
    keyboard.add_hotkey('end', killED)

    icon.run(setup)


if __name__ == '__main__':
    tray()
