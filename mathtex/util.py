import os, tempfile

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

class maxdict(dict):
    """
    A dictionary with a maximum size; this doesn't override all the
    relevant methods to contrain size, just setitem, so use with
    caution
    """
    def __init__(self, maxsize):
        dict.__init__(self)
        self.maxsize = maxsize
        self._killkeys = []
    def __setitem__(self, k, v):
        if len(self)>=self.maxsize:
            del self[self._killkeys[0]]
            del self._killkeys[0]
        dict.__setitem__(self, k, v)
        self._killkeys.append(k)

def get_configdir():
    """
    Return the string representing the configuration dir.

    default is HOME/.matplotlib.  you can override this with the
    MATHTEXCONFIGDIR environment variable
    """

    configdir = os.environ.get('MATHTEXCONFIGDIR')
    if configdir is not None:
        if not _is_writable_dir(configdir):
            raise RuntimeError('Could not write to MATHTEXCONFIGDIR="%s"'%configdir)
        return configdir

    h = get_home()
    p = os.path.join(get_home(), '.mathtex')

    if os.path.exists(p):
        if not _is_writable_dir(p):
            raise RuntimeError("'%s' is not a writable dir; you must set %s/.mathtex to be a writable dir.  You can also set environment variable MATHTEXCONFIGDIR to any writable directory where you want mathtex data stored "% (h, h))
    else:
        if not _is_writable_dir(h):
            raise RuntimeError("Failed to create %s/.mathtex; consider setting MATHTEXCONFIGDIR to a writable directory for matplotlib configuration data"%h)

        os.mkdir(p)

    return p

def get_datadir():
    'get the path to mathtex data'

    if 'MATHTEXDATA' in os.environ:
        path = os.environ['MATHTEXDATA']
        if not os.path.isdir(path):
            raise RuntimeError('Path in environment MATHTEXDATA not a directory')
        return path

    path = os.sep.join([os.path.dirname(__file__), 'data'])
    if os.path.isdir(path): return path

    raise RuntimeError('Could not find the mathtex data files')

def get_home():
    """
    Find user's home directory if possible.
    Otherwise raise error.

    :see:  http://mail.python.org/pipermail/python-list/2005-February/263921.html
    """
    path=''
    try:
        path=os.path.expanduser("~")
    except:
        pass
    if not os.path.isdir(path):
        for evar in ('HOME', 'USERPROFILE', 'TMP'):
            try:
                path = os.environ[evar]
                if os.path.isdir(path):
                    break
            except: pass
    if path:
        return path
    else:
        raise RuntimeError('please define environment variable $HOME')

def is_string_like(obj):
    try: obj + ''
    except (TypeError, ValueError): return 0
    return 1

def _is_writable_dir(p):
    """
    p is a string pointing to a putative writable dir -- return True p
    is such a string, else False
    """
    try: p + ''  # test is string like
    except TypeError: return False
    try:
        t = tempfile.TemporaryFile(dir=p)
        t.write('1')
        t.close()
    except OSError: return False
    else: return True
