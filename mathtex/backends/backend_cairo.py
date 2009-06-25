"""
Cairo backend for Mathtex.

Requires: cairo, pycairo
"""

try:
    import cairo
except ImportError:
    raise ImportErorr("Cairo backend requires pycairo.")

from mathtex.backends import MathtexBackend

class MathtexBackendCairo(MathtexBackend):
    """
    A Cairo backend for Mathtex.
    """

    def __init__(self, dpi):
        self._rendered = False
        MathtexBackend.__init__(self, dpi)

    def render(self, glyphs, rects):
        self._glyphs = glyphs
        self._rects = rects
        self._rendered = True

    def get_formats(self):
        formats = ['png'] # Always have the PNG backend

        if cairo.HAS_PDF_SURFACE:
            formats.append('pdf')
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

            ctx.save()
            ctx.select_font_face(font.name, font.slant, font.weight)
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
                                         self.width, self.height)

        ctx = cairo.Context(surface)
        self.render_to_context(ctx)

        if format == 'png':
            surface.write_to_png(filename)
