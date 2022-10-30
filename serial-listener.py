#
# serial port listener / decoder for Prolaser III
#
# listens on com3 for traffic coming FROM host
# listens on com4 for traffic from device under test
#
import logging
import serial
import sys
import time

import pl3

BAUD_RATE = 19200  # note that this depends on the EEPROM programming


def main():
    verbosity = 5
    try:
        tx_port = serial.Serial(port='com3:',
                                baudrate=BAUD_RATE,
                                parity=serial.PARITY_NONE,
                                bytesize=serial.EIGHTBITS,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=0)
        rx_port = serial.Serial(port='com4:',
                                baudrate=BAUD_RATE,
                                parity=serial.PARITY_NONE,
                                bytesize=serial.EIGHTBITS,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=0)

        tx_buffer = bytearray()
        rx_buffer = bytearray()
        tx_escaped = False
        rx_escaped = False

        eeprom_data = pl3.get_eeprom_data()
        while True:
            while True:
                buf = tx_port.read(32)
                if buf is not None and len(buf) > 0:
                    # dump_buffer('tx', buf, True)
                    for b in buf:
                        tx_was_escaped = tx_escaped
                        if tx_escaped:
                            tx_escaped = False
                        else:
                            if b == pl3.MESSAGE_ESCAPE:
                                tx_escaped = True
                        if b == pl3.START_OF_MESSAGE and len(tx_buffer) > 0 and tx_buffer[0] != pl3.START_OF_MESSAGE:
                            tx_buffer.clear()
                        tx_buffer.append(b)
                        if b == pl3.END_OF_MESSAGE and not tx_was_escaped:
                            cmd, result = pl3.process_tx_buffer(tx_buffer, verbosity=verbosity)
                            if cmd == pl3.CMD_WRITE_EEPROM:
                                addr = result[0]
                                data = result[1]
                                if eeprom_data[addr] != data:
                                    print('    eeprom_data[{.02x}] was {:02x}, wrote {:02x}', format(addr,
                                                                                                     eeprom_data[addr],
                                                                                                     data))
                                    eeprom_data[addr] = data

                            tx_buffer.clear()
                else:
                    break
            while True:
                buf = rx_port.read(32)
                if buf is not None and len(buf) > 0:
                    # dump_buffer('rx', buf, True)
                    for b in buf:
                        rx_was_escaped = rx_escaped
                        if rx_escaped:
                            rx_escaped = False
                        else:
                            if b == pl3.MESSAGE_ESCAPE:
                                rx_escaped = True
                        if b == pl3.START_OF_MESSAGE and len(rx_buffer) > 0 and rx_buffer[0] != pl3.START_OF_MESSAGE:
                            rx_buffer.clear()
                        rx_buffer.append(b)
                        if b == pl3.END_OF_MESSAGE and not rx_was_escaped:
                            cmd, result = pl3.process_rx_buffer(rx_buffer, verbosity=verbosity)
                            if cmd == pl3.CMD_READ_EEPROM:
                                addr = result[0]
                                data = result[1]
                                if eeprom_data[addr] != data:
                                    print('    eeprom_data[{.02x}] was {:02x}, read {:02x}', format(addr,
                                                                                                    eeprom_data[addr],
                                                                                                    data))
                                    eeprom_data[addr] = data
                            rx_buffer.clear()
                else:
                    break

    except IOError as e:
        print(e)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:{}',
                        level=logging.INFO,
                        stream=sys.stdout)
    logging.Formatter.converter = time.gmtime
    main()
