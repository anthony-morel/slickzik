import subprocess
import re

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
    print get_meta('/home/amorel/Music/Seawind - (1980) Seawind/05 - Shout.flac')


