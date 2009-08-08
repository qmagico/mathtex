from __future__ import division
from numpy import inf, isinf

from mathtex.fonts import *

##############################################################################
# TeX-LIKE BOX MODEL
# The following is based directly on the document 'woven' from the
# TeX82 source code.  This information is also available in printed
# form:
#
#    Knuth, Donald E.. 1986.  Computers and Typesetting, Volume B:
#    TeX: The Program.  Addison-Wesley Professional.
#
# The most relevant "chapters" are:
#    Data structures for boxes and their friends
#    Shipping pages out (Ship class)
#    Packaging (hpack and vpack)
#    Data structures for math mode
#    Subroutines for math mode
#    Typesetting math formulas
#
# Many of the docstrings below refer to a numbered "node" in that
# book, e.g. node123

# How much text shrinks when going to the next-smallest level.  GROW_FACTOR
# must be the inverse of SHRINK_FACTOR.
SHRINK_FACTOR   = 0.7
GROW_FACTOR     = 1.0 / SHRINK_FACTOR
# The number of different sizes of chars to use, beyond which they will not
# get any smaller
NUM_SIZE_LEVELS = 6
# Percentage of x-height of additional horiz. space after sub/superscripts
SCRIPT_SPACE    = 0.2
# Percentage of x-height that sub/superscripts drop below the baseline
SUBDROP         = 0.3
# Percentage of x-height that superscripts drop below the baseline
SUP1            = 0.5
# Percentage of x-height that subscripts drop below the baseline
SUB1            = 0.0
# Percentage of x-height that superscripts are offset relative to the subscript
DELTA           = 0.18

class Node(object):
    """
    A node in the TeX box model
    """
    def __init__(self):
        self.size = 0

    def __repr__(self):
        return self.__internal_repr__()

    def __internal_repr__(self):
        return self.__class__.__name__

    def get_kerning(self, next):
        return 0.0

    def shrink(self):
        """
        Shrinks one level smaller.  There are only three levels of
        sizes, after which things will no longer get smaller.
        """
        self.size += 1

    def grow(self):
        """
        Grows one level larger.  There is no limit to how big
        something can get.
        """
        self.size -= 1

    def render(self, x, y):
        pass

class Box(Node):
    """
    Represents any node with a physical location.
    """
    def __init__(self, width, height, depth):
        Node.__init__(self)
        self.width  = width
        self.height = height
        self.depth  = depth

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.width  *= SHRINK_FACTOR
            self.height *= SHRINK_FACTOR
            self.depth  *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        self.width  *= GROW_FACTOR
        self.height *= GROW_FACTOR
        self.depth  *= GROW_FACTOR

    def render(self, x1, y1, x2, y2):
        pass

class Vbox(Box):
    """
    A box with only height (zero width).
    """
    def __init__(self, height, depth):
        Box.__init__(self, 0., height, depth)

class Hbox(Box):
    """
    A box with only width (zero height and depth).
    """
    def __init__(self, width):
        Box.__init__(self, width, 0., 0.)

class Char(Node):
    """
    Represents a single character.  Unlike TeX, the font information
    and metrics are stored with each :class:`Char` to make it easier
    to lookup the font metrics when needed.  Note that TeX boxes have
    a width, height, and depth, unlike Type1 and Truetype which use a
    full bounding box and an advance in the x-direction.  The metrics
    must be converted to the TeX way, and the advance (if different
    from width) must be converted into a :class:`Kern` node when the
    :class:`Char` is added to its parent :class:`Hlist`.
    """
    def __init__(self, c, state):
        Node.__init__(self)
        self.c = c
        self.font_output = state.font_output
        assert isinstance(state.font, (str, unicode, int))
        self.font = state.font
        self.font_class = state.font_class
        self.fontsize = state.fontsize
        self.dpi = state.dpi
        # The real width, height and depth will be set during the
        # pack phase, after we know the real fontsize
        self._update_metrics()

    def __internal_repr__(self):
        return '`%s`' % self.c

    def _update_metrics(self):
        metrics = self._metrics = self.font_output.get_metrics(
            self.font, self.font_class, self.c, self.fontsize, self.dpi)
        if self.c == ' ':
            self.width = metrics.advance
        else:
            self.width = metrics.width
        self.height = metrics.iceberg
        self.depth = -(metrics.iceberg - metrics.height)

    def is_slanted(self):
        return self._metrics.slanted

    def get_kerning(self, next):
        """
        Return the amount of kerning between this and the given
        character.  Called when characters are strung together into
        :class:`Hlist` to create :class:`Kern` nodes.
        """
        advance = self._metrics.advance - self.width
        kern = 0.
        if isinstance(next, Char):
            kern = self.font_output.get_kern(
                self.font, self.font_class, self.c, self.fontsize,
                next.font, next.font_class, next.c, next.fontsize,
                self.dpi)
        return advance + kern

    def render(self, x, y):
        """
        Render the character to the canvas
        """
        info = self.font_output._get_info(self.font, self.font_class,
                                          self.c, self.fontsize, self.dpi)
        return (x, y, info)

    def bbox(self):
        info = self.font_output._get_info(self.font, self.font_class,
        self.c, self.fontsize, self.dpi)
        return [info.metrics.xmin,
                info.metrics.ymin,
                info.metrics.xmax,
                info.metrics.ymax]

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.fontsize *= SHRINK_FACTOR
            self.width    *= SHRINK_FACTOR
            self.height   *= SHRINK_FACTOR
            self.depth    *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        self.fontsize *= GROW_FACTOR
        self.width    *= GROW_FACTOR
        self.height   *= GROW_FACTOR
        self.depth    *= GROW_FACTOR

class Accent(Char):
    """
    The font metrics need to be dealt with differently for accents,
    since they are already offset correctly from the baseline in
    TrueType fonts.
    """
    def _update_metrics(self):
        metrics = self._metrics = self.font_output.get_metrics(
            self.font, self.font_class, self.c, self.fontsize, self.dpi)
        self.width = metrics.xmax - metrics.xmin
        self.height = metrics.ymax - metrics.ymin
        self.depth = 0

    def shrink(self):
        Char.shrink(self)
        self._update_metrics()

    def grow(self):
        Char.grow(self)
        self._update_metrics()

    def render(self, x, y):
        """
        Render the character to the canvas.
        """
        info = self.font_output._get_info(self.font, self.font_class,
                                          self.c, self.fontsize, self.dpi)
        return (x - self._metrics.xmin,
                y + self._metrics.ymin,
                info)

class List(Box):
    """
    A list of nodes (either horizontal or vertical).
    """
    def __init__(self, elements):
        Box.__init__(self, 0., 0., 0.)
        self.shift_amount = 0.   # An arbitrary offset
        self.children     = elements # The child nodes of this list
        # The following parameters are set in the vpack and hpack functions
        self.glue_set     = 0.   # The glue setting of this list
        self.glue_sign    = 0    # 0: normal, -1: shrinking, 1: stretching
        self.glue_order   = 0    # The order of infinity (0 - 3) for the glue

    def __repr__(self):
        return '[%s <%.02f %.02f %.02f %.02f> %s]' % (
            self.__internal_repr__(),
            self.width, self.height,
            self.depth, self.shift_amount,
            ' '.join([repr(x) for x in self.children]))

    def _determine_order(self, totals):
        """
        A helper function to determine the highest order of glue
        used by the members of this list.  Used by vpack and hpack.
        """
        o = 0
        for i in range(len(totals) - 1, 0, -1):
            if totals[i] != 0.0:
                o = i
                break
        return o

    def _set_glue(self, x, sign, totals, error_type):
        o = self._determine_order(totals)
        self.glue_order = o
        self.glue_sign = sign
        if totals[o] != 0.:
            self.glue_set = x / totals[o]
        else:
            self.glue_sign = 0
            self.glue_ratio = 0.
        if o == 0:
            if len(self.children):
                warn("%s %s: %r" % (error_type, self.__class__.__name__, self))

    def shrink(self):
        for child in self.children:
            child.shrink()
        Box.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.shift_amount *= SHRINK_FACTOR
            self.glue_set     *= SHRINK_FACTOR

    def grow(self):
        for child in self.children:
            child.grow()
        Box.grow(self)
        self.shift_amount *= GROW_FACTOR
        self.glue_set     *= GROW_FACTOR

class Hlist(List):
    """
    A horizontal list of boxes.
    """
    def __init__(self, elements, w=0., m='additional', do_kern=True):
        List.__init__(self, elements)
        if do_kern:
            self.kern()
        self.hpack()

    def kern(self):
        """
        Insert :class:`Kern` nodes between :class:`Char` nodes to set
        kerning.  The :class:`Char` nodes themselves determine the
        amount of kerning they need (in :meth:`~Char.get_kerning`),
        and this function just creates the linked list in the correct
        way.
        """
        new_children = []
        num_children = len(self.children)
        if num_children:
            for i in range(num_children):
                elem = self.children[i]
                if i < num_children - 1:
                    next = self.children[i + 1]
                else:
                    next = None

                new_children.append(elem)
                kerning_distance = elem.get_kerning(next)
                if kerning_distance != 0.:
                    kern = Kern(kerning_distance)
                    new_children.append(kern)
            self.children = new_children

    # This is a failed experiment to fake cross-font kerning.
#     def get_kerning(self, next):
#         if len(self.children) >= 2 and isinstance(self.children[-2], Char):
#             if isinstance(next, Char):
#                 print "CASE A"
#                 return self.children[-2].get_kerning(next)
#             elif isinstance(next, Hlist) and len(next.children) and isinstance(next.children[0], Char):
#                 print "CASE B"
#                 result = self.children[-2].get_kerning(next.children[0])
#                 print result
#                 return result
#         return 0.0

    def hpack(self, w=0., m='additional'):
        """
        The main duty of :meth:`hpack` is to compute the dimensions of
        the resulting boxes, and to adjust the glue if one of those
        dimensions is pre-specified.  The computed sizes normally
        enclose all of the material inside the new box; but some items
        may stick out if negative glue is used, if the box is
        overfull, or if a ``\\vbox`` includes other boxes that have
        been shifted left.

          - *w*: specifies a width

          - *m*: is either 'exactly' or 'additional'.

        Thus, ``hpack(w, 'exactly')`` produces a box whose width is
        exactly *w*, while ``hpack(w, 'additional')`` yields a box
        whose width is the natural width plus *w*.  The default values
        produce a box with the natural width.
        """
        # I don't know why these get reset in TeX.  Shift_amount is pretty
        # much useless if we do.
        #self.shift_amount = 0.
        h = 0.
        d = 0.
        x = 0.
        total_stretch = [0.] * 4
        total_shrink = [0.] * 4
        for p in self.children:
            if isinstance(p, Char):
                x += p.width
                h = max(h, p.height)
                d = max(d, p.depth)
            elif isinstance(p, Box):
                x += p.width
                if not isinf(p.height) and not isinf(p.depth):
                    s = getattr(p, 'shift_amount', 0.)
                    h = max(h, p.height - s)
                    d = max(d, p.depth + s)
            elif isinstance(p, Glue):
                glue_spec = p.glue_spec
                x += glue_spec.width
                total_stretch[glue_spec.stretch_order] += glue_spec.stretch
                total_shrink[glue_spec.shrink_order] += glue_spec.shrink
            elif isinstance(p, Kern):
                x += p.width
        self.height = h
        self.depth = d

        if m == 'additional':
            w += x
        self.width = w
        x = w - x

        if x == 0.:
            self.glue_sign = 0
            self.glue_order = 0
            self.glue_ratio = 0.
            return
        if x > 0.:
            self._set_glue(x, 1, total_stretch, "Overfull")
        else:
            self._set_glue(x, -1, total_shrink, "Underfull")

class Vlist(List):
    """
    A vertical list of boxes.
    """
    def __init__(self, elements, h=0., m='additional'):
        List.__init__(self, elements)
        self.vpack()

    def vpack(self, h=0., m='additional', l=float(inf)):
        """
        The main duty of :meth:`vpack` is to compute the dimensions of
        the resulting boxes, and to adjust the glue if one of those
        dimensions is pre-specified.

          - *h*: specifies a height
          - *m*: is either 'exactly' or 'additional'.
          - *l*: a maximum height

        Thus, ``vpack(h, 'exactly')`` produces a box whose height is
        exactly *h*, while ``vpack(h, 'additional')`` yields a box
        whose height is the natural height plus *h*.  The default
        values produce a box with the natural width.
        """
        # I don't know why these get reset in TeX.  Shift_amount is pretty
        # much useless if we do.
        # self.shift_amount = 0.
        w = 0.
        d = 0.
        x = 0.
        total_stretch = [0.] * 4
        total_shrink = [0.] * 4
        for p in self.children:
            if isinstance(p, Box):
                x += d + p.height
                d = p.depth
                if not isinf(p.width):
                    s = getattr(p, 'shift_amount', 0.)
                    w = max(w, p.width + s)
            elif isinstance(p, Glue):
                x += d
                d = 0.
                glue_spec = p.glue_spec
                x += glue_spec.width
                total_stretch[glue_spec.stretch_order] += glue_spec.stretch
                total_shrink[glue_spec.shrink_order] += glue_spec.shrink
            elif isinstance(p, Kern):
                x += d + p.width
                d = 0.
            elif isinstance(p, Char):
                raise RuntimeError("Internal mathtext error: Char node found in Vlist.")

        self.width = w
        if d > l:
            x += d - l
            self.depth = l
        else:
            self.depth = d

        if m == 'additional':
            h += x
        self.height = h
        x = h - x

        if x == 0:
            self.glue_sign = 0
            self.glue_order = 0
            self.glue_ratio = 0.
            return

        if x > 0.:
            self._set_glue(x, 1, total_stretch, "Overfull")
        else:
            self._set_glue(x, -1, total_shrink, "Underfull")

class Rule(Box):
    """
    A :class:`Rule` node stands for a solid black rectangle; it has
    *width*, *depth*, and *height* fields just as in an
    :class:`Hlist`. However, if any of these dimensions is inf, the
    actual value will be determined by running the rule up to the
    boundary of the innermost enclosing box. This is called a "running
    dimension." The width is never running in an :class:`Hlist`; the
    height and depth are never running in a :class:`Vlist`.
    """
    def __init__(self, width, height, depth, state):
        Box.__init__(self, width, height, depth)

    def render(self, x, y, w, h):
        return (x, y, x + w, y + h)

    def bbox(self, x, y, w, h):
        return [x, y, x + w, y + h]

class Hrule(Rule):
    """
    Convenience class to create a horizontal rule.
    """
    def __init__(self, state, thickness=None):
        if thickness is None:
            thickness = state.font_output.get_underline_thickness(
                state.font, state.fontsize, state.dpi)
        height = depth = thickness * 0.5
        Rule.__init__(self, inf, height, depth, state)

class Vrule(Rule):
    """
    Convenience class to create a vertical rule.
    """
    def __init__(self, state):
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        Rule.__init__(self, thickness, inf, inf, state)

class Glue(Node):
    """
    Most of the information in this object is stored in the underlying
    :class:`GlueSpec` class, which is shared between multiple glue objects.  (This
    is a memory optimization which probably doesn't matter anymore, but it's
    easier to stick to what TeX does.)
    """
    def __init__(self, glue_type, copy=False):
        Node.__init__(self)
        self.glue_subtype   = 'normal'
        if isinstance(glue_type, (str, unicode)):
            glue_spec = GlueSpec.factory(glue_type)
        elif isinstance(glue_type, GlueSpec):
            glue_spec = glue_type
        else:
            raise ArgumentError("glue_type must be a glue spec name or instance.")
        if copy:
            glue_spec = glue_spec.copy()
        self.glue_spec      = glue_spec

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            if self.glue_spec.width != 0.:
                self.glue_spec = self.glue_spec.copy()
                self.glue_spec.width *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        if self.glue_spec.width != 0.:
            self.glue_spec = self.glue_spec.copy()
            self.glue_spec.width *= GROW_FACTOR

class GlueSpec(object):
    """
    See :class:`Glue`.
    """
    def __init__(self, width=0., stretch=0., stretch_order=0, shrink=0., shrink_order=0):
        self.width         = width
        self.stretch       = stretch
        self.stretch_order = stretch_order
        self.shrink        = shrink
        self.shrink_order  = shrink_order

    def copy(self):
        return GlueSpec(
            self.width,
            self.stretch,
            self.stretch_order,
            self.shrink,
            self.shrink_order)

    def factory(cls, glue_type):
        return cls._types[glue_type]
    factory = classmethod(factory)

GlueSpec._types = {
    'fil':         GlueSpec(0., 1., 1, 0., 0),
    'fill':        GlueSpec(0., 1., 2, 0., 0),
    'filll':       GlueSpec(0., 1., 3, 0., 0),
    'neg_fil':     GlueSpec(0., 0., 0, 1., 1),
    'neg_fill':    GlueSpec(0., 0., 0, 1., 2),
    'neg_filll':   GlueSpec(0., 0., 0, 1., 3),
    'empty':       GlueSpec(0., 0., 0, 0., 0),
    'ss':          GlueSpec(0., 1., 1, -1., 1)
}

# Some convenient ways to get common kinds of glue

class Fil(Glue):
    def __init__(self):
        Glue.__init__(self, 'fil')

class Fill(Glue):
    def __init__(self):
        Glue.__init__(self, 'fill')

class Filll(Glue):
    def __init__(self):
        Glue.__init__(self, 'filll')

class NegFil(Glue):
    def __init__(self):
        Glue.__init__(self, 'neg_fil')

class NegFill(Glue):
    def __init__(self):
        Glue.__init__(self, 'neg_fill')

class NegFilll(Glue):
    def __init__(self):
        Glue.__init__(self, 'neg_filll')

class SsGlue(Glue):
    def __init__(self):
        Glue.__init__(self, 'ss')

class HCentered(Hlist):
    """
    A convenience class to create an :class:`Hlist` whose contents are
    centered within its enclosing box.
    """
    def __init__(self, elements):
        Hlist.__init__(self, [SsGlue()] + elements + [SsGlue()],
                       do_kern=False)

class VCentered(Hlist):
    """
    A convenience class to create a :class:`Vlist` whose contents are
    centered within its enclosing box.
    """
    def __init__(self, elements):
        Vlist.__init__(self, [SsGlue()] + elements + [SsGlue()])

class Kern(Node):
    """
    A :class:`Kern` node has a width field to specify a (normally
    negative) amount of spacing. This spacing correction appears in
    horizontal lists between letters like A and V when the font
    designer said that it looks better to move them closer together or
    further apart. A kern node can also appear in a vertical list,
    when its *width* denotes additional spacing in the vertical
    direction.
    """
    def __init__(self, width):
        Node.__init__(self)
        self.width = width

    def __repr__(self):
        return "k%.02f" % self.width

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.width *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        self.width *= GROW_FACTOR

class SubSuperCluster(Hlist):
    """
    :class:`SubSuperCluster` is a sort of hack to get around that fact
    that this code do a two-pass parse like TeX.  This lets us store
    enough information in the hlist itself, namely the nucleus, sub-
    and super-script, such that if another script follows that needs
    to be attached, it can be reconfigured on the fly.
    """
    def __init__(self):
        self.nucleus = None
        self.sub = None
        self.super = None
        Hlist.__init__(self, [])

class AutoHeightChar(Hlist):
    """
    :class:`AutoHeightChar` will create a character as close to the
    given height and depth as possible.  When using a font with
    multiple height versions of some characters (such as the BaKoMa
    fonts), the correct glyph will be selected, otherwise this will
    always just return a scaled version of the glyph.
    """
    def __init__(self, c, height, depth, state, always=False):
        alternatives = state.font_output.get_sized_alternatives_for_symbol(
            state.font, c)

        state = state.copy()
        target_total = height + depth
        for fontname, sym in alternatives:
            state.font = fontname
            char = Char(sym, state)
            if char.height + char.depth >= target_total:
                break

        factor = target_total / (char.height + char.depth)
        state.fontsize *= factor
        char = Char(sym, state)

        shift = (depth - char.depth)
        Hlist.__init__(self, [char])
        self.shift_amount = shift

class AutoWidthChar(Hlist):
    """
    :class:`AutoWidthChar` will create a character as close to the
    given width as possible.  When using a font with multiple width
    versions of some characters (such as the BaKoMa fonts), the
    correct glyph will be selected, otherwise this will always just
    return a scaled version of the glyph.
    """
    def __init__(self, c, width, state, always=False, char_class=Char):
        alternatives = state.font_output.get_sized_alternatives_for_symbol(
            state.font, c)

        state = state.copy()
        for fontname, sym in alternatives:
            state.font = fontname
            char = char_class(sym, state)
            if char.width >= width:
                break

        factor = width / char.width
        state.fontsize *= factor
        char = char_class(sym, state)

        Hlist.__init__(self, [char])
        self.width = char.width

class Ship(object):
    """
    Once the boxes have been set up, this sends them to output.  Since
    boxes can be inside of boxes inside of boxes, the main work of
    :class:`Ship` is done by two mutually recursive routines,
    :meth:`hlist_out` and :meth:`vlist_out`, which traverse the
    :class:`Hlist` nodes and :class:`Vlist` nodes inside of horizontal
    and vertical boxes.  The global variables used in TeX to store
    state as it processes have become member variables here.
    """
    def __call__(self, ox, oy, box):
        self.max_push    = 0 # Deepest nesting of push commands so far
        self.cur_s       = 0
        self.cur_v       = 0.
        self.cur_h       = 0.
        self.off_h       = ox
        self.off_v       = oy + box.height

        self.rects = []
        self.glyphs = []
        self.bbox = [0, 0, 0, 0]

        self.hlist_out(box)

        return (self.rects, self.glyphs, self.bbox)

    @staticmethod
    def clamp(value):
        if value < -1000000000.:
            return -1000000000.
        if value > 1000000000.:
            return 1000000000.
        return value

    def _update_bbox(self, x1, y1, x2, y2):
        self.bbox = [min(self.bbox[0], x1),
                     min(self.bbox[1], y1),
                     max(self.bbox[2], x2),
                     max(self.bbox[3], y2)]

    def hlist_out(self, box):
        cur_g         = 0
        cur_glue      = 0.
        glue_order    = box.glue_order
        glue_sign     = box.glue_sign
        base_line     = self.cur_v
        left_edge     = self.cur_h
        self.cur_s    += 1
        self.max_push = max(self.cur_s, self.max_push)
        clamp         = self.clamp

        for p in box.children:
            if isinstance(p, Char):
                ox, oy = self.cur_h + self.off_h, self.cur_v + self.off_v
                bbox = p.bbox()
                self.glyphs.append(p.render(ox, oy))
                self._update_bbox(ox + bbox[0], oy - bbox[1],
                                  ox + bbox[2], oy - bbox[3])
                self.cur_h += p.width
            elif isinstance(p, Kern):
                self.cur_h += p.width
            elif isinstance(p, List):
                # node623
                if len(p.children) == 0:
                    self.cur_h += p.width
                else:
                    edge = self.cur_h
                    self.cur_v = base_line + p.shift_amount
                    if isinstance(p, Hlist):
                        self.hlist_out(p)
                    else:
                        # p.vpack(box.height + box.depth, 'exactly')
                        self.vlist_out(p)
                    self.cur_h = edge + p.width
                    self.cur_v = base_line
            elif isinstance(p, Box):
                # node624
                rule_height = p.height
                rule_depth  = p.depth
                rule_width  = p.width
                if isinf(rule_height):
                    rule_height = box.height
                if isinf(rule_depth):
                    rule_depth = box.depth
                if rule_height > 0 and rule_width > 0:
                    self.cur_v = baseline + rule_depth
                    ox, oy = self.cur_h + self.off_h, self.cur_v + self.off_v
                    self.rects.append(p.render(ox, oy, rule_width, rule_height))
                    self._update_bbox(p.bbox(ox, oy, rule_width, rule_height))
                    self.cur_v = baseline
                self.cur_h += rule_width
            elif isinstance(p, Glue):
                # node625
                glue_spec = p.glue_spec
                rule_width = glue_spec.width - cur_g
                if glue_sign != 0: # normal
                    if glue_sign == 1: # stretching
                        if glue_spec.stretch_order == glue_order:
                            cur_glue += glue_spec.stretch
                            cur_g = round(clamp(float(box.glue_set) * cur_glue))
                    elif glue_spec.shrink_order == glue_order:
                        cur_glue += glue_spec.shrink
                        cur_g = round(clamp(float(box.glue_set) * cur_glue))
                rule_width += cur_g
                self.cur_h += rule_width
        self.cur_s -= 1

    def vlist_out(self, box):
        cur_g         = 0
        cur_glue      = 0.
        glue_order    = box.glue_order
        glue_sign     = box.glue_sign
        self.cur_s    += 1
        self.max_push = max(self.max_push, self.cur_s)
        left_edge     = self.cur_h
        self.cur_v    -= box.height
        top_edge      = self.cur_v
        clamp         = self.clamp

        for p in box.children:
            if isinstance(p, Kern):
                self.cur_v += p.width
            elif isinstance(p, List):
                if len(p.children) == 0:
                    self.cur_v += p.height + p.depth
                else:
                    self.cur_v += p.height
                    self.cur_h = left_edge + p.shift_amount
                    save_v = self.cur_v
                    p.width = box.width
                    if isinstance(p, Hlist):
                        self.hlist_out(p)
                    else:
                        self.vlist_out(p)
                    self.cur_v = save_v + p.depth
                    self.cur_h = left_edge
            elif isinstance(p, Box):
                rule_height = p.height
                rule_depth = p.depth
                rule_width = p.width
                if isinf(rule_width):
                    rule_width = box.width
                rule_height += rule_depth
                if rule_height > 0 and rule_depth > 0:
                    self.cur_v += rule_height
                    ox, oy = self.cur_h + self.off_h, self.cur_v + self.off_v
                    rect = p.render(ox, oy, rule_width, rule_height)
                    if rect is not None:
                        self.rects.append(rect)
                        self._update_bbox(ox, oy, ox + rule_width, oy + rule_height)
            elif isinstance(p, Glue):
                glue_spec = p.glue_spec
                rule_height = glue_spec.width - cur_g
                if glue_sign != 0: # normal
                    if glue_sign == 1: # stretching
                        if glue_spec.stretch_order == glue_order:
                            cur_glue += glue_spec.stretch
                            cur_g = round(clamp(float(box.glue_set) * cur_glue))
                    elif glue_spec.shrink_order == glue_order: # shrinking
                        cur_glue += glue_spec.shrink
                        cur_g = round(clamp(float(box.glue_set) * cur_glue))
                rule_height += cur_g
                self.cur_v += rule_height
            elif isinstance(p, Char):
                raise RuntimeError("Internal mathtext error: Char node found in vlist")
        self.cur_s -= 1

ship = Ship()
