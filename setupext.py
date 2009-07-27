# -*- coding: iso-8859-1 -*-
"""
Some helper functions for building the C extensions

you may need to edit basedir to point to the default location of your
required libs, eg, png, z, freetype

DARWIN

  I have installed all of the backends on OSX.

  Tk: If you want to install TkAgg, I recommend the "batteries included"
  binary build of Tcl/Tk at
  http://www.apple.com/downloads/macosx/unix_open_source/tcltkaqua.html

  GTK: I installed GTK from src as described at
  http://www.macgimp.org/index.php?topic=gtk.  There are several
  packages, but all configure/make/make install w/o problem.  In
  addition to the packages listed there, You will also need libpng,
  libjpeg, and libtiff if you want output to these formats from GTK.

WIN32 - MINGW

  If you are sufficiently masochistic that you want to build this
  yourself, download the win32_static dir from
  http://matplotlib.sourceforge.net/win32_static.tar.gz and
  see the README file in that dir

  > python setup.py build --compiler=mingw32 bdist_wininst  > build23.out

  NOTE, if you are building on python24 on win32, see
  http://mail.python.org/pipermail/python-list/2004-December/254826.html

WIN32 - VISUAL STUDIO 7.1 (2003)

  This build is similar to the mingw.  Download the visual studio static
  dependencies from
  http://matplotlib.sourceforge.net/win32_static_vs.tar.gz and
  see the README in that dir

  > python setup.py build --compiler=msvc bdist_wininst

"""

import os
import re
import subprocess

basedir = {
    'win32'  : ['win32_static',],
    'linux2' : ['/usr/local', '/usr'],
    'linux'  : ['/usr/local', '/usr',],
    'cygwin' : ['/usr/local', '/usr',],
    'darwin' : ['/sw/lib/freetype2', '/sw/lib/freetype219', '/usr/local',
                '/usr', '/sw', '/usr/X11R6'],
    'freebsd4' : ['/usr/local', '/usr'],
    'freebsd5' : ['/usr/local', '/usr'],
    'freebsd6' : ['/usr/local', '/usr'],
    'sunos5' : [os.getenv('MPLIB_BASE') or '/usr/local',],
    'gnukfreebsd5' : ['/usr/local', '/usr'],
    'gnukfreebsd6' : ['/usr/local', '/usr'],
    'aix5' : ['/usr/local'],
}

import sys, os, stat
if sys.platform != 'win32':
    import commands
from textwrap import fill
from distutils.core import Extension
import glob
import ConfigParser
import cStringIO

BUILT_PNG       = False
BUILT_FT2FONT   = False

# for nonstandard installation/build with --prefix variable
numpy_inc_dirs = []

# matplotlib build options, which can be altered using setup.cfg
options = {'display_status': True,
           'verbose': False,
           'backend': None}

# Based on the contents of setup.cfg, determine the build options
if os.path.exists("setup.cfg"):
    config = ConfigParser.SafeConfigParser()
    config.read("setup.cfg")

    try: options['display_status'] = not config.getboolean("status", "suppress")
    except: pass

    try: options['verbose'] = not config.getboolean("status", "verbose")
    except: pass

    try: options['backend'] = config.get("rc_options", "backend")
    except: pass


if options['display_status']:
    def print_line(char='='):
        print char * 76

    def print_status(package, status):
        initial_indent = "%22s: " % package
        indent = ' ' * 24
        print fill(str(status), width=76,
                   initial_indent=initial_indent,
                   subsequent_indent=indent)

    def print_message(message):
        indent = ' ' * 24 + "* "
        print fill(str(message), width=76,
                   initial_indent=indent,
                   subsequent_indent=indent)

    def print_raw(section):
        print section
else:
    def print_line(*args, **kwargs):
        pass
    print_status = print_message = print_raw = print_line

def run_child_process(cmd):
    p = subprocess.Popen(cmd, shell=True,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         close_fds=True)
    return p.stdin, p.stdout

class CleanUpFile:
    """CleanUpFile deletes the specified filename when self is destroyed."""
    def __init__(self, name):
        self.name = name
    def __del__(self):
        os.remove(self.name)

def temp_copy(_from, _to):
    """temp_copy copies a named file into a named temporary file.
    The temporary will be deleted when the setupext module is destructed.
    """
    # Copy the file data from _from to _to
    s = open(_from).read()
    open(_to,"w+").write(s)
    # Suppress object rebuild by preserving time stamps.
    stats = os.stat(_from)
    os.utime(_to, (stats.st_atime, stats.st_mtime))
    # Make an object to eliminate the temporary file at exit time.
    globals()["_cleanup_"+_to] = CleanUpFile(_to)

def get_win32_compiler():
    # Used to determine mingw32 or msvc
    # This is pretty bad logic, someone know a better way?
    for v in sys.argv:
        if 'mingw32' in v:
            return 'mingw32'
    return 'msvc'
win32_compiler = get_win32_compiler()
if sys.platform == 'win32' and win32_compiler == 'msvc':
    std_libs = []
else:
    std_libs = ['stdc++', 'm']

def has_pkgconfig():
    if has_pkgconfig.cache is not None:
        return has_pkgconfig.cache
    if sys.platform == 'win32':
        has_pkgconfig.cache = False
    else:
        #print 'environ',  os.environ['PKG_CONFIG_PATH']
        status, output = commands.getstatusoutput("pkg-config --help")
        has_pkgconfig.cache = (status == 0)
    return has_pkgconfig.cache
has_pkgconfig.cache = None

def get_pkgconfig(module,
                  packages,
                  flags="--libs --cflags",
                  pkg_config_exec='pkg-config',
                  report_error=False):
    """Loosely based on an article in the Python Cookbook:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/502261"""
    if not has_pkgconfig():
        return False

    _flags = {'-I': 'include_dirs',
              '-L': 'library_dirs',
              '-l': 'libraries',
              '-D': 'define_macros',
              '-U': 'undef_macros'}

    cmd = "%s %s %s" % (pkg_config_exec, flags, packages)
    status, output = commands.getstatusoutput(cmd)
    if status == 0:
        for token in output.split():
            attr = _flags.get(token[:2], None)
            if attr is not None:
                if token[:2] == '-D':
                    value = tuple(token[2:].split('='))
                    if len(value) == 1:
                        value = (value[0], None)
                else:
                    value = token[2:]
                set = getattr(module, attr)
                if value not in set:
                    set.append(value)
            else:
                if token not in module.extra_link_args:
                    module.extra_link_args.append(token)
        return True
    if report_error:
        print_status("pkg-config", "looking for %s" % packages)
        print_message(output)
    return False

def get_pkgconfig_version(package):
    default = "found, but unknown version (no pkg-config)"
    if not has_pkgconfig():
        return default

    status, output = commands.getstatusoutput(
        "pkg-config %s --modversion" % (package))
    if status == 0:
        return output
    return default

def try_pkgconfig(module, package, fallback):
    if not get_pkgconfig(module, package):
        module.libraries.append(fallback)

def find_include_file(include_dirs, filename):
    for d in include_dirs:
        if os.path.exists(os.path.join(d, filename)):
            return True
    return False

def check_for_freetype():
    module = Extension('test', [])
    add_base_flags(module)
    if not get_pkgconfig(module, 'freetype2'):
        basedirs = module.include_dirs[:]  # copy the list to avoid inf loop!
        for d in basedirs:
            module.include_dirs.append(os.path.join(d, 'freetype2'))

    print_status("freetype2", get_pkgconfig_version('freetype2'))
    if not find_include_file(module.include_dirs, 'ft2build.h'):
        print_message(
            "WARNING: Could not find 'freetype2' headers in any of %s." %
            ", ".join(["'%s'" % x for x in module.include_dirs]))

    return True

def check_for_libpng():
    module = Extension("test", [])
    get_pkgconfig(module, 'libpng')
    add_base_flags(module)

    print_status("libpng", get_pkgconfig_version('libpng'))
    if not find_include_file(module.include_dirs, 'png.h'):
        print_message(
            "Could not find 'libpng' headers in any of %s" %
            ", ".join(["'%s'" % x for x in module.include_dirs]))

    return True

def add_base_flags(module):
    incdirs = filter(os.path.exists,
                     [os.path.join(p, 'include') for p in basedir[sys.platform] ])
    libdirs = filter(os.path.exists,
                     [os.path.join(p, 'lib')     for p in basedir[sys.platform] ]+
                     [os.path.join(p, 'lib64')     for p in basedir[sys.platform] ] )

    module.include_dirs.extend(incdirs)
    module.include_dirs.append('.')
    module.library_dirs.extend(libdirs)

def getoutput(s):
    'get the output of a system command'

    ret =  os.popen(s).read().strip()
    return ret


def check_for_numpy():
    try:
        import numpy
    except ImportError:
        print_status("numpy", "no")
        print_message("You must install numpy 1.1 or later to build matplotlib.")
        return False
    nn = numpy.__version__.split('.')
    if not (int(nn[0]) >= 1 and int(nn[1]) >= 1):
        print_message(
           'numpy 1.1 or later is required; you have %s' % numpy.__version__)
        return False
    module = Extension('test', [])
    add_numpy_flags(module)
    add_base_flags(module)

    print_status("numpy", numpy.__version__)
    if not find_include_file(module.include_dirs, os.path.join("numpy", "arrayobject.h")):
        print_message("Could not find the headers for numpy.  You may need to install the development package.")
        return False
    return True

def add_numpy_flags(module):
    "Add the modules flags to build extensions which use numpy"
    import numpy
    module.include_dirs.append(numpy.get_include())

def add_png_flags(module):
    try_pkgconfig(module, 'libpng', 'png')
    add_base_flags(module)
    add_numpy_flags(module)
    module.libraries.append('z')
    module.include_dirs.extend(['.'])
    module.libraries.extend(std_libs)

def add_ft2font_flags(module):
    'Add the module flags to ft2font extension'
    add_numpy_flags(module)
    if not get_pkgconfig(module, 'freetype2'):
        module.libraries.extend(['freetype', 'z'])
        add_base_flags(module)

        basedirs = module.include_dirs[:]  # copy the list to avoid inf loop!
        for d in basedirs:
            module.include_dirs.append(os.path.join(d, 'freetype2'))
            p = os.path.join(d, 'lib/freetype2/include')
            if os.path.exists(p): module.include_dirs.append(p)
            p = os.path.join(d, 'lib/freetype2/include/freetype2')
            if os.path.exists(p): module.include_dirs.append(p)

        basedirs = module.library_dirs[:]  # copy the list to avoid inf loop!
        for d in basedirs:
            p = os.path.join(d, 'freetype2/lib')
            if os.path.exists(p): module.library_dirs.append(p)
    else:
        add_base_flags(module)
        module.libraries.append('z')

    # put this last for library link order
    module.libraries.extend(std_libs)

def check_for_macosx():
    gotit = False
    import sys
    if sys.platform=='darwin':
        gotit = True
    if gotit:
        print_status("Mac OS X native", "yes")
    else:
        print_status("Mac OS X native", "no")
    return gotit

def build_ft2font(ext_modules, packages):
    global BUILT_FT2FONT
    if BUILT_FT2FONT: return # only build it if you you haven't already
    deps = ['src/ft2font.cpp', 'src/mplutils.cpp']
    deps.extend(glob.glob('CXX/*.cxx'))
    deps.extend(glob.glob('CXX/*.c'))

    module = Extension('mathtex.ft2font', deps,
                       define_macros=[('PY_ARRAYAUNIQUE_SYMBOL', 'MPL_ARRAY_API')])
    add_ft2font_flags(module)
    ext_modules.append(module)
    BUILT_FT2FONT = True

def build_png(ext_modules, packages):
    global BUILT_PNG
    if BUILT_PNG: return # only build it if you you haven't already

    deps = ['src/_png.cpp', 'src/mplutils.cpp']
    deps.extend(glob.glob('CXX/*.cxx'))
    deps.extend(glob.glob('CXX/*.c'))

    module = Extension(
        'mathtex._png',
        deps,
        include_dirs=numpy_inc_dirs,
        define_macros=[('PY_ARRAY_UNIQUE_SYMBOL', 'MPL_ARRAY_API')]
        )

    add_png_flags(module)
    ext_modules.append(module)

    BUILT_PNG = True