import os
import subprocess
import logging
import metautils


def add_dsp_downsampler(dsp, srate):
    # Apply a short filter for higher sampling rate
    # '95' at 48kHz gives passband of 0 .. 23 kHz
    # '74' at 96kHz gives passband of 0 .. 35 kHz and less utrasonic echoes
    dsp += ['rate', '-v', '-b', '95' if srate <= 48000 else '74', str(srate)]


def add_dsp_gain(dsp, gain):
    dsp += ['gain', str(gain)]


def reencode_with_dsp(flacfile, outfile, dsp):
    cmd = ['sox', '-G', flacfile, '-C', '8', outfile] + dsp
    logging.debug(cmd)
    subprocess.call(cmd)


def reencode_no_dsp(flacfile, outfile):
    # flac -8 -s <input.flac> -o <output.flac>
    # --> may fail with ERROR: input file has an ID3v2 tag
    # Use flac -c -d <input.flac> | flac -8 -s - -o <output.flac>
    cmd = ['flac', '-c', '-s', '-d', flacfile]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    logging.debug(cmd)
    cmd = ['flac', '-8', '-s', '-', '-o', outfile]
    p2 = subprocess.Popen(cmd, stdin=p.stdout)
    logging.debug(cmd)
    p2.communicate()


class transcoder:

    def __init__(self, args=None):
        self.args = args
        self.directory = ''
        self.filemeta = {}

    def probe(self, directory):
        self.directory = directory
        self.files = sorted(
            [name for name in os.listdir(directory)
                if name.lower().endswith('.flac')])
        return self.files

    def _extract_metadata(self):
        self.filemeta = {}
        album, artist, date = metautils.infer_from_dir(self.directory)
        for f in self.files:
            metadata = metautils.get_meta(os.path.join(self.directory, f))
            if 'album' not in metadata:
                metadata['album'] = album
            if 'artist' not in metadata:
                metadata['artist'] = artist
            if date:
                if ('date' not in metadata) or (date < metadata['date']):
                    metadata['date'] = date
            if 'tracknumber' not in metadata:
                metadata['tracknumber'] = metautils.infer_tracknumber(f)
            if 'title' not in metadata:
                metadata['title'] = metautils.infer_title(f)
            self.filemeta[f] = metadata

    def _transcode_one(self, f, outdir):
        pathname = os.path.join(self.directory, f)
        outfile = metautils.get_filename(outdir, self.filemeta[f])
        logging.info('Creating\t' + os.path.basename(outfile))
        dsp = []
        if self.filemeta[f]['channels'] > 2 and self.args.mix:
            raise NotImplementedError(
                'Downmix of multi-channel flac is not implemented yet.')
        if self.filemeta[f]['srate'] > self.args.srate:
            add_dsp_downsampler(dsp, self.args.srate)
        if self.args.gain != 0:
            add_dsp_gain(dsp, self.args.gain)
        if dsp:
            reencode_with_dsp(pathname, outfile, dsp)
        else:
            reencode_no_dsp(pathname, outfile)
        metadata = {k: self.filemeta[f][k] for k in
                    ('album', 'artist', 'date', 'tracknumber', 'title')
                    if k in self.filemeta[f]}
        logging.debug(metadata)
        metautils.set_meta(metadata, outfile)

    def transcode(self):
        self._extract_metadata()
        self.outdir = []
        pending = self.files
        while pending:
            next = []
            album = self.filemeta[pending[0]]['album']
            outdir = metautils.get_output_dir(
                self.args.rootdir, self.filemeta[pending[0]])
            os.mkdir(outdir)
            logging.info('To ' + outdir)
            self.outdir.append(outdir)
            for f in pending:
                if self.filemeta[f]['album'] == album:
                    self._transcode_one(f, outdir)
                else:
                    next.append(f)
            pending = next
        return self.outdir


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info('Test 1')

    class args:
        srate = 48000
        rootdir = '.'
        mix = False
        gain = 0
    t = transcoder(args)
    f = t.probe('testset/cd')
    assert f, 'check testset/cd folder for cd quality flac files'
    d = t.transcode()
    assert d, 'transcode did not create output folder'
    logging.warn('DONE - Test 1. Verify ' + str(d) + ' matches testset/cd')

    logging.info('Test 2')
    f = t.probe('testset/hr')
    assert f, 'check testset/hr folder for high-res flac files'
    d = t.transcode()
    assert d, 'transcode did not create output folder'
    logging.warn(
        'DONE - Test 2. Verify ' + str(d) + ' is testset/hr downsampled to 48kHz')

    logging.info('Test 3')
    f = t.probe('testset/mixed')
    assert f, 'check testset/mixed for two+ different album files in same folder'
    d = t.transcode()
    assert len(d) >= 2, 'transcode did not create at least 2 output folders'
    logging.warn(
        'DONE - Test 3. Verify ' + str(d) + ' span all tracks in testset/mixed')

    logging.info('Test 4')

    class args:
        srate = 48000
        rootdir = '.'
        mix = False
        gain = -6
    t = transcoder(args)
    f = t.probe('testset/cd')
    assert f, 'check testset/cd folder for cd quality flac files'
    d = t.transcode()
    logging.warn(
        'DONE - Test 4. Verify ' + str(d) + ' is testset/cd attenuated by 6 dB')

    # TODO: test case of different albums in same folder
