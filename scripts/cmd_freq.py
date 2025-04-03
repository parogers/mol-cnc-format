#!/usr/bin/env python3

from collections import Counter
import sys
from dataclasses import dataclass


@dataclass
class Command:
    cmd_type: str
    args: list[str]


def read_laser_txt(path):
    commands = []
    with open(path) as file:
        for line in file.readlines():
            if not line.strip():
                continue
            args = line.strip().split(',')
            cmd = Command(
                cmd_type=args[0],
                args=args[1:],
            )
            commands.append(cmd)
    return commands


def main():
    commands = read_laser_txt(sys.argv[1])
    counter = Counter([
        f'{cmd.cmd_type}-{len(cmd.args)}'
        for cmd in commands
    ])
    for cmd_type, count in counter.most_common():
        print(f'{cmd_type:20s} {count}')


if __name__ == '__main__':
    main()
