# Main parser
from mathtex.parser import MathtexParser
from mathtex.boxmodel import ship
from mathtex.util import is_string_like

# Might not have Py Cairo installed
HAVE_CAIRO_BACKEND = True
try:
    from mathtex.backends.backend_cairo import MathtexBackendCairo
except ImportError:
    HAVE_CAIRO_BACKEND = False

# Image backend is always available
from mathtex.backends.backend_image import MathtexBackendImage

# Fontsets
from mathtex.fonts import BakomaFonts, UnicodeFonts, StixFonts

class Mathtex:
    fontset_mapping = {
        'bakoma'  : BakomaFonts,
        'cm'      : BakomaFonts, # Alias for Bakoma
        'unicode' : UnicodeFonts,
        'stix'    : StixFonts
        }

    def __init__(self, expr, fontset = 'bakoma', fontsize = 12, dpi = 100,
                       default_style = 'it'):
        if is_string_like(fontset):
            fontset = self.fontset_mapping[fontset](default_style)

        # Parse the expression
        self.boxmodel = MathtexParser().parse(expr, fontset, fontsize,
                                              dpi)

        # Use ship to get a stream of glyphs and rectangles
        self.rects, self.glyphs, bbox = ship(0, 0, self.boxmodel)

        # Calculate the exact width, height and depth
        self.width = bbox[2] - bbox[0]
        self.height = self.boxmodel.height
        self.depth = self.boxmodel.depth

        self.fontset = fontset
        self.fontsize = fontsize
        self.dpi = dpi

    def render_to_backend(self, backend):
        backend.set_canvas_size(self.width, self.height, self.depth, self.dpi)
        backend.render(self.glyphs, self.rects)

    def as_rgba_bitmap(self):
        """
        Renders the expression to an RGBA bitmap using the Image backend and
        returns it.
        """
        backend = MathtexBackendImage()
        self.render_to_backend(backend)

        return backend.as_rgba()

    def save(self, filename, format, backend='auto', backend_options={}):
        if backend == 'auto':
            if format == 'png':
                backend = 'image'
            else:
                backend = 'cairo'

        # Create the backend instance
        if backend == 'image':
            backend = MathtexBackendImage()
        elif backend == 'cairo':
            if not HAVE_CAIRO_BACKEND:
                raise RuntimeError("Cairo backend requested when not available.")
            backend = MathtexBackendCairo()

        # Set the options for the backend
        backend.options = backend_options

        # Render!
        self.render_to_backend(backend)

        # Save
        backend.save(filename, format)