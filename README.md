# Simple Alarm Clock with GUI

"Written" by Agentseed. | Actually written by ChatGPT (o1 model, 3/2024).

Basically the windows clock app kinda sucks, so I "made" a better solution (kinda).
## Installation

Download the [latest release](https://github.com/agent-seed/alarm-clock/releases/latest)

Run it

## Run as python file

**Clone repo:**
`git clone https://github.com/agent-seed/alarm-clock` or download zip and decompress it

**Enter app directory:**

`cd alarm-clock`

**Install required packages:**

`pip -r requirements.txt`

**Run:**

`python alarm.py`

## Build the app from source

**Clone repo:**
`git clone https://github.com/agent-seed/alarm-clock` or download zip and decompress it

**Enter app directory:**

`cd alarm-clock`

**Install required packages:**

`pip -r requirements.txt`

**Install pyinstaller:**

`pip install pyinstaller`

**Build app:**

`pyinstaller --onefile --noconsole --icon=assets/alarm.ico alarm.py`

The exe should be located at `alarm-clock/dist`
