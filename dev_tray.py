import keyboard
import threading
from PIL import Image
from pystray import Icon  # , MenuItem, Menu
from os.path import join, abspath
from ctypes import pythonapi, py_object

from dev_autopilot import autopilot, get_bindings, clear_input, kill_ed, safe_net

STATE = 1
ICON = None
main_thread, safeNet_thread = None, None


class ThreadWithException(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        # target function of the thread class
        if self.name == 'EDAutopilot':
            autopilot()
        elif self.name == 'SafeNet':
            safe_net()

    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for t_id, thread in threading._active.items():
            if thread is self:
                return t_id

    def raise_exception(self):
        thread_id = self.get_id()
        res = pythonapi.PyThreadState_SetAsyncExc(thread_id, py_object(SystemExit))
        if res > 1:
            pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Exception raise failure')


def setup(icon):
    icon.visible = True


def exit_action():
    stop_action()
    ICON.visible = False
    ICON.stop()


def start_action():

    global main_thread
    main_thread = ThreadWithException("EDAutopilot")
    main_thread.start()
    main_thread.isAlive = main_thread.is_alive()  # KThread workaround

    global safeNet_thread
    safeNet_thread = ThreadWithException("SafeNet")
    safeNet_thread.start()
    safeNet_thread.isAlive = safeNet_thread.is_alive()


def stop_action():
    global main_thread, safeNet_thread

    if main_thread.isAlive:
        main_thread.raise_exception()
        main_thread.join()

    if safeNet_thread.isAlive:
        safeNet_thread.raise_exception()
        safeNet_thread.join()

    clear_input(get_bindings())


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
