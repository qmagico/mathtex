inf = float('inf')

def isinf(f):
    return f == inf

class Bunch:
    """
    Often we want to just collect a bunch of stuff together, naming each
    item of the bunch; a dictionary's OK for that, but a small do- nothing
    class is even handier, and prettier to use.  Whenever you want to
    group a few variables:

      >>> point = Bunch(datum=2, squared=4, coord=12)
      >>> point.datum

      By: Alex Martelli
      From: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52308
    """
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


    def __repr__(self):
        keys = self.__dict__.keys()
        return 'Bunch(%s)'%', '.join(['%s=%s'%(k,self.__dict__[k]) for k in keys])
