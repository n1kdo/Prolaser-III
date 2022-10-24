
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


def dump_buffer(name, buffer, dump_all=False):
    if len(buffer) < 5:
        dump_all = True
    if dump_all:
        print('{} message {}'.format(name, buffer_to_hexes(buffer)))
    else:
        print('{} payload {}'.format(name, buffer_to_hexes(buffer[2:-2])))

