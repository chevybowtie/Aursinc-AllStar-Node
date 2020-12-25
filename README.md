# SA818 Programming

My friend (W6IPA) and I developed a versatile Raspberry-Pi hat that
can be used for Allstar, Echolink, APRS, or any digital modes.

We use the program in this GitHub repository to program the radio
module SA818 used for the Pi-Hat.

![Screen Shoot](docs/IMG_0716.JPG)

We have some PCB left. We are selling them for [$25 on tindie][1]

**Before programming the SA818 module, make sure you consult the band
plan for your country and transmit on a frequency you are allowed to
use.**

## Example

```
[root@allstar ~]# python ./sa818-2.py version
SA818: INFO: Firmware version: V4.2

[root@allstar ~]# python ./sa818-2.py radio --frequency 146.43 --ctcss 118.8
SA818: INFO: +DMOSETGROUP:0 frequency: 146.4300, tone: 0017, squelsh: 4, OK

[root@allstar ~]# python ./sa818-2.py volume --level 5
SA818: INFO: +DMOSETVOLUME:0 Volume level: 5
```

If you use an FTDI dongle to program the SA828 module the USB port can
be specified with the `--port` argument

```
[root@allstar ~]# python ./sa818-2.py --port /dev/ttyAMA0 volume --level 5
SA818: INFO: +DMOSETVOLUME:0 Volume level: 5
```

## Usage

This program has for sections:

 - radio: Program the radio's frequency, tone and squelsh level
 - volume: Set the volume level
 - filters: Turn on or off the [pre/de]-emphasis and as well as the high and low pass filter
 - version: display the firmware version of the SA818 module

```
usage: sa818.py [-h] [--port PORT] [--debug]
                {radio,volume,filters,version} ...

generate configuration for switch port

positional arguments:
  {radio,volume,filters,version}
    radio               Program the radio (frequency/tome/squelsh)
    volume              Set the volume level
    filters             Set filters
    version             Show the firmware version of the SA818

optional arguments:
  -h, --help            show this help message and exit
  --port PORT           Serial port [default: linux console port]
  --debug
```

### Radio

```
usage: sa818.py radio [-h] --frequency FREQUENCY [--offset OFFSET]
                      [--squelsh SQUELSH] [--ctcss CTCSS | --dcs DCS]

optional arguments:
  -h, --help            show this help message and exit
  --frequency FREQUENCY
                        Transmit frequency
  --offset OFFSET       0.0 for no offset [default: 0.0]
  --squelsh SQUELSH     Squelsh value (1 to 9) [default: 4]
  --ctcss CTCSS         CTCSS (PL Tone) 0 for no CTCSS [default: None]
  --dcs DCS             DCS code must me the number followed by [N normal] or
                        [I inverse] [default: None]
```

### Volume

```
usage: sa818.py volume [-h] [--level LEVEL]

optional arguments:
  -h, --help     show this help message and exit
  --level LEVEL  Volume value (1 to 8) [default: 4]
```

### Filters

```
usage: sa818.py filters [-h] [--emphasis EMPHASIS] [--highpass HIGHPASS]
                        [--lowpass LOWPASS]

optional arguments:
  -h, --help           show this help message and exit
  --emphasis EMPHASIS  Enable [Pr/De]-emphasis (yes/no) [default: no]
  --highpass HIGHPASS  Enable high pass filter (yes/no) [default: no]
  --lowpass LOWPASS    Enable low pass filters (yes/no) [default: no]
```

## CTCSS codes (PL Tones)

```
67.0, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5, 94.8, 97.4,
100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3, 131.8, 136.5,
141.3, 146.2, 151.4, 156.7, 162.2, 167.9, 173.8, 179.9, 186.2, 192.8,
203.5, 210.7, 218.1, 225.7, 233.6, 241.8, 250.3
```

## DCS Codes

DCS codes must be followed by N or I for Normal or Inverse:
> Example: 047I

```
023, 025, 026, 031, 032, 036, 043, 047, 051, 053, 054, 065, 071, 072,
073, 074, 114, 115, 116, 122, 125, 131, 132, 134, 143, 145, 152, 155,
156, 162, 165, 172, 174, 205, 212, 223, 225, 226, 243, 244, 245, 246,
251, 252, 255, 261, 263, 265, 266, 271, 274, 306, 311, 315, 325, 331,
332, 343, 346, 351, 356, 364, 365, 371, 411, 412, 413, 423, 431, 432,
445, 446, 452, 454, 455, 462, 464, 465, 466, 503, 506, 516, 523, 526,
532, 546, 565, 606, 612, 624, 627, 631, 632, 654, 662, 664, 703, 712,
723, 731, 732, 734, 743, 754
```


[1]: https://www.tindie.com/products/w6ipa/radio-interface-module-pirim-for-raspberry-pi/
