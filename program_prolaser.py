#!/usr/bin/env python3
#
# write Prolaser III EEPROM data
#

import time

import pl3

from serialport import SerialPort

eeprom_data = pl3.get_eeprom_data()
BAUD_RATE = 19200  # note that this is a function of the EEPROM programming


def main():
    port = SerialPort(baudrate=BAUD_RATE)

    # program EEPROM
    # first stage: make sure Prolaser III
    expect = pl3.read_ee(port, 0x01)
    device_id = pl3.receive_response(port, expect=expect)
    if device_id != 0x12:
        print('bad device_id {}'.format(device_id))
        return
    time.sleep(1.0)

    #fw_address = 0xaf  # address to fuck with
    #print('eeprom_data[{:02x}] = {:02x}'.format(fw_address, eeprom_data[fw_address]))
    #eeprom_data[fw_address] |= 0x80
    #print('eeprom_data[{:02x}] = {:02x}'.format(fw_address, eeprom_data[fw_address]))

    # recalculate checksum:
    eeprom_checksum = 0
    for address in range(0, pl3.EEPROM_LENGTH - 1):
        eeprom_checksum = (eeprom_checksum + eeprom_data[address]) & 0x00ff
    eeprom_data[0xb7] = eeprom_checksum  # CHECKSUM!

    expect = pl3.enable_remote(port)
    pl3.receive_response(port, expect=expect)
    for i in range(0, pl3.EEPROM_LENGTH):
        expect = pl3.write_ee(port, i, eeprom_data[i])
        result = pl3.receive_response(port, expect=expect)
    expect = pl3.exit_remote(port)
    pl3.receive_response(port, expect=expect)

    expect = pl3.reset(port)
    result = pl3.receive_response(port, expect=expect, timeouts=1000)

    print('done')


if __name__ == '__main__':
    main()
