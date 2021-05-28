# Elite Dangerous: AutoPilot v2
Elite Dangerous computer vision based autopilot version 2

Program uses openCV and other tools in python to navigate automatically in Elite Dangerous.

## Usage:
  0. Config your setting by editing the config.json
  
  1. Setup a route in the galaxy map as you would normally, then:

  2. Press **Page Up** key to start autopilot.

  3. Press **Page Down** key to abort autopilot.  

## Necessary Setup:
In game, you must have configured keyboard keys for all of the following. You may configure them in either
the left or the right slot, and this program will automatically fetch your most recent changes.
  * In 'Flight Rotation':
    * Yaw Left
    * Yaw Right
    * Roll Left
    * Roll Right
    * Pitch Up
    * Pitch Down
  * In 'Flight Throttle':
    * Set Speed To 0%
    * Set Speed To 75%
    * Set Speed To 100%
  * In 'Flight Miscellaneous'
    * Toggle Frameshift Drive
  * In 'Mode Switches':
    * UI Focus
  * In 'Interface Mode':
    * UI Panel Up
    * UI Panel Down
    * UI Panel Left
    * UI Panel Right
    * UI Panel Select
    * UI Back
    * Next Panel Tab
  * In 'Headlook Mode':
    * Reset Headlook

## Optimal Game Settings:
1. Game resolution:      1080p Borderless (1080p, 1440p, 2160p All works fine)
2. Ship UI color:        Orange (default colour) (Custom color should works fine)
3. Ship UI brightness:   60% ~ 100%
4. FOV: Lowest position in the slider

## General Guidelines

I recommend setting your route finder to use only scoopable stars. For full functionality, "Advanced Autodocking" module must be outfitted on ship. Definitely do not leave this running unsupervised unless you don't mind paying rebuy.

##
Or if you'd like to set it up and run the script directly...

## Setup:
_Requires **python 3** and **git**_
1. Clone this repository
```sh
> git clone https://github.com/203Null/EDAutopilot.git
```
or just download the entire repo as a zip

2. Install requirements
```sh
> cd EDAutoPilot
> pip install -r requirements.txt
```
3. Run script

#### Windows
Run the run.bat if you only have python3 installed. 
If youu have both python 2 and python 3 then change the python in the bat to python3

#### Other System
```sh
> python autopilot.py
OR you may have to run
> python3 autopilot.py
if you have both python 2 and 3 installed.
```

If you encounter any issues during pip install, try running:
> python -m pip install -r requirements.txt
instead of > pip install -r requirements.txt

## WARNING:

ALPHA VERSION IN DEVELOPMENT. 

Absolutely DO NOT LEAVE UNSUPERVISED. 

Use at YOUR OWN RISK.

## CONTACT:

Discord NuLL#0156
