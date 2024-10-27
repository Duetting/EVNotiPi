""" Transmit data to EVNotify and handle notifications """
from threading import Thread, Condition
import logging
import paho.mqtt.client as mqtt
import json
import datetime
from gpiozero import CPUTemperature

class MQTTService:
    """ Interface to MQTT. """

    def __init__(self, config, car):
        self._log = logging.getLogger("EVNotiPi/MQTT")
        self._log.info("Initializing MQTT")

        self._car = car
        self._config = config
        self._poll_interval = config['interval']
        self._running = False
        self._thread = None
        self._heartbeat = 1000

        self._data = []
        self._data_lock = Condition()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, self._config.get('clientid'))
        if self._config.get('usetls', True):
            self._client.tls_set()
            self._client.tls_insecure_set(True)
        if self._config.get('uselogger', True):
            self._client.enable_logger(self._log)
        if 'user' in self._config:
            self._client.username_pw_set(self._config.get('user'), self._config.get('password'))
        self._topic = self._config.get('topic')
        self._cpu = CPUTemperature()

    def start(self):
        """ Start submit thread. """
        self._running = True
        self._thread = Thread(target=self.submit_data, name="EVNotiPi/MQTT")
        self._thread.start()
        self._car.register_data(self.data_callback)
        self._client.connect_async(self._config.get('server'), self._config.get('port', 1883), self._config.get('keepalive', 60))
        self._client.loop_start()

    def stop(self):
        """ Stop submit thread. """
        if self._client.is_connected:
            try:
                self._client.disconnect()
                self._client.loop_stop()
                if self._config.get('uselogger', True):
                    self._client.disable_logger()
            except Exception as e:
                self._log.info("MQTT Communication Error: %s", e)
        self._car.unregister_data(self.data_callback)
        self._running = False
        with self._data_lock:
            self._data_lock.notify()
        self._thread.join()

    def data_callback(self, data):
        """ Callback to be called from 'car'. """
        with self._data_lock:
            self._data = data.copy()
            self._data_lock.notify()

    def submit_data(self):
        """ Thread that submits data via MQTT. """
        log = self._log

        while self._running:
            with self._data_lock:
                log.debug('Waiting...')
                self._data_lock.wait(self._poll_interval)

            self._heartbeat += 1
            if self._heartbeat >= 5:
                self._heartbeat = 0
                try:
                    self._client.publish(self._topic + "/heartbeat",
                      json.dumps( { "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "CPU-Temp": self._cpu.temperature }))
                except Exception as e:
                    log.info("MQTT Communication Error: %s", e)

            if len(self._data) == 0:
                continue

            if (self._data['SOC_DISPLAY'] is None):
                continue

            log.debug("Transmit...")
            try:
                self._client.publish(self._topic, json.dumps(self._data), retain=True)
            except Exception as e:
                log.info("MQTT Communication Error: %s", e)

            self._data.clear()

    def check_thread(self):
        """ Return running state of thread. """
        return self._thread.is_alive()
