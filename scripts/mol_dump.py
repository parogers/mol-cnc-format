#!/usr/bin/env python3

import sys
import io


# LEETRO float: [eeeeeeee|smmmmmmm|mmmmmmm0|00000000]
def read_float(file):
    v = 0
    vExp = 0
    vMnt = 0
    vSgn = 1
    b = file.read(4)
    if not b:
        raise IOError()

    vExp = b[3]

    b1 = b[1]
    if b1<0: b1 = 256+b1
    b2 = b[2]
    if b2<0: b2 = 256+b2
    if b2>127: b2 = b2 - 128
    vMnt = b1/2 + 128*b2 + 0x4000

    if b[2]<0: vSgn = -1

    v = (vMnt/16384.0)*(2**vExp)
    return v


def read_uword(file):
    v = 0
    b = file.read(4)
    if not b:
        raise IOError()

    for i in [3, 2, 1, 0]:
        d = b[i]
        if d<0: d = 256+d
        v = v * 256 + d
    return v


def read_word(file):
    v = read_uword(file)
    if v>=0x80000000:
        v = v - 0x80000000
        v = -0x80000000 + v
    return v



def read_unknown_command(file, cmd):
    num_words = cmd >> 24
    if num_words == 0x80:
        num_words = read_uword(file)
    # file.seek(file.tell()+4*nWords)
    for n in range(num_words):
        # value = read_word(file)
        data = file.read(4)
        value_word = read_word(io.BytesIO(data))
        value_float = read_float(io.BytesIO(data))
        print('->', value_word, value_float)
    print()


def dump_file(file):
    print('##################')
    print('# Header section #')
    print('##################')
    print()
    file_size = read_uword(file) # 0x00
    num_motion_blocks = read_uword(file)	# 0x04
    dll_version = read_word(file)	# 0x08 (DLL version)
    file_format_version = read_word(file)	# 0x0c (file format version?)
    assert file_format_version == 1
    unknown1 = read_word(file)	# 0x10 (related to number of commands)
    laser_position = read_word(file)	# 0x14 (laser position relative to bounding box - four booleans)
    x_max = read_word(file)	# 0x18
    y_max = read_word(file)	# 0x1c
    x_min = read_word(file)	# 0x20
    y_min = read_word(file)	# 0x24
    unknown2 = read_word(file) # 0x28
    unknown3 = read_word(file) # 0x2c
    while file.tell() < 0x00000070:
        assert read_word(file) == 0
    config_start = read_word(file) * 512	# 0x70
    test_start = read_word(file) * 512	# 0x74
    cutbox_start = read_word(file) * 512	# 0x78
    cut_start = read_word(file) * 512	# 0x7c

    while file.tell() < config_start:
        assert read_uword(file) == 0

    print(num_motion_blocks)
    print(unknown1, unknown2, unknown3)

    px = 0
    py = 0
    scale = 0

    print('##################')
    print('# Config section #')
    print('##################')
    print()

    file.seek(config_start)
    while True:
        cmd_pos = file.tell()
        cmd = read_uword(file)
        if cmd in (0x03026000, 0x03026040): # move to first cut
            read_uword(file)
            px = read_word(file)
            py = read_word(file)
        elif cmd == 0x03000e46: # set stepper scale
            scale = read_float(file)
            read_float(file)
            read_float(file) # z scale
        elif cmd == 0x00200648:
            print('DONE')
            break
        elif cmd == 0x80600148:
            # 6-param version according to london hackerspace
            # arg1 is unknown, but repeats in 'unknown 11'
            # arg2 is the start speed for all head movements as described in the settings
            # arg3 is the maximum speed for moving around "quickly"
            # arg4 is the acceleration value to get to the above speed (space acc)
            # arg5 is the value for acceleration from the settings
            # arg6 is the acceleration when going from vector to vector
            print('axis related command at', hex(cmd_pos))
            num_words = read_word(file)
            assert num_words in (2, 6)
            for n in range(num_words):
                if n == 0:
                    value = read_word(file)
                else:
                    value = read_float(file)
                print('->', value)
            print()
        else:
            print('skipping', hex(cmd), hex(cmd_pos))
            read_unknown_command(file, cmd)

    while file.tell() < cut_start:
        cmd_pos = file.tell()
        cmd = read_uword(file)
        print('unknown command', hex(cmd), hex(cmd_pos))
        read_unknown_command(file, cmd)

    assert scale, 'expecting file to define scale'

    print('start at', px, py, scale)
    print('bounds', x_min, x_max, y_min, y_max)
    print()

    print('###################')
    print('# Artwork section #')
    print('###################')
    print()

    assert file.tell() == cut_start

    laser_on = 0
    file.seek(cut_start)
    while True:
        cmd_pos = file.tell()
        cmd = read_uword(file)
        if cmd == 0x80000946: # begin motion block
            print('motion block')
            value = read_uword(file)
        elif cmd == 0x01000606: # switch laser
            laser_on = read_uword(file)
            print('laser is', laser_on)
        elif cmd == 0x03000301: # set speeds
            speed_min = read_float(file) #/scale # float: min
            speed_max = read_float(file) #/scale # float: max
            accel = read_float(file) # float: accel
            # print('speed', spdMin, spdMax)
        elif cmd == 0x03026000: # move relative
            axis = read_uword(file)
            dx = read_word(file)
            dy = read_word(file)
            px = px + dx
            py = py + dy
            print('move to', px, py)
        elif cmd == 0x01400048: # end of subroutine
            read_word(file) # subroutine number
            print('DONE')
            break
        elif cmd == 0x1004601:
            value = read_word(file)
            print('move/power-related command:', value, hex(value))
        else:
            print('skipping', hex(cmd), hex(cmd_pos))
            read_unknown_command(file, cmd)

    while True:
        cmd_pos = file.tell()
        try:
            cmd = read_uword(file)
        except IOError:
            break
        print('unknown command', hex(cmd), hex(cmd_pos))
        read_unknown_command(file, cmd)


def main():
    assert len(sys.argv) == 2, 'usage: mol_dump.py FILE.MOL'
    with open(sys.argv[1], 'rb') as file:
        dump_file(file)


if __name__ == '__main__':
    main()
