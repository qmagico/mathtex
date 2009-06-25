from mathtex.util import Bunch

class Fonts(object):
    """
    An abstract base class for a system of fonts used by Mathtex.
    """

    def __init__(self):
        self.used_characters = {}

    def get_kern(self, font1, fontclass2, sym1, fontsize1,
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

    
