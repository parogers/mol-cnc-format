#!/usr/bin/env python3

from collections import Counter
import sys
import io


commands = []

def read_command(file):
    cmd = read_uword(file)
    if cmd is not None:
        commands.append(cmd)
    return cmd


# LEETRO float: [eeeeeeee|smmmmmmm|mmmmmmm0|00000000]
def read_float(file):
    v = 0
    vExp = 0
    vMnt = 0
    vSgn = 1
    b = file.read(4)
    if not b:
        return None

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
        return None

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
    if cmd == 0:
        print('skipping no-op')
        print()
        return
    cmd_pos = file.tell() - 4
    print('unknown command', hex(cmd), 'at', hex(cmd_pos))
    num_words = cmd >> 24
    if num_words == 0x80:
        num_words = read_uword(file)
    for n in range(num_words):
        data = file.read(4)
        value_word = read_word(io.BytesIO(data))
        value_float = read_float(io.BytesIO(data))
        print('->', value_word, value_float)
    print()


def read_motion_block(file):
    num_words = read_uword(file)
    end_pos = file.tell() + 4*num_words

    print()
    print('motion block length:', num_words)
    print()
    while file.tell() < end_pos:
        cmd = read_command(file)
        if cmd == 0x03026000: # move relative
            axis = read_uword(file) # lower two nibbles (values 3, 4)
            dx = read_word(file)
            dy = read_word(file)
            # px = px + dx
            # py = py + dy
            print('move by', dx, dy, hex(axis))
        elif cmd == 0x1000b06:
            read_unknown_command(file, cmd)
        elif cmd == 0x1000806:
            read_unknown_command(file, cmd)
        elif cmd == 0x01000606: # switch laser
            laser_on = read_uword(file)
            print('laser is', laser_on)
        elif cmd == 0x1004601:
            value = read_word(file)
            print('move/power-related command:', value, hex(value))
        elif cmd == 0x03000301: # set speeds
            speed_min = read_float(file) #/scale # float: min
            speed_max = read_float(file) #/scale # float: max
            accel = read_float(file)
            print('set speeds', speed_min, speed_max, accel)
        else:
            raise Exception(f'unknown command: {hex(cmd)}')


def read_subroutine(file):
    laser_on = 0
    while True:
        cmd_pos = file.tell()
        cmd = read_command(file)

        if cmd == 0x1300048:
            section = read_uword(file)
            print('subroutine', section)
            print()
        elif cmd == 0x80000946:
            read_motion_block(file)
        elif cmd == 0x01400048: # end of subroutine
            section = read_word(file) # subroutine number
            print('done subroutine', section)
            break
        elif cmd == 0x80600148:
            print('motion settings', hex(cmd), 'at', hex(cmd_pos))
            read_motion_settings_command(file, cmd)
        else:
            read_unknown_command(file, cmd)
    print()


def read_motion_settings_command(file, cmd):
    # 6-param version according to london hackerspace
    # arg1 is unknown, but repeats in 'unknown 11'
    # arg2 is the start speed for all head movements as described in the settings
    # arg3 is the maximum speed for moving around "quickly"
    # arg4 is the acceleration value to get to the above speed (space acc)
    # arg5 is the value for acceleration from the settings
    # arg6 is the acceleration when going from vector to vector
    num_words = read_word(file)
    assert num_words in (2, 6)
    for n in range(num_words):
        if n == 0:
            value = read_word(file)
        else:
            value = read_float(file)
        print('->', value)
    print()


def dump_file(file):
    print('##################')
    print('# Header section #')
    print('##################')
    print()
    file_size = read_uword(file) # 0x00
    unknown1 = read_uword(file)	# 0x04 (related to number of motion blocks)
    dll_version = read_word(file)	# 0x08 (DLL version)
    file_format_version = read_word(file)	# 0x0c (file format version?)
    assert file_format_version == 1
    unknown2 = read_word(file)	# 0x10 (related to number of commands)
    laser_position = read_word(file)	# 0x14 (laser position relative to bounding box - four booleans)
    x_max = read_word(file)	# 0x18
    y_max = read_word(file)	# 0x1c
    x_min = read_word(file)	# 0x20
    y_min = read_word(file)	# 0x24
    unknown3 = read_word(file) # 0x28
    unknown4 = read_word(file) # 0x2c
    while file.tell() < 0x00000070:
        assert read_word(file) == 0
    config_start = read_word(file) * 512	# 0x70
    test_start = read_word(file) * 512	# 0x74
    cutbox_start = read_word(file) * 512	# 0x78
    cut_start = read_word(file) * 512	# 0x7c

    while file.tell() < config_start:
        assert read_uword(file) == 0

    print('unknowns:', unknown1, unknown2, unknown3, unknown4)
    print()

    px = 0
    py = 0

    print('##################')
    print('# Config section #')
    print('##################')
    print()

    file.seek(config_start)
    while True:
        cmd_pos = file.tell()
        cmd = read_command(file)
        if cmd == 0x200548:
            # Probably start of config section (appears at 0x200)
            pass
        elif cmd in (0x03026000, 0x03026040): # move to first cut
            value = read_uword(file)
            px = read_word(file)
            py = read_word(file)
            print('first cut', value, px, py)
        elif cmd == 0x03000e46:
            # Set stepper scale (steps/mm)
            x_scale = read_float(file)
            y_scale = read_float(file)
            z_scale = read_float(file)
            print('scale', hex(cmd), x_scale, y_scale, z_scale)
        elif cmd == 0x00200648:
            print('DONE')
            break
        elif cmd == 0x80600148:
            print('motion settings', hex(cmd), 'at', hex(cmd_pos))
            read_motion_settings_command(file, cmd)
        else:
            read_unknown_command(file, cmd)

    while file.tell() < test_start:
        cmd = read_command(file)
        read_unknown_command(file, cmd)

    print('start at', px, py, x_scale, y_scale)
    print('bounds', x_min, x_max, y_min, y_max)
    print()

    print('################')
    print('# Test section #')
    print('################')
    print()
    file.seek(test_start)
    read_subroutine(file)

    while file.tell() < cutbox_start:
        cmd = read_command(file)
        read_unknown_command(file, cmd)

    print('##################')
    print('# Cutbox section #')
    print('##################')
    print()
    file.seek(cutbox_start)
    read_subroutine(file)

    while file.tell() < cut_start:
        cmd = read_command(file)
        read_unknown_command(file, cmd)

    print('###################')
    print('# Artwork section #')
    print('###################')
    print()
    file.seek(cut_start)
    read_subroutine(file)

    while True:
        cmd = read_command(file)
        if cmd is None:
            break
        read_unknown_command(file, cmd)


def main():
    assert len(sys.argv) == 2, 'usage: mol_dump.py FILE.MOL'
    with open(sys.argv[1], 'rb') as file:
        dump_file(file)

    print('############################')
    print('# Summary of commands used #')
    print('############################')
    print()

    for cmd, count in Counter(commands).most_common():
        print(f'{hex(cmd):15s} {count}')


if __name__ == '__main__':
    main()
