#!/usr/bin/env python3

from collections import Counter
import sys
import io


commands = []
unknown_commands = set()

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
    if v is None:
        return None
    if v>=0x80000000:
        v = v - 0x80000000
        v = -0x80000000 + v
    return v


def read_num_words(file):
    value = read_uword(file)
    # What do the upper two bytes represent? (they're usually zero)
    return value & 0xFFFF


def read_unknown_command(file, cmd):
    if cmd == 0:
        print('skipping no-op')
        print()
        return
    unknown_commands.add(cmd)
    cmd_pos = file.tell() - 4
    print(f'unknown command {hex(cmd)} (at {hex(cmd_pos)})')
    num_words = cmd >> 24
    if num_words == 0x80:
        num_words = read_num_words(file)
        print('variable length words:', num_words)
    for n in range(num_words):
        data = file.read(4)
        if not data:
            raise Exception('unexpected end of file')
        value_word = read_word(io.BytesIO(data))
        value_uword = read_uword(io.BytesIO(data))
        value_float = read_float(io.BytesIO(data))
        print('->', hex(value_uword), value_uword, value_word, value_float)
    print()


def read_motion_block(file):
    moves = 0
    num_words = read_uword(file)
    end_pos = file.tell() + 4*num_words
    print()
    print('motion block length:', num_words)
    print()
    while file.tell() < end_pos:
        cmd = read_command(file)
        if cmd == 0x03026000: # move relative
            # X axis is 4
            # Y axis is 3
            axis = read_uword(file) # lower two bytes (values 3, 4)
            dx = read_word(file)
            dy = read_word(file)
            # px = px + dx
            # py = py + dy
            print('move by', dx, dy, hex(axis))
            moves += 1
        elif cmd == 0x1000b06:
            # Blower control (lowest byte is on/off, second lowest is register/port/IO address?)
            value = read_uword(file)
            print('blower control:', hex(value))
            print()
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
    return moves


def read_subroutine(file, scale=None, origin_x=0, origin_y=0):
    laser_on = 0
    moves = 0
    x_pos = origin_x
    y_pos = origin_y
    while True:
        cmd_pos = file.tell()
        cmd = read_command(file)
        if cmd == 0x1300048:
            section = read_uword(file)
            print('subroutine', section)
            print()
        elif cmd == 0x80000946:
            moves += read_motion_block(file)
        elif cmd == 0x01400048: # end of subroutine
            section = read_word(file) # subroutine number
            print('done subroutine', section)
            print('move commands:', moves)
            break
        elif cmd == 0x80600148:
            print('motion settings', hex(cmd), 'at', hex(cmd_pos))
            read_motion_settings_command(file, cmd)
        elif cmd == 0x5000e46:
            # Laser power and speed settings
            corner_power = read_word(file)
            max_power = read_word(file)
            cutting_start_speed = read_float(file)
            cutting_max_speed = read_float(file)
            unknown = read_uword(file)
            # assert unknown == 0, unknown # unknown
            print(
                'laser power',
                corner_power,
                max_power,
                cutting_start_speed,
                cutting_max_speed,
                unknown,
            )
            print()
        elif cmd == 0x7000e46:
            # Extended laser power and speed settings
            corner_power = read_word(file)
            max_power = read_word(file)
            corner_power2 = read_word(file) # (second head?)
            max_power2 = read_word(file) # (second head?)
            cutting_start_speed = read_float(file)
            cutting_max_speed = read_float(file)
            unknown = read_uword(file)
            # assert unknown == 0 # unknown
            print(
                'laser power (extended)',
                corner_power,
                max_power,
                corner_power2,
                max_power2,
                cutting_start_speed,
                cutting_max_speed,
                unknown,
            )
            print()
        elif cmd == 0x2004a41:
            axis = read_uword(file)
            value = read_uword(file)
            print('something about axis', axis, value)
            print()
        elif cmd == 0x1004b41:
            value = read_uword(file)
            print('something about axis', hex(value))
            print()

        elif cmd == 0x80000146:
            # TODO - are engrave related commands part of their own block? (ie
            # grouped together with another command like motion blocks)
            num_words = read_num_words(file)
            print(f'engrave line ({hex(cmd)}, num={num_words}, x={round(x_pos/scale, 2)}, y={round(y_pos/scale, 2)})')
            for n in range(num_words):
                amount_data = file.read(4)
                amount_word = read_uword(io.BytesIO(amount_data))
                amount_short1 = amount_word >> 16
                amount_short2 = amount_word & 0xFFFF
                # amount_float = read_float(io.BytesIO(amount_data))
                print(f'-> {amount_word:08x}', round(amount_short1/scale, 2), round(amount_short2/scale, 2))
            print()

        elif cmd == 0x2010040:
            # Related to engraving
            axis = read_uword(file)
            amount = read_word(file)
            print('step axis')
            if axis == 3:
                y_pos += amount
                print('-> y-axis by', amount, 'to', round(y_pos/scale, 2))
            else:
                x_pos += amount
                print('-> axis', axis, 'by', amount)
            print()

        elif cmd == 0x2014040:
            # Related to engraving
            axis = read_uword(file)
            amount = read_word(file)
            assert axis == 4
            print('sweep axis')
            print('-> axis', axis, 'from', round(x_pos/scale, 2), 'by', round(amount/scale, 2))
            print()
            x_pos += amount

        else:
            read_unknown_command(file, cmd)
    print()


def read_motion_settings_command(file, cmd):
    num_words = read_uword(file)
    if num_words == 2:
        value1 = read_word(file)
        value2 = read_float(file)
        assert value1 == int(value2)
        print('short settings', value1, value2)
        print()

    elif num_words == 6:
        # 6-param version according to london hackerspace
        # arg1 is unknown, but repeats in 'unknown 11'
        # arg2 is the start speed for all head movements as described in the settings
        # arg3 is the maximum speed for moving around "quickly"
        # arg4 is the acceleration value to get to the above speed (space acc)
        # arg5 is the value for acceleration from the settings
        # arg6 is the acceleration when going from vector to vector
        value = read_word(file) # subroutine number 603? (Matthias indicated so)
        start_speed = read_float(file)
        max_speed = read_float(file)
        accel = read_float(file)
        accel2 = read_float(file)
        accel3 = read_float(file)
        print('long settings', value, start_speed, max_speed, accel, accel2, accel3)
        print()

    else:
        raise Exception(f'unknown motion settings block ({num_words} words)')


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
    # unknown3 = read_word(file) # 0x28
    # unknown4 = read_word(file) # 0x2c
    unknown_data3 = file.read(4)
    unknown_data4 = file.read(4)

    while file.tell() < 0x00000070:
        assert read_word(file) == 0

    config_start = read_word(file) * 512	# 0x70
    test_start = read_word(file) * 512	# 0x74
    cutbox_start = read_word(file) * 512	# 0x78
    cut_start = read_word(file) * 512	# 0x7c

    while file.tell() < config_start:
        assert read_uword(file) == 0

    print('unknowns:', unknown1, unknown2)
    print(
        'unknown3:',
        hex(read_word(io.BytesIO(unknown_data3))),
        read_word(io.BytesIO(unknown_data3)),
        read_uword(io.BytesIO(unknown_data3)),
        read_float(io.BytesIO(unknown_data3)),
    )
    print(
        'unknown4:',
        hex(read_word(io.BytesIO(unknown_data4))),
        read_word(io.BytesIO(unknown_data4)),
        read_uword(io.BytesIO(unknown_data4)),
        read_float(io.BytesIO(unknown_data4)),
    )
    print()

    print('##################')
    print('# Config section #')
    print('##################')
    print()

    origin_x = 0
    origin_y = 0
    px = 0
    py = 0
    x_scale = 1
    y_scale = 1
    file.seek(config_start)
    while True:
        cmd_pos = file.tell()
        cmd = read_command(file)
        if cmd == 0x200548:
            # Probably start of config section (appears at 0x200)
            pass
        elif cmd in (0x03026000, 0x03026040):
            # Move to first cut (does this take laser "origin" settings into account?)
            axes = read_uword(file) # lower 2 bytes
            px = read_word(file)
            py = read_word(file)
            origin_x = px
            origin_y = py
            print('first cut', px, py, hex(axes))
            print()
        elif cmd in (0x03000e46, 0x3000e06):
            # Set stepper scale (steps/mm)
            x_scale = read_float(file)
            y_scale = read_float(file)
            z_scale = read_float(file)
            print('scale', hex(cmd), x_scale, y_scale, z_scale)
            print()
        elif cmd == 0x00200648:
            print('DONE')
            print()
            break
        elif cmd == 0x200608:
            print('DONE???')
            break
        elif cmd == 0x80600148:
            print('motion settings', hex(cmd), 'at', hex(cmd_pos))
            read_motion_settings_command(file, cmd)
        elif cmd == 0x3000341:
            start_speed = read_float(file)
            max_speed = read_float(file)
            accel = read_float(file)
            print('speed settings', start_speed, max_speed, accel)
            print()
        elif cmd == 0x3046040:
            motion_axis = read_word(file) # lower two bytes
            value1 = read_uword(file) # (table width + art width)/2
            value2 = read_uword(file) # (table height + art height)/2
            print('artwork origin', hex(motion_axis), value1, value2)
            print()
        elif cmd == 0x80500048:
            num_words = read_uword(file)
            if num_words == 1:
                value = read_uword(file)
                assert value == 603
                print('end subroutine(?)', value)
                print()
            elif num_words == 3:
                value1 = read_uword(file)
                value2 = read_uword(file)
                value3 = read_uword(file)
                assert value1 == 3
                print('related to subroutine(?)', value1, hex(value2), hex(value3))
                print()
            else:
                raise Exception('unknown arguments to 0x80500048')
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
    read_subroutine(file, scale=x_scale, origin_x=origin_x, origin_y=origin_y)

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
    print()

    print('####################')
    print('# Unknown comments #')
    print('####################')
    print()

    for cmd in sorted(unknown_commands):
        print(hex(cmd))
    print()


if __name__ == '__main__':
    main()
