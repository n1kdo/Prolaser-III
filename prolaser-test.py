#!/usr/bin/env python3
#
# Prolaser III data collector.
# collect speed data from Prolaser III
#
import time

import pl3

from serialport import SerialPort

_eeprom_data = pl3._eeprom_data
BAUD_RATE = 19200  # note that this is a function of the EEPROM programming
log_all_rx = False


def main():
    port = SerialPort(baudrate=BAUD_RATE)

    expect = pl3.enable_remote(port)
    pl3.receive_response(port, expect=expect)

    expect = pl3.read_ee(port, 0x01)
    cmd, result = pl3.receive_response(port, expect=expect)
    device_id = result[1]
    if device_id != 0x12:
        print('bad device_id {}'.format(device_id))

    expect = pl3.exit_remote(port)
    pl3.receive_response(port, expect=expect)

    expect = pl3.set_mode(port, pl3.MODE_RANGE)
    pl3.receive_response(port, expect=expect)

    expect = pl3.enable_remote(port)
    pl3.receive_response(port, expect=expect)

    expect = pl3.read_ee(port, 0x01)
    command, result = pl3.receive_response(port, expect=expect)
    # addr = result[0]
    device_id = result[1]
    if device_id != 0x12:
        print('bad device_id {:02x}'.format(device_id))

    expect = pl3.read_ee(port, 0xa9)
    command, result = pl3.receive_response(port, expect=expect)
    packet_type = result[1]

    if packet_type != 2:
        print('bad packet type {}'.format(packet_type))

    expect = pl3.exit_remote(port)
    pl3.receive_response(port, expect=expect)

    expect = pl3.toggle_laser(port)  # if laser is off, nothing is expected...
    command, result = pl3.receive_response(port, expect=expect, timeouts=20)
    print(command, result)

    print('listening...')
    s = time.time() + 10
    while time.time() < s:
        msg = pl3.receive_response(port, expect=11, timeouts=20)  # receive timeout at 20 ms, so <= 400 msec
        print(msg)

    # send fire laser toggle command 07
    expect = pl3.toggle_laser(port)  # if laser is off, nothing is expected...

    result = pl3.receive_response(port, expect=expect, timeouts=100)
    print(result)

    #send_1_byte_command(port, CMD_TOGGLE_LASER, timeouts=25)  # <= 500 msec
    # send_1_byte_command(port, 0x01, timeouts=25)  # <= 500 msec

    print('done')


if __name__ == '__main__':
    main()
