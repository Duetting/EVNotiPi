#!/usr/bin/env python3

from gevent.monkey import patch_all; patch_all()
from gpspoller import GpsPoller
from subprocess import check_call, check_output
from time import sleep,time
import os
import sys
import signal
import sdnotify
import logging
from argparse import ArgumentParser
import evnotify

Systemd = sdnotify.SystemdNotifier()

class WatchdogFailure(Exception): pass

parser = ArgumentParser(description='EVNotiPi')
parser.add_argument('-d', '--debug', dest='debug', action='store_true', default=False)
parser.add_argument('-c', '--config', dest='config', action='store', default='config.yaml')
args = parser.parse_args()
del parser

# load config
if os.path.exists(args.config):
    if args.config[-5:] == '.json':
        import json
        with open(args.config, encoding='utf-8') as config_file:
            config = json.loads(config_file.read())
    elif args.config[-5:] == '.yaml':
        import yaml
        with open(args.config, encoding='utf-8') as config_file:
            config = None
            # use the last document in config.yaml as config
            for c in yaml.load_all(config_file, Loader=yaml.SafeLoader):
                config = c
    else:
        raise Exception('Unknown config type')
else:
    raise Exception('No config found')

loglevel=logging.INFO
if args.debug:
    loglevel=logging.DEBUG
elif 'loglevel' in config:
    loglevel=config['loglevel']

# set up logging to file - see previous section for more details
logging.basicConfig(level=loglevel,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='evnotipi.log')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(loglevel)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

log = logging.getLogger("EVNotiPi")

del args

# Load OBD2 interface module
if not "{}.py".format(config['dongle']['type']) in os.listdir('dongles'):
    raise Exception('Unsupported dongle {}'.format(config['dongle']['type']))

# Init ODB2 adapter
sys.path.insert(0, 'dongles')
exec("from {0} import {0} as DONGLE".format(config['dongle']['type']))
sys.path.remove('dongles')

if not "{}.py".format(config['car']['type']) in os.listdir('cars'):
    raise Exception('Unsupported car {}'.format(config['car']['type']))

sys.path.insert(0, 'cars')
exec("from {0} import {0} as CAR".format(config['car']['type']))
sys.path.remove('cars')


Threads = []

if 'watchdog' in config and config['watchdog'].get('enable') == True:
    import watchdog
    Watchdog = watchdog.Watchdog(config['watchdog'])
else:
    Watchdog = None

# Init dongle
dongle = DONGLE(config['dongle'], watchdog = Watchdog)

# Init GPS interface
gps = GpsPoller()
Threads.append(gps)

# Init car
car = CAR(config['car'], dongle, gps)
Threads.append(car)

# Init EVNotify
EVNotify = evnotify.EVNotify(config['evnotify'], car)
Threads.append(EVNotify)

# Init WiFi control
if 'wifi' in config and config['wifi'].get('enable') == True:
    from wifi_ctrl import WiFiCtrl
    wifi = WiFiCtrl()
else:
    wifi = None

# Init some variables
main_running = True

# Set up signal handling
def exit_gracefully(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, exit_gracefully)

# Start polling loops
for t in Threads:
    t.start()

Systemd.notify("READY=1")
log.info("Starting main loop")
try:
    while main_running:
        now = time()
        watchdogs_ok = True
        for t in Threads:
            status = t.checkWatchdog()
            if status == False:
                log.error("Watchdog Failed " + str(t))
                watchdogs_ok = False
                raise WatchdogFailure(str(t))

        if watchdogs_ok:
            Systemd.notify("WATCHDOG=1")

        if 'system' in config and 'shutdown_delay' in config['system']:
            if now - car.last_data > config['system']['shutdown_delay'] and dongle.isCarAvailable() == False:
                usercnt = int(check_output(['who','-q']).split(b'\n')[1].split(b'=')[1])
                if usercnt == 0:
                    log.info("Not charging and car off => Shutdown")
                    check_call(['/bin/systemctl','poweroff'])
                    sleep(5)
                else:
                    log.info("Not charging and car off; Not shutting down, users connected")

        if wifi and config['wifi']['shutdown_delay'] != None:
            if now - car.last_data > config['wifi']['shutdown_delay'] and dongle.isCarAvailable() == False:
                wifi.disable()
            else:
                wifi.enable()

        sys.stdout.flush()

        if main_running:
            loop_delay = 1 - (time()-now)
            if loop_delay > 0: sleep(loop_delay)

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False
    Systemd.notify("STOPPING=1")
finally:
    Systemd.notify("STOPPING=1")
    log.info("Exiting ...")
    for t in Threads[::-1]: # reverse Threads
        t.stop()
    log.info("Bye.")

