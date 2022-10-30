#
# serial port access
# compatible with both pyserial on cpython and machine.UARt on micropython
#
import sys


class SerialPort:
    def __init__(self, name='', baudrate=19200, timeout=0.040):
        impl_name = sys.implementation.name
        if impl_name == 'cpython':
            import serial
            if name == '':
                name = 'com1:'
            self.port = serial.Serial(port=name,
                                      baudrate=baudrate,
                                      parity=serial.PARITY_NONE,
                                      bytesize=serial.EIGHTBITS,
                                      stopbits=serial.STOPBITS_ONE,
                                      timeout=timeout)  # seems fully reliable at 20 ms at 19200
            # reliable at 0.040 for 4800
        elif impl_name == 'micropython':
            import machine
            if name == '':
                name = '0'
            timeout_msec = int(timeout * 1000)
            self.port = machine.UART(int(name),
                                     baudrate=baudrate,
                                     parity=None,
                                     stop=1,
                                     timeout=timeout_msec,
                                     timeout_char=timeout_msec,
                                     tx=machine.Pin(0),
                                     rx=machine.Pin(1))
        else:
            raise RuntimeError('no support for {}.'.format(impl_name))

    def close_port(self):
        self.port.close()

    def write(self, buffer):
        self.port.write(buffer)

    def read(self, size=16):
        buffer = self.port.read(size)
        if buffer is None:  # micropython machine.UART returns None on timeout.
            return b''  # cpython pyserial returns empty bytes object
        else:
            return buffer
