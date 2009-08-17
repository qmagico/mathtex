# Import Mathtex and the appropriate font set
from mathtex.mathtex_main import Mathtex
from mathtex.fonts import UnicodeFonts

# Create the font set instance; if \bf and \it are not provided
# they will be the bold and italic versions of \rm
u = UnicodeFonts(rm='Times New Roman', sf='Arial')

# Create the expression object and save it as a PNG
m = Mathtex(r"${\it x} = {\rm x} = {\sf x} = {\bf x}$", u, 20)
m.save('unicode.png')

# Attempt to also save it as a PDF -- requires PyCairo
try:
    m.save('unicode.pdf')
except:
    print 'PDF output requires PyCairo.'