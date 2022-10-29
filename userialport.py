#
# serial port access for Micropython on Pico-W
#
from machine import Pin, UART


class SerialPort:
    def __init__(self, name='0', baudrate=19200):
        self.port = UART(int(name),
                         baudrate=baudrate,
                         parity=None,
                         stop=1,
                         timeout=40,
                         timeout_char=40,
                         tx=Pin(0),
                         rx=Pin(1))

    def close_port(self):
        self.port.close()

    def write(self, buffer):
        self.port.write(buffer)

    def read(self, size=16):
        read_buffer = self.port.read(size)
        if read_buffer is None:
            read_buffer = []
        return read_buffer

    def flush_read(self):
        self.port.read()
