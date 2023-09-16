from enum import Enum
from enum import IntEnum
import ctypes
import logging

LOG_MESSAGE_SIZE = 128

class LogLevel(Enum):
  LOG_LEVEL_DEBUG = 0
  LOG_LEVEL_INFO = 1
  LOG_LEVEL_WARNING = 2
  LOG_LEVEL_ERROR = 3
  LOG_LEVEL_VERBOSE = 4

class PayloadLog(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("level", ctypes.c_uint8),
        ("message", ctypes.c_uint8 * LOG_MESSAGE_SIZE)
    ]

    def __init__(self, packet = None):
       if packet is not None:
          self.level = packet[0]
          ctypes.memmove(self.message, packet[1:], len(packet) - 1)
          self.log_message = bytes(self.message).decode("utf-8")

    def get_text_message(self):
       return self.log_message
