# Prolaser III protocol

"""
Kustom Signals Prolaser III serial signal protocol analysis.

reverse engineered from analyzing serial traffic from ulceeprom

Message format

0x02 0x0n 0xqq ... 0xzz 0x03
  ^    ^    ^        ^    ^
  |    |    |        |    +--- always 0x03.  indicates end of message
  |    |    |        +-------- checksum. sum of length byte and all data bytes.
  |    |    +----------------- N data byte/s. value included in checksum.
  |    +---------------------- number of bytes in message. value included in checksum.
  +--------------------------- always 0x02.  indicates start of message.

Magic numbers and Escape codes:

0x10 works as an escape character and causes the next character not to have its special meaning:
0x03 is an end of message character and must be escaped to be sent as any payload byte: 0x10 0x03
0x10 itself must be escaped, to send 0x10 as part of the payload, send 0x10 0x10

The escape code is not counted in the checksum calculation, but the escaped value _is_.

The _payload_ of the message is in bytes [2:-2]...
assuming the first byte of the message is a command, then I have seen these

01: send 01, get 01 back.  appears to exit remote control mode
02: send 02 98 a0 -- read RAM
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

"""
import sys


# message bytes
START_OF_MESSAGE = 0x02
END_OF_MESSAGE = 0x03
MESSAGE_ESCAPE = 0x10

# command bytes

CMD_UNK_00 = 0x00  # sends back message 0 of 260 bytes back of mostly zeros
CMD_EXIT_REMOTE = 0x01
CMD_READ_RAM = 0x02
CMD_UNK_03 = 0x03  # sends back message 0 260 bytes
CMD_UNK_04 = 0x04  # sends back message 0 260 bytes
CMD_WHO_ARE_YOU = 0x05
CMD_ENABLE_REMOTE = 0x06
CMD_TOGGLE_LASER = 0x07
CMK_UNK_08 = 0x08  # sends back message 0 260 bytes
CMD_UNK_09 = 0x09  # sends back message 0 260 bytes
CMD_SET_MODE = 0x0a
CMD_READ_EEPROM = 0x0b
CMD_WRITE_EEPROM = 0x0c
CMD_UNK_0D = 0x0d  # sends back message 0 260 bytes
CMD_UNK_0E = 0x0e  # sends back message 0 260 bytes
CMD_UNK_0F = 0x0f  # sends back message 0 260 bytes
CMD_UNK_10 = 0x10  # sends back message 0 260 bytes
CMD_UNK_11 = 0x11  # sends back message 0 260 bytes
CMD_UNK_12 = 0x12  # sends back message 0 260 bytes
CMD_INIT_SPD23 = 0x12  # this is a response message
CMD_RESET = 0x13
CMD_READING = 0x18  # this is a response message
CMD_INIT_SPD4 = 0x19  # this is a response message

# known command data bytes
MODE_SPEED = 0x00
MODE_RANGE = 0x03
MODE_RTR = 0x01

# EEPROM data for Prolaser III
#
# right now this is both a memory map and a set of defaults.
#
EEPROM_LENGTH = 0xb7 + 1
_eeprom_data = None


def get_eeprom_data():
    global _eeprom_data
    if _eeprom_data is None:
        _eeprom_data = bytearray(EEPROM_LENGTH)

        _eeprom_data[0x00] = 0x00
        _eeprom_data[0x01] = 0x12  # magic value
        _eeprom_data[0x02] = 0x07  # tac/cal leading edge low value MSB (0x07)
        _eeprom_data[0x03] = 0x14  # tac/cal leading edge low value LSB (0x14)  (1812)
        _eeprom_data[0x04] = 0x08  # tac/cal leading edge high value MSB (0x08)
        _eeprom_data[0x05] = 0x40  # tac/cal leading edge high value LSB (0x40)  (2112)
        _eeprom_data[0x06] = 0x07  # tac/cal trailing edge low value MSB (0x07)
        _eeprom_data[0x07] = 0x22  # tac/cal trailing edge low value LSB (0x22) (1826)
        _eeprom_data[0x08] = 0x08  # tac/cal trailing edge high value MSB (0x08)
        _eeprom_data[0x09] = 0x4e  # tac/cal trailing edge high value LSB (0x4e) (2126)
        _eeprom_data[0x0a] = 0x00  # ??? set to 01 does not affect poor environment
        _eeprom_data[0x0b] = 0x00  # ??? set to 01 does not affect poor environment
        _eeprom_data[0x0c] = 0x00  # range offset hi byte (# feet * 0x64)
        _eeprom_data[0x0d] = 0xdc  # range offset lo byte
        _eeprom_data[0x0e] = 0x00  # speed offset hi byte (mph * 10)
        _eeprom_data[0x0f] = 0x00  # speed offset lo byte

        _eeprom_data[0x10] = 0x00  # absolute minimum speed hi byte (mph * 10) -- set to 5
        _eeprom_data[0x11] = 0x32  # absolute minimum speed lo byte
        _eeprom_data[0x12] = 0x00  # minimum speed hi byte (mph * 10) -- set to 5
        _eeprom_data[0x13] = 0x32  # minimum speed
        _eeprom_data[0x14] = 0x07  # maximum speed hi byte (mph * 10) -- set to 201
        _eeprom_data[0x15] = 0xda  # maximum speed lo byte (mph * 10)
        _eeprom_data[0x16] = 0x00  # ??? set to 01 does not affect poor environment
        _eeprom_data[0x17] = 0x00  # ??? set to 01 does not affect poor environment
        _eeprom_data[0x18] = 0x03  # minimum range hi byte (feet * 0x64) -- set to 5
        _eeprom_data[0x19] = 0xe8  # minimum range lo byte
        _eeprom_data[0x1a] = 0x00  # ??? set to 01 does not affect poor environment
        _eeprom_data[0x1b] = 0x00  # ??? set to 01 does not affect poor environment
        _eeprom_data[0x1c] = 0x27  # max range hi byte (feet * 0x64) -- set to 100
        _eeprom_data[0x1d] = 0x10  # max range lo byte
        _eeprom_data[0x1e] = 0x00  # delta speed KPH (kph * 10) -- set to 3
        _eeprom_data[0x1f] = 0x1e  # delta speed KPH

        _eeprom_data[0x20] = 0x4b  # baud rate hi byte  19200=>4b, 9600=>25, 4800=>12 is literally the baud rate
        _eeprom_data[0x21] = 0x00  # baud rate lo byte  19200=>00, 9600=>80, 4800=>c0
        _eeprom_data[0x22] = 0x00  # continuity value MSB
        _eeprom_data[0x23] = 0x0a  # continuity value LSB (10)
        _eeprom_data[0x24] = 0x00  # minimum number MSB
        _eeprom_data[0x25] = 0x2b  # minimum number LSB (43)
        _eeprom_data[0x26] = 0x00  # maximum number MSB
        _eeprom_data[0x27] = 0xb4  # maximum number LSB (180)
        _eeprom_data[0x28] = 0x00  # display lock timeout MSB (0)
        _eeprom_data[0x29] = 0x00  # display lock timeout LSB (0) # seconds * 20
        _eeprom_data[0x2a] = 0x00  # sleep timeout MSB (0)
        _eeprom_data[0x2b] = 0x00  # sleep timeout LSB (0)  # seconds * 20
        _eeprom_data[0x2c] = 0x00  # power off timeout MSB (0)
        _eeprom_data[0x2d] = 0x00  # Power off timeout LSB (0) # seconds * 20
        _eeprom_data[0x2e] = 0x00  # gun fire timeout MSB (0)
        _eeprom_data[0x2f] = 0x00  # gun fire timeout LSB (0) # seconds * 25 (!)

        _eeprom_data[0x30] = 0x01  # filter # 1 min pulse width MSB (0x01)
        _eeprom_data[0x31] = 0x1e  # filter # 1 min pulse width MSB (0x14) 28.6 ns
        _eeprom_data[0x32] = 0x01  # filter
        _eeprom_data[0x33] = 0xa0  # filter
        _eeprom_data[0x34] = 0x00  # filter
        _eeprom_data[0x35] = 0x02  # filter
        _eeprom_data[0x36] = 0x78  # filter
        _eeprom_data[0x37] = 0xd0  # filter
        _eeprom_data[0x38] = 0x01  # filter
        _eeprom_data[0x39] = 0x68  # filter
        _eeprom_data[0x3a] = 0x01  # filter
        _eeprom_data[0x3b] = 0x4f  # filter
        _eeprom_data[0x3c] = 0x00  # filter
        _eeprom_data[0x3d] = 0x02  # filter
        _eeprom_data[0x3e] = 0x26  # filter
        _eeprom_data[0x3f] = 0xc8  # filter

        _eeprom_data[0x40] = 0x02  # filter
        _eeprom_data[0x41] = 0x05  # filter
        _eeprom_data[0x42] = 0x01  # filter
        _eeprom_data[0x43] = 0xab  # filter
        _eeprom_data[0x44] = 0x00  # filter
        _eeprom_data[0x45] = 0x05  # filter
        _eeprom_data[0x46] = 0x09  # filter
        _eeprom_data[0x47] = 0x10  # filter
        _eeprom_data[0x48] = 0x05  # filter # 4 min pulse width MSB (0x05) (140 nsec)
        _eeprom_data[0x49] = 0x78  # filter # 4 min pulse width LSB (0x78 = 140 nsec)
        _eeprom_data[0x4a] = 0x2c  # filter
        _eeprom_data[0x4b] = 0x24  # filter
        _eeprom_data[0x4c] = 0x00  # filter # 4 offset MSB
        _eeprom_data[0x4d] = 0xf1  # filter
        _eeprom_data[0x4e] = 0x64  # filter
        _eeprom_data[0x4f] = 0xd9  # filter # 4 offset LSB

        _eeprom_data[0x50] = 0x00  # range variance minimum 1 MSB
        _eeprom_data[0x51] = 0x00  # range variance minimum 1 LSB (0) feet * 10.
        _eeprom_data[0x52] = 0xe9  # range variance
        _eeprom_data[0x53] = 0x4c  # range variance
        _eeprom_data[0x54] = 0x66  # range variance
        _eeprom_data[0x55] = 0x2a  # range variance
        _eeprom_data[0x56] = 0x01  # range variance
        _eeprom_data[0x57] = 0xf4  # range variance
        _eeprom_data[0x58] = 0xe9  # range variance
        _eeprom_data[0x59] = 0x4c  # range variance
        _eeprom_data[0x5a] = 0x66  # range variance
        _eeprom_data[0x5b] = 0x2a  # range variance
        _eeprom_data[0x5c] = 0x03  # range variance
        _eeprom_data[0x5d] = 0xe8  # range variance
        _eeprom_data[0x5e] = 0xe9  # range variance
        _eeprom_data[0x5f] = 0x4c  # range variance

        _eeprom_data[0x60] = 0x66  # range variance
        _eeprom_data[0x61] = 0x2a  # range variance
        _eeprom_data[0x62] = 0x0b  # range variance
        _eeprom_data[0x63] = 0xb8  # range variance
        _eeprom_data[0x64] = 0xe9  # range variance
        _eeprom_data[0x65] = 0x4c  # range variance
        _eeprom_data[0x66] = 0x66  # range variance
        _eeprom_data[0x67] = 0x2a  # range variance
        _eeprom_data[0x68] = 0x1b  # range variance maximum 4 MSB
        _eeprom_data[0x69] = 0x58  # range variance minimum 4 LSB (700) feet * 10.
        _eeprom_data[0x6a] = 0xe9  # float value variance 4 MSB
        _eeprom_data[0x6b] = 0x4c  # range variance
        _eeprom_data[0x6c] = 0x66  # range variance
        _eeprom_data[0x6d] = 0x2a  # float value variance 4 LSB (0.199999998765385)
        _eeprom_data[0x6e] = 0x00  # range variance maximum 5 MSB
        _eeprom_data[0x6f] = 0x00  # range variance maximum 5 LSB

        _eeprom_data[0x70] = 0x00  # range variance
        _eeprom_data[0x71] = 0x00  # range variance
        _eeprom_data[0x72] = 0x00  # range variance
        _eeprom_data[0x73] = 0x00  # range variance
        _eeprom_data[0x74] = 0x00  # range variance
        _eeprom_data[0x75] = 0x00  # range variance
        _eeprom_data[0x76] = 0x00  # range variance
        _eeprom_data[0x77] = 0x00  # range variance
        _eeprom_data[0x78] = 0x00  # range variance
        _eeprom_data[0x79] = 0x00  # range variance
        _eeprom_data[0x7a] = 0x00  # range variance
        _eeprom_data[0x7b] = 0x00  # range variance
        _eeprom_data[0x7c] = 0x00  # range variance
        _eeprom_data[0x7d] = 0x00  # range variance
        _eeprom_data[0x7e] = 0x00  # range variance
        _eeprom_data[0x7f] = 0x00  # range variance

        _eeprom_data[0x80] = 0x00  # range variance
        _eeprom_data[0x81] = 0x00  # range variance
        _eeprom_data[0x82] = 0x00  # range variance
        _eeprom_data[0x83] = 0x00  # range variance
        _eeprom_data[0x84] = 0x00  # range variance
        _eeprom_data[0x85] = 0x00  # range variance
        _eeprom_data[0x86] = 0x00  # range variance
        _eeprom_data[0x87] = 0x00  # range variance
        _eeprom_data[0x88] = 0x00  # range variance
        _eeprom_data[0x89] = 0x00  # range variance
        _eeprom_data[0x8a] = 0x00  # range variance
        _eeprom_data[0x8b] = 0x00  # end of range/variance data
        _eeprom_data[0x8c] = 0x83
        _eeprom_data[0x8d] = 0x3a
        _eeprom_data[0x8e] = 0xf9
        _eeprom_data[0x8f] = 0x28

        _eeprom_data[0x90] = 0x00  # HUD [0] (0)
        _eeprom_data[0x91] = 0x50  # Reticle [0] (80)
        _eeprom_data[0x92] = 0x00  # HUD [1] (0)
        _eeprom_data[0x93] = 0x52  # Reticle [0] (82)
        _eeprom_data[0x94] = 0x01  # HUD [2] (1)
        _eeprom_data[0x95] = 0x54  # Reticle [2] (84)
        _eeprom_data[0x96] = 0x02  # HUD [2] (2)
        _eeprom_data[0x97] = 0x55  # Reticle [3] (85)
        _eeprom_data[0x98] = 0x03  # HUD [3] (3)
        _eeprom_data[0x99] = 0x57  # Reticle [4] (87)
        _eeprom_data[0x9a] = 0x05  # HUD [4] (5)
        _eeprom_data[0x9b] = 0x58  # Reticle [4] (88)
        _eeprom_data[0x9c] = 0x09  # HUD [5] (9)
        _eeprom_data[0x9d] = 0x5b  # Reticle [5] (91)
        _eeprom_data[0x9e] = 0x0f  # HUD [6] (15)
        _eeprom_data[0x9f] = 0x5e  # Reticle [6] (94)

        _eeprom_data[0xa0] = 0x58  # --> brightness 7: hud bright 6: 5b, 5: 58, 4: 57, 3: 55, 2: 54, 1: 52, 0: 50 (58)
        _eeprom_data[0xa1] = 0x05  # HUD brightness level (5)
        _eeprom_data[0xa2] = 0x05  # piezo volume level (5)
        _eeprom_data[0xa3] = 0x01  # units. 01: english, 02: SI, 03: knots/feet, 04: knots/meters, 05: feet/sec, 06: meters/sec
        _eeprom_data[0xa4] = 0x03  # speed type. 01: approaching. 02: receding, 03: both
        _eeprom_data[0xa5] = 0x3c  # update rate (60)
        _eeprom_data[0xa6] = 0x00  # operating mode: 00: speed, 01: RTR, 03: range
        _eeprom_data[0xa7] = 0x03  # set to 03 when above is 0, literally  (-(eeprom[0xa6] != '\0') & 0xfdU) + 3;
        _eeprom_data[0xa8] = 0x00  # display lock enable when 01
        _eeprom_data[0xa9] = 0x02  # speed packet op code: SPD2: 01, SPD3: 00, SPD4: 02
        _eeprom_data[0xaa] = 0x00  # use first speed delta, value is 01 when selected
        _eeprom_data[0xab] = 0x01  # reset sample window when 01.
        _eeprom_data[0xac] = 0x14  # prefilter count
        _eeprom_data[0xad] = 0x0a  # good data % (10)
        _eeprom_data[0xae] = 0x02  # number of speeds averaged.
        _eeprom_data[0xaf] = 0x01  # clock start compensation, 1 is on, 0 is off, other bits do not affect poor env mode

        _eeprom_data[0xb0] = 0x00  # CFAR toggle, 1 is on, 0 is off, other bits do not affect poor env mode
        _eeprom_data[0xb1] = 0x0a  # min range set (single byte value?)  10 feet
        _eeprom_data[0xb2] = 0x40  # 64 what?
        _eeprom_data[0xb3] = 0x14  # range filter #1, feet -- this is 20
        _eeprom_data[0xb4] = 0x3c  # range filter #2, feet -- this is 80
        _eeprom_data[0xb5] = 0x82  # bit-mapped options: 1000 0010
                                # 7 10000000 short serial output
                                # 6 01000000 not used? tested, does not affect poor env.
                                # 5 00100000 not used? tested, does not affect poor env.
                                # 4 00010000 Italian text
                                # 3 00001000 camera mode
                                # 2 00000100 French text
                                # 1 00000010 disable checksum on lcd
                                # 0 00000001 enable calculate tac calibrate window (does not stay on)
        _eeprom_data[0xb6] = 0x50  # data quality % literal value.
        eeprom_checksum = 0
        for address in range(0, 0xb7):
            eeprom_checksum = (eeprom_checksum + _eeprom_data[address]) & 0x00ff
        _eeprom_data[0xb7] = eeprom_checksum  # CHECKSUM!
    return _eeprom_data


def buffer_to_hexes(buffer):
    return ' '.join('{:02x}'.format(b) for b in buffer)


def hexdump_buffer(buffer):
    result = ''
    hex_bytes = ''
    printable = ''
    offset = 0
    ofs = '{:04x}'.format(offset)
    for b in buffer:
        hex_bytes += '{:02x} '.format(b)
        printable += chr(b) if 32 <= b <= 126 else '.'
        offset += 1
        if len(hex_bytes) >= 48:
            result += ofs + '  ' + hex_bytes + '  ' + printable +'\n'
            hex_bytes = ''
            printable = ''
            ofs = '{:04x}'.format(offset)
    if len(hex_bytes) > 0:
        hex_bytes += ' ' * 47
        hex_bytes = hex_bytes[0:47]
        result += ofs + '  ' + hex_bytes + '   ' + printable + '\n'
    return result


def dump_buffer(name, buffer, dump_all=False):
    if len(buffer) < 5:
        dump_all = True
    if dump_all:
        print('{} message {}'.format(name, buffer_to_hexes(buffer)))
    else:
        print('{} payload {}'.format(name, buffer_to_hexes(buffer[2:-2])))


def _build_message(buffer):
    msg = bytearray()
    msg.append(START_OF_MESSAGE)
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


def _unescape_message(message):
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
    command = None
    result = None
    if len(buffer) < 5:
        print('message too short: {}: {}'.format(len(buffer), buffer_to_hexes(buffer)))
        return command, result
    if not validate_checksum('tx', buffer):
        return command, result

    buffer = _unescape_message(buffer)
    command = buffer[2]
    if command == CMD_EXIT_REMOTE:
        if verbosity >= 4:
            print('tx CMD_EXIT_REMOTE')
    elif command == CMD_WHO_ARE_YOU:
        if verbosity >= 4:
            print('tx CMD_WHO_ARE_YOU')
    elif command == CMD_READ_RAM:
        if verbosity >= 4:
            print('tx CMD_READ_RAM: {}'.format(buffer_to_hexes(buffer)))
    elif command == CMD_ENABLE_REMOTE:
        if verbosity >= 4:
            print('tx CMD_ENABLE_REMOTE')
    elif command == CMD_TOGGLE_LASER:
        if verbosity >= 4:
            print('tx CMD_TOGGLE_LASER (on/off?)')
    elif command == CMD_SET_MODE:
        sub_command = buffer[3]
        result = sub_command
        if sub_command == MODE_SPEED:
            if verbosity >= 4:
                print('tx CMD_SET_MODE Speed')
        elif sub_command == MODE_RTR:
            if verbosity >= 4:
                print('tx CMD_SET_MODE RTR')
        elif sub_command == MODE_RANGE:
            if verbosity >= 4:
                print('tx CMD_SET_MODE_RANGE Set mode Range')
        else:
            print('tx CMD_SET_MODE_RANGE unknown mode {:02x}'.format(sub_command))
    elif command == CMD_READ_EEPROM:
        addr = buffer[3]
        if verbosity > 4:
            print('tx CMD_READ_EEPROM address {:02x}'.format(addr))
            result = addr
    elif command == CMD_WRITE_EEPROM:
        if buffer[3] == 0x80:
            addr = buffer[4]
            data = buffer[5]
            result = (addr, data)
            if verbosity > 4:
                print('tx CMD_WRITE_EEPROM address {:02x} data {:02x}'.format(addr, data))
                if addr == 0xb7:  # checksum byte
                    checksum = 0
                    for ca in range(0, 0xb7):
                        checksum = (checksum + _eeprom_data[ca]) & 0x00ff
                    print('   calculated checksum {:02x}, checksum={:02x}'.format(checksum, data))
        else:
            print('tx unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer)))
    elif command == CMD_RESET:
        if verbosity >= 4:
            print('tx CMD_RESET')
    else:
        print('tx unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer)))
        command = None
    return command, result


def process_rx_buffer(buffer, verbosity=5):
    result = None
    command = None
    if len(buffer) < 5:
        print('message too short: {}: {}'.format(len(buffer), buffer_to_hexes(buffer)))
        return command, result
    if not validate_checksum('rx', buffer):
        return command, result
    buffer = _unescape_message(buffer)
    command = buffer[2]
    if command == CMD_EXIT_REMOTE:
        if verbosity > 4:
            print('rx ACK CMD_EXIT_REMOTE')
        result = 'ACK CMD_EXIT_REMOTE'
    elif command == CMD_READ_RAM:
        print('rx CMD_READ_RAM response: {}'.format(buffer_to_hexes(buffer)))
        result = buffer[3:-2]
    elif command == CMD_ENABLE_REMOTE:
        if verbosity > 4:
            print('rx ACK CMD_ENABLE_REMOTE')
        result = 'ACK CMD_ENABLE_REMOTE'
    elif command == CMD_TOGGLE_LASER:
        if verbosity > 4:
            print('rx ACK CMD_TOGGLE_LASER (off)')
    elif command == CMD_SET_MODE:
        sub_command = buffer[3]
        result = sub_command
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
        result = (addr, data)
        if verbosity > 4:
            print('rx CMD_READ_EEPROM response address {:02x} data {:02x}'.format(addr, data))
    elif command == CMD_WRITE_EEPROM:
        sub_command = buffer[3]
        if sub_command == 0x00:
            addr = buffer[4]
            result = addr
            if verbosity > 4:
                print('rx CMD_WRITE_EEPROM response {:02x}'.format(addr))
        else:
            print('rx CMD_WRITE_EEPROM response unhandled subcommand {:02x} in {}'.format(sub_command,
                                                                                          buffer_to_hexes(buffer)))
    elif command == CMD_READING:
        if buffer[8] == 0x01:
            speed = buffer[4] if buffer[4] != 0xff else 0
            rng = (buffer[6] + 256 * buffer[7]) / 10.0
            if verbosity > 2:
                print('rx CMD_READING: {} : {:5.1f} feet {} mph'.format(buffer_to_hexes(buffer[3:-2]), rng, speed))
            result = (buffer_to_hexes(buffer[3:-2]), rng, speed)
        else:
            warn = 'CMD_READING: {}'.format(buffer_to_hexes(buffer[3:-2]))
            print('rx ' + warn)
            result = warn
    elif command == CMD_INIT_SPD23:
        start = 3
        while buffer[start] < 0x20:
            start += 1
        stuff = buffer[start:-2]
        if verbosity > 3:
            print('rx CMD_INIT_SPD23 text payload follows:')
            print(stuff)
        result = stuff
    elif command == CMD_INIT_SPD4:
        if verbosity > 3:
            print('rx CMD_INIT_SPD4 text payload follows:')
            print(hexdump_buffer(buffer[3:-2]))
        result = str(buffer[3:-2])
    else:
        warn = 'unhandled command {:02x} in {}'.format(command, buffer_to_hexes(buffer))
        print('rx {}'.format(warn))
        result = warn
    return command, result


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
                            msg.append(b)
                            escaped = True
                    else:
                        expected -= 1
                        if escaped:
                            escaped = False
                            msg.append(b)
                        else:
                            msg.append(b)
                            if b == END_OF_MESSAGE:
                                if expected != 0:
                                    print('    **** expected = {}'.format(expected))
                                    if len(msg) != expect:
                                        msg_len = msg[1] + 4
                                        fmt = '   received {} but expected {}, message claims {} message {} '
                                        print(fmt.format(len(msg), expect, msg_len, buffer_to_hexes(msg)))
                                # print('   called with {} timeouts, {} left'.format(timeouts, timeouts_left))
                                return msg
        else:
            timeouts_left -= 1
            # print('   still listening... received {} {} wanted {} left'.format(len(msg), expect, timeouts_left))
    print('   timed out! called with {} timeouts, {} left'.format(timeouts, timeouts_left), file=sys.stderr)
    return msg


def validate_checksum(name, buffer):
    if len(buffer) < 5:
        print('buffer is too short to checksum: {}'.format(buffer_to_hexes(buffer)))
        return False
    buffer = _unescape_message(buffer)
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


def send_cmd(port, msg, verbosity=0):
    cmd = _build_message(msg)
    process_tx_buffer(cmd, verbosity=verbosity)
    port.write(cmd)


def enable_remote(port, verbosity=0):
    send_cmd(port, [CMD_ENABLE_REMOTE], verbosity=verbosity)
    return 5


def read_ee(port, address, verbosity=0):
    send_cmd(port, [CMD_READ_EEPROM, address], verbosity=verbosity)
    return 8


def exit_remote(port, verbosity=0):
    send_cmd(port, [CMD_EXIT_REMOTE], verbosity=verbosity)
    return 5


def reset(port, verbosity=0):
    send_cmd(port, [CMD_RESET], verbosity=verbosity)
    return 160


def set_mode(port, mode, verbosity=0):
    send_cmd(port, [CMD_SET_MODE, mode], verbosity=verbosity)
    return 5


def toggle_laser(port, verbosity=0):
    send_cmd(port, [CMD_TOGGLE_LASER], verbosity=verbosity)
    return 5


def write_ee(port, address, data, verbosity=0):
    send_cmd(port, [CMD_WRITE_EEPROM, 0x80, address, data], verbosity=verbosity)
    return 8


def receive_response(port, expect=16, timeouts=1, verbosity=5):
    if expect > 0:
        msg = receive_message(port, expect=expect, timeouts=timeouts)
        if len(msg) == 0:
            return None, None
        else:
            return process_rx_buffer(msg, verbosity=verbosity)
    else:
        return None, None

