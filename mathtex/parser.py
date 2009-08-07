from mathtex.pyparsing import Combine, Group, Optional, Forward, Literal, \
    OneOrMore, ZeroOrMore, ParseException, Empty, ParseResults, Suppress, \
    oneOf, StringEnd, FollowedBy, Regex, ParserElement, ParseFatalException
# Enable packrat parsing, this gives a ~2x speed-up
ParserElement.enablePackrat()

from mathtex.boxmodel import *
from mathtex.fonts import *

try:
    from mathtex.ft2font import FT2Font
except ImportError:
    from matplotlib.ft2font import FT2Font

##############################################################################
# PARSER

def Error(msg):
    """
    Helper class to raise parser errors.
    """
    def raise_error(s, loc, toks):
        raise ParseFatalException(msg + "\n" + s)

    empty = Empty()
    empty.setParseAction(raise_error)
    return empty

class MathtexParser(object):
    """
    This is the pyparsing-based parser for math expressions.  It
    actually parses full strings *containing* math expressions, in
    that raw text may also appear outside of pairs of ``$``.

    The grammar is based directly on that in TeX, though it cuts a few
    corners.
    """
    _binary_operators = set(r'''
      + *
      \pm             \sqcap                   \rhd
      \mp             \sqcup                   \unlhd
      \times          \vee                     \unrhd
      \div            \wedge                   \oplus
      \ast            \setminus                \ominus
      \star           \wr                      \otimes
      \circ           \diamond                 \oslash
      \bullet         \bigtriangleup           \odot
      \cdot           \bigtriangledown         \bigcirc
      \cap            \triangleleft            \dagger
      \cup            \triangleright           \ddagger
      \uplus          \lhd                     \amalg'''.split())

    _relation_symbols = set(r'''
      = < > :
      \leq            \geq             \equiv           \models
      \prec           \succ            \sim             \perp
      \preceq         \succeq          \simeq           \mid
      \ll             \gg              \asymp           \parallel
      \subset         \supset          \approx          \bowtie
      \subseteq       \supseteq        \cong            \Join
      \sqsubset       \sqsupset        \neq             \smile
      \sqsubseteq     \sqsupseteq      \doteq           \frown
      \in             \ni              \propto
      \vdash          \dashv           \dots'''.split())

    _arrow_symbols = set(r'''
      \leftarrow              \longleftarrow           \uparrow
      \Leftarrow              \Longleftarrow           \Uparrow
      \rightarrow             \longrightarrow          \downarrow
      \Rightarrow             \Longrightarrow          \Downarrow
      \leftrightarrow         \longleftrightarrow      \updownarrow
      \Leftrightarrow         \Longleftrightarrow      \Updownarrow
      \mapsto                 \longmapsto              \nearrow
      \hookleftarrow          \hookrightarrow          \searrow
      \leftharpoonup          \rightharpoonup          \swarrow
      \leftharpoondown        \rightharpoondown        \nwarrow
      \rightleftharpoons      \leadsto'''.split())

    _spaced_symbols = _binary_operators | _relation_symbols | _arrow_symbols

    _punctuation_symbols = set(r', ; . ! \ldotp \cdotp'.split())

    _overunder_symbols = set(r'''
       \sum \prod \coprod \bigcap \bigcup \bigsqcup \bigvee
       \bigwedge \bigodot \bigotimes \bigoplus \biguplus
       '''.split())

    _overunder_functions = set(
        r"lim liminf limsup sup max min".split())

    _dropsub_symbols = set(r'''\int \oint'''.split())

    _fontnames = set("rm cal it tt sf bf default bb frak circled scr regular".split())

    _function_names = set("""
      arccos csc ker min arcsin deg lg Pr arctan det lim sec arg dim
      liminf sin cos exp limsup sinh cosh gcd ln sup cot hom log tan
      coth inf max tanh""".split())

    _ambiDelim = set(r"""
      | \| / \backslash \uparrow \downarrow \updownarrow \Uparrow
      \Downarrow \Updownarrow .""".split())

    _leftDelim = set(r"( [ { < \lfloor \langle \lceil".split())

    _rightDelim = set(r") ] } > \rfloor \rangle \rceil".split())

    def __init__(self):
        # All forward declarations are here
        font = Forward().setParseAction(self.font).setName("font")
        latexfont = Forward()
        subsuper = Forward().setParseAction(self.subsuperscript).setName("subsuper")
        placeable = Forward().setName("placeable")
        simple = Forward().setName("simple")
        autoDelim = Forward().setParseAction(self.auto_sized_delimiter)
        self._expression = Forward().setParseAction(self.finish).setName("finish")

        float        = Regex(r"[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)")

        lbrace       = Literal('{').suppress()
        rbrace       = Literal('}').suppress()
        start_group  = (Optional(latexfont) - lbrace)
        start_group.setParseAction(self.start_group)
        end_group    = rbrace.copy()
        end_group.setParseAction(self.end_group)

        bslash       = Literal('\\')

        accent       = oneOf(self._accent_map.keys() +
                             list(self._wide_accents))

        function     = oneOf(list(self._function_names))

        fontname     = oneOf(list(self._fontnames))
        latex2efont  = oneOf(['math' + x for x in self._fontnames])

        space        =(FollowedBy(bslash)
                     + oneOf([r'\ ',
                              r'\/',
                              r'\,',
                              r'\;',
                              r'\quad',
                              r'\qquad',
                              r'\!'])
                      ).setParseAction(self.space).setName('space')

        customspace  =(Literal(r'\hspace')
                     - (( lbrace
                        - float
                        - rbrace
                       ) | Error(r"Expected \hspace{n}"))
                     ).setParseAction(self.customspace).setName('customspace')

        unicode_range = u"\U00000080-\U0001ffff"
        symbol       =(Regex(UR"([a-zA-Z0-9 +\-*/<>=:,.;!'@()\[\]|%s])|(\\[%%${}\[\]_|])" % unicode_range)
                     | (Combine(
                         bslash
                       + oneOf(tex2uni.keys())
                       ) + FollowedBy(Regex("[^a-zA-Z]")))
                     ).setParseAction(self.symbol).leaveWhitespace()

        c_over_c     =(Suppress(bslash)
                     + oneOf(self._char_over_chars.keys())
                     ).setParseAction(self.char_over_chars)

        accent       = Group(
                         Suppress(bslash)
                       + accent
                       - placeable
                     ).setParseAction(self.accent).setName("accent")

        function     =(Suppress(bslash)
                     + function
                     ).setParseAction(self.function).setName("function")

        group        = Group(
                         start_group
                       + ZeroOrMore(
                           autoDelim
                         ^ simple)
                       - end_group
                     ).setParseAction(self.group).setName("group")

        font        <<(Suppress(bslash)
                     + fontname)

        latexfont   <<(Suppress(bslash)
                     + latex2efont)

        frac         = Group(
                       Suppress(Literal(r"\frac"))
                     + ((group + group)
                        | Error(r"Expected \frac{num}{den}"))
                     ).setParseAction(self.frac).setName("frac")

        stackrel     = Group(
                       Suppress(Literal(r"\stackrel"))
                     + ((group + group)
                        | Error(r"Expected \stackrel{num}{den}"))
                     ).setParseAction(self.stackrel).setName("stackrel")

        binom        = Group(
                       Suppress(Literal(r"\binom"))
                     + ((group + group)
                        | Error(r"Expected \binom{num}{den}"))
                     ).setParseAction(self.binom).setName("binom")

        ambiDelim    = oneOf(list(self._ambiDelim))
        leftDelim    = oneOf(list(self._leftDelim))
        rightDelim   = oneOf(list(self._rightDelim))
        rightDelimSafe = oneOf(list(self._rightDelim - set(['}'])))
        genfrac      = Group(
                       Suppress(Literal(r"\genfrac"))
                     + ((Suppress(Literal('{')) +
                         oneOf(list(self._ambiDelim | self._leftDelim | set(['']))) +
                         Suppress(Literal('}')) +
                         Suppress(Literal('{')) +
                         oneOf(list(self._ambiDelim |
                                    (self._rightDelim - set(['}'])) |
                                    set(['', r'\}']))) +
                         Suppress(Literal('}')) +
                         Suppress(Literal('{')) +
                         Regex("[0-9]*(\.?[0-9]*)?") +
                         Suppress(Literal('}')) +
                         group + group + group)
                        | Error(r"Expected \genfrac{ldelim}{rdelim}{rulesize}{style}{num}{den}"))
                     ).setParseAction(self.genfrac).setName("genfrac")

        sqrt         = Group(
                       Suppress(Literal(r"\sqrt"))
                     + Optional(
                         Suppress(Literal("["))
                       - Regex("[0-9]+")
                       - Suppress(Literal("]")),
                         default = None
                       )
                     + (group | Error("Expected \sqrt{value}"))
                     ).setParseAction(self.sqrt).setName("sqrt")

        operatorname = Group(
                       Suppress(Literal(r"\operatorname"))
                     + ((start_group + Regex("[A-Za-z]+") + end_group)
                        | Error("Expected \operatorname{value}"))
                     ).setParseAction(self.operatorname).setName("operatorname")

        placeable   <<(function
                     ^ (c_over_c | symbol)
                     ^ accent
                     ^ group
                     ^ frac
                     ^ stackrel
                     ^ binom
                     ^ genfrac
                     ^ sqrt
                     ^ operatorname
                     )

        simple      <<(space
                     | customspace
                     | font
                     | subsuper
                     )

        subsuperop   = oneOf(["_", "^"])

        subsuper    << Group(
                         ( Optional(placeable)
                         + OneOrMore(
                             subsuperop
                           - placeable
                           )
                         )
                       | placeable
                     )

        autoDelim   <<(Suppress(Literal(r"\left"))
                     + ((leftDelim | ambiDelim) | Error("Expected a delimiter"))
                     + Group(
                         autoDelim
                       ^ OneOrMore(simple))
                     + Suppress(Literal(r"\right"))
                     + ((rightDelim | ambiDelim) | Error("Expected a delimiter"))
                     )

        math         = OneOrMore(
                       autoDelim
                     ^ simple
                     ).setParseAction(self.math).setName("math")

        math_delim   = ~bslash + Literal('$')

        non_math     = Regex(r"(?:(?:\\[$])|[^$])*"
                     ).setParseAction(self.non_math).setName("non_math").leaveWhitespace()

        self._expression << (
            non_math
          + ZeroOrMore(
                Suppress(math_delim)
              + Optional(math)
              + (Suppress(math_delim)
                 | Error("Expected end of math '$'"))
              + non_math
            )
          ) + StringEnd()

        self.clear()

    def clear(self):
        """
        Clear any state before parsing.
        """
        self._expr = None
        self._state_stack = None
        self._em_width_cache = {}

    def parse(self, s, fonts_object, fontsize, dpi):
        """
        Parse expression *s* using the given *fonts_object* for
        output, at the given *fontsize* and *dpi*.

        Returns the parse tree of :class:`Node` instances.
        """
        self._default_style = fonts_object.default_style
        self._state_stack = [self.State(fonts_object, 'default', 'rm', fontsize, dpi)]
        try:
            self._expression.parseString(s)
        except (ParseException, ParseFatalException), err:
            raise ValueError(str(err))

        return self._expr

    # The state of the parser is maintained in a stack.  Upon
    # entering and leaving a group { } or math/non-math, the stack
    # is pushed and popped accordingly.  The current state always
    # exists in the top element of the stack.
    class State(object):
        """
        Stores the state of the parser.

        States are pushed and popped from a stack as necessary, and
        the "current" state is always at the top of the stack.
        """
        def __init__(self, font_output, font, font_class, fontsize, dpi):
            self.font_output = font_output
            self._font = font
            self.font_class = font_class
            self.fontsize = fontsize
            self.dpi = dpi

        def copy(self):
            return MathtexParser.State(
                self.font_output,
                self.font,
                self.font_class,
                self.fontsize,
                self.dpi)

        def _get_font(self):
            return self._font
        def _set_font(self, name):
            if name in ('rm', 'it', 'bf'):
                self.font_class = name
            self._font = name
        font = property(_get_font, _set_font)

    def get_state(self):
        """
        Get the current :class:`State` of the parser.
        """
        return self._state_stack[-1]

    def pop_state(self):
        """
        Pop a :class:`State` off of the stack.
        """
        self._state_stack.pop()

    def push_state(self):
        """
        Push a new :class:`State` onto the stack which is just a copy
        of the current state.
        """
        self._state_stack.append(self.get_state().copy())

    def finish(self, s, loc, toks):
        #~ print "finish", toks
        self._expr = Hlist(toks)
        return [self._expr]

    def math(self, s, loc, toks):
        #~ print "math", toks
        hlist = Hlist(toks)
        self.pop_state()
        return [hlist]

    def non_math(self, s, loc, toks):
        #~ print "non_math", toks
        s = toks[0].replace(r'\$', '$')
        symbols = [Char(c, self.get_state()) for c in s]
        hlist = Hlist(symbols)
        # We're going into math now, so set font to 'it'
        self.push_state()
        self.get_state().font =  self._default_style
        return [hlist]

    def _make_space(self, percentage):
        # All spaces are relative to em width
        state = self.get_state()
        key = (state.font, state.fontsize, state.dpi)
        width = self._em_width_cache.get(key)
        if width is None:
            metrics = state.font_output.get_metrics(
                state.font, self._default_style, 'm', state.fontsize, state.dpi)
            width = metrics.advance
            self._em_width_cache[key] = width
        return Kern(width * percentage)

    _space_widths = { r'\ '      : 0.3,
                      r'\,'      : 0.4,
                      r'\;'      : 0.8,
                      r'\quad'   : 1.6,
                      r'\qquad'  : 3.2,
                      r'\!'      : -0.4,
                      r'\/'      : 0.4 }
    def space(self, s, loc, toks):
        assert(len(toks)==1)
        num = self._space_widths[toks[0]]
        box = self._make_space(num)
        return [box]

    def customspace(self, s, loc, toks):
        return [self._make_space(float(toks[1]))]

    def symbol(self, s, loc, toks):
        # print "symbol", toks
        c = toks[0]
        try:
            char = Char(c, self.get_state())
        except ValueError:
            raise ParseFatalException("Unknown symbol: %s" % c)

        if c in self._spaced_symbols:
            return [Hlist( [self._make_space(0.2),
                            char,
                            self._make_space(0.2)] ,
                           do_kern = False)]
        elif c in self._punctuation_symbols:
            return [Hlist( [char,
                            self._make_space(0.2)] ,
                           do_kern = False)]
        return [char]

    _char_over_chars = {
        # The first 2 entires in the tuple are (font, char, sizescale) for
        # the two symbols under and over.  The third element is the space
        # (in multiples of underline height)
        r'AA' : (  ('rm', 'A', 1.0), (None, '\circ', 0.5), 0.0),
    }

    def char_over_chars(self, s, loc, toks):
        sym = toks[0]
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        under_desc, over_desc, space = \
            self._char_over_chars.get(sym, (None, None, 0.0))
        if under_desc is None:
            raise ParseFatalException("Error parsing symbol")

        over_state = state.copy()
        if over_desc[0] is not None:
            over_state.font = over_desc[0]
        over_state.fontsize *= over_desc[2]
        over = Accent(over_desc[1], over_state)

        under_state = state.copy()
        if under_desc[0] is not None:
            under_state.font = under_desc[0]
        under_state.fontsize *= under_desc[2]
        under = Char(under_desc[1], under_state)

        width = max(over.width, under.width)

        over_centered = HCentered([over])
        over_centered.hpack(width, 'exactly')

        under_centered = HCentered([under])
        under_centered.hpack(width, 'exactly')

        return Vlist([
                over_centered,
                Vbox(0., thickness * space),
                under_centered
                ])

    _accent_map = {
        r'hat'   : r'\circumflexaccent',
        r'breve' : r'\combiningbreve',
        r'bar'   : r'\combiningoverline',
        r'grave' : r'\combininggraveaccent',
        r'acute' : r'\combiningacuteaccent',
        r'ddot'  : r'\combiningdiaeresis',
        r'tilde' : r'\combiningtilde',
        r'dot'   : r'\combiningdotabove',
        r'vec'   : r'\combiningrightarrowabove',
        r'"'     : r'\combiningdiaeresis',
        r"`"     : r'\combininggraveaccent',
        r"'"     : r'\combiningacuteaccent',
        r'~'     : r'\combiningtilde',
        r'.'     : r'\combiningdotabove',
        r'^'     : r'\circumflexaccent',
        r'overrightarrow' : r'\rightarrow',
        r'overleftarrow'  : r'\leftarrow'
        }

    _wide_accents = set(r"widehat widetilde".split())

    def accent(self, s, loc, toks):
        assert(len(toks)==1)
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        if len(toks[0]) != 2:
            raise ParseFatalException("Error parsing accent")
        accent, sym = toks[0]
        if accent in self._wide_accents:
            accent = AutoWidthChar(
                '\\' + accent, sym.width, state, char_class=Accent)
        else:
            accent = Accent(self._accent_map[accent], state)
        centered = HCentered([accent])
        centered.hpack(sym.width, 'exactly')
        return Vlist([
                centered,
                Vbox(0., thickness * 2.0),
                Hlist([sym])
                ])

    def function(self, s, loc, toks):
        #~ print "function", toks
        self.push_state()
        state = self.get_state()
        state.font = 'rm'
        l = [self._make_space(0.2)]
        l += [Char(c, state) for c in toks[0]]
        l += [self._make_space(0.2)]
        hlist = Hlist(l)
        self.pop_state()
        hlist.function_name = toks[0]
        return hlist

    def operatorname(self, s, loc, toks):
        return self.function(s, loc, toks[0])

    def start_group(self, s, loc, toks):
        self.push_state()
        # Deal with LaTeX-style font tokens
        if len(toks):
            self.get_state().font = toks[0][4:]
        return []

    def group(self, s, loc, toks):
        grp = Hlist(toks[0])
        return [grp]

    def end_group(self, s, loc, toks):
        self.pop_state()
        return []

    def font(self, s, loc, toks):
        assert(len(toks)==1)
        name = toks[0]
        self.get_state().font = name
        return []

    def is_overunder(self, nucleus):
        if isinstance(nucleus, Char):
            return nucleus.c in self._overunder_symbols
        elif isinstance(nucleus, Hlist) and hasattr(nucleus, 'function_name'):
            return nucleus.function_name in self._overunder_functions
        return False

    def is_dropsub(self, nucleus):
        if isinstance(nucleus, Char):
            return nucleus.c in self._dropsub_symbols
        return False

    def is_slanted(self, nucleus):
        if isinstance(nucleus, Char):
            return nucleus.is_slanted()
        return False

    def subsuperscript(self, s, loc, toks):
        assert(len(toks)==1)
        # print 'subsuperscript', toks

        nucleus = None
        sub = None
        super = None

        if len(toks[0]) == 1:
            return toks[0].asList()
        elif len(toks[0]) == 2:
            op, next = toks[0]
            nucleus = Hbox(0.0)
            if op == '_':
                sub = next
            else:
                super = next
        elif len(toks[0]) == 3:
            nucleus, op, next = toks[0]
            if op == '_':
                sub = next
            else:
                super = next
        elif len(toks[0]) == 5:
            nucleus, op1, next1, op2, next2 = toks[0]
            if op1 == op2:
                if op1 == '_':
                    raise ParseFatalException("Double subscript")
                else:
                    raise ParseFatalException("Double superscript")
            if op1 == '_':
                sub = next1
                super = next2
            else:
                super = next1
                sub = next2
        else:
            raise ParseFatalException(
                "Subscript/superscript sequence is too long. "
                "Use braces { } to remove ambiguity.")

        state = self.get_state()
        rule_thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        xHeight = state.font_output.get_xheight(
            state.font, state.fontsize, state.dpi)

        # Handle over/under symbols, such as sum or product
        if self.is_overunder(nucleus):
            vlist = []
            shift = 0.
            width = nucleus.width
            if super is not None:
                super.shrink()
                width = max(width, super.width)
            if sub is not None:
                sub.shrink()
                width = max(width, sub.width)

            if super is not None:
                hlist = HCentered([super])
                hlist.hpack(width, 'exactly')
                vlist.extend([hlist, Kern(rule_thickness * 3.0)])
            hlist = HCentered([nucleus])
            hlist.hpack(width, 'exactly')
            vlist.append(hlist)
            if sub is not None:
                hlist = HCentered([sub])
                hlist.hpack(width, 'exactly')
                vlist.extend([Kern(rule_thickness * 3.0), hlist])
                shift = hlist.height
            vlist = Vlist(vlist)
            vlist.shift_amount = shift + nucleus.depth
            result = Hlist([vlist])
            return [result]

        # Handle regular sub/superscripts
        shift_up = nucleus.height - SUBDROP * xHeight
        if self.is_dropsub(nucleus):
            shift_down = nucleus.depth + SUBDROP * xHeight
        else:
            shift_down = SUBDROP * xHeight
        if super is None:
            # node757
            sub.shrink()
            x = Hlist([sub])
            # x.width += SCRIPT_SPACE * xHeight
            shift_down = max(shift_down, SUB1)
            clr = x.height - (abs(xHeight * 4.0) / 5.0)
            shift_down = max(shift_down, clr)
            x.shift_amount = shift_down
        else:
            super.shrink()
            x = Hlist([super, Kern(SCRIPT_SPACE * xHeight)])
            # x.width += SCRIPT_SPACE * xHeight
            clr = SUP1 * xHeight
            shift_up = max(shift_up, clr)
            clr = x.depth + (abs(xHeight) / 4.0)
            shift_up = max(shift_up, clr)
            if sub is None:
                x.shift_amount = -shift_up
            else: # Both sub and superscript
                sub.shrink()
                y = Hlist([sub])
                # y.width += SCRIPT_SPACE * xHeight
                shift_down = max(shift_down, SUB1 * xHeight)
                clr = (2.0 * rule_thickness -
                       ((shift_up - x.depth) - (y.height - shift_down)))
                if clr > 0.:
                    shift_up += clr
                    shift_down += clr
                if self.is_slanted(nucleus):
                    x.shift_amount = DELTA * (shift_up + shift_down)
                x = Vlist([x,
                           Kern((shift_up - x.depth) - (y.height - shift_down)),
                           y])
                x.shift_amount = shift_down

        result = Hlist([nucleus, x])
        return [result]

    def _genfrac(self, ldelim, rdelim, rule, style, num, den):
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        rule = float(rule)
        num.shrink()
        den.shrink()
        cnum = HCentered([num])
        cden = HCentered([den])
        width = max(num.width, den.width)
        cnum.hpack(width, 'exactly')
        cden.hpack(width, 'exactly')
        vlist = Vlist([cnum,                      # numerator
                       Vbox(0, thickness * 2.0),  # space
                       Hrule(state, rule),        # rule
                       Vbox(0, thickness * 2.0),  # space
                       cden                       # denominator
                       ])

        # Shift so the fraction line sits in the middle of the
        # equals sign
        metrics = state.font_output.get_metrics(
            state.font, self._default_style, '=', state.fontsize, state.dpi)
        shift = (cden.height -
                 ((metrics.ymax + metrics.ymin) / 2 -
                  thickness * 3.0))
        vlist.shift_amount = shift

        result = [Hlist([vlist, Hbox(thickness * 2.)])]
        if ldelim or rdelim:
            if ldelim == '':
                ldelim = '.'
            if rdelim == '':
                rdelim = '.'
            elif rdelim == r'\}':
                rdelim = '}'
            return self._auto_sized_delimiter(ldelim, result, rdelim)
        return result

    def genfrac(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==6)

        return self._genfrac(*tuple(toks[0]))

    def frac(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==2)
        state = self.get_state()

        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        num, den = toks[0]

        return self._genfrac('', '', thickness, '', num, den)

    def stackrel(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==2)
        num, den = toks[0]

        return self._genfrac('', '', 0.0, '', num, den)

    def binom(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==2)
        num, den = toks[0]

        return self._genfrac('(', ')', 0.0, '', num, den)

    def sqrt(self, s, loc, toks):
        #~ print "sqrt", toks
        root, body = toks[0]
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        # Determine the height of the body, and add a little extra to
        # the height so it doesn't seem cramped
        height = body.height - body.shift_amount + thickness * 5.0
        depth = body.depth + body.shift_amount + thickness * 2.0
        check = AutoHeightChar(r'\__sqrt__', height, depth, state, always=True)
        height = check.height - check.shift_amount
        depth = check.depth + check.shift_amount

        rightside = Vlist([Hrule(state),
                           Fill(),
                           body])
        # Stretch the glue between the hrule and the body
        rightside.vpack(height + (state.fontsize * state.dpi) / (100.0 * 12.0),
                        depth, 'exactly')

        # Add the root and shift it upward so it is above the tick.
        # The value of 0.6 is a hard-coded hack ;)
        if root is None:
            root = Box(check.width * 0.5, 0., 0.)
        else:
            root = Hlist([Char(x, state) for x in root])
            root.shrink()
            root.shrink()

        root_vlist = Vlist([Hlist([root])])
        root_vlist.shift_amount = -height * 0.6

        hlist = Hlist([root_vlist,               # Root
                       # Negative kerning to put root over tick
                       Kern(-check.width * 0.5),
                       check,                    # Check
                       rightside])               # Body
        return [hlist]

    def _auto_sized_delimiter(self, front, middle, back):
        state = self.get_state()
        height = max([x.height for x in middle])
        depth = max([x.depth for x in middle])
        parts = []
        # \left. and \right. aren't supposed to produce any symbols
        if front != '.':
            parts.append(AutoHeightChar(front, height, depth, state))
        parts.extend(middle)
        if back != '.':
            parts.append(AutoHeightChar(back, height, depth, state))
        hlist = Hlist(parts)
        return hlist

    def auto_sized_delimiter(self, s, loc, toks):
        #~ print "auto_sized_delimiter", toks
        front, middle, back = toks

        return self._auto_sized_delimiter(front, middle.asList(), back)
