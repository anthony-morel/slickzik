import os
import subprocess
import logging
import re
import tempfile
import metautils


def sacd_extract(isofile):
    # Extracts the sacd tracks into dff files
    # This can take many minutes due to dst de-compression
    tmpdir = tempfile.mkdtemp()
    cmd = ['sacd_extract', '-i',
           os.path.realpath(isofile), '-P', '-2', '-p', '-c']
    logging.debug(cmd)
    output = subprocess.check_output(cmd, cwd=tmpdir)
    logging.debug(output)
    return tmpdir, output


class transcoder:

    def __init__(self, args=None):
        self.args = args
        # self.directory    -> input directory
        # self.dff          -> Intermediary DFF files
        # self.metadata     -> Common metadata (no track titles and numbers)
        # self.titles       -> Track titles (implicit numbering)

    def probe(self, directory):
        self.directory = directory
        self.files = sorted(
            [name for name in os.listdir(directory)
                if name.lower().endswith('.iso')])
        # TODO: call SACD extract to check that it is really an iso file of
        # SACD
        return self.files

    def _extract_metadata(self, log):
        self.metadata = {}
        album, artist, date = metautils.infer_from_dir(self.directory)
        match = re.findall(r'Title:\s*(.*)', log, re.MULTILINE)
        if match:
            self.metadata['album'] = match[0]
        else:
            self.metadata['album'] = album
        match = re.findall(r'Artist:\s*(.*)', log, re.MULTILINE)
        if match:
            self.metadata['artist'] = match[0]
        else:
            self.metadata['artist'] = artist
        match = re.findall(r'19\d{2}|20\d{2}', log, re.MULTILINE)
        if match:
            match.sort()
            logging.debug('possible dates ' + str(match))
            self.metadata['date'] = match[0]
        if date:
            if ('date' not in self.metadata) or (date < metadata['date']):
                self.metadata['date'] = date
        logging.debug('date ' + self.metadata['date'])
        self.titles = re.findall(r'Title\[\d+\]:\s*(.*)', log, re.MULTILINE)
        logging.debug(self.titles)
        self.dff = re.findall(r'Processing \[(.*)\]', log, re.MULTILINE)
        logging.debug(self.dff)

    def _transcode_one(self, f, outdir):
        outfile = metautils.get_filename(outdir, self.metadata)
        logging.info('Creating\t' + os.path.basename(outfile))
        # dff2raw -i <file.dff> | sox -t raw -e float -b 32 -r 2822400 -c 2 -
        # -b 24 <file.flac> rate -v 48000 gain 6 stats
        cmd = ['dff2raw', '-i', f]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        logging.debug(cmd)
        cmd = ['sox', '-t', 'raw', '-e', 'float', '-b', '32', '-r', '2822400',
               '-c', '2', '-', '-b', '24', outfile,
               'rate', '-v', str(self.args.srate), 'gain', str(self.args.gain)]
        p2 = subprocess.Popen(cmd, stdin=p.stdout)
        logging.debug(cmd)
        p2.communicate()
        logging.debug(self.metadata)
        metautils.set_meta(self.metadata, outfile)

    def transcode(self):
        self.outdir = []
        for f in self.files:
            # Convert to DFF using sacd_extract() and parse info from log
            tmpdir, log = sacd_extract(os.path.join(self.directory, f))
            self._extract_metadata(log)
            if self.dff:
                outdir = metautils.get_output_dir(
                    self.args.rootdir, self.metadata)
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

    class args:
        srate = 48000
        rootdir = '.'
        mix = False
        gain = 3
    t = transcoder(args)
    f = t.probe('testset/sacd')
    assert f, 'check testset/sacd folder for sacd iso files'
    d = t.transcode()
    assert d, 'transcode did not create output folder(s)'
    logging.warn('DONE - Test 1. Verify ' + str(d) + ' matches testset/sacd')
