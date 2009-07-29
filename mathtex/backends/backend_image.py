"""
Image backend for Mathtex.

Requires: FT2Font, numpy
"""
from math import ceil

try:
    from mathtex.ft2font import FT2Image
    from mathtex import _png
except ImportError:
    from matplotlib.ft2font import FT2Image
    from matplotlib import _png

from mathtex.backend import MathtexBackend

class MathtexBackendImage(MathtexBackend):
    """
    A image backend for Mathtex.
    """

    def __init__(self):
        self._rendered = False
        self.image = None
        MathtexBackend.__init__(self)

    def get_formats(self):
        return ['png']

    def _render_glyph(self, ox, oy, info):
        info.font.draw_glyph_to_bitmap(self.image,
                                       ox,
                                       oy - info.metrics.iceberg,
                                       info.glyph)

    def _render_rect(self, x1, y1, x2, y2):
        height = max(int(y2 - y1) - 1, 0)
        if height == 0:
            center = (y2 + y1) / 2.0
            y = int(center - (height + 1) / 2.0)
        else:
            y = int(y1)
        self.image.draw_rect_filled(int(x1), y, ceil(x2), y + height)

    def render(self, glyphs, rects):
        # Create the image
        self.image = FT2Image(ceil(self.width), ceil(self.height + self.depth))

        # Render each glyph
        for ox, oy, info in glyphs:
            self._render_glyph(ox, oy, info)

        # Render each rectangle
        for x1, y1, x2, y2 in rects:
            self._render_rect(x1, y1, x2, y2)

        self._rendered = True

    def save(self, filename, format):
        if format not in self.get_formats():
            raise RuntimeError('Unsupported save format')

        fh = file(filename, 'wb')
        _png.write_png(self.image.as_rgba_str(),
                       self.image.get_width(),
                       self.image.get_height(),
                       fh,
                       self.dpi)

    def as_rgba(self):
        assert self._rendered == True
        return self.image.as_rgba_str()

    def as_mask(self):
        assert self._rendered == True
        return self.image.as_array()
