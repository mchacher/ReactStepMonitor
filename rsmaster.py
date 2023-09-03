"""
Module handling serial communication
"""
import threading
import queue
import logging
import time
import serial
from enum import Enum
import sys
import ctypes
import serial.tools.list_ports as list_ports
import uart_driver as ud
import payload_log as pl


RS_IDENTIFIER = "USB"


class SerialMsgType(Enum):
    NULL = 0
    LOG = 1
    SYS = 2


class RSMaster:
    """Serial API"""

    PYTHON_LIB_VERSION = "1.0.0"

    FIFO_SIZE = 20

    def __init__(
        self, uart_driver=ud.UartDriver()
    ):
        self.uart_driver: ud.UartDriver = uart_driver
        self.rx_fifo_sys = queue.Queue(RSMaster.FIFO_SIZE)

    def get_python_lib_version():
        """return lib version"""
        return RSMaster.PYTHON_LIB_VERSION

    def __manage_communication_error(self):
        self.run = False
        self.uart_driver.serial_port.close()
        self.uart_driver.serial_port.port = None

    # def __serial_tx(self):
    #     #  Tx communication
    #     for node in self.nodes_registry.get_all_nodes():
    #         while not node.tx_queue.empty():
    #             packet: lhp.LoraHomePacket = node.tx_queue.get_nowait()
    #             packet_bytes = packet.serialize()
    #             logging.debug("--- Tx[lora home packet]: %s", packet_bytes)
    #             self.uart_driver.send_tx_buffer(
    #                 SerialMsgType.LORA_HOME.value, packet_bytes
    #             )
    #     try:
    #         packet = self.dongle_system.tx_queue.get_nowait()
    #         logging.debug("--- Tx[dongle system packet]: %s", packet)
    #         self.uart_driver.send_tx_buffer(SerialMsgType.SYS.value, packet)
    #     except queue.Empty:
    #         # logging.info("queue is empty")
    #         pass

    def __serial_rx(self):
        # Rx communication
        rx = self.uart_driver.get_rx_buffer()
        if rx is not None:
            logging.debug("--- Rx: %s", rx)
        if (rx is not None) and (len(rx) > 5):
            if rx[3] == SerialMsgType.LOG.value:
                log = pl.PayloadLog(rx[5:])
                if log.level == pl.LogLevel.LOG_LEVEL_INFO.value:
                    logging.info("info: %s", log.get_text_message())
            elif rx[3] == SerialMsgType.SYS.value:
                pass
                # logging.debug("System Dongle message: %s", rx.hex("-"))
                # # put in the dongle system queue
                # self.dongle_system.add_to_rx_queue(rx[5:])

    def __worker_task(self):
        last_time = time.time()
        while self.run:
            if time.time() - last_time > 5:
                logging.debug("Serial API worker task running")
                last_time = time.time()
            try:
                self.__serial_rx()
                # self.__serial_tx()
            except Exception as exception:
                # TODO improve exception handling
                logging.info("Communication error - closing serial port")
                logging.debug(
                    "An exception of type %s was raised.", type(exception).__name__
                )
                self.__manage_communication_error()

    def start_communication(self):
        """ UART RX / TX communication thread start """
        logging.debug("Start communication")
        self.thread_uart = threading.Thread(
            name="uart_thread", target=self.__worker_task
        )
        # self.thread_uart.daemon = True
        self.run = True
        self.thread_uart.start()

    def stop_communication(self):
        """stop polling"""
        if self.thread_uart.is_alive():
            self.run = False
            self.thread_uart.join()
            logging.info("Communication stopped")

    def connect(self):
        """connect"""
        if not self.uart_driver.serial_port.port:
            ports = list_ports.comports()
            for port, desc, hw in ports:
                logging.debug("description: %s", desc)
                if desc.find(RS_IDENTIFIER) != -1:
                    self.uart_driver.serial_port.port = port
        if not self.uart_driver.serial_port.port:
            logging.info("React Step Master Not identified")
            return False
        self.uart_driver.serial_port.open()
        logging.info(
            "Connected to React Step Master: %s",
            self.uart_driver.serial_port.port,
        )
        self.start_communication()
        return True

    def is_connected(self):
        """
        check wheter it is connected
        returns
            true if connected
            false if not connected
        """
        return self.uart_driver.serial_port.is_open

    def disconnect(self):
        """disconnect the communication"""
        if self.uart_driver.serial_port.is_open:
            self.stop_communication()
            self.uart_driver.serial_port.close()
