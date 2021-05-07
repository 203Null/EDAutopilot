import tkinter as tk
import webbrowser
from tkinter import messagebox

import requests

from dev_autopilot import RELEASE
from os.path import join, abspath
from dev_tray import tray


def update():
    releases_url = 'https://api.github.com/repos/skai2/EDAutopilot/releases'
    response = requests.get(releases_url)
    # Raise an exception if the API call fails.
    response.raise_for_status()
    data = response.json()
    try:
        latest_release = data[0]['tag_name']
        if latest_release and latest_release != RELEASE:
            message = "There is a new version of EDAutopilot available!\nWould you like to go to the release download page?"
            root = tk.Tk()
            root.withdraw()
            root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file=join(abspath("."), 'src/logo.png')))
            go_to_update = messagebox.askyesno("ED - Autopilot Update", message)
            if go_to_update:
                webbrowser.open_new(data[0]['html_url'])
                return True
    except Exception as e:
        print(e)
    return False


if __name__ == '__main__':
    if not update():
        tray()
