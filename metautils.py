import os
import re

# utility functions to infer metadata from path name

def infer_from_dir(dirname):
    # TODO: infer album and artist    
    album = 'Unknown Album'
    artist = 'Unknown Artist'
    # There may be two or more dates. If so, should the earliest for the original release date.
    matches = re.findall( r'\((19\d{2}|20\d{2})\)', dirname)
    if matches:
        date = min(matches)
    else:
        matches = re.findall( r'19\d{2}|20\d{2}', dirname)
        if matches:
            date = min(matches)
        else:
            date = None
    return album, artist, date

def infer_tracknumber(filename):
    match = re.match( r'([0-9]+)', filename)
    if match:
        return '%02d' % int(match.group(1))
    else:
        return '00'

def infer_title(filename):
    match = re.match( r'[0-9 _.-]*(.*)\s*.flac', filename)
    if match:
        metadata['title'] = match.group(1)
    else:
        metadata['title'] = 'Unknown Title'

# utility functions to create directory and filenames from metadata

def make_pathname(path, name):
    # handle os.sep and os.altsep in name, so that it does not create a subdirectory
    # replace them by ',' with beautiful spacing
    name = re.sub( r'\s*[/\\]+(\s?)\s*', r',\1', name)
    return os.path.join(path, name)

def get_output_dir(rootdir, metadata):
    if 'date' in metadata:
        outdir = metadata['artist']+' - ('+metadata['date']+') '+metadata['album']
    else:
        outdir = metadata['artist']+' - '+metadata['album']
    outdir = make_pathname(rootdir, outdir)
    if os.path.exists(outdir):
        basedir = outdir
        if 'comment' in metadata:
            outdir = basedir+' ['+metadata['comment']+']'
        i = 2
        while os.path.exists(outdir):
            outdir = basedir + '.' + str(i)
            i += 1
    return outdir

def get_filename(outdir, metadata):
    return make_pathname(outdir, metadata['tracknumber']+' - '+metadata['title']+'.flac')


if __name__ == '__main__':
    metadata = {}
    metadata['artist'] = 'Artist / Name'
    metadata['date'] = '1999'
    metadata['album'] = 'Album Name'
    metadata['tracknumber'] = '01'
    metadata['title'] = 'Track \ Title'
    outdir = get_output_dir('.', metadata)
    print outdir
    filename = get_filename(outdir, metadata)
    print filename


