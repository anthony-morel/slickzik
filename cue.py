import os
import subprocess
import logging
import re
import tempfile
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from metautils import *


def convert_to_flac(sndfile, flacfile):
    cmd = ['avconv', '-v', 'quiet', '-y', '-i', sndfile, flacfile]
    subprocess.check_call(cmd)


def get_cue_metadata(cuesheet):
    metadata = {}
    match = re.search(r'TITLE\s*"([^"]*)"', cuesheet, re.MULTILINE)
    if match:
        albumlong = dontshout(match.group(1))
        match = re.match(r'([^[]+?)\s*\[(.*)\]', albumlong)
        if match:
            metadata['album'] = match.group(1)
            metadata['comment'] = match.group(2)
        else:
            metadata['album'] = albumlong
    match = re.search(r'PERFORMER\s*"([^"]*)"', cuesheet, re.MULTILINE)
    if match:
        metadata['artist'] = dontshout(match.group(1))
    match = re.search(r'DATE\s*(19\d{2}|20\d{2})', cuesheet, re.MULTILINE)
    if match:
        metadata['date'] = match.group(1)
    return metadata


def filter_cue(cuesheet):
    # Filter cuedata to get INDEX 01 of each song
    # and also workaround shnsplit parsing defects/limitations
    # sed -ni '/TRACK/p; /TITLE/p; /INDEX 01/p' "$CUEFILEUTF"
    matches = re.findall(
        r'^(\s*(?:TRACK|TITLE|INDEX 01).*)$', cuesheet, flags=re.MULTILINE)
    '''
    # Non integrated code to handle non-CD cue in shnsplit
    # shnsplit does not allow the use of frames in non-CD cue -> translate
    print(matches)
    for i, line in enumerate(matches):
        # translate mm:ss:ff (ff = frames 1/75s) to mm:ss:nnn (nnn = 1/1000s)
        match = re.match(
            r'(\s+INDEX 01\s+\d{2}:\d{2}:)(\d{2})(?=[^\d])', line)
        if match:
            matches[i] = match.group(1) + \
                ("%03d" % (1000*int(match.group(2))/75.+0.5))
    # TODO: Second, shnsplit does not cope well with > 44.1k sampling rate
    # and is failing on the last track
    # workaround consists of adding a track for ~ last sample
    # metaflac --show-total-samples
    # divide by srate and convert to mm:ss:nnn
    print(matches)
    '''
    return '\n'.join(matches)


def cuesplit(sndfile, outdir, cuesheet, metadata):
    cuedata = filter_cue(cuesheet)
    # Execute shnsplit in outdir to declutter the log
    # Need to make input path absolute
    cmd = ['shnsplit', '-o', 'flac flac -8 -s - -o %f',
           '-n', '%02d', '-t', '%n - %t', '-P', 'none',
           os.path.realpath(sndfile)]
    p = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, cwd=outdir)
    output = p.communicate(input=cuedata)
    # TODO: have a pipeline instead to access flac files as they are created
    flacfiles = re.findall(r'--> \[(.*.flac)\].* : OK', output[1])
    logging.debug(flacfiles)
    if not flacfiles:
        logging.error('Unexpected result splitting CUE file')
        logging.debug(output[0])
        logging.debug(output[1])
    else:
        for f in flacfiles:
            pathname = os.path.join(outdir, f)
            if f == '00 - pregap.flac':
                os.remove(pathname)
            else:
                logging.info('Creating\t' + f)
                metadata['tracknumber'] = infer_tracknumber(f)
                metadata['title'] = infer_title(f)
                set_meta(metadata, pathname)
    return outdir


class cuetranscoder:

    def __init__(self, args={}):
        self.args = args
        # self.directory    -> input directory
        # self.files        -> list of (sound file, cue sheet) pairs

    def probe(self, directory):
        self.directory = directory
        self.files = []
        # Detect file.cue pointing to a single sndfile.(flac|wav|ape|wv))
        cuefiles = sorted(
            [name for name in os.listdir(directory)
                if name.lower().endswith('.cue')])
        sndfiles = sorted(
            [name for name in os.listdir(directory)
                if name.lower().endswith(('.flac', '.wav', '.ape', '.wv'))])
        logging.debug('cuefiles=' + str(cuefiles))
        logging.debug('sndfiles=' + str(sndfiles))
        cuepairs = []
        # Read all the cue sheet
        for cuefile in cuefiles:
            with open(os.path.join(self.directory, cuefile), 'r') as f:
                cuesheet = f.read().decode(self.args['cuecharset'])
                # Only retain cue sheets that point to exactly one file
                matches = re.findall(
                    r'^FILE\s*"([^"]*)"', cuesheet, re.MULTILINE)
                if len(matches) == 1:
                    cuepairs.append((matches[0], cuefile))
        logging.debug('cuepairs=' + str(cuepairs))
        # Accept all pairs where the sound file exists as is
        rempairs = []
        for pair in cuepairs:
            sndfile = [
                name for name in sndfiles if name.lower() == pair[0].lower()]
            if sndfile:
                # accepts this pair
                self.files.append((sndfile[0], pair[1]))
                logging.debug('use=' + sndfile[0])
                # ensure the audio file cannot be grabbed by another pair
                fnoext = os.path.splitext(pair[0])[0].lower()
                sndfiles = [
                    name for name in sndfiles
                    if not name.lower().startswith(fnoext)]
            else:
                rempairs.append(pair)
        # For remaing cue try to match with audio file of different encoding
        for pair in rempairs:
            fnoext = os.path.splitext(pair[0])[0].lower()
            sndfile = [
                name for name in sndfiles if name.lower().startswith(fnoext)]
            if sndfile:
                self.files.append((sndfile[0], pair[1]))
                logging.debug('convert=' + sndfile[0])
        return self.files

    def transcode(self):
        outdirs = []
        for sndfile, cuefile in self.files:
            logging.info('Processing\t' + sndfile)
            logging.info('CUE sheet\t' + cuefile)
            with open(os.path.join(self.directory, cuefile), 'r') as f:
                cuesheet = f.read().decode(self.args['cuecharset'])
            metadata = get_cue_metadata(cuesheet)
            outdir = get_output_dir(self.args['rootdir'], metadata)
            os.mkdir(outdir)
            logging.info('To ' + outdir)
            outdirs.append(outdir)
            if sndfile.lower().endswith(('.wv', '.ape')):
                fd, flacfile = tempfile.mkstemp('.flac')
                # creating a file object from low-level handle fd
                # closes the handle when the file object is out of scope
                with os.fdopen(fd) as f:
                    logging.info('Converting\t' + sndfile)
                    convert_to_flac(
                        os.path.join(self.directory, sndfile), flacfile)
                cuesplit(flacfile, outdir, cuesheet, metadata)
                os.remove(flacfile)
            else:
                flacfile = os.path.join(self.directory, sndfile)
                cuesplit(flacfile, outdir, cuesheet, metadata)
        return outdirs


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.info('Test 1')

    args = {'srate':48000, 'rootdir':'.', 'mix':False, 'gain':0, 'cuecharset':'iso-8859-1'}
    t = transcoder(args)
    f = t.probe('testset/cue')
    assert f, 'check testset/cue folder for .cue + single large audio file (any format)'
    print(f)
    d = t.transcode()
    assert d, 'transcode did not create output folder'
    logging.warn('DONE - Test 1. Verify ' + str(d) + ' matches testset/cue')
