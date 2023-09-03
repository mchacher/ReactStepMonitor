import logging
import time
import signal
import threading
import rsmaster as rs
import reactstepmonitor_config as lc


class ReactStepMonitor:
    MQTT_TOPIC_STATUS = "/Status"

    def exit_gracefully(self, signum, frame):
        """handle system message CTRL+C to properly stop threads and exit"""
        self.stop()
        logging.info("Exit")

    def __init__(self):
        self.exit_now = False
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGINT, self.exit_gracefully)
        config = lc.LoRa2MQTTConfiguration()
        self.worker = threading.Thread(
            target=self.worker_task, name="React Step Monitor worker thread"
        )
        # activate RS Master
        self.rsm = rs.RSMaster()
        self.rsm.connect()

    def worker_task(self):
        while not self.exit_now:
            if not self.rsm.is_connected():
                self.rsm.disconnect()
                self.rsm.connect()
            time.sleep(1)

    def start(self):
        if not (self.worker.is_alive()):
            self.worker.start()

    def stop(self):
        self.rsm.stop_communication()
        self.exit_now = True
        if self.worker.is_alive():
            self.worker.join()
            logging.info("%s is stopped", self.worker.name)


if __name__ == "__main__":
    if lc.LoRa2MQTTConfiguration().logging_level == "info":
        logging_level = logging.INFO
    else:
        logging_level = logging.DEBUG
    # print python lib version
    logging.basicConfig(
        level=logging_level, format="%(asctime)s %(message)s", datefmt="%b %d %H:%M:%S"
    )
    logging.info("----------------------------------------------")
    logging.info(
        "React Step Monitor Python Library: %s", rs.RSMaster.get_python_lib_version()
    )
    logging.info("----------------------------------------------")
    rsmonitor = ReactStepMonitor()
    rsmonitor.start()
