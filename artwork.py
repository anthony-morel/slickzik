import os
import logging
import subprocess
import sqlite3


def geometry(w, h, x=0, y=0):
    if (x == 0 and y == 0):
        return str(w)+'x'+str(h)
    else:
        return str(w)+'x'+str(h)+'+'+str(x)+'+'+str(y)


def find(rootdir, matchfn):
    return [os.path.join(root, name)
            for root, dirs, files in os.walk(rootdir)
            for name in files if matchfn(name)]


def by_ext(ext):
    return lambda name: name.lower().endswith(ext)


def by_name(name2):
    return lambda name: name == name2


def cover_search_queries():
    # Any image with size >= 500x500 and <= 800x800 and ~1:1 ratio named
    # *cover*, *folder*, *front*, *thumb*
    # Any image with size > 800x800 name and ~1:1 ratio named
    # *cover*, *folder*, *front*, *thumb*
    # (which is then resized to 512x512)
    # Any image with ~2:1 ratio named
    # *cover*, *folder*, *front*, *thumb*, *[^1-9]1, *01*
    # (whose right side is extracted and resized to 512x512)
    # Any image with ~1:2 ratio
    # *cover*, *folder*, *front*, *thumb*, *[^1-9]1, *01*
    # (that we rotate clockwise, extract right side and resize to 512x512)
    return \
    ['''ratio > 0.95 AND ratio < 1.20 AND
        width >= 500 AND width <= 800 AND
        (name LIKE '%cover%' OR name LIKE '%folder%' OR name LIKE '%front%' OR name LIKE '%thumb%'
            OR name LIKE 'prev')
        ORDER BY encoding, width DESC LIMIT 1''',
     '''ratio > 0.95 AND ratio < 1.20 AND
        width > 800 AND
        (name LIKE '%cover%' OR name LIKE '%folder%' OR name LIKE '%front%' OR name LIKE '%thumb%')
        ORDER BY encoding, name LIMIT 1''',
     '''(   (ratio > 1.90 AND width > 800) OR
            (ratio > 0.43 AND ratio < 0.52 AND height > 800)
        ) AND
        (name LIKE '%cover%' OR name LIKE '%folder%' OR name LIKE '%front%' OR name LIKE '%thumb%')
        ORDER BY encoding, name LIMIT 1''',
     '''(   (ratio > 1.90 AND width > 800) OR
            (ratio > 0.43 AND ratio < 0.52 AND height > 800)
        ) AND
        name LIKE '%00'
        ORDER BY encoding, name LIMIT 1''',
     '''(   (ratio > 1.90 AND width > 800) OR
            (ratio > 0.43 AND ratio < 0.52 AND height > 800)
        ) AND
        name LIKE '%01'
        ORDER BY encoding, name LIMIT 1''',
     '''(   (ratio > 1.90 AND width > 800) OR
            (ratio > 0.43 AND ratio < 0.52 AND height > 800)
        ) AND
        name LIKE '%01%'
        ORDER BY encoding, name LIMIT 1''',
     '''(   (ratio > 1.90 AND width > 800) OR
            (ratio > 0.43 AND ratio < 0.52 AND height > 800)
        ) AND
        name LIKE '%1'
        ORDER BY encoding, name LIMIT 1''',
     '''ratio > 0.95 AND ratio < 1.20
        ORDER BY encoding, width DESC LIMIT 1''']


class coverart_processor:

    def __init__(self):
        # default settings for possible override
        self.blacklist = ('*test*', 'prevdr', 'frequency', 'eac', 'tau',
                'eac *', 'obi*')
        self.pictypes = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')
        self.covername = 'cover.jpg'
        self.zipname = 'Artwork'


    def probe(self, directory):
        self.directory = directory
        self.picfiles = find(directory, by_ext(self.pictypes))
        return self.picfiles


    def _create_pic_database(self):
        # Create a picture database to search for cover art candidates
        db = sqlite3.connect(':memory:')
        cur = db.cursor()
        cur.execute('''CREATE TABLE picts (name TEXT, pathname TEXT, encoding TEXT,
                    width INTEGER, height INTEGER, ratio FLOAT)''')
        for picfile in self.picfiles:
            try:
                output = unicode(subprocess.check_output(['identify','-format','%t\t%d/%f\t%m\t%w\t%h\n',picfile]))
            except subprocess.CalledProcessError, e:
                print e.output
            else:
                lines = output.split('\n')
                for line in lines:
                    if line:
                        row = line.split('\t')
                        row[0]=row[0].lower() # fix a case-sensitive problem with mysql
                        row.append(int(row[3]) / float(row[4])) # compute ratio to simply queries
                        cur.execute('INSERT INTO Picts VALUES(?,?,?,?,?,?)', row)
                db.commit()
        return db


    def extract_to(self, outdir):
        db = self._create_pic_database()
        cur = db.cursor()
        for idx, query in enumerate(cover_search_queries()):
            cur.execute(
                'SELECT pathname, encoding, width, height, ratio FROM picts WHERE '
                + query)
            for pathname, encoding, width, height, ratio in cur.fetchall():
                break
            else:
                continue
            # Found best cover picture.  Make it in the right format
            cover = outdir+'/'+self.covername
            break
        else:
            db.close()
            return None

        if encoding == 'JPEG' and ratio > 0.95 and ratio < 1.05 and width >= 400 and width <= 800:
            cmd = ['cp', pathname, cover]
        else:
            # 1) Find the rectangular clip size
            # 2) Find the rectangle offset in the original picture
            rotate = []
            if ratio < 0.52:
                length = width
                if height > 2*length:
                    ypos = (height + (height - 2*length + 1) / 2)/2
                else:
                    ypos = height - length
                xpos = 0
                rotate = ['-rotate', '90']
            elif ratio > 1.90 and ratio < 2.30:
                length = height
                if width > 2*length:
                    #  <---width/2.0---><---width/2.0--->
                    #                     <--length--->
                    xpos = (width + (width - 2*length + 1) / 2)/2
                else:
                    #  <---width/2.0---><---width/2.0--->
                    #                  <-----length----->
                    xpos = width - length
                ypos = 0
            elif ratio >= 2.30:
                length = height
                xpos = width - length
                ypos = 0
            else:
                length = min(width, height)
                xpos = (width - length + 1) / 2
                ypos = (height - length) / 2
            newlength = min(length, 720)
            cmd = ['convert'] + rotate + ['-extract', geometry(length,length,xpos,ypos),
                  '-resize', geometry(newlength,newlength), pathname, cover]
        subprocess.call(cmd)

        # Ensure reprocessing already processed folder gives identity
        Artworkzip = find(self.directory, by_name(self.zipname+'.zip'))
        if Artworkzip:
            cmd = ['cp', Artworkzip[0], outdir]
        else:
            pdffiles = find(self.directory, by_ext('.pdf'))
        # Create a zip file will all pictures (ignore original path)
        # Blacklist some file names, as they are not artwork
        query = "name NOT LIKE '" + "' AND name NOT LIKE '".join(self.blacklist) + "'"
        query = query.replace('*','%')
        logging.debug(query)
        cur.execute('SELECT pathname FROM picts WHERE '+query+' ORDER BY pathname')
        # TODO: prevent duplicate names
        cmd = ['zip', '-j', outdir+'/'+self.zipname] + [pathname for pathname, in cur.fetchall()] + pdffiles
        subprocess.call(cmd)

        db.close()
        return cover
    

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    a = coverart_processor()

    f = a.probe('testset/art')
    assert f, 'check testset/art for cover art picture files'
    logging.info(f)

    f = a.extract_to('.')
    logging.info(f)

