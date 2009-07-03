# -*- coding: iso-8859-1 -*-
# TODO

from mathtex.parser import MathtexParser
from mathtex.boxmodel import ship
from mathtex.fonts import BakomaFonts
from mathtex.backends.backend_cairo import MathtexBackendCairo
from mathtex.backends.backend_image import MathtexBackendImage

parser = MathtexParser()
bakoma = BakomaFonts()

box =  parser.parse("$\sqrt{x}$", bakoma, 12, 99.0)

print box

rects, glyphs =  ship(0, -box.depth, box)

print glyphs

backend = MathtexBackendImage(99.0)
backend.set_canvas_size(box.width, box.height, box.depth)
backend.render(glyphs, rects)
backend.save('test.png', 'png')
