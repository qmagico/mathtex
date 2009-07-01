# -*- coding: iso-8859-1 -*-
# TODO

from mathtex.parser import MathtexParser
from mathtex.boxmodel import ship
from mathtex.fonts import BakomaFonts
from mathtex.backends.backend_cairo import MathtexBackendCairo

parser = MathtexParser()
bakoma = BakomaFonts()

box =  parser.parse("$\sqrt{x}$", bakoma, 12, 72.0)

print box

rects, glyphs =  ship(0, -box.depth, box)

print rects
print glyphs

cairo = MathtexBackendCairo(72.0)
cairo.set_canvas_size(box.width+100, box.height+100, box.depth)
cairo.render(glyphs, rects)
cairo.save('test.png', 'png')
