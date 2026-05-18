# EVNotiPi Nerd Edition
Python Version of EVNotify
## Needed Hardware
- Raspberry Pi Zero W with GPIO Header https://buyzero.de/collections/boards-kits/products/raspberry-pi-zero-w-easy-mit-bestucktem-header
- small wires in different colors: https://www.amazon.de/AZDelivery-Jumper-Arduino-Raspberry-Breadboard/dp/B07KYHBVR7?tag=gplay97-21
- Blutooth USB Dongle
- GPS Module plus external GPS Antena
- mobile phone with active hotspot
## Installation
### Raspberry Pi
- sudo apt update
- sudo apt upgrade
- sudo apt install python3 gpsd git watchdog libffi-dev libssl-dev autoconf rsyslog-
- sudo systemctl disable --now serial-getty@ttyAMA0.service
- sudo sed -i -re "\\$agpu_mem=16\nenable_uart=1\" /boot/firmware/config.txt
- sudo sed -i -re '/console=/ s/$/ panic=1/' /boot/firmware/cmdline.txt
- sudo sed -i -re '/max-load/ s/^#//' /etc/watchdog.conf
- sudo sed -i -re "\\$adtparam=watchdog=on" /boot/firmware/config.txt
#### Set up Bluetooth OBDII dongle
- `sudo bluetoothctl`
- [bluetooth]# `power on`
- [bluetooth]# `scan on`
###### Note the MAC address of your dongle
- [bluetooth]# `scan off`
- [bluetooth]# `pair <MAC>`
- [bluetooth]# `quit`
- `sudo rfcomm bind 0 <MAC> `
- `ls /dev/rfcomm0` # /dev/rfcomm0 should appear
#### Set up a GPS receiver
Verify that the GPS receiver is working correctly. If not, see a tutorial here: https://maker.pro/raspberry-pi/tutorial/how-to-use-a-gps-receiver-with-raspberry-pi-4
- `gpsmon`  

I had to make changes to /etc/default/gpsd, or else sometimes the GPS would not work after the device was off for a few hours (>4 hours?).
- `sudo sed -i -re 's/^(DEVICES=).*/\1\"\/dev\/serial0\"/' -e 's/^(GPSD_OPTIONS=).*/\1\"-n\"/' /etc/default/gpsd`
#### Set up wifi network connections
- Call "sudo nmtui" and add all necessary wifi connections
- Optional: set wlan prio: 
  - "sudo nmcli connection modify "Wi-Fi ..." connection.autoconnect-priority 50
  - "sudo nmcli connection modify "Wi-Fi Ioniq ..." connection.autoconnect-priority 50
- Optional: Modify /etc/dhcpcd.conf to specify fixed IP addresses for the networks, at least for the Hotspot one as my cheap and old Android phone doesn't allow that afaik
### EVNotiPi
- sudo chown :pi /opt
- sudo chmod g+w /opt
- sudo git clone https://github.com/Duetting/EVNotiPi /opt/evnotipi
- cd /opt/evnotipi
- python3 -m venv .venv
- source .venv/bin/activate
- mkdir ~/tmp
- export TMPDIR=~/tmp
- pip install uv
- uv sync
- sudo systemctl link /opt/evnotipi/evnotipi.service
- sudo systemctl enable evnotipi.service
- sudo cp config.yaml.template config.yaml
#### Edit config, follow comments in the file
- sudo nano config.yaml # nano or any other editor
- sudo mkdir -p /var/cache/evnotipi
