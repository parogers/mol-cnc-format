
# Engraving analysis

## Engraving test (test-engrave-rectangle)

The size of the rectangle: 30x40mm or 4167x5555 steps (scale factor 138.88671875 steps/mm)

The bulk of the work is carried out by command 0x80000146 which is probably a single engraving (horizontal) pass of the laser.

* There are 1001 commands: 0x80000146
* The rectangle measures 30x40 mm
* The INI file specifies: LaserEngraveScanStepLen=0.04000
* 40mm/(0.04mm/scan step) = 1000 scan steps, so 1001 scan passes

The command 0x80000146 should have a variable length number of words following it, as determined by the next (unsigned) word in the file, but that results in nonsense: (ie. way more words than are remaining in the file)

    0x80000146          Command
    0x830001            Number of words (8,585,217)

But the file makes sense if you discard the upper 2 bytes when reading the number of words. I'm not sure what those two bytes represent but most of the time they're 0x0000, but for these engraving commands I see:

* 0x830001 - first pass
* 0x840002 - in-between passes
* 0xda0002 - last pass

It could just be uninitialized random cruft, or maybe it encodes state or some other command argument.

### Data file (test-engrave-rectangle)

```
(snip)

0x2014341 (at 0xa28)    configuring axis speed?
0x4                     x-axis
42361.0                 scan speed (305 mm => approx 42360 steps)

0x4010141 (at 0xa34)    configuring axis scan speed?
0x4                     x-axis
3472.0                  (about 25 mm with scale)
42361.0                 scan speed
1388864.0               (about 10000 mm with scale)

0x2010041 (at 0xa48)    configuring axis step speed?
0x3                     y-axis
1388.0                  speed? (about 10 mm with scale)

(snip)

0x1000b46 (at 0xaa0)    similar to 0x1000b06 (blower control)
0x201                   same value as in 0x1000b06

(snip)
```

First pass: (file position 0xaa8)

```
0x80000146          Engraving pass
0x830001            One argument follows
0x1a1046

0x2014040
0x4                 x-axis
0x2b66              Value: 11110 (about 80 mm)

0x2010040
0x3                 y-axis
0x5                 move down one scan step (note: 0.04mm/step is about 5.6)
```

Second pass:

```
0x80000146          Engraving pass
0x840002            Two arguments follow
0x230000
0x161047

0x2014040
0x4                 x-axis
0xffffd475          Value: -11147

0x2010040
0x3                 y-axis
0x6                 move down one scan step
```

Third pass:

```
0x80000146
0x840002
0x240000
0x161046

0x2014040
0x4                 x-axis
0x2b8c              Value: 11148

0x2010040
0x3
0x5

(snip)

0x80000146
0x840002
0x280000
0x181040

0x2014040
0x4
0xffffd477

0x1000b46
0x200

0x80000146
0xda0002
0x230000
0x0

0x1400048
0x3
```

### Axis sweeping (test-engrave-rectangle)

The way engraving works is the head moves back and forward, along the x-axis, while the laser state is toggled rapidly to engrave the pattern. The software can be configured to engrave in one direction only, or sweeping in both directions along the x-axis.

After each sweep (or pair) the head moves along the artwork an amount specified by the step size. Step counts are specified for both commands. Since steps are always integer values, there is some rounding up/down to compensate for mm step size (specified by the software) to motor step conversion.

The result is the amount stepped by the y-axis will tend to bounce between two values as it tries to follow exactly where it's supposed to be:

```
step axis
-> y-axis by 4 to 0.05
step axis
-> y-axis by 5 to 0.09
step axis
-> y-axis by 5 to 0.12
step axis
-> y-axis by 5 to 0.16
step axis
-> y-axis by 5 to 0.19
step axis
-> y-axis by 5 to 0.23
step axis
-> y-axis by 5 to 0.27
step axis
-> y-axis by 4 to 0.3
```

The laser "overscans" the artwork as it sweeps along the x-axis. Looking at the data file (and others) it looks like each sweep has an extra 50 mm of travel than is specified by the artwork. The laser starts moving a short distance before it begins engraving, and ends a short distance after.

I'm assuming this is to ensure the laser is moving at a constant speed, having finished its acceleration, by the time it starts engraving.

### Engrave line commands (test-engrave-rectangle)

Each sweep and step pair is preceeded by a 0x80000146 "engrave line" command. (just what I'm calling them) I'm pretty sure this instructs the machine at which points to turn on/off the laser for engraving. The command takes a variable number of arguments that seems to correspond to the complexity of the line being etched. (ie. more on/offs required, more arguments)

```
engrave line (0x80000146)
-> 001a1046 1708102 3       Argument in hex, in decimal, y-position
                            (note y-position is not part of the argument - just here for convenience)

--
engrave line (0x80000146)
-> 00230000 2293760 8
-> 00161047 1445959 8

--
engrave line (0x80000146)
-> 00240000 2359296 14
-> 00161046 1445958 14

--
engrave line (0x80000146)
-> 00240000 2359296 19
-> 00161046 1445958 19

--
engrave line (0x80000146)
-> 00240000 2359296 25
-> 00161046 1445958 25

--
engrave line (0x80000146)
-> 00240000 2359296 30
-> 00161046 1445958 30

(snip)
```

The argument values are too large to represent mm distances. After analyzing other files I'm guessing each word-length argument actually encodes two short integers. (maybe representing start/stop positions to laser)

## Engraving test (test-triangle1)

This file contains a right angle triangle, fitting inside a box 25x50 mm, with the hypotenuse having a "positive slope". (ie. looking like /)

The first engrave/sweep/step looks like this:

```
engrave line (0x80000146, x=-24.93, y=0.02)
-> 00120d8e 1183118

sweep axis
-> axis 4 from -24.93 by 74.98

step axis
-> y-axis by 4 to 0.05
```

The engrave line command somehow needs to encode when to turn on/off the laser to make it engrave the first row of the triangle - which corresponds to the base measuring 25mm long. So this sweep should engrave a line from x=0 to x=25 mm, with the head starting back at about x=-25mm. (note I'm not sure the script is calculating scale properly so -24.93 may not be accurate)

Breaking the engrave line argument into shorts:

* 0012 - This should encode at what position to turn on the laser but the value is so small it can't represent a step count. Maybe the lead-offset is always fixed and this value actually represents something else.
* 0d8e - This is 3470 or about 25mm. So this is probably the run length of the engraving.

The next sweep moves backwards:

```
engrave line (0x80000146, x=50.05, y=0.05)
-> 00230000 2293760
-> 00110d8c 1117580

sweep axis
-> axis 4 from 50.05 by -75.23

step axis
-> y-axis by 5 to 0.09
```

Breaking down the arguments into shorts:

* 0023 - Not sure what this represents. In subsequent commands this first argument is one of: 0023, 0024, 0026
* 0000 - Always zero in subsequent commands
* 0011 - Slightly less than in the first sweep (0012)
* 0d8c - Slightly less than in the first sweep (0d8e) which makes sense because the triangle is slightly more narrow.

Across all commands, the first (word) argument is one of:

* 00120d8e (1 time) - The first command
* 00230000 (2 times) - The second and also last command
* 00240000 (712 times) - All commands sweeping forwards (ie. positive x direction)
* 00260000 (713 times) - All commands sweeping backwards (ie. negative x direction)

The file test-engrave-rectangle has:

* 001a1046 (1 time) - The first command (note 0x1046 is 30 mm)
* 00230000 (2 times)
* 00240000 (997 times)
* 00280000 (1 time)

And the test-engrave-letters file has 58 unique values for the first argument, with the most frequent being 00240000. (864 times)

## Engraving test (test-engrave-boxes)

This file has a series of boxes in rows, starting at the top:

1. A single box having width 100 mm
2. Gap of 10 mm, width of 20, gap of 30, width of 40, gap of 50, width of 10
3. Width of 10, gap of 20, width of 30, gap of 40, width of 50

This file is strange in that it uses some "alternative" instructions:

* 0x3000e06 for setting the motor scale (instead of 0x03000e46)
* 0x0200608 to end the config section (instead of 0x00200648)

The engrave line at y=2.26 corresponds to #3 above and starts at x=-25.2. When its arguments are interpreted as shorts (16 bit), assumed to be step counts, and converted to mm, they look like:

* 0.26      Off
* 0.0       Laser on
* 19.99     Off
* 10.0      Laser on
* 40.0      Off
* 30.0      Laser on
* 0.19      Off
* 50.0      Laser on

So each argument word (ie pair of shorts) appear to be of the form (OFF)(ON), where the laser is first turned on, travels (ON) distance, then turns off, then travels the (OFF) distance.

This interpretation lines up nicely with the file artwork, except for the first two shorts and the second last one. If the sweep starts at x=-25.2, and the first box starts at x=0, then there should be a skip of 25.2 mm before we hit the first box. There's a similar issue at the end of the sequence.

I suspect the first word 00240000 may be a special instruction. The interpretation of (0.26)(0) just doesn't seem right. Same for the final instruction.

The subsequent engraving line starts at x=175.06

* 0.26      Off
* 0.0       Laser on
* 40.0      Off
* 50.0      Laser on
* 20.0      Off
* 30.0      Laser on
* 0.19      Off
* 10.0      Laser on

This line has the laser sweeping backwards (along negative X axis) so the engraving should happen in reverse order - which is the case here. Interestingly, the same values show up for the first two shorts and the second last one. (maybe not that interesting because the leading and trailing distances are about the same)

## Engraving test (test-engrave-letters)

```
engrave line (0x80000146, num=10, x=-18.61, y=8.24)
-> 00240000   0.26   0.0
-> 06e002c9  12.67  5.13
-> 04bd03f0   8.73  7.26
-> 06810423  11.99  7.62
-> 02c90335   5.13  5.91
-> 02e102c0   5.31  5.07
-> 03cd02c0   7.01  5.07
-> 04b202c0   8.65  5.07
-> 018902a5   2.83  4.87
-> 001602c0   0.16  5.07

sweep axis
-> axis 4 from -18.61 by 163.67

step axis
-> y-axis by 4 to 8.27

engrave line (0x80000146, num=10, x=145.06, y=8.27)
-> 00240000   0.26   0.0
-> 017d02c0   2.74  5.07
-> 04a702bc   8.58  5.04
-> 03cd02c0   7.01  5.07
-> 02e102c0   5.31  5.07
-> 02b802c0   5.01  5.07
-> 06670351  11.80  6.11
-> 049a0444   8.48  7.86
-> 06d10410  12.56  7.49
-> 001602c9   0.16  5.13

sweep axis
-> axis 4 from 145.06 by -163.67

step axis
-> y-axis by 5 to 8.3
```


```
engrave line (0x80000146, num=10, x=-18.61, y=16.46)
-> 00240000 0.26 0.0
-> 038002c9 6.45 5.13
-> 03e40945 7.17 17.09
-> 02d104fe 5.19 9.2
-> 04f702c0 9.15 5.07
-> 02e102c0 5.31 5.07
-> 03cd02c0 7.01 5.07
-> 023a02c0 4.1 5.07
-> 040702ce 7.42 5.17
-> 00160291 0.16 4.73

sweep axis
-> axis 4 from -18.61 by 163.67

step axis
-> y-axis by 4 to 16.49
```
