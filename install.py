import sys
import os
import re

imports = []
src = []
for imported in sys.argv[1:]:
    for line in open(imported, 'r'):
        if line.startswith(('#!','import','reload','sys')):
            imports.append(line)
        elif line.startswith('if __name__'):
            break
        elif not line.startswith('from'):
            src.append(line)

print(''.join(sorted(set(imports))))
print(''.join(src))

