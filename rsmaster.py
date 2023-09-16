"""
Module handling serial communication
"""
import threading
import queue
import logging
import time
import serial
import os
from enum import Enum
import sys
import ctypes
import serial.tools.list_ports as list_ports
import uart_driver as ud
import payload_file as pf
import payload_log as pl

RS_IDENTIFIER = "USB"


class SerialMsgType(Enum):
    NULL = 0
    LOG = 1
    SYS = 2
    FILE = 3


class RSMaster:
    """Serial API"""

    PYTHON_LIB_VERSION = "1.0.0"

    def __init__(
        self, uart_driver=ud.UartDriver()
    ):
        self.uart_driver: ud.UartDriver = uart_driver
        self.rx_fifo_sys = queue.Queue()
        self.tx_fifo = queue.Queue()
        self.log = True

    def get_python_lib_version():
        """return lib version"""
        return RSMaster.PYTHON_LIB_VERSION

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

    def send_workout_file(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                binary_data = file.read()
                total_chunks = (len(binary_data) + pf.PayloadFile.FILE_CHUNK_SIZE - 1) // pf.PayloadFile.FILE_CHUNK_SIZE

                for chunk_id in range(total_chunks):
                    start_idx = chunk_id * pf.PayloadFile.FILE_CHUNK_SIZE
                    end_idx = (chunk_id + 1) * pf.PayloadFile.FILE_CHUNK_SIZE
                    chunk_data = binary_data[start_idx:end_idx]

                    payload = pf.PayloadFile()
                    payload.chunk_id = chunk_id
                    payload.number_of_chunks = total_chunks
                    payload.chunk_size = len(chunk_data)
                    filename = os.path.basename(file_path)
                    filename_bytes = filename.encode('ascii')[:pf.PayloadFile.FILE_NAME_SIZE]
                    payload.name[:len(filename_bytes)] = filename_bytes
                    payload.data[:len(chunk_data)] = chunk_data
                    logging.info("Sending file: %s, chunk: %i/%i, chunk_size:%i",
                                 filename, payload.chunk_id + 1, payload.number_of_chunks,
                                 len(chunk_data))
                    self.uart_driver.send_tx_buffer(SerialMsgType.FILE.value, payload.serialize())

        except FileNotFoundError:
            logging.info(f"File not found: {file_path}")

    def __serial_rx(self):
        # Rx communication
        rx = self.uart_driver.get_rx_buffer()
        if rx is not None:
            logging.debug("--- Rx: %s", rx)
        if (rx is not None) and (len(rx) > 5):
            if rx[3] == SerialMsgType.LOG.value:
                log = pl.PayloadLog(rx[5:])
                if self.log:
                    message = log.get_text_message()
                    logging.info("%s: %s", pl.LogLevel(log.level).name.rsplit("_", 1)[-1].ljust(10), message)
            elif rx[3] == SerialMsgType.SYS.value:
                pass
                # logging.debug("System Dongle message: %s", rx.hex("-"))
                # # put in the dongle system queue
                # self.dongle_system.add_to_rx_queue(rx[5:])

    def __worker_task(self):
        while self.run:
            try:
                self.__serial_rx()
                # self.__serial_tx()
            except Exception as exception:
                logging.info("Communication error - closing serial port")
                self.run = False
                self.uart_driver.serial_port.close()
                self.uart_driver.serial_port.port = None

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
        logging.info("Stopping RS Master communication ...")
        self.run = False
        if self.thread_uart.is_alive():
            self.thread_uart.join()
        logging.info("RS Master communication stopped")

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
