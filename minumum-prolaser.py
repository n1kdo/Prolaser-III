#!/usr/bin/env python3
#
# Prolaser III data collector.
# collect speed data from Prolaser III
#
# minimum-prolaser just the facts ma'am.  least effort to get device collecting data.
#
import time

import pl3

from serialport import SerialPort

eeprom_data = pl3.eeprom_data
BAUD_RATE = 19200  # note that this is a function of the EEPROM programming
log_all_rx = False


def main():
    port = SerialPort(baudrate=BAUD_RATE)

    expect = pl3.read_ee(port, 0x01)
    command, device_id = pl3.receive_response(port, expect=expect)
    if device_id != 0x12:
        print('bad device_id {}'.format(device_id))

    expect = pl3.set_mode(port, pl3.MODE_RANGE)
    pl3.receive_response(port, expect=expect)

    pl3.toggle_laser(port)  # if laser is off, nothing is expected...

    print('listening...')
    s = time.time() + 10
    while time.time() < s:
        cmd, result = pl3.receive_response(port, expect=11, timeouts=20)  # receive timeout at 20 ms, so <= 400 msec
        print(result)

    # send fire laser toggle command 07
    expect = pl3.toggle_laser(port)  # if laser is off, nothing is expected...

    command, result = pl3.receive_response(port, expect=expect, timeouts=100)
    print(result)
    #expect = pl3.exit_remote(port)
    #pl3.receive_response(port, expect=expect)
    print('done')


if __name__ == '__main__':
    main()
