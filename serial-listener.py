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

from prolaser import dump_buffer, process_rx_buffer, process_tx_buffer, validate_checksum

BAUD_RATE = 19200
eeprom_data = bytearray(256)
log_all_rx = False


"""
Kustom Signals Prolaser III serial signal protocol analysis.

Message format

0x02 0x0n 0xqq ... 0xzz 0x03
  ^    ^    ^        ^    ^
  |    |    |        |    +--- always 0x03.  indicates end of message
  |    |    |        +-------- checksum. sum of length byte and all data bytes.
  |    |    +----------------- data byte/s. value included in checksum.  
  |    +---------------------- number of bytes in message. value included in checksum.
  +--------------------------- always 0x02.  indicates start of message.
  
Magic numbers and Escape codes:

0x10 works as an escape character and causes the next character not to have its special meaning:
0x03 is an end of message character and must be escaped to be sent as any payload byte: 0x10 0x03
0x10 itself must be escaped, to send 0x10 as part of the payload, send 0x10 0x10

The _payload_ of the message is in bytes 2:-2...
assuming the first byte of the message is a command, then I have seen these

06: send 06, get 06 back.  appears to set remote control mode.
0b: send 0b xx, get 0b 00 xx yy back.  Read location? xx in range 00-b6.
01: send 01, get 01 back.  appears to exit remote control mode
02: send 02 98 a0 ??? read RAM?
0a: send 0a 00, get 0a 00 back  -- this appears to set speed mode. (payloads are 06 0b01 01, 0a00)
    send 0a 03, get 0a 03 back  -- this appears to set range mode. (payloads are 06 0b01 01, 0a03)
    send 0a 01, get 0a 01 back  -- this appears to set RTR mode. (payloads are 06 0b01 01, 0a01)

07: automatic fire mode. send once to turn on, send again to turn off,  get 07 back on turn off
    (payloads are 06 0b01 01 02 0ba3 0ba9 01 01 07 07)

13: reset / self test?
    
manual fire button press 
   sends 06 0b01 01 06 0ba3 0ba9 01
   deselect sends nothing.
    
write eeprom:

06 0b01 01 06 THEN...
0c80xxyy gets back 0c00xx00 xx range from 00-b7
THEN... 
01 
13 RESET
 
"""


def main():
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

        tx_buffer = []
        rx_buffer = []
        tx_escaped = False
        rx_escaped = False
        while True:
            while True:
                buf = tx_port.read(32)
                if buf is not None and len(buf) > 0:
                    for b in buf:
                        if tx_escaped:
                            print('tx escaped {:02x}'.format(b))
                            tx_buffer.append(b)
                            tx_escaped = False
                        else:
                            if b == 0x10:
                                tx_escaped = True
                            else:
                                if b == 0x02 and len(tx_buffer) > 0 and tx_buffer[0] != 0x02:
                                    tx_buffer.clear()
                                tx_buffer.append(b)
                                if b == 0x03:
                                    if validate_checksum(tx_buffer):
                                        #dump_buffer('tx', tx_buffer)
                                        process_tx_buffer(tx_buffer)
                                    else:
                                        dump_buffer('tx', tx_buffer, True)
                                    tx_buffer.clear()
                else:
                    break
            while True:
                buf = rx_port.read(32)
                if buf is not None and len(buf) > 0:
                    for b in buf:
                        if log_all_rx:
                            print('{:02x} '.format(b), end='')
                        if rx_escaped:
                            # print('rx escaped {:02x}'.format(b))
                            rx_buffer.append(b)
                            rx_escaped = False
                        else:
                            if b == 0x10:
                                rx_escaped = True
                            else:
                                if b == 0x02 and len(rx_buffer) > 0 and rx_buffer[0] != 0x02:
                                    rx_buffer.clear()
                                rx_buffer.append(b)
                                if b == 0x03:
                                    if validate_checksum(rx_buffer):
                                        #dump_buffer('rx', rx_buffer)
                                        process_rx_buffer(rx_buffer)
                                    else:
                                        dump_buffer('rx', rx_buffer, True)
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
