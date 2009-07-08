"""
Cairo backend for Mathtex.

Requires: cairo, pycairo
"""
from math import ceil

from mathtex.font_manager import ttfFontProperty

try:
    import cairo
except ImportError:
    raise ImportError("Cairo backend requires pycairo.")

from mathtex.backend import MathtexBackend

class MathtexBackendCairo(MathtexBackend):
    """
    A Cairo backend for Mathtex.
    """
    fontweights = {
        100          : cairo.FONT_WEIGHT_NORMAL,
        200          : cairo.FONT_WEIGHT_NORMAL,
        300          : cairo.FONT_WEIGHT_NORMAL,
        400          : cairo.FONT_WEIGHT_NORMAL,
        500          : cairo.FONT_WEIGHT_NORMAL,
        600          : cairo.FONT_WEIGHT_BOLD,
        700          : cairo.FONT_WEIGHT_BOLD,
        800          : cairo.FONT_WEIGHT_BOLD,
        900          : cairo.FONT_WEIGHT_BOLD,
        'ultralight' : cairo.FONT_WEIGHT_NORMAL,
        'light'      : cairo.FONT_WEIGHT_NORMAL,
        'normal'     : cairo.FONT_WEIGHT_NORMAL,
        'medium'     : cairo.FONT_WEIGHT_NORMAL,
        'semibold'   : cairo.FONT_WEIGHT_BOLD,
        'bold'       : cairo.FONT_WEIGHT_BOLD,
        'heavy'      : cairo.FONT_WEIGHT_BOLD,
        'ultrabold'  : cairo.FONT_WEIGHT_BOLD,
        'black'      : cairo.FONT_WEIGHT_BOLD,
        }

    fontangles = {
        'italic'  : cairo.FONT_SLANT_ITALIC,
        'normal'  : cairo.FONT_SLANT_NORMAL,
        'oblique' : cairo.FONT_SLANT_OBLIQUE,
        }

    def __init__(self):
        self._rendered = False
        MathtexBackend.__init__(self)

    def render(self, glyphs, rects):
        # Extract the info Cairo needs to render the equation
        self._glyphs = [(info.font, info.fontsize, unichr(info.num),
                         ox, oy - info.offset)
                        for ox, oy, info in glyphs]
        self._rects = [(x1, y1, x2 - x1, y2 - y1)
                       for x1, y1, x2, y2 in rects]

        self._rendered = True

    def get_formats(self):
        formats = ['png'] # Always have the PNG backend

        if cairo.HAS_PDF_SURFACE:
            formats.append('pdf')
        if cairo.HAS_PS_SURFACE:
            formats.append('ps')
        if cairo.HAS_SVG_SURFACE:
            formats.append('svg')

        return formats

    def render_to_context(self, ctx):
        """
        Renders the glyphs and rectangles to a Cairo context.
        """
        ctx.save()

        for font, fontsize, s, ox, oy in self._glyphs:
            ctx.new_path()
            ctx.move_to(ox, oy)

            fontProp = ttfFontProperty(font)
            ctx.save()
            ctx.select_font_face (fontProp.name,
                                 self.fontangles [fontProp.style],
                                 self.fontweights[fontProp.weight])
            size = fontsize * self.dpi / 72.0
            ctx.set_font_size(size)
            ctx.show_text(s.encode("utf-8"))
            ctx.restore()

        for ox, oy, w, h in self._rects:
            ctx.new_path()
            ctx.rectangle(ox, oy, w, h)
            ctx.set_source_rgb(0, 0, 0)
            ctx.fill_preserve()

        ctx.restore()

    def save(self, filename, format):
        if format not in self.get_formats():
            raise RuntimeError('Unsupported save format')

        if format == 'png':
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                         int(ceil(self.width)),
                                         int(ceil(self.height + self.depth)))
        elif format == 'pdf':
            width = self.width
            height = self.height + self.depth
            surface = cairo.PDFSurface(filename, width, height)
        elif format == 'ps':
            surface = cairo.PSSurface(filename,
                                      self.width,
                                      self.height + self.depth)
        elif format == 'svg':
            surface = cairo.SVGSurface(filename,
                                       self.width,
                                       self.height + self.depth)

        ctx = cairo.Context(surface)
        self.render_to_context(ctx)

        if format == 'png':
            surface.write_to_png(filename)
