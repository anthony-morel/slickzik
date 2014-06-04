import os
import subprocess
import logging

def sacd_extract(isofile):
    cmd = ['sacd_extract','-i', isofile, '-P', '-2', '-p', '-c']
    output = subprocess.check_output(cmd)
    return output

class transcoder:
    def __init__(self, args=None):
        self.args = args
        self.directory = ''
        self.dff = []       # Intermediary DFF files
        self.metadata = {}  # Common metadata (no track titles and numbers)
        self.titles = []    # Track titles (implicit numbering)

    def probe(self, directory):
        self.directory = directory
        self.files=sorted([name for name in os.listdir(directory) if name.lower().endswith('.iso')])
        return self.files

    def _extract_metadata(self, log):
        self.metadata = {}
        album, artist, date = metautils.infer_from_dir(self.directory)
        match = re.findall( r'Title:\s*(.*)', log, re.MULTILINE)
        if match:
            self.metadata['album'] = match[0]
        else:
            self.metadata['album'] = album
        match = re.findall( r'Artist:\s*(.*)', data, re.MULTILINE)
        if match:
            self.metadata['artist'] = match[0]
        else:
            self.metadata['artist'] = artist
        match = re.findall( r'19\d{2}|20\d{2}', data, re.MULTILINE)
        if match:
            match.sort()
            self.metadata['date'] = match[0]
        if date:
            if ('date' not in self.metadata) or (date < metadata['date']):
                self.metadata['date'] = date
        self.titles = re.findall( r'Title\[\d+\]:\s*(.*)', data, re.MULTILINE)
        self.dff = re.findall( r'Processing \[(.*)\]', data, re.MULTILINE)

    def _transcode_one(self, f, outdir):
        logging.info('Processing\t'+f)
        pathname = os.path.join(self.directory,f)
        outfile = metautils.get_filename(outdir,self.metadata)
        # dff2raw -i <file.dff> | sox -t raw -e float -b 32 -r 2822400 -c 2 - -b 24 <file.flac> rate -v 48000 gain 6 stats
        cmd = ['dff2raw','-i',f]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        logging.debug(cmd)
        cmd = ['sox','-t','raw','-e','float','-b','32','-r','2822400','-c','2','-',
            '-b','24',outfile,'rate','-v','48k','gain','6']
        p2 = subprocess.Popen(cmd, stdin=p.stdout)
        logging.debug(cmd)
        p2.communicate()
        logging.debug(self.metadata)
        flacmeta.set_meta(self.metadata, outfile)

    def transcode(self):
        self.outdir = []
        for f in self.files:
            # Convert to DFF using sacd_extract() and parse info from log
            log = sacd_extract(f)
            self._extract_metadata(log)
            if self.dff:
                outdir = metautils.get_output_dir(self.args.rootdir, self.metadata)
                os.mkdir(outdir)
                self.outdir.append(outdir)
                for idx, dff in enumerate(self.dff):
                    self.metadata['tracknumber'] = '%02d' % (idx+1)
                    self.metadata['title'] = self.titles[idx]
                    self._transcode_one(dff, outdir)
                    # remove intermediary file created by sacd_extract
                    os.remove(dff)
                # remove intermediary directory created by sacd_extract
                os.rmdir(os.path.dirname(files[0]))
        return self.outdir

if __name__ == '__main__':
    import argparse
    from pprint import pprint
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument('rootdir')
    add_options(parser)
    t=transcoder(parser.parse_args(['-s','48k','-g','6','.']))
    pprint(vars(t))
    #t.args=parser.parse_args([])
    # TODO:
    pprint(t.probe('/path/to/sacd.iso'))
    print(t.transcode())


