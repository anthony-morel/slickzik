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
        for isofile in files:
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
        area = area[2] if self._mch() else area[1]
        logging.debug(area)
        self.channels = int(area[0])
        self.titles = re.findall(r'Title\[\d+\]:\s*(.*)', area, re.MULTILINE)
        self.titles = dontshout('\n'.join(self.titles)).split('\n')
        logging.debug(self.titles)

    def _sacd_extract_info(self, isofile):
        # Extracts sacd area info
        cmd = ['sacd_extract', '-i', os.path.realpath(isofile), '-P']
        logging.debug(cmd)
        output = subprocess.check_output(cmd)
        logging.debug(output)
        return output

    def _sacd_extract(self, isofile):
        # Extracts the sacd tracks into dff files
        # This can take many minutes due to dst de-compression
        tmpdir = tempfile.mkdtemp()
        cmd = ['sacd_extract', '-i', os.path.realpath(isofile), '-p', '-c']
        if self.args['t']:
            cmd += ['-t',','.join(self.args['t'])]
        if self._mch():
            cmd += ['-m']
        logging.debug(cmd)
        output = subprocess.check_output(cmd, cwd=tmpdir)
        logging.debug(output)
        return tmpdir, output

    def _transcode_one(self, f, outdir):
        outfile = get_filename(outdir, self.metadata)
        logging.info('Creating\t' + os.path.basename(outfile))
        # dff2raw <file.dff> | sox -t raw -e float -b 32 -r 2822400 -c 2 -
        # -b 24 <file.flac> rate -v 48000 gain 6 stats
        cmd = ['dff2raw', f]
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
               'rate', '-v', str(self.args['srate']), 'gain', str(self.args['gain'])]
        # Don't generate flac with odd-channel count (ALSA no more supports)
        if self.channels == 5:
            # flac channel order: 1=L, 2=R, 3=C, 4=null LFE, 5/6 = rear
            cmd += ['remix', '1', '2', '3', '0', '4', '5']
        logging.debug(cmd)
        p2 = subprocess.Popen(cmd, stdin=p.stdout)
        p2.communicate()
        logging.debug(self.metadata)
        set_meta(self.metadata, outfile)

    def transcode(self):
        self.outdir = []
        for f in self.files:
            isofile = os.path.join(self.directory, f)
            self._extract_metadata(isofile)
            # Convert to DFF using sacd_extract() and parse info from log
            tmpdir, log = self._sacd_extract(isofile)
            dffs = re.findall(r'Processing \[(.*)\]', log, re.MULTILINE)
            logging.debug(dffs)
            if dffs:
                outdir = get_output_dir(
                    self.args['rootdir'], self.metadata)
                os.mkdir(outdir)
                logging.info('To ' + outdir)
                self.outdir.append(outdir)
                for idx, f in enumerate(dffs):
                    logging.debug('Processing\t' + f)
                    dff = os.path.join(tmpdir, f)
                    self.metadata['tracknumber'] = '%02d' % (idx + 1)
                    self.metadata['title'] = self.titles[idx]
                    self._transcode_one(dff, outdir)
                    # remove intermediary file created by sacd_extract
                    os.remove(dff)
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
