import os
import subprocess
import logging
import re
import tempfile
from metautils import *

def get_dff_params(f):
    cmd = ['dff2raw', '-p', f]
    output = subprocess.check_output(cmd)
    match = re.search(r'^numChannels\s*=\s*(\d+)', output, re.MULTILINE)
    if match:
        channels = int(match.group(1))
    match = re.search(r'^sampleRate\s*=\s*(\d+)', output, re.MULTILINE)
    if match:
        srate = int(match.group(1))
    logging.debug(str((channels, srate)))
    return channels, srate

class sacdtranscoder:

    def __init__(self, args={}):
        self.args = args
        # self.directory    -> input directory
        # self.dff          -> Intermediary DFF files
        # self.metadata     -> Common metadata (no track titles and numbers)
        # self.titles       -> Track titles (implicit numbering)

    def probe(self, directory):
        self.directory = directory
        files = sorted(
            [name for name in os.listdir(directory)
                if name.lower().endswith('.iso')])
        self.files = []
        for isofile in files:
            cmd = ['sacd_extract', '-i', os.path.realpath(isofile), '-P']
            logging.debug(cmd)
            output = subprocess.check_output(cmd)
            logging.debug(output)
            match = re.findall(r'Speaker config: (\d) Channel', output, re.MULTILINE)
            if self.args['mix'] or self.args['mch']:
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

    def _extract_metadata(self, log):
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
        self.titles = re.findall(r'Title\[\d+\]:\s*(.*)', log, re.MULTILINE)
        self.titles = dontshout('\n'.join(self.titles)).split('\n')
        logging.debug(self.titles)
        self.dff = re.findall(r'Processing \[(.*)\]', log, re.MULTILINE)
        logging.debug(self.dff)

    def _sacd_extract(self, isofile):
        # Extracts the sacd tracks into dff files
        # This can take many minutes due to dst de-compression
        tmpdir = tempfile.mkdtemp()
        cmd = ['sacd_extract', '-i', os.path.realpath(isofile),
               '-P', '-p', '-c']
        if self.args['t']:
            cmd += ['-t',','.join(self.args['t'])]
        if self.args['mix'] or self.args['mch']:
            cmd += ['-m']
        logging.debug(cmd)
        output = subprocess.check_output(cmd, cwd=tmpdir)
        logging.debug(output)
        return tmpdir, output

    def _transcode_one(self, f, outdir):
        outfile = get_filename(outdir, self.metadata)
        logging.info('Creating\t' + os.path.basename(outfile))
        channels, srate = get_dff_params(f)
        # dff2raw <file.dff> | sox -t raw -e float -b 32 -r 2822400 -c 2 -
        # -b 24 <file.flac> rate -v 48000 gain 6 stats
        cmd = ['dff2raw', f]
        if self.args['mix'] and (channels == 5 or channels == 6):
            channels = 2
            cmd += ['-m'] + \
                   ['-'+k[0]+str(self.args[k])
                    for k in ('front', 'ctr', 'rear', 'sub')]
        logging.debug(cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        cmd = ['sox', '-t', 'raw', '-e', 'float', '-b', '32', '-r', str(srate),
               '-c', str(channels), '-', '-b', '24', outfile,
               'rate', '-v', str(self.args['srate']), 'gain', str(self.args['gain'])]
        logging.debug(cmd)
        p2 = subprocess.Popen(cmd, stdin=p.stdout)
        p2.communicate()
        logging.debug(self.metadata)
        set_meta(self.metadata, outfile)

    def transcode(self):
        self.outdir = []
        for f in self.files:
            # Convert to DFF using sacd_extract() and parse info from log
            tmpdir, log = self._sacd_extract(os.path.join(self.directory, f))
            self._extract_metadata(log)
            if self.dff:
                outdir = get_output_dir(
                    self.args['rootdir'], self.metadata)
                os.mkdir(outdir)
                logging.info('To ' + outdir)
                self.outdir.append(outdir)
                for idx, f in enumerate(self.dff):
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
