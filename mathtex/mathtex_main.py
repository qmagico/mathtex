# Main parser
from mathtex.parser import MathtexParser
from mathtex.boxmodel import ship
from mathtex.util import is_string_like, maxdict

# Might not have Py Cairo installed
HAVE_CAIRO_BACKEND = True
try:
    from mathtex.backends.backend_cairo import MathtexBackendCairo
except ImportError:
    HAVE_CAIRO_BACKEND = False

# Image backend is always available
from mathtex.backends.backend_image import MathtexBackendImage

# Fontsets
from mathtex.fonts import BakomaFonts, UnicodeFonts, StixFonts,\
                          StixSansFonts

class Mathtex:
    fontset_mapping = {
        'bakoma'  : BakomaFonts,
        'cm'      : BakomaFonts, # Alias for Bakoma
        'unicode' : UnicodeFonts,
        'stix'    : StixFonts,
        'stixsans': StixSansFonts
        }
    _cache = maxdict(50)

    def __init__(self, expr, fontset = 'bakoma', fontsize = 12, dpi = 100,
                       default_style = 'it', cache=False):
        # Hash the arguments
        h = hash((expr, fontset, fontsize, dpi, default_style))

        if is_string_like(fontset):
            fontset = self.fontset_mapping[fontset](default_style)

        # Check the cache first
        if cache and h in self._cache:
            self.boxmodel = self._cache[h]
        # Parse the expression
        else:
            self.boxmodel = MathtexParser().parse(expr, fontset, fontsize,
                                                  dpi)
            if cache:
                self._cache[h] = self.boxmodel

        # Use ship to get a stream of glyphs and rectangles
        bbox = ship(0, 0, self.boxmodel)[2]
        self.rects, self.glyphs, bbox = ship(-bbox[0], 0, self.boxmodel)

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

    def as_mask(self):
        """
        Renders the expression to an alpha mask using the Image backend.
        The result is returned as a numpy array.
        """
        backend = MathtexBackendImage()
        self.render_to_backend(backend)

        return backend.as_mask()

    def as_rgba_bitmap(self):
        """
        Renders the expression to an RGBA bitmap using the Image backend and
        returns it.
        """
        backend = MathtexBackendImage()
        self.render_to_backend(backend)

        return backend.as_rgba()

    def save(self, filename, format='auto', backend='auto', backend_options={}):
        if format == 'auto':
            format = filename.split('.')[-1]
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