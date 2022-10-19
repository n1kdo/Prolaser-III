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
                         timeout=50,
                         timeout_char=20,
                         tx=Pin(0),
                         rx=Pin(1))

    def close_port(self):
        self.port.close()

    def write(self, buffer):
        self.port.write(bytes(buffer))
        while not self.port.txdone():
            pass  # spin while waiting for buffer to send

    def read(self, size=16):
        buffer = self.port.read(size)
        if buffer is None:
            buffer = []
        return buffer

    def flush_read(self):
        self.port.read()
