import os
import flacmeta
import metautils
import subprocess
import logging

def add_options(parser):
    parser.add_argument('-s', choices=('48k','96k'), default='192k', help='downsample to this maximum sample rate as required')

def reencode_same_rate(flacfile, outfile):
    # flac -8 -s <input.flac> -o <output.flac> --> may fail with ERROR: input file has an ID3v2 tag
    # Use flac -c -d <input.flac> | flac -8 -s - -o <output.flac>
    cmd = ['flac','-c','-s','-d',flacfile]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    logging.debug(cmd)
    cmd = ['flac','-8','-s','-','-o',outfile]
    p2 = subprocess.Popen(cmd, stdin=p.stdout)
    logging.debug(cmd)
    p2.communicate()

def reencode_96k(flacfile, outfile):
    # Don't need wasteful ultrasonics (noise / DSD noise shaping, spurs)
    # Keep bandwith = 0 .. 35 kHz using a short filter to prevent
    # (ultrasonic) echoes
    cmd = ['sox','-G',flacfile,'-C','8',outfile,'rate','-b','74','96000']
    logging.debug(cmd)
    subprocess.call(cmd)

def reencode_48k(flacfile, outfile):
    # Don't need wasteful ultrasonics (noise / DSD noise shaping, spurs)
    # Keep bandwith = 0 .. 23 kHz
    cmd = ['sox','-G',flacfile,'-C','8',outfile,'rate','-b','95','48000']
    logging.debug(cmd)
    subprocess.call(cmd)

reencode_algo = { '48k':reencode_48k, '96k':reencode_96k, '192k':reencode_same_rate }

class transcoder:
    def __init__(self, args=None):
        self.args = args
        self.directory = ''
        self.filemeta = {}

    def probe(self, directory):
        self.directory = directory
        self.files=sorted([name for name in os.listdir(directory) if name.lower().endswith('.flac')])
        return self.files

    def _extract_metadata(self):
        self.filemeta = {}
        album, artist, date = metautils.infer_from_dir(self.directory)
        for f in self.files:
            metadata = flacmeta.get_meta(os.path.join(self.directory,f))
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
        logging.info('Processing\t'+f)
        pathname = os.path.join(self.directory,f)
        outfile = metautils.get_filename(outdir,self.filemeta[f])
        if self.filemeta[f]['srate'] > int(self.args.s[:-1])*1000:
            reencode_algo[self.args.s](pathname, outfile)
        else:
            reencode_same_rate(pathname, outfile)
            metadata = { k:self.filemeta[f][k] for k in
                ('album','artist','date','tracknumber','title') if k in self.filemeta[f] }
            logging.debug(metadata)
            flacmeta.set_meta(metadata, outfile)
    
    def transcode(self):
        self._extract_metadata()
        self.outdir = []
        pending = self.files
        while pending:
            next = []
            album = self.filemeta[pending[0]]['album']
            outdir = metautils.get_output_dir(self.args.rootdir, self.filemeta[pending[0]])
            os.mkdir(outdir)
            self.outdir.append(outdir)
            for f in pending:
                if self.filemeta[f]['album'] == album:
                    self._transcode_one(f, outdir)
                else:
                    next.append(f)
            pending = next
        return self.outdir


if __name__ == '__main__':
    import argparse
    from pprint import pprint
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument('rootdir')
    add_options(parser)
    t=transcoder(parser.parse_args(['-s','48k','.']))
    pprint(vars(t))
    #t.args=parser.parse_args([])
    pprint(t.probe('/home/amorel/Music/Seawind - (1980) Seawind'))
    t.srate=176400
    print(t.transcode())


