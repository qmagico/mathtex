from mathtex.util import Bunch
from mathtex.data import latex_to_bakoma, \
        latex_to_standard, tex2uni, latex_to_cmex

from mathtex.ft2font import FT2Font

class Fonts(object):
    """
    An abstract base class for a system of fonts used by Mathtex.
    """

    def __init__(self):
        self.used_characters = {}

    def get_kern(self, font1, fontclass1, sym1, fontsize1,
                       font2, fontclass2, sym2, fontsize2, dpi):
        return 0

    def get_metrics(self, font, fontclass, sym, fontsize, dpi):
        info = self._get_info(font, fontclass, sym, fontsize, dpi)
        return info.metrics

    def get_xheight(self, font, fontsize, dpi):
        raise NotImplementedError()

    def get_underline_thickness(self, font, fontsize, dpi):
        raise NotImplementedError()

    def get_used_characters(self):
        return self.used_characters

    def get_sized_alternatives_for_symbol(self, fontname, sym):
        return [(fontname, sym)]

# Legacy Matplotlib font definitions

class TruetypeFonts(Fonts):
    """
    A generic base class for all font setups that use Truetype fonts
    (through FT2Font).
    """
    class CachedFont:
        def __init__(self, font):
            self.font     = font
            self.charmap  = font.get_charmap()
            self.glyphmap = dict(
                [(glyphind, ccode) for ccode, glyphind in self.charmap.iteritems()])

        def __repr__(self):
            return repr(self.font)

    def __init__(self):
        Fonts.__init__(self)
        self.glyphd = {}
        self._fonts = {}

    def destroy(self):
        self.glyphd = None
        Fonts.destroy(self)

    def _get_font(self, font):
        if font in self.fontmap:
            basename = self.fontmap[font]
        else:
            basename = font

        cached_font = self._fonts.get(basename)
        if cached_font is None:
            font = FT2Font(basename)
            cached_font = self.CachedFont(font)
            self._fonts[basename] = cached_font
            self._fonts[font.postscript_name] = cached_font
            self._fonts[font.postscript_name.lower()] = cached_font
        return cached_font

    def _get_offset(self, cached_font, glyph, fontsize, dpi):
        if cached_font.font.postscript_name == 'Cmex10':
            return glyph.height/64.0/2.0 + 256.0/64.0 * dpi/72.0
        return 0.

    def _get_info(self, fontname, font_class, sym, fontsize, dpi):
        key = fontname, font_class, sym, fontsize, dpi
        bunch = self.glyphd.get(key)
        if bunch is not None:
            return bunch

        cached_font, num, symbol_name, fontsize, slanted = \
            self._get_glyph(fontname, font_class, sym, fontsize)

        font = cached_font.font
        font.set_size(fontsize, dpi)
        glyph = font.load_char(num)

        xmin, ymin, xmax, ymax = [val/64.0 for val in glyph.bbox]
        offset = self._get_offset(cached_font, glyph, fontsize, dpi)
        metrics = Bunch(
            advance = glyph.linearHoriAdvance/65536.0,
            height  = glyph.height/64.0,
            width   = glyph.width/64.0,
            xmin    = xmin,
            xmax    = xmax,
            ymin    = ymin+offset,
            ymax    = ymax+offset,
            # iceberg is the equivalent of TeX's "height"
            iceberg = glyph.horiBearingY/64.0 + offset,
            slanted = slanted
            )

        result = self.glyphd[key] = Bunch(
            font            = font,
            fontsize        = fontsize,
            postscript_name = font.postscript_name,
            metrics         = metrics,
            symbol_name     = symbol_name,
            num             = num,
            glyph           = glyph,
            offset          = offset
            )
        return result

    def get_xheight(self, font, fontsize, dpi):
        cached_font = self._get_font(font)
        cached_font.font.set_size(fontsize, dpi)
        pclt = cached_font.font.get_sfnt_table('pclt')
        if pclt is None:
            # Some fonts don't store the xHeight, so we do a poor man's xHeight
            metrics = self.get_metrics(font, rcParams['mathtext.default'], 'x', fontsize, dpi)
            return metrics.iceberg
        xHeight = (pclt['xHeight'] / 64.0) * (fontsize / 12.0) * (dpi / 100.0)
        return xHeight

    def get_underline_thickness(self, font, fontsize, dpi):
        # This function used to grab underline thickness from the font
        # metrics, but that information is just too un-reliable, so it
        # is now hardcoded.
        return ((0.75 / 12.0) * fontsize * dpi) / 72.0

    def get_kern(self, font1, fontclass1, sym1, fontsize1,
                 font2, fontclass2, sym2, fontsize2, dpi):
        if font1 == font2 and fontsize1 == fontsize2:
            info1 = self._get_info(font1, fontclass1, sym1, fontsize1, dpi)
            info2 = self._get_info(font2, fontclass2, sym2, fontsize2, dpi)
            font = info1.font
            return font.get_kerning(info1.num, info2.num, KERNING_DEFAULT) / 64.0
        return Fonts.get_kern(self, font1, fontclass1, sym1, fontsize1,
                              font2, fontclass2, sym2, fontsize2, dpi)

class BakomaFonts(TruetypeFonts):
    """
    Use the Bakoma TrueType fonts for rendering.

    Symbols are strewn about a number of font files, each of which has
    its own proprietary 8-bit encoding.
    """
    _fontmap = { 'cal' : 'cmsy10',
                 'rm'  : 'cmr10',
                 'tt'  : 'cmtt10',
                 'it'  : 'cmmi10',
                 'bf'  : 'cmb10',
                 'sf'  : 'cmss10',
                 'ex'  : 'cmex10'
                 }

    def __init__(self, *args, **kwargs):
        #self._stix_fallback = StixFonts(*args, **kwargs)

        TruetypeFonts.__init__(self, *args, **kwargs)
        self.fontmap = {}
        for key, val in self._fontmap.iteritems():
            fullpath = "/usr/share/fonts/texcm-ttf/%s.ttf" % (val)
            self.fontmap[key] = fullpath
            self.fontmap[val] = fullpath


    _slanted_symbols = set(r"\int \oint".split())

    def _get_glyph(self, fontname, font_class, sym, fontsize):
        symbol_name = None

        if fontname is 'default':
            fontname = 'rm'

        if fontname in self.fontmap and sym in latex_to_bakoma:
            basename, num = latex_to_bakoma[sym]
            slanted = (basename == "cmmi10") or sym in self._slanted_symbols
            try:
                cached_font = self._get_font(basename)
            except RuntimeError:
                pass
            else:
                symbol_name = cached_font.font.get_glyph_name(num)
                num = cached_font.glyphmap[num]
        elif len(sym) == 1:
            slanted = (fontname == "it")
            try:
                cached_font = self._get_font(fontname)
            except RuntimeError:
                pass
            else:
                num = ord(sym)
                gid = cached_font.charmap.get(num)
                if gid is not None:
                    symbol_name = cached_font.font.get_glyph_name(
                        cached_font.charmap[num])

        #if symbol_name is None:
        #    return self._stix_fallback._get_glyph(
        #        fontname, font_class, sym, fontsize)

        return cached_font, num, symbol_name, fontsize, slanted

    # The Bakoma fonts contain many pre-sized alternatives for the
    # delimiters.  The AutoSizedChar class will use these alternatives
    # and select the best (closest sized) glyph.
    _size_alternatives = {
        '('          : [('rm', '('), ('ex', '\xa1'), ('ex', '\xb3'),
                        ('ex', '\xb5'), ('ex', '\xc3')],
        ')'          : [('rm', ')'), ('ex', '\xa2'), ('ex', '\xb4'),
                        ('ex', '\xb6'), ('ex', '\x21')],
        '{'          : [('cal', '{'), ('ex', '\xa9'), ('ex', '\x6e'),
                        ('ex', '\xbd'), ('ex', '\x28')],
        '}'          : [('cal', '}'), ('ex', '\xaa'), ('ex', '\x6f'),
                        ('ex', '\xbe'), ('ex', '\x29')],
        # The fourth size of '[' is mysteriously missing from the BaKoMa
        # font, so I've ommitted it for both '[' and ']'
        '['          : [('rm', '['), ('ex', '\xa3'), ('ex', '\x68'),
                        ('ex', '\x22')],
        ']'          : [('rm', ']'), ('ex', '\xa4'), ('ex', '\x69'),
                        ('ex', '\x23')],
        r'\lfloor'   : [('ex', '\xa5'), ('ex', '\x6a'),
                        ('ex', '\xb9'), ('ex', '\x24')],
        r'\rfloor'   : [('ex', '\xa6'), ('ex', '\x6b'),
                        ('ex', '\xba'), ('ex', '\x25')],
        r'\lceil'    : [('ex', '\xa7'), ('ex', '\x6c'),
                        ('ex', '\xbb'), ('ex', '\x26')],
        r'\rceil'    : [('ex', '\xa8'), ('ex', '\x6d'),
                        ('ex', '\xbc'), ('ex', '\x27')],
        r'\langle'   : [('ex', '\xad'), ('ex', '\x44'),
                        ('ex', '\xbf'), ('ex', '\x2a')],
        r'\rangle'   : [('ex', '\xae'), ('ex', '\x45'),
                        ('ex', '\xc0'), ('ex', '\x2b')],
        r'\__sqrt__' : [('ex', '\x70'), ('ex', '\x71'),
                        ('ex', '\x72'), ('ex', '\x73')],
        r'\backslash': [('ex', '\xb2'), ('ex', '\x2f'),
                        ('ex', '\xc2'), ('ex', '\x2d')],
        r'/'         : [('rm', '/'), ('ex', '\xb1'), ('ex', '\x2e'),
                        ('ex', '\xcb'), ('ex', '\x2c')],
        r'\widehat'  : [('rm', '\x5e'), ('ex', '\x62'), ('ex', '\x63'),
                        ('ex', '\x64')],
        r'\widetilde': [('rm', '\x7e'), ('ex', '\x65'), ('ex', '\x66'),
                        ('ex', '\x67')],
        r'<'         : [('cal', 'h'), ('ex', 'D')],
        r'>'         : [('cal', 'i'), ('ex', 'E')]
        }

    for alias, target in [('\leftparen', '('),
                          ('\rightparent', ')'),
                          ('\leftbrace', '{'),
                          ('\rightbrace', '}'),
                          ('\leftbracket', '['),
                          ('\rightbracket', ']')]:
        _size_alternatives[alias] = _size_alternatives[target]

    def get_sized_alternatives_for_symbol(self, fontname, sym):
        return self._size_alternatives.get(sym, [(fontname, sym)])
