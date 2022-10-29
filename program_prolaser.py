#!/usr/bin/env python3
#
# write Prolaser III EEPROM data
#

import time

from prolaser_protocol import process_rx_buffer, receive_message, send_1_byte_command, \
    send_2_byte_command, send_multi_byte_command

import prolaser_protocol
from prolaser_protocol import CMD_EXIT_REMOTE, CMD_READ_RAM, CMD_ENABLE_REMOTE, CMD_TOGGLE_LASER, CMD_SET_MODE, \
    CMD_READ_EEPROM, CMD_WRITE_EEPROM, CMD_RESET, CMD_READING, CMD_INIT_SPD4, CMD_WHO_ARE_YOU
from prolaser_protocol import MODE_SPEED, MODE_RANGE, MODE_RTR
from prolaser_protocol import EEPROM_LENGTH

from serialport import SerialPort

eeprom_data = prolaser_protocol.eeprom_data
BAUD_RATE = 19200  # note that this is a function of the EEPROM programming
log_all_rx = False


def main():
    port = SerialPort(baudrate=BAUD_RATE)

    # program EEPROM
    # first stage: make sure Prolaser III
    send_1_byte_command(port, CMD_WHO_ARE_YOU, 160)
    send_1_byte_command(port, CMD_ENABLE_REMOTE)
    result = send_2_byte_command(port, CMD_READ_EEPROM, 0x01, 8)  # read address 0x01
    send_1_byte_command(port, CMD_EXIT_REMOTE)

    if result != 0x12:
        print('bad data read from address 0x01, expecting 0x12, got {:02x}'.format(result))
        return

    time.sleep(1.0)

    #fw_address = 0xaf
    #print('eeprom_data[{:02x}] = {:02x}'.format(fw_address, eeprom_data[fw_address]))
    #eeprom_data[fw_address] |= 0x80
    #print('eeprom_data[{:02x}] = {:02x}'.format(fw_address, eeprom_data[fw_address]))
    # recalculate checksum:
    eeprom_checksum = 0
    for eeaddr in range(0, EEPROM_LENGTH - 1):
        eeprom_checksum = (eeprom_checksum + eeprom_data[eeaddr]) & 0x00ff
    eeprom_data[0xb7] = eeprom_checksum  # CHECKSUM!

    send_1_byte_command(port, CMD_ENABLE_REMOTE)
    for i in range(0, EEPROM_LENGTH):
        send_multi_byte_command(port, [CMD_WRITE_EEPROM, 0x80, i, eeprom_data[i]], expect=8, verbosity=4)
    send_1_byte_command(port, CMD_EXIT_REMOTE)

    send_1_byte_command(port, CMD_RESET, expect=160, timeouts=1000)

    print('done')


if __name__ == '__main__':
    main()
