# TODO

from mathtex.parser import MathtexParser
from mathtex.boxmodel import ship
from mathtex.fonts import BakomaFonts
from mathtex.backends.backend_cairo import MathtexBackendCairo

parser = MathtexParser()
bakoma = BakomaFonts()

box =  parser.parse("$x$", bakoma, 12, 99.0)

print box

rects, glyphs =  ship(0, -box.depth, box)

print glyphs

cairo = MathtexBackendCairo(99.0)
cairo.set_canvas_size(box.width, box.height, box.depth)
cairo.render(glyphs, rects)
cairo.save('test.png', 'png')
