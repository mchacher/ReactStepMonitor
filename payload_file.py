from enum import Enum
from enum import IntEnum
import ctypes
import logging



class PayloadFile(ctypes.Structure):
    FILE_NAME_SIZE   = 20
    FILE_CHUNK_SIZE  = 196

    _pack_ = 2
    _fields_ = [
        ("chunk_id", ctypes.c_uint8),
        ("number_of_chunks", ctypes.c_uint8),
        ("chunk_size", ctypes.c_uint8),
        ("name", ctypes.c_uint8 * FILE_NAME_SIZE),
        ("data", ctypes.c_uint8 * FILE_CHUNK_SIZE)
    ]

    # def __init__(self, packet = None):
    #    if packet is not None:
    #       self.chunk_id = packet[0]
    #       self.number_of_chunks = packet[1]
    #       ctypes.memmove(self.message, packet[1:], len(packet) - 1)
    #       self.log_message = bytes(self.message).decode("ascii")

    # def get_text_message(self):
    #    return self.log_message

    def serialize(self):
        # Serialize all fields as a bytearray
        serialized_data = bytearray()
        
        # Append chunk_id, number_of_chunks and chunk_size as single bytes
        serialized_data.append(self.chunk_id)
        serialized_data.append(self.number_of_chunks)
        serialized_data.append(self.chunk_size)
        # Append name field (up to 16 bytes)
        serialized_data.extend(self.name)

        # Append data field (up to 1024 bytes)
        serialized_data.extend(self.data)

        return serialized_data
