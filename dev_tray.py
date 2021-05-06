import keyboard
import kthread
from PIL import Image
from pystray import Icon  # , MenuItem, Menu
from os.path import join, abspath

from dev_autopilot import autopilot, get_bindings, clear_input, kill_ed, safe_net

STATE = 1
ICON = None
main_thread, safeNet_thread = None, None


def setup(icon):
    icon.visible = True


def exit_action():
    set_state(0)
    stop_action()
    ICON.visible = False
    ICON.stop()


def start_action():
    # stop_action()

    set_state(1)

    global main_thread
    main_thread = kthread.KThread(target=autopilot, name="EDAutopilot")
    main_thread.start()
    main_thread.isAlive = main_thread.is_alive()  # KThread workaround

    global safeNet_thread
    safeNet_thread = kthread.KThread(target=safe_net, name="EDAutopilot_SafeNet")
    safeNet_thread.start()
    safeNet_thread.isAlive = safeNet_thread.is_alive()


def stop_action():
    set_state(0)
    clear_input(get_bindings())


def set_state(v):
    global STATE
    STATE = v


def get_state():
    return STATE


def tray():
    global ICON
    name = 'ED - Autopilot'
    ICON = Icon(name=name, title=name)
    logo = Image.open(join(abspath("."), 'src/logo.png'))
    ICON.icon = logo

    keyboard.add_hotkey('page up', start_action)
    keyboard.add_hotkey('page down', stop_action)
    keyboard.add_hotkey('end', kill_ed)

    # keyboard.wait()
    ICON.run(setup)


if __name__ == '__main__':
    tray()
