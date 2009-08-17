# -*- coding: iso-8859-1 -*-
"""
You will need to have freetype, libpng and zlib installed to comile
mathtex, inlcuding the *-devel versions of these libraries if you
are using a package manager like RPM or debian.

"""
# distutils is breaking our sdists for files in symlinked dirs.
# distutils will copy if os.link is not available, so this is a hack
# to force copying
import os
try:
    del os.link
except AttributeError:
    pass

# BEFORE importing disutils, remove MANIFEST. distutils doesn't properly
# update it when the contents of directories change.
import os
if os.path.exists('MANIFEST'): os.remove('MANIFEST')

import sys
major, minor1, minor2, s, tmp = sys.version_info

if major==2 and minor1<4 or major<2:
    raise SystemExit("""mathtex requires Python 2.4 or later.""")

import glob
from distutils.core import setup
from setupext import \
     build_ft2font, print_line, print_status,\
     print_message, print_raw, check_for_freetype, check_for_libpng,\
     check_for_macosx, check_for_numpy, build_png, options
#import distutils.sysconfig

packages = ['mathtex', 'mathtex.backends']

# No modules
py_modules = []
ext_modules = []

# Mathtex version
__version__ = '0.3'

print_line()
print_raw("BUILDING MATHTEX")
print_status('mathtex', __version__)
print_status('python', sys.version)
print_status('platform', sys.platform)
if sys.platform == 'win32':
    print_status('Windows version', sys.getwindowsversion())
print_raw("")
print_raw("REQUIRED DEPENDENCIES")

# Font data
package_data = {'mathtex' : ['data/fonts/*.ttf'] }

# Check for numpy, but it does not need to be built
if not check_for_numpy():
    sys.exit(1)

if not check_for_freetype():
    sys.exit(1)

build_ft2font(ext_modules, packages)

if not check_for_libpng():
    sys.exit(1)

build_png(ext_modules, packages)

print_raw("")
print_raw("[Edit setup.cfg to suppress the above messages]")
print_line()

try: additional_params # has setupegg.py provided
except NameError: additional_params = {}

for mod in ext_modules:
    if options['verbose']:
        mod.extra_compile_args.append('-DVERBOSE')

print 'pymods', py_modules
print 'packages', packages
distrib = setup(name="mathtex",
      version= __version__,
      description = "Python TeX rendering engine",
      author = "Freddie Witherden and the matplotlib team.",
      author_email="freddie@witherden.org",
      url = "http://code.google.com/p/mathtex/",
      long_description = """
      mathtex is a TeX math rendering engine written in Python.
      """,
      packages = packages,
      platforms='any',
      py_modules = py_modules,
      ext_modules = ext_modules,
      package_data = package_data,
      **additional_params
      )
