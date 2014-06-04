import os
import subprocess
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


def get_flac_metadata(data):
    metadata = {}

    data = data.split('\n',3)
    # Extract channels, bps, sample-rate
    metadata['channels'] = int(data[0])
    metadata['bps'] = int(data[1])
    metadata['srate'] = int(data[2])

    # Now skip to the exported tags
    data = data[3]

    match = re.search( r'^\s*album\s*=\s*(.*)', data, re.MULTILINE | re.IGNORECASE)
    if match:
        albumlong = match.group(1).rstrip()
        match = re.match( r'([^[]+?)\s*\[(.*)\]', albumlong)
        if match:
            metadata['album'] = match.group(1)
            metadata['comment'] = match.group(2)
        else:
            metadata['album'] = albumlong

    match = re.search( r'^\s*artist\s*=\s*(.*)', data, re.MULTILINE | re.IGNORECASE)
    if match:
        metadata['artist'] = match.group(1)

    match = re.search( r'^\s*date\s*=\s*(19\d{2}|20\d{2})', data, re.MULTILINE | re.IGNORECASE)
    if match:
        metadata['date']  = match.group(1)

    match = re.search( r'^\s*tracknumber\s*=\s*([0-9]*)', data, re.MULTILINE | re.IGNORECASE)
    if match:
        metadata['tracknumber'] = '%02d' % int(match.group(1))

    match = re.search( r'^\s*title\s*=\s*(.*)', data, re.MULTILINE | re.IGNORECASE)
    if match:
        metadata['title'] = match.group(1)
    
    return metadata

def get_meta(f):
    cmd = ['metaflac', '--show-channels','--show-bps','--show-sample-rate',
        '--export-tags-to=-', f]
    metadata = get_flac_metadata(unicode(subprocess.check_output(cmd)))
    return metadata

def set_meta(metadata, pathname):
    cmd = ['--set-tag='+tag+'='+val for tag, val in sorted(metadata.items())]
    cmd = ['metaflac','--remove-all-tags'] + cmd + [ pathname ]
    subprocess.check_call(cmd)


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


