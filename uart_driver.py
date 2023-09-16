import sys
import serial
import logging
import time

class UartDriver:
    """UART data link layer implementation
    data integrity and correctness is managed with bytestuffing flags"""

    FLAG_START = b"\x12"
    FLAG_STOP = b"\x13"
    FLAG_ESC = b"\x14"

    TX_PACKET_ID = 0

    def __init__(self):
        """constructor"""
        self.serial_port = serial.Serial(port=None)
        self.serial_port.baudrate = 115200
        self.serial_port.bytesize = serial.EIGHTBITS
        self.serial_port.parity = serial.PARITY_NONE
        self.serial_port.stopbits = serial.STOPBITS_ONE

    def send_tx_buffer(self, type, payload):
        """send serial packet over uart with given type and payload
        manage bytestuffing

        Args:
            type (byte): the type of the serial packet
            payload (bytearray): the payload of the packet
        """
        logging.debug("SEND_TX_BUFFER")
        data_length = int.to_bytes(
            len(payload), length=1, byteorder="big", signed=False
        )
        # add message type and packet_id
        p_id = int.to_bytes(
            UartDriver.TX_PACKET_ID, length=2, byteorder="big", signed=False
        )
        type = int.to_bytes(type, length=1, byteorder="big", signed=False)
        UartDriver.TX_PACKET_ID = UartDriver.TX_PACKET_ID + 1
        txbuffer = p_id + type + data_length + payload
        # do byte stuffing
        txbuffer = txbuffer.replace(
            UartDriver.FLAG_ESC, UartDriver.FLAG_ESC + UartDriver.FLAG_ESC
        )
        txbuffer = txbuffer.replace(
            UartDriver.FLAG_START, UartDriver.FLAG_ESC + UartDriver.FLAG_START
        )
        txbuffer = txbuffer.replace(
            UartDriver.FLAG_STOP, UartDriver.FLAG_ESC + UartDriver.FLAG_STOP
        )

        # add FLAG_START and FLAG_STOP
        txbuffer = (
            bytearray(UartDriver.FLAG_START)
            + txbuffer
            + bytearray(UartDriver.FLAG_STOP)
        )
        self.serial_port.write(txbuffer)
        time.sleep(.050) #TODO to be better managed

    def get_rx_buffer(self):
        """processing incoming bytes on the uart - manage bytestuffing

        Returns:
            bytearry: rx packet received over uart
        """
        escaping = False
        if self.serial_port.in_waiting:
            rx = self.serial_port.read()
            if rx == bytearray(self.FLAG_START):
                while True:
                    rx += self.serial_port.read()
                    if escaping:
                        escaping = False
                    elif rx[-1].to_bytes(1, sys.byteorder) == self.FLAG_ESC:
                        escaping = True
                        rx = rx[:-1]
                    elif rx[-1].to_bytes(1, sys.byteorder) == self.FLAG_STOP:
                        logging.debug("rx buffer: %s", rx.hex(":"))
                        return rx
        return None
