# Prolaser III protocol

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

The escape code is not counted in the checksum calculation, but the escaped value _is_.

The _payload_ of the message is in bytes 2:-2...
assuming the first byte of the message is a command, then I have seen these

01: send 01, get 01 back.  appears to exit remote control mode
02: send 02 98 a0 ??? read RAM
05: reply with init message
06: send 06, get 06 back.  appears to enable remote control mode.
07: automatic fire mode. send once to turn on, send again to turn off,  get 07 back on turn off
    (payloads are 06 0b01 01 02 0ba3 0ba9 01 01 07 07)
0a: send 0a 00, get 0a 00 back  -- this appears to set speed mode. (payloads are 06 0b01 01, 0a00)
    send 0a 03, get 0a 03 back  -- this appears to set range mode. (payloads are 06 0b01 01, 0a03)
    send 0a 01, get 0a 01 back  -- this appears to set RTR mode. (payloads are 06 0b01 01, 0a01)
0b: send 0b xx, get 0b 00 xx yy back.  Read eeprom. xx in range 00-b6.
0c: write eeprom.
13: reset / self test?
18: distance reading
19: message
manual fire button press
   sends 06 0b01 01 06 0ba3 0ba9 01
   deselect sends nothing.

write eeprom:

06 0b01 01 06 THEN...
0c80xxyy gets back 0c00xx00 xx range from 00-b7
THEN...
01
13 RESET

eeprom mapping

0x0c range offset high byte of 16 bit value. # feet * 64
0x0d range offset.   0.1 ft -> 000a
                     2.2 ft -> 00dc
                     2.0 ft -> 00c8
                     1.0 ft -> 0064
                    10.0 ft -> 03e8

0e speed offset hi byte MPH * 10
0f speed offset lo byte
  val hi lo
   30 01 sc
   20 00 c8
   00 00 00

0x18 min range high byte of 16-bit value
0x19 min range low  byte of 16-bit value
  "minimum range" mapping to 0x18, 0x19 addresses
  val  18 19
  01:  00 64
  02:  00 c8
  03:  01 2c
  04:  01 90
  05:  01 f4
  06:  02 58
  10:  03 e8
  20:  07 d0
 100:  27 10

This appears to be a 16-bit value calculated by # feet * 0x64.  Hi byte in 0x18, low byte in 0x19

0xa3: Units.  01: english, 02: SI, 03: knots/feet, 04: knots/meters, 05: feet/sec, 06: meters/sec

0xa9: speed packet op code: SPD2: 01, SPD3: 00, SPD4: 02

0xaf: clock start compensation, 1 is on, 0 is off.

0xb0: CFAR toggle, 1 is on, 0 is off

0xb1: min range set value

0xb5: calculate TAC area calibrate window on->off was 0b, changed to 0a
                                          off->on was 0a, change to 0b
                                          appears that bit 0 (LSB) toggles Calculate TAC calibrate window
0xb5: do not show checksum on lcd of->off was 0b, changed to 09
                                  off->on was 09, changed to 0b
                                  appears that bit 1 when set disables checksum on LCD
0xb5: french text off->on: was 0b, changed to 0f
                  on->off: was of, changed to 0b
                  appears that bit 2 enables french text
0xb5: camera mode on->off: was 0b, changed to 03
                  off->on: was 03, changed to 0b
                  appears that bit 3 toggles camera mode.
0xb5: italian text off->on: was 0b, changed to 1b
                   on->off: was 1b, changed to 0b
                   appears that bit 4 enables italian text
0xb5: short serial output: off->on was 0b changed to 8b
                           on->off was 9b changed to 0b
                           appears that bit 7 enables short serial
0xb7: checksum of bytes 00-b6

"""
import sys
from buffer_utils import buffer_to_hexes, hexdump_buffer
log_all_rx = False

# message bytes
START_OF_MESSAGE = 0x02
END_OF_MESSAGE = 0x03
MESSAGE_ESCAPE = 0x10

# command bytes
CMD_EXIT_REMOTE = 0x01
CMD_READ_RAM = 0x02
CMD_WHO_ARE_YOU = 0x05
CMD_ENABLE_REMOTE = 0x06
CMD_TOGGLE_LASER = 0x07
CMD_SET_MODE = 0x0a
CMD_READ_EEPROM = 0x0b
CMD_WRITE_EEPROM = 0x0c
CMD_INIT_SPD23 = 0x12
CMD_RESET = 0x13
CMD_READING = 0x18
CMD_INIT_SPD4 = 0x19

# known command data bytes
MODE_SPEED = 0x00
MODE_RANGE = 0x03
MODE_RTR = 0x01

# EEPROM data for Prolaser III
EEPROM_LENGTH = 0xb7 + 1
eeprom_data = [0x00] * EEPROM_LENGTH

eeprom_data[0x00] = 0x00
eeprom_data[0x01] = 0x12
eeprom_data[0x02] = 0x07
eeprom_data[0x03] = 0x12  # changes from 14 to 13 to 12 to 10
eeprom_data[0x04] = 0x08
eeprom_data[0x05] = 0x3e  # changes from 40 t0 3f to 3e to 3c
eeprom_data[0x06] = 0x07
eeprom_data[0x07] = 0x1f  # changes from 22 to 21 to 20 to 1f
eeprom_data[0x08] = 0x08
eeprom_data[0x09] = 0x4b  # changes from 4e to 4c to 4b
eeprom_data[0x0a] = 0x00
eeprom_data[0x0b] = 0x00
eeprom_data[0x0c] = 0x00  # range offset hi byte (# feet * 0x64)
eeprom_data[0x0d] = 0xdc  # range offset lo byte
eeprom_data[0x0e] = 0x00  # speed offset hi byte (mph * 10)
eeprom_data[0x0f] = 0x00  # speed offset lo byte

eeprom_data[0x10] = 0x00  # absolute minimum speed hi byte (mph * 10) -- set to 5
eeprom_data[0x11] = 0x32  # absolute minimum speed lo byte
eeprom_data[0x12] = 0x00  # minimum speed hi byte (mph * 10) -- set to 5
eeprom_data[0x13] = 0x32  # minimum speed
eeprom_data[0x14] = 0x07  # maximum speed hi byte (mph * 10) -- set to 201
eeprom_data[0x15] = 0xda  # maximum speed lo byte (mph * 10)
eeprom_data[0x16] = 0x00
eeprom_data[0x17] = 0x00
eeprom_data[0x18] = 0x03  # minimum range hi byte (feet * 0x64) -- set to 5
eeprom_data[0x19] = 0xe8  # minimum range lo byte
eeprom_data[0x1a] = 0x00
eeprom_data[0x1b] = 0x00
eeprom_data[0x1c] = 0x27  # max range hi byte (feet * 0x64) -- set to 100
eeprom_data[0x1d] = 0x10  # max range lo byte
eeprom_data[0x1e] = 0x00  # delta speed KPH (kph * 10) -- set to 3
eeprom_data[0x1f] = 0x1e  # delta speed KPH

eeprom_data[0x20] = 0x4b  # baud rate hi byte  19200=>4b, 9600=>25, 4800=>12 is literally the baud rate
eeprom_data[0x21] = 0x00  # baud rate lo byte  19200=>00, 9600=>80, 4800=>c0
eeprom_data[0x22] = 0x00
eeprom_data[0x23] = 0x0a
eeprom_data[0x24] = 0x00
eeprom_data[0x25] = 0x2b
eeprom_data[0x26] = 0x00
eeprom_data[0x27] = 0xb4
eeprom_data[0x28] = 0x00
eeprom_data[0x29] = 0x00
eeprom_data[0x2a] = 0x00
eeprom_data[0x2b] = 0x00
eeprom_data[0x2c] = 0x00
eeprom_data[0x2d] = 0x00
eeprom_data[0x2e] = 0x00
eeprom_data[0x2f] = 0x00

eeprom_data[0x30] = 0x01
eeprom_data[0x31] = 0x1e
eeprom_data[0x32] = 0x01
eeprom_data[0x33] = 0xa0
eeprom_data[0x34] = 0x00
eeprom_data[0x35] = 0x02
eeprom_data[0x36] = 0x78
eeprom_data[0x37] = 0xd0
eeprom_data[0x38] = 0x01
eeprom_data[0x39] = 0x68
eeprom_data[0x3a] = 0x01
eeprom_data[0x3b] = 0x4f
eeprom_data[0x3c] = 0x00
eeprom_data[0x3d] = 0x02
eeprom_data[0x3e] = 0x26
eeprom_data[0x3f] = 0xc8

eeprom_data[0x40] = 0x02
eeprom_data[0x41] = 0x05
eeprom_data[0x42] = 0x01
eeprom_data[0x43] = 0xab
eeprom_data[0x44] = 0x00
eeprom_data[0x45] = 0x05
eeprom_data[0x46] = 0x09
eeprom_data[0x47] = 0x10
eeprom_data[0x48] = 0x05
eeprom_data[0x49] = 0x78
eeprom_data[0x4a] = 0x2c
eeprom_data[0x4b] = 0x24
eeprom_data[0x4c] = 0x00
eeprom_data[0x4d] = 0xf1
eeprom_data[0x4e] = 0x64
eeprom_data[0x4f] = 0xd9

eeprom_data[0x50] = 0x00
eeprom_data[0x51] = 0x00
eeprom_data[0x52] = 0xe9
eeprom_data[0x53] = 0x4c
eeprom_data[0x54] = 0x66
eeprom_data[0x55] = 0x2a
eeprom_data[0x56] = 0x01
eeprom_data[0x57] = 0xf4
eeprom_data[0x58] = 0xe9
eeprom_data[0x59] = 0x4c
eeprom_data[0x5a] = 0x66
eeprom_data[0x5b] = 0x2a
eeprom_data[0x5c] = 0x03
eeprom_data[0x5d] = 0xe8
eeprom_data[0x5e] = 0xe9
eeprom_data[0x5f] = 0x4c

eeprom_data[0x60] = 0x66
eeprom_data[0x61] = 0x2a
eeprom_data[0x62] = 0x0b
eeprom_data[0x63] = 0xb8
eeprom_data[0x64] = 0xe9
eeprom_data[0x65] = 0x4c
eeprom_data[0x66] = 0x66
eeprom_data[0x67] = 0x2a
eeprom_data[0x68] = 0x1b
eeprom_data[0x69] = 0x58
eeprom_data[0x6a] = 0xe9
eeprom_data[0x6b] = 0x4c
eeprom_data[0x6c] = 0x66
eeprom_data[0x6d] = 0x2a
eeprom_data[0x6e] = 0x00
eeprom_data[0x6f] = 0x00

eeprom_data[0x70] = 0x00
eeprom_data[0x71] = 0x00
eeprom_data[0x72] = 0x00
eeprom_data[0x73] = 0x00
eeprom_data[0x74] = 0x00
eeprom_data[0x75] = 0x00
eeprom_data[0x76] = 0x00
eeprom_data[0x77] = 0x00
eeprom_data[0x78] = 0x00
eeprom_data[0x79] = 0x00
eeprom_data[0x7a] = 0x00
eeprom_data[0x7b] = 0x00
eeprom_data[0x7c] = 0x00
eeprom_data[0x7d] = 0x00
eeprom_data[0x7e] = 0x00
eeprom_data[0x7f] = 0x00

eeprom_data[0x80] = 0x00
eeprom_data[0x81] = 0x00
eeprom_data[0x82] = 0x00
eeprom_data[0x83] = 0x00
eeprom_data[0x84] = 0x00
eeprom_data[0x85] = 0x00
eeprom_data[0x86] = 0x00
eeprom_data[0x87] = 0x00
eeprom_data[0x88] = 0x00
eeprom_data[0x89] = 0x00
eeprom_data[0x8a] = 0x00
eeprom_data[0x8b] = 0x00
eeprom_data[0x8c] = 0x83
eeprom_data[0x8d] = 0x3a
eeprom_data[0x8e] = 0xf9
eeprom_data[0x8f] = 0x28

eeprom_data[0x90] = 0x00
eeprom_data[0x91] = 0x50
eeprom_data[0x92] = 0x00
eeprom_data[0x93] = 0x52
eeprom_data[0x94] = 0x01
eeprom_data[0x95] = 0x54
eeprom_data[0x96] = 0x02
eeprom_data[0x97] = 0x55
eeprom_data[0x98] = 0x03
eeprom_data[0x99] = 0x57
eeprom_data[0x9a] = 0x05
eeprom_data[0x9b] = 0x58
eeprom_data[0x9c] = 0x09
eeprom_data[0x9d] = 0x5b
eeprom_data[0x9e] = 0x0f
eeprom_data[0x9f] = 0x5e

eeprom_data[0xa0] = 0x58
eeprom_data[0xa1] = 0x05
eeprom_data[0xa2] = 0x05
eeprom_data[0xa3] = 0x01  # units. 01: english, 02: SI, 03: knots/feet, 04: knots/meters, 05: feet/sec, 06: meters/sec
eeprom_data[0xa4] = 0x03  # speed type. 01: approaching. 02: receding, 03: both
eeprom_data[0xa5] = 0x3c
eeprom_data[0xa6] = 0x00
eeprom_data[0xa7] = 0x03
eeprom_data[0xa8] = 0x00
eeprom_data[0xa9] = 0x02  # speed packet op code: SPD2: 01, SPD3: 00, SPD4: 02
eeprom_data[0xaa] = 0x00
eeprom_data[0xab] = 0x01
eeprom_data[0xac] = 0x14
eeprom_data[0xad] = 0x0a
eeprom_data[0xae] = 0x02
eeprom_data[0xaf] = 0x01  # clock start compensation, 1 is on, 0 is off.

eeprom_data[0xb0] = 0x00  # CFAR toggle, 1 is on, 0 is off
eeprom_data[0xb1] = 0x0a  # min range set (single byte value?)  10 feet
eeprom_data[0xb2] = 0x40
eeprom_data[0xb3] = 0x14  # range filter #1, feet -- this is 20
eeprom_data[0xb4] = 0x3c  # range filter #2, feet -- this is 80
eeprom_data[0xb5] = 0x82  # bitmapped options: 1000 0010
                            # 7 10000000 short serial output
                            # 6 01000000 ?
                            # 5 00100000 ?
                            # 4 00010000 Italian text
                            # 3 00001000 camera mode
                            # 2 00000100 French text
                            # 1 00000010 disable checksum on lcd
                            # 0 00000001 enable calculate tac calibrate window (does not stay on)
eeprom_data[0xb6] = 0x50
eeprom_checksum = 0
for eeaddr in range(0, 0xb7):
    eeprom_checksum = (eeprom_checksum + eeprom_data[eeaddr]) & 0x00ff
eeprom_data[0xb7] = eeprom_checksum  # CHECKSUM!


def build_message(buffer):
    msg = [START_OF_MESSAGE]
    lb = len(buffer)
    checksum = lb
    msg.append(lb)
    for b in buffer:
        if b == END_OF_MESSAGE or b == MESSAGE_ESCAPE:
            msg.append(MESSAGE_ESCAPE)
        msg.append(b)
        checksum = (checksum + b) & 0x00ff
    if checksum == END_OF_MESSAGE or checksum == MESSAGE_ESCAPE:
        msg.append(MESSAGE_ESCAPE)
    msg.append(checksum)
    msg.append(END_OF_MESSAGE)
    if not validate_checksum('tx', msg):
        print('shit! checksum mismatch: {}'.format(buffer_to_hexes(msg)), file=sys.stderr)
    return msg


def de_escape_message(message):
    result = []
    escaped = False
    for b in message:
        if b == MESSAGE_ESCAPE:
            if escaped:
                result.append(b)
                escaped = False
            else:
                escaped = True
        else:
            escaped = False
            result.append(b)
    return result


def process_tx_buffer(buffer, verbosity=5):
    global eeprom_data
    global log_all_rx
    if len(buffer) < 5:
        print('message too short: {}: {}'.format(len(buffer), buffer_to_hexes(buffer)))
        return
    if not validate_checksum('tx', buffer):
        return

    buffer = de_escape_message(buffer)
    command = buffer[2]
    if command == CMD_EXIT_REMOTE:
        print('tx CMD_EXIT_REMOTE')
    elif command == CMD_WHO_ARE_YOU:
        print('tx CMD_WHO_ARE_YOU')
    elif command == CMD_READ_RAM:
        print('tx CMD_READ_RAM: {}'.format(buffer_to_hexes(buffer)))
    elif command == CMD_ENABLE_REMOTE:
        print('tx CMD_ENABLE_REMOTE')
    elif command == CMD_TOGGLE_LASER:
        print('tx CMD_TOGGLE_LASER (on/off?)')
        log_all_rx = True
    elif command == CMD_SET_MODE:
        sub_command = buffer[3]
        if sub_command == MODE_SPEED:
            print('tx CMD_SET_MODE Speed')
        elif sub_command == MODE_RTR:
            print('tx CMD_SET_MODE RTR')
        elif sub_command == MODE_RANGE:
            print('tx CMD_SET_MODE_RANGE Set mode Range')
        else:
            print('tx CMD_SET_MODE_RANGE unknown mode {:02x}'.format(sub_command))
    elif command == CMD_READ_EEPROM:
        addr = buffer[3]
        print('tx CMD_READ_EEPROM address {:02x}'.format(addr))
    elif command == CMD_WRITE_EEPROM:
        sub_command = buffer[3]
        if sub_command == 0x80:
            addr = buffer[4]
            data = buffer[5]
            print('tx CMD_WRITE_EEPROM address {:02x} data {:02x}'.format(addr, data))
            if eeprom_data[addr] != data:
                print('                           updating eeprom address {:02x} from {:02x} to {:02x}'.format(addr,
                                                                                                               eeprom_data[
                                                                                                                   addr],
                                                                                                               data))
                eeprom_data[addr] = data
            if addr == 0xb7:  # checksum byte
                checksum = 0
                for ca in range(0, 0xb7):
                    checksum = (checksum + eeprom_data[ca]) & 0x00ff
                print('   calculated checksum {:02x}, checksum={:02x}'.format(checksum, data))
        else:
            print('tx unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer)))
    elif command == CMD_RESET:
        print('tx CMD_RESET')
    else:
        print('tx unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer)))


def process_rx_buffer(buffer, verbosity=5):
    global eeprom_data
    global log_all_rx
    if len(buffer) < 5:
        print('message too short: {}: {}'.format(len(buffer), buffer_to_hexes(buffer)))
        return
    if not validate_checksum('rx', buffer):
        return
    buffer = de_escape_message(buffer)
    command = buffer[2]
    if command == CMD_EXIT_REMOTE:
        if verbosity > 4:
            print('rx ACK CMD_EXIT_REMOTE')
    elif command == CMD_READ_RAM:
        print('rx CMD_READ_RAM response: {}'.format(buffer_to_hexes(buffer)))
    elif command == CMD_ENABLE_REMOTE:
        if verbosity > 4:
            print('rx ACK CMD_ENABLE_REMOTE')
    elif command == CMD_TOGGLE_LASER:
        print('rx ACK CMD_TOGGLE_LASER (off)')
        log_all_rx = False
    elif command == CMD_SET_MODE:
        sub_command = buffer[3]
        if sub_command == MODE_SPEED:
            if verbosity > 4:
                print('rx ACK CMD_SET_MODE Speed')
        elif sub_command == MODE_RTR:
            if verbosity > 4:
                print('rx ACK CMD_SET_MODE RTR')
        elif sub_command == MODE_RANGE:
            if verbosity > 4:
                print('rx ACK CMD_SET_MODE Range')
        else:
            print('rx ACK CMD_SET_MODE unknown mode {:02x}'.format(sub_command))
    elif command == CMD_READ_EEPROM:
        addr = buffer[4]
        data = buffer[5]
        if verbosity > 4:
            print('rx CMD_READ_EEPROM response address {:02x} data {:02x}'.format(addr, data))
        spaces = ' ' * 20
        if eeprom_data[addr] == -1:
            print('{}assigning eeprom address {:02x} from {:02x} to {:02x}'.format(spaces, addr, eeprom_data[addr], data))
            eeprom_data[addr] = data
        if eeprom_data[addr] != data:
            print('{}updating eeprom address {:02x} from {:02x} to {:02x}'.format(spaces, addr, eeprom_data[addr], data))
            eeprom_data[addr] = data
    elif command == CMD_WRITE_EEPROM:
        sub_command = buffer[3]
        if sub_command == 0x00:
            addr = buffer[4]
            if verbosity > 4:
                print('rx CMD_WRITE_EEPROM response {:02x}'.format(addr))
        else:
            print('rx CMD_WRITE_EEPROM response unhandled subcommand {:02x} in {}'.format(sub_command,
                                                                                          buffer_to_hexes(buffer)))
    elif command == CMD_READING:
        if buffer[4] == 0xff and buffer[5] == 0x7f:
            print('rx CMD_READING: {} : {:5.1f} feet'.format(buffer_to_hexes(buffer[3:-2]), buffer[6] / 10.0))
        else:
            print('rx CMD_READING: {}'.format(buffer_to_hexes(buffer[3:-2])))
    elif command == CMD_INIT_SPD23:
        print('rx CMD_INIT_SPD23 text payload follows:')
        start = 3
        while buffer[start] < 0x20:
            start += 1
        print(bytes(buffer[start:-2]).decode())
    elif command == CMD_INIT_SPD4:
        print('rx CMD_INIT_SPD4 text payload follows:')
        start = 3
        print(hexdump_buffer(buffer[start:-2]))
        #while buffer[start] < 0x20:
        #    start += 1
        #print(bytes(buffer[start:-2]).decode())
    else:
        print('rx unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer)))


def receive_message(port, expect=16, timeouts=5):
    msg = []
    escaped = False
    timeouts_left = timeouts
    expected = expect
    while timeouts_left > 0:
        if expected < 1:
            expected = 1
        buf = port.read(expected)
        if len(buf) != 0:
            for b in buf:
                # print('.{:02X}.'.format(b))
                if len(msg) > 0 and msg[0] != START_OF_MESSAGE and b == START_OF_MESSAGE:
                    msg.clear()
                    msg.append(b)
                    expected = expect - 1
                else:
                    if b == MESSAGE_ESCAPE:
                        if escaped:
                            msg.append(b)
                            expected -= 1
                            escaped = False
                        else:
                            escaped = True
                    else:
                        expected -= 1
                        if escaped:
                            escaped = False
                            msg.append(b)
                        else:
                            msg.append(b)
                            if b == END_OF_MESSAGE:
                                if len(msg) != expect:
                                    msg_len = msg[1] + 4
                                    print(
                                        '   received {} but expected {}, message claims {} message {} '.format(len(msg),
                                                                                                               expect,
                                                                                                               msg_len,
                                                                                                               buffer_to_hexes(
                                                                                                                   msg)))
                                # print('   called with {} timeouts, {} left'.format(timeouts, timeouts_left))
                                return msg
        else:
            timeouts_left -= 1
            # print('   still listening... received {} {} wanted {} left'.format(len(msg), expect, timeouts_left))
    print('   timed out! called with {} timeouts, {} left'.format(timeouts, timeouts_left), file=sys.stderr)
    return msg


def send_receive_command(port, cmd, expect=16, timeouts=1):
    port.write(cmd)
    process_tx_buffer(cmd)
    if expect > 0:
        msg = receive_message(port, expect=expect, timeouts=timeouts)
        if len(msg) == 0:
            print('rx: None *********')
        else:
            process_rx_buffer(msg)
        return msg
    else:
        return None


def send_1_byte_command(port, b, expect=5, timeouts=1):
    cmd = build_message([b])
    return send_receive_command(port, cmd, expect=expect, timeouts=timeouts)


def send_2_byte_command(port, b0, b1, expect=6, timeouts=1):
    cmd = build_message([b0, b1])
    return send_receive_command(port, cmd, expect=expect, timeouts=timeouts)


def validate_checksum(name, buffer):
    if len(buffer) < 5:
        print('buffer is too short to checksum: {}'.format(buffer_to_hexes(buffer)))
        return False
    buffer = de_escape_message(buffer)
    checksum = 0
    for b in buffer[1:-2]:
        checksum = (checksum + b) & 0x00ff
    if checksum == buffer[-2]:
        return True
    else:
        print()
        print('---------------------------------------------------------------------------------------')
        print('{} checksum mismatch, calculated {:02x} got {:02x}!'.format(name, checksum, buffer[-2]))
        print(hexdump_buffer(buffer))
        print('---------------------------------------------------------------------------------------')
        return False


