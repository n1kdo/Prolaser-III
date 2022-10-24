#
# serial port access...
#
import serial


class SerialPort:
    def __init__(self, name='com1:', baudrate=19200):
        self.port = serial.Serial(port=name,
                                  baudrate=baudrate,
                                  parity=serial.PARITY_NONE,
                                  bytesize=serial.EIGHTBITS,
                                  stopbits=serial.STOPBITS_ONE,
                                  timeout=0.040)  # seems fully reliable at 20 ms at 19200
        # reliable at 0.040 for 4800

    def close_port(self):
        self.port.close()

    def write(self, buffer):
        self.port.write(buffer)

    def read(self, size=16):
        buffer = self.port.read(size)
        return buffer

    def flush_read(self):
        self.port.reset_input_buffer()
