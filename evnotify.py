import serial
import re
import time
import string
import io
import json
import importlib
import evnotifyapi

# load config
with open('config.json', encoding='utf-8') as config_file:
    config = json.loads(config_file.read())

# load api lib
EVNotify = evnotifyapi.EVNotify(config['akey'], config['token'])

ser = serial.Serial("/dev/rfcomm0", timeout=5)
ser.baudrate=9600

def sendCommand(command):
    ser.flushInput()
    cmd = command + '\r\n'
    print(cmd)
    ser.write(bytes(command + '\r\n'))
    ser.flush()
    if (command == '2105'): return
    return ser.readline()
#set soc to not empty
soc = 0
def parseData(data):
    filtered = [byte.replace('\r', '') for byte in data]
    resolved = ''.join(filtered)
    print(resolved)
    block5 = resolved.find('7EC25')
    print(int(resolved[block5-2:block5], 16) / 2)
    soc = int(resolved[block5-2:block5], 16) / 2

initCMDs = ['ATD', 'ATZ', 'ATE0', 'ATL0', 'ATS0', 'ATH1', 'ATSP0', 'ATSTFF', 'ATFE', 'ATCRA7EC']

for cmd in initCMDs:
    sendCommand(cmd)

sendCommand('2105')
curBytes = []
while True:
    for byte in ser.read():
        curBytes.append(byte)
        if str(byte).find('>') and str(byte).find('7EC25') and curBytes[-2:] == ['\r', '\r']:
            print('Found end')
            print(curBytes)
            parseData(curBytes)
            break
    #exit when soc found, doesn't handle nothing found
    if soc > 0:
        break