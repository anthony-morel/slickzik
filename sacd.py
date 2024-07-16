import os
import subprocess
import logging
import re
import tempfile
from metautils import *

class sacdtranscoder:

    def __init__(self, args={}):
        self.args = args
        # self.directory    -> input directory
        # self.metadata     -> Common metadata (no track titles and numbers)
        # self.titles       -> Track titles (implicit numbering)
        # self.channels     -> Number of channels of current iso>area (2,5,6)

    def _mch(self):
        logging.debug(self.args)
        return self.args['mix'] or self.args['mch']

    def probe(self, directory):
        self.directory = directory
        files = sorted(
            [name for name in os.listdir(directory)
                if name.lower().endswith('.iso')])
        self.files = []
        for f in files:
            isofile = os.path.join(self.directory, f)
            logging.debug(isofile)
            output = self._sacd_extract_info(isofile)
            match = re.findall(r'Speaker config: (\d) Channel', output, re.MULTILINE)
            if self._mch():
                # Require a multichannel track
                if not ('5' in match or '6' in match):
                    logging.info(isofile + ' has no multichannel track')
                    continue
            elif not '2' in match:
                # Not a SACD iso: SACD must have a stereo track
                logging.info(isofile + ' is not a SACD')
                continue
            self.files.append(isofile)
        return self.files

    def _extract_metadata(self, isofile):
        log = self._sacd_extract_info(isofile)
        self.metadata = {}
        album, artist, date = infer_from_dir(self.directory)
        match = re.findall(r'Title:\s*(.*)', log, re.MULTILINE)
        if match:
            self.metadata['album'] = dontshout(match[0])
        else:
            self.metadata['album'] = album
        match = re.findall(r'Artist:\s*(.*)', log, re.MULTILINE)
        if match:
            self.metadata['artist'] = dontshout(match[0])
        else:
            self.metadata['artist'] = artist
        match = re.findall(r'19\d{2}|20\d{2}', log, re.MULTILINE)
        if match:
            match.sort()
            logging.debug('possible dates ' + str(match))
            self.metadata['date'] = match[0]
        if date:
            if ('date' not in self.metadata) or (date < self.metadata['date']):
                self.metadata['date'] = date
            logging.debug('date ' + self.metadata['date'])
        # Get metadata corresponding to the requested area (stereo, mch)
        # as the number of tracks and their names may differ btw areas
        area = re.split(r'Speaker config: ', log, 0, re.MULTILINE)
        area = area[-1] if self._mch() else area[1]
        logging.debug(area)
        self.channels = int(area[0])
        self.titles = re.findall(r'Title\[\d+\]:\s*(.*)', area, re.MULTILINE)
        if self.titles:
            self.titles = dontshout('\n'.join(self.titles)).split('\n')
        logging.debug(self.titles)

    def _sacd_extract_info(self, isofile):
        # Extracts sacd area info
        cmd = ['sacd_extract', '-i', os.path.realpath(isofile), '-P']
        logging.debug(cmd)
        output = subprocess.check_output(cmd).decode()
        logging.debug(output)
        return output

    def _transcode_one(self, idx, dff, outdir):
        self.metadata['tracknumber'] = '%02d' % idx
        # May fail if SACD does not embedded title
        try:
            self.metadata['title'] = self.titles[idx - 1]
        except:
            self.metadata['title'] = 'Unknown Title'
        outfile = get_filename(outdir, self.metadata)
        logging.info('Creating\t' + os.path.basename(outfile))
        # dff2raw <file.dff> | sox -t raw -e float -b 32 -r 2822400 -c 2 -
        # -b 24 <file.flac> rate -v 48000 gain 6 stats
        cmd = ['dff2raw', dff]
        if self.args['mix'] and self.channels >= 5:
            channels = 2
            cmd += ['-m'] + \
                   ['-'+k[0]+str(self.args[k])
                    for k in ('front', 'ctr', 'rear', 'sub')]
        else:
            channels = self.channels
        logging.debug(cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        cmd = ['sox', '-t', 'raw', '-e', 'float', '-b', '32', '-r', '2822400',
               '-c', str(channels), '-', '-b', '24', outfile,
               'rate', '-v', str(self.args['srate']),
               'fade', '0.001']
        if self.args['gain'] != 0:
            cmd += ['gain', str(self.args['gain'])]
        # Don't generate flac with odd-channel count (ALSA no more supports)
        if self.channels == 5:
            # flac channel order: 1=L, 2=R, 3=C, 4=null LFE, 5/6 = rear
            cmd += ['remix', '1', '2', '3', '0', '4', '5']
        logging.debug(cmd)
        p2 = subprocess.Popen(cmd, stdin=p.stdout)
        p2.communicate()
        logging.debug(self.metadata)
        set_meta(self.metadata, outfile)
        # remove intermediary file created by sacd_extract
        os.remove(dff)

    def transcode(self):
        self.outdir = []
        for f in self.files:
            isofile = os.path.join(self.directory, f)
            self._extract_metadata(isofile)
            # Convert to DFF using sacd_extract() and parse info from log
            tmpdir = tempfile.mkdtemp()
            cmd = ['nice', 'sacd_extract', '-i', os.path.realpath(isofile), '-p', '-c']
            if self.args['t']:
                cmd += ['-t',','.join(self.args['t'])]
            if self._mch():
                cmd += ['-m']
            logging.debug(cmd)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=tmpdir)
            prev_dff = ''
            idx = 0
            for line in p.stdout:
                m = re.search(r'Processing \[(.*)\]', line.decode())
                if not m:
                    continue
                if not prev_dff:
                    # Decoding started: create final output dir
                    outdir = get_output_dir(self.args['rootdir'], self.metadata)
                    os.mkdir(outdir)
                    logging.info('To ' + outdir)
                    self.outdir.append(outdir)
                else:
                    # Previous dff file is now complete
                    dff = os.path.join(tmpdir, prev_dff)
                    self._transcode_one(idx, dff, outdir)
                prev_dff = m.group(1)
                idx += 1
            # Transcode final dff
            dff = os.path.join(tmpdir, prev_dff)
            self._transcode_one(idx, dff, outdir)
            # remove intermediary directory created by sacd_extract
            os.rmdir(os.path.dirname(dff))
            os.rmdir(tmpdir)
        return self.outdir

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.info('Test 1')

    args = {'srate':48000, 'rootdir':'.', 'mix':False, 'mch':True, 'gain':3}
    t = transcoder(args)
    f = t.probe('testset/sacd')
    assert f, 'check testset/sacd folder for sacd iso files'
    d = t.transcode()
    assert d, 'transcode did not create output folder(s)'
    logging.warn('DONE - Test 1. Verify ' + str(d) + ' matches testset/sacd')
