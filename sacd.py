def int_or_off(s):
    if s.lower()=='off':
        return None
    else:
        return int(s)

def add_options(parser):
    parser.add_argument('-m', action='store_true',
        help='(sacd) mix multichannel down to stereo')
    parser.add_argument('--front', type=int_or_off, metavar='{G,off}', default=0,
        help='front channels gain in dB or off')
    parser.add_argument('--ctr', type=int_or_off, metavar='{G,off}', default=0,
        help='centre channel gain in dB or off')
    parser.add_argument('--sub', type=int_or_off, metavar='{G,off}', default=0,
        help='subwoofer channel gain in dB or off')
    parser.add_argument('--rear', type=int_or_off, metavar='{G,off}', default=0,
        help='rear channels gain in dB or off')

class transcoder:
    def __init__(self, args=None):
        self.args = args
        self.directory = ''

    def probe(self, directory):
        return []

    def transcode(self):
        return []

