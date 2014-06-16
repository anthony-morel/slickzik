RUN-TIME
========

usage: slickzik [-h] [-d] [-f sacd,pcm] [-g G] [-m] [--front {G,off}]
                [--ctr {G,off}] [--rear {G,off}] [--sub {G,off}] [--mch] [-r]
                [-s S] [-t {t1,t2,..}] [--cuecharset CS]
                rootdir folder [folder ...]

Reformat music album folders into a consistent format: 1 flac file per track
(cue + flac/wav/ape/wv and sacd-iso are transcoded) + cover.jpg + Artwork.zip

positional arguments:
  rootdir          directory where reformatted album folders are created
  folder           source folder to scan and process for album data

optional arguments:
  -h, --help       show this help message and exit
  -d, --display    display covert art for processed albums
  -f sacd,pcm      only process folder with listed audio type
  -g G, --gain G   apply gain in dB, e.g., -g -3
  -m, --mix        mix multichannel down to stereo
  --front {G,off}  front channels gain in dB or off
  --ctr {G,off}    centre channel gain in dB or off
  --rear {G,off}   rear channels gain in dB or off
  --sub {G,off}    subwoofer chnl gain in dB or off
  --mch            select multichannel track on sacd (implied with -m)
  -r, --rename     rename processed folder using prefix 0K (zero-K) for ok, 0C
                   (zero-C) for no cover art
  -s S, --srate S  max sample rate, e.g., -s 48k, -s 88200, ... files with
                   higher rates are downsampled, others are untouched
  -t {t1,t2,..}    convert only the specified tracks, e.g., -t 1,5,13
  --cuecharset CS  Character set used by cue sheets

defaults: process both sacd-iso and pcm (flac/wav/ape/wv), G = 0dB, S = 192k,
CS=iso-8859-1

DEPENDENCIES
============

Uses the following commands:
* External
  * flac and metaflac
  * shnsplit (part of shntools package)
  * avconv
  * sox
* From this repo
  * dff2raw - front-end for sox to handle dff files

BUILDING / INSTALLING
=====================

make
make install

