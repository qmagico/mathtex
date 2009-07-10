# -*- coding: iso-8859-1 -*-
# TODO
"""
from mathtex.parser import MathtexParser
from mathtex.boxmodel import ship
from mathtex.fonts import BakomaFonts
from mathtex.fonts import StixFonts
from mathtex.backends.backend_cairo import MathtexBackendCairo
from mathtex.backends.backend_image import MathtexBackendImage

parser = MathtexParser()
bakoma = BakomaFonts()
stix = StixFonts()

box =  parser.parse(r"$x_{1,2}=\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$", stix, 18, 99.0)

#print box

rects, glyphs, bbox =  ship(0, 0, box)

width = bbox[2] - bbox[0]
height = box.height
depth = box.depth

backend = MathtexBackendImage(99.0)
backend.set_canvas_size(box.width, box.height, box.depth)
backend.render(glyphs, rects)
backend.save('test.png', 'png')
"""
from mathtex.mathtex_main import Mathtex
from mathtex.fonts import UnicodeFonts

u = UnicodeFonts(rm="times new roman",it='times new roman:italic',bf='times new roman:bold')

m = Mathtex(r"$\sqrt{x^2} \times \frac{2}{3}$", u)
m.save('testnew.png', 'png')
