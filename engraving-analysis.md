
# Engraving test (test-engrave-rectangle)

The size of the rectangle in steps: 4167x5555 (scale factor 138.88671875 steps/mm)

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

## Data file

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


First pass: (file position 0xaa8)

0x80000146          Engraving pass
0x830001            One argument follows
0x1a1046

0x2014040
0x4                 x-axis
0x2b66              Value: 11110
                    (this is double the rectangle width for some reason)

0x2010040
0x3                 y-axis
0x5                 move down one scan step (note: 0.04mm/step is about 5.6)


Second pass:

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


Third pass:

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
