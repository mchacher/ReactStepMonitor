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
import payload_ack as pa

RS_IDENTIFIER = "RP2040"


class SerialMsgType(Enum):
    NULL = 0
    LOG = 1
    COMMAND = 2
    FILE = 3
    EVENT = 4
    ACK = 5

class CommandType(Enum):
  CONNECT = 0
  LIST_WORKOUTS = 1
  LIST_SESSIONS = 2
  DELETE_FILE = 3


class RSMaster:
    """Serial API"""

    PYTHON_LIB_VERSION = "1.0.0"
    QUEUE_SIZE = 10
    
    def __init__(
        self, uart_driver=ud.UartDriver()
    ):
        self.uart_driver: ud.UartDriver = uart_driver
        self.thread_uart = threading.Thread(
            name="uart_thread", target=self.__worker_task
        )
        self.rx_command_queue = queue.Queue(self.QUEUE_SIZE)
        self.tx_fifo = queue.Queue(self.QUEUE_SIZE)
        self.rx_ack_queue = queue.Queue(self.QUEUE_SIZE)
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

    def add_to_rx_sys_queue(self, packet):
        """add packet to rx sys queue"""
        try:
            self.rx_sys_queue.put_nowait(packet)
        except queue.Full:
            self.rx_sys_queue.get_nowait()
            self.rx_sys_queue.put_nowait(packet)
    
    def add_to_rx_ack_queue(self, packet):
        """add packet to rx ack queue"""
        try:
            self.rx_ack_queue.put_nowait(packet)
        except queue.Full:
            self.rx_ack_queue.get_nowait()
            self.rx_ack_queue.put_nowait(packet)


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
                    # Wait for ack
                    try:
                        ack = self.rx_ack_queue.get(timeout=3)
                        if ack[0] == pa.AckType.ERROR.value:
                            error_message = "Error sending file: %s, chunk: %i/%i - file error ack received" % (filename, payload.chunk_id, payload.number_of_chunks)
                            raise Exception(error_message)  # Raise an exception
                        elif ack[0] == pa.AckType.OK.value:
                            logging.info("Ack received")
                        else:
                            error_message = "Error sending file: %s, chunk: %i/%i - no valid ack received" % (filename, payload.chunk_id, payload.number_of_chunks)
                            raise Exception(error_message)  # Raise an exception
                    except queue.Empty:
                        error_message = "Timeout waiting for ack. " + "Error sending file: %s, chunk: %i/%i" % (filename, payload.chunk_id, payload.number_of_chunks)
                        raise Exception(error_message)  # Raise an exception

        except FileNotFoundError:
            logging.info(f"File not found: {file_path}")
            raise Exception(f"File not found: {file_path}") 

    
    def send_list_workout(self):
        self.uart_driver.send_tx_buffer(SerialMsgType.COMMAND.value, bytearray([CommandType.LIST_WORKOUTS.value]))

        received_data = []
        try:
            to = 1
            while True:
                file = self.rx_command_queue.get(timeout=to)
                to = 0.2
                received_data.append(file)
        except queue.Empty:
            if received_data:
                full_response = b'\r\n'.join(received_data)  # Add carriage return between filenames
                decoded_response = full_response[:].decode('ascii')
                return decoded_response.split('\r\n')
            else:
                return []  # Return an empty list if no files are received
    
    def send_connect_request(self):
        self.uart_driver.send_tx_buffer(SerialMsgType.COMMAND.value, bytearray([CommandType.CONNECT.value]))

    def send_delete_file(self, filename):
        # Convert the filename string to bytes using ASCII encoding
        filename_bytes = filename.encode('ascii')
        filename_bytes += b'\0'
        # Create a bytearray with the CommandType and the filename bytes
        command = bytearray([CommandType.DELETE_FILE.value]) + filename_bytes
        self.uart_driver.send_tx_buffer(SerialMsgType.COMMAND.value, command)
        # Wait for ack
        try:
            ack = self.rx_ack_queue.get(timeout=2)
            if ack[0] == pa.AckType.ERROR.value:
                print("Error deleting file: %s" % filename)
            elif ack[0] == pa.AckType.OK.value:
                print("File: %s deleted" % filename)
        except queue.Empty:
           print("Error deleting file: %s" % filename)

    def __serial_rx(self):
        # Rx communication
        rx = self.uart_driver.get_rx_buffer()
        if rx is not None:
            logging.debug("--- Rx: %s", rx)
        if (rx is not None) and (len(rx) > 5):
            if rx[3] == SerialMsgType.LOG.value:
                log = pl.PayloadLog(rx[5:len(rx)-1])
                if self.log:
                    message = log.get_text_message()
                    logging.info("%s: %s", pl.LogLevel(log.level).name.rsplit("_", 1)[-1].ljust(10), message)
            elif rx[3] == SerialMsgType.COMMAND.value:
                logging.debug("System message received: %s", rx.hex("-"))
                self.rx_command_queue.put_nowait(rx[5:-1])
                # put in system queue
            elif rx[3] == SerialMsgType.ACK.value:
                logging.debug("Ack message received: %s", rx[5:].hex("-"))
                # put in system queue
                self.add_to_rx_ack_queue(rx[5:])

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
        # self.thread_uart.daemon = True
        self.run = True
        self.thread_uart.start()

    def stop_communication(self):
        """stop polling"""
        logging.info("Stopping React Sync communication ...")
        self.run = False
        if self.thread_uart.is_alive():
            self.thread_uart.join()
        logging.info("React Sync communication stopped")

    def connect(self):
        """connect"""
        if not self.uart_driver.serial_port.port:
            ports = list_ports.comports()
            for port, desc, hw in ports:
                logging.info("description: %s", desc)
                if desc.find(RS_IDENTIFIER) != -1:
                    self.uart_driver.serial_port.port = port
        if not self.uart_driver.serial_port.port:
            logging.info("React Sync Not identified")
            return False
        self.uart_driver.serial_port.open()
        logging.info(
            "Connected to React Sync: %s",
            self.uart_driver.serial_port.port,
        )

        self.start_communication()
        logging.info("Sending connect request")
        self.send_connect_request()
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
