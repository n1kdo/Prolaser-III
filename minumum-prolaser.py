#!/usr/bin/env python3
#
# Prolaser III data collector.
# collect speed data from Prolaser III
#
# minimum-prolaser just the facts ma'am.  least effort to get device collecting data.
#
import time

from prolaser_protocol import process_rx_buffer, receive_message, send_1_byte_command, \
    send_2_byte_command

import prolaser_protocol
from prolaser_protocol import CMD_EXIT_REMOTE, CMD_READ_RAM, CMD_ENABLE_REMOTE, CMD_TOGGLE_LASER, CMD_SET_MODE, \
    CMD_READ_EEPROM, CMD_WRITE_EEPROM, CMD_RESET, CMD_READING, CMD_INIT_SPD4
from prolaser_protocol import MODE_SPEED, MODE_RANGE, MODE_RTR

from serialport import SerialPort

eeprom_data = prolaser_protocol.eeprom_data
BAUD_RATE = 19200  # note that this is a function of the EEPROM programming
log_all_rx = False


def main():
    port = SerialPort(baudrate=BAUD_RATE)

    #send_1_byte_command(port, CMD_ENABLE_REMOTE)
    deviceid = send_2_byte_command(port, CMD_READ_EEPROM, 0x01, expect=8)
    #send_1_byte_command(port, CMD_EXIT_REMOTE)
    if deviceid != 0x12:
        print('who dat?')
        exit(1)
    mode = MODE_RANGE
    # send_2_byte_command(port, CMD_SET_MODE, MODE_SPEED)  # speed mode
    send_2_byte_command(port, CMD_SET_MODE, mode)  # range mode for debugging

    # send fire laser command 07
    send_1_byte_command(port, CMD_TOGGLE_LASER, 0)

    print('listening...')
    s = time.time() + 10
    while True:
        msg = receive_message(port, expect=11, timeouts=20)  # receive timeout at 20 ms, so <= 400 msec
        # first one times out.
        if len(msg) > 0:
            process_rx_buffer(msg)
            # print(buffer_to_hexes(msg))
        if time.time() > s:
            break

    # send fire laser toggle command 07
    send_1_byte_command(port, CMD_TOGGLE_LASER, timeouts=25)  # <= 500 msec
    # send_1_byte_command(port, 0x01, timeouts=25)  # <= 500 msec

    print('done')


if __name__ == '__main__':
    main()
