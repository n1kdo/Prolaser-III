#!/usr/bin/env python3
#
# Prolaser III data collector.
# collect speed data from Prolaser III
#
import time

from serialport import SerialPort

BAUD_RATE = 19200
eeprom_data = [-1 for i in range(256)]

log_all_rx = False

CMD_EXIT_REMOTE   = 0x01
CMD_READ_RAM      = 0x02
CMD_ENABLE_REMOTE = 0x06
CMD_TOGGLE_LASER  = 0x07
CMD_SET_MODE      = 0x0a
CMD_READ_EEPROM   = 0x0b
CMD_WRITE_EEPROM  = 0x0c

MODE_SPEED = 0x00
MODE_RANGE = 0x03
MODE_RTR   = 0x01


def validate_checksum(buffer):
    if len(buffer) < 5:
        print('buffer is too short to checksum: {}'.format(buffer_to_hexes(buffer)))
        return False
    checksum = 0
    escaped = False
    for b in buffer[1:-2]:
        if b == 0x10:
            if not escaped:
                escaped = True
            else:
                checksum = (checksum + b) & 0x00ff
                escaped = False
        else:
            escaped = False
            checksum = (checksum + b) & 0x00ff
    if checksum != buffer[-2]:
        print('checksum mismatch, calculated {:02x} got {:02x}!'.format(checksum, buffer[-2]))
        print(hexdump_buffer(buffer))
        return False
    else:
        return True


def buffer_to_hexes(buffer):
    return ' '.join('{:02x}'.format(b) for b in buffer)


def hexdump_buffer(buffer):
    s = ''
    sh = ''
    st = ''

    offset = 0
    ofs = '{:04x}'.format(offset)
    for b in buffer:
        sh += '{:02x} '.format(b)
        st += chr(b) if 32 <= b <= 126 else '.'
        offset += 1
        if len(sh) >= 48:
            s += ofs
            s += '  '
            s += sh
            s += '  '
            s += st
            s += '\n'
            sh = ''
            st = ''
            ofs = '{:04x}'.format(offset)
    if len(sh) > 0:
        s += ofs
        s += '  '
        sh += '                                                '
        sh = sh[0:47]
        s += sh
        s += '   '
        s += st
        s += '\n'
    return s


def build_message(buffer):
    msg = [0x02]
    lb = len(buffer)
    checksum = lb
    msg.append(lb)
    for b in buffer:
        if b == 0x03 or b == 0x10:
            msg.append(0x10)
        msg.append(b)
        checksum = (checksum + b) & 0x00ff
    if checksum == 0x03 or checksum == 0x10:
        msg.append(0x10)
    msg.append(checksum)
    msg.append(0x03)
    if not validate_checksum(msg):
        print('shit! checksum mismatch: {}'.format(buffer_to_hexes(msg)))
    return msg


def receive_message(port, expect=16, timeouts=5):
    msg = []
    escaped = False
    timeouts_left = timeouts
    while timeouts_left > 0:
        buf = port.read(expect)
        if len(buf) != 0:
            for b in buf:
                # print('.{:02X}.'.format(b))
                if len(msg) > 0 and msg[0] != 0x02 and b == 0x02:
                    msg.clear()
                    msg.append(b)
                else:
                    if b == 0x10:
                        if escaped:
                            msg.append(b)
                            escaped = False
                        else:
                            escaped = True
                    else:
                        if escaped:
                            escaped = False
                            msg.append(b)
                        else:
                            msg.append(b)
                            if b == 0x03:
                                if len(msg) != expect:
                                    msg_len = msg[1] + 4
                                    print('   received {} but expected {}, message claims {} message {} '.format(len(msg), expect, msg_len, buffer_to_hexes(msg)))
                                # print('   called with {} timeouts, {} left'.format(timeouts, timeouts_left))
                                return msg
        else:
            timeouts_left -= 1
            #print('   still listening... received {} {} wanted {} left'.format(len(msg), expect, timeouts_left))
    print('   timed out! called with {} timeouts, {} left'.format(timeouts, timeouts_left))
    return msg


def send_receive_command(port, cmd, expect=16, timeouts=1):
    port.write(cmd)
    process_tx_buffer(de_escape_message(cmd))
    if expect > 0:
        msg = receive_message(port, expect=expect, timeouts=timeouts)
        if len(msg) == 0:
            print('rx: None')
        else:
            process_rx_buffer(msg)
            #print('rx: {}'.format(buffer_to_hexes(msg)))
        return msg
    else:
        return None


def send_1_byte_command(port, b, expect=5, timeouts=1):
    cmd = build_message([b])
    return send_receive_command(port, cmd, expect=expect, timeouts=timeouts)


def send_2_byte_command(port, b0, b1, expect=6, timeouts=1):
    cmd = build_message([b0, b1])
    return send_receive_command(port, cmd, expect=expect, timeouts=1)


def dump_buffer(name, buffer, dump_all=False):
    if len(buffer) < 5:
        dump_all = True
    if dump_all:
        print('{} message {}'.format(name, buffer_to_hexes(buffer)))
    else:
        print('{} payload {}'.format(name, buffer_to_hexes(buffer[2:-2])))


def de_escape_message(message):
    result = []
    escaped = False
    for b in message:
        if b == 0x10:
            if escaped:
                result.append(b)
                escaped = False
            else:
                escaped = True
        else:
            escaped = False
            result.append(b)
    return result


def process_tx_buffer(buffer):
    global eeprom_data
    global log_all_rx
    command = buffer[2]

    if command == CMD_EXIT_REMOTE:
        print('tx Exit Remote Control')
    elif command == CMD_ENABLE_REMOTE:
        print('tx Enter Remote Control')
    elif command == CMD_TOGGLE_LASER:
        print('tx toggle auto-fire on/off')
        log_all_rx = True
    elif command == CMD_SET_MODE:
        sub_command = buffer[3]
        if sub_command == MODE_SPEED:
            print('tx set mode Speed')
        elif sub_command == MODE_RTR:
            print('rx set mode Real Time Range')
        elif sub_command == MODE_RANGE:
            print('rx set mode Range')
        else:
            print('tx set unknown mode {:02x}'.format(sub_command))
    elif command == CMD_READ_EEPROM:
        addr = buffer[3]
        print('tx read ee address {:02x}'.format(addr))
    elif command == 0x0c:
        sub_command = buffer[3]
        if sub_command == 0x80:
            addr = buffer[4]
            data = buffer[5]
            print('tx write ee address {:02x} data {:02x}'.format(addr, data))
            if eeprom_data[addr] != data:
                print('updating eeprom address {} from {} to {}'.format(addr, eeprom_data[addr], data))
                eeprom_data[addr] = data
        else:
            print('tx unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer)))
    elif command == 0x13:
        print('tx send RESET')
    else:
        print('tx unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer) ))


def process_rx_buffer(buffer):
    global eeprom_data
    global log_all_rx
    if len(buffer) < 5:
        print('message too short: {}: {}'.format(len(buffer), buffer_to_hexes(buffer)))
        return
    if not validate_checksum(buffer):
        return
    command = buffer[2]
    if command == CMD_EXIT_REMOTE:
        print('rx ACK Exit Remote Control')
    elif command == CMD_ENABLE_REMOTE:
        print('rx ACK Enter Remote Control')
    elif command == CMD_TOGGLE_LASER:
        print('rx ACK toggle auto-fire off')
        log_all_rx = False
    elif command == CMD_SET_MODE:
        sub_command = buffer[3]
        if sub_command == 0x00:
            print('rx ACK set mode Speed')
        elif sub_command == 0x01:
            print('rx ACK set mode Real Time Range')
        elif sub_command == 0x03:
            print('rx ACK set mode Range')
        else:
            print('rx ACK set unknown mode {:02x}'.format(sub_command))
    elif command == CMD_READ_EEPROM:
        addr = buffer[4]
        data = buffer[5]
        print('rx read ee address {:02x} data {:02x}'.format(addr, data))
        if eeprom_data[addr] == -1:
            print('   assigning eeprom address {} from {} to {}'.format(addr, eeprom_data[addr], data))
            eeprom_data[addr] = data
        if eeprom_data[addr] != data:
            print('   updating  eeprom address {} from {} to {}'.format(addr, eeprom_data[addr], data))
            eeprom_data[addr] = data
    elif command == 0x0c:
        sub_command = buffer[3]
        if sub_command == 0x00:
            addr = buffer[4]
            print('rx write ee address ACK {:02x}'.format(addr))
        else:
            print('rx unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer)))
    elif command == 0x18:
        print('rx reading: {}'.format(buffer_to_hexes(buffer[3:-2])))
    elif command == 0x19:
        print('rx command 19...')
        print(hexdump_buffer(buffer[3:-2]))
    else:
        print('rx unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer)))


def main():
    port = SerialPort()

    send_1_byte_command(port, CMD_ENABLE_REMOTE)
    send_2_byte_command(port, CMD_READ_EEPROM, 0x01, expect=8)
    send_1_byte_command(port, CMD_EXIT_REMOTE)
    #send_2_byte_command(port, CMD_SET_MODE, MODE_SPEED)  # speed mode
    send_2_byte_command(port, CMD_SET_MODE, MODE_RANGE)  # range mode for debugging

    send_1_byte_command(port, CMD_ENABLE_REMOTE)
    # send read ee address 1
    send_2_byte_command(port, CMD_READ_EEPROM, 0x01, expect=8)
    # send command 01 -- exit remote control
    send_1_byte_command(port, CMD_EXIT_REMOTE)
    # send command 06 -- enter remote control
    send_1_byte_command(port, CMD_ENABLE_REMOTE)
    # send read ee address a3
    send_2_byte_command(port, CMD_READ_EEPROM, 0xa3, expect=8)
    # send read ee address a9
    send_2_byte_command(port, CMD_READ_EEPROM, 0xa9, expect=8)
    # send command 01 -- exit remote control
    send_1_byte_command(port, CMD_EXIT_REMOTE)
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

    print('turning laser off')
    # send fire laser toggle command 07
    send_1_byte_command(port, CMD_TOGGLE_LASER, timeouts=25)  # <= 500 msec
    #send_1_byte_command(port, 0x01, timeouts=25)  # <= 500 msec

    print('done')


if __name__ == '__main__':
    main()
