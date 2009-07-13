#! /usr/bin/env python
# Mathtex unit tests
import sys, os
from mathtex.mathtex_main import Mathtex
from optparse import OptionParser
from hashlib import md5
import pickle

tests = {
    'basic_dots' : r'$a+b+\dots+\dot{s}+\ldots$',
    'equal'      : r'$x \doteq y$',
    'basic_esc'  : r'\$100.00 $\alpha \_$',
    'basic_frac' : r'$\frac{\$100.00}{y}$',
    'basic_sym'  : r'$x   y$',
    'bin_opts'   : r'$x+y\ x=y\ x<y\ x:y\ x,y\ x@y$',
    'bin_opts2'  : r'$100\%y\ x*y\ x/y x\$y$',
    'forall'     :r'$x\leftarrow y\ x\forall y\ x-y$',
    'fonts'      : r'$x \sf x \bf x {\cal X} \rm x$',
    'spaces'     : r'$x\ x\,x\;x\quad x\qquad x\!x\hspace{ 0.5 }y$',
    'braces'     : r'$\{ \rm braces \}$',
    'braces2'    : r'$\left[\left\lfloor\frac{5}{\frac{\left(3\right)}{4}} y\right)\right]$',
    'braces3'    : r'$\left(x\right)$',
    'func'  : r'$\sin(x)$',
    'subscript'  : r'$x_2$',
    'superscript' : r'$x^2$',
    'subsuper'   : r'$x^2_y$',
    'subsuper2'  : r'$x_y^2$',
    'product'    : r'$\prod_{i=\alpha_{i+1}}^\infty$',
    'frac'       : r'$x = \frac{x+\frac{5}{2}}{\frac{y+3}{8}}$',
    'deriv'      : r'$dz/dt = \gamma x^2 + {\rm sin}(2\pi y+\phi)$',
    'mixin'      : r'Foo: $\alpha_{i+1}^j = {\rm sin}(2\pi f_j t_i) e^{-5 t_i/\tau}$',
    'maxin2'     : r'$\mathcal{R}\prod_{i=\alpha_{i+1}}^\infty a_i \sin(2 \pi f x_i)$',
    'nonmath'    : r'Variable $i$ is good',
    'greek'      : r'$\Delta_i^j$',
    'greek2'     : r'$\Delta^j_{i+1}$',
    'accent'     :  r'$\ddot{o}\acute{e}\grave{e}\hat{O}\breve{\imath}\tilde{n}\vec{q}$',
    'func2'      : r"$\arccos((x^i))$",
    'frac2'      : r"$\gamma = \frac{x=\frac{6}{8}}{y} \delta$",
    'limit'      : r'$\limsup_{x\to\infty}$',
    'int'        : r'$\oint^\infty_0$',
    'prime'      : r"$f^'$",
    'frac3'      : r'$\frac{x_2888}{y}$',
    'sqrt'       : r"$\sqrt[3]{\frac{X_2}{Y}}=5$",
    'sqrt2'      : r"$\sqrt[5]{\prod^\frac{x}{2\pi^2}_\infty}$",
    'sqrt3'      : r"$\sqrt[3]{x}=5$",
    'frac4'      : r'$\frac{X}{\frac{X}{Y}}$',
    'mixin3'     : r"$W^{3\beta}_{\delta_1 \rho_1 \sigma_2} = U^{3\beta}_{\delta_1 \rho_1} + \frac{1}{8 \pi 2} \int^{\alpha_2}_{\alpha_2} d \alpha^\prime_2 \left[\frac{ U^{2\beta}_{\delta_1 \rho_1} - \alpha^\prime_2U^{1\beta}_{\rho_1 \sigma_2} }{U^{0\beta}_{\rho_1 \sigma_2}}\right]$",
    'int2'       : r'$\mathcal{H} = \int d \tau \left(\epsilon E^2 + \mu H^2\right)$',
    'accent2'    : r'$\widehat{abc}\widetilde{def}$',
    'greek3'     : r'$\Gamma \Delta \Theta \Lambda \Xi \Pi \Sigma \Upsilon \Phi \Psi \Omega$',
    'greek4'     : r'$\alpha \beta \gamma \delta \epsilon \zeta \eta \theta \iota \lambda \mu \nu \xi \pi \kappa \rho \sigma \tau \upsilon \phi \chi \psi$'
}

# A list of (font size, dpi) to run each test at
presets = [(10, 100), (12, 100), (32, 100),
           (10, 300), (12, 300), (32, 300)]

# Command line options
arg_parser = OptionParser()

# Save test files or not (for visual comparison)
arg_parser.add_option('-n', '--no-output', dest='gen_output',
                      default=True, action='store_false',
                      help="don't generate output files (.png)")

# Hashfile
arg_parser.add_option('-o', '--hash-file', dest='hashfile',
                      default=os.path.join(os.path.dirname(__file__), 'test-hashes.pickle'),
                      help='pickled hash file to compare with')

# Update hashfile
arg_parser.add_option('-u', '--update', dest='update',
                      default=False, action='store_true',
                      help='update the hash file')

# List available tests & combinations thereof
arg_parser.add_option('-l', '--list-tests', dest='list_tests',
                      default=False, action='store_true',
                      help='list available tests')
arg_parser.add_option('-L', '--list-presets', dest='list_presets',
                      default=False, action='store_true',
                      help='list preset test rendering styles')

# Tests & presets to run
arg_parser.add_option('-t', '--run-tests', dest='tests',
                      default=','.join(tests.keys()),
                      help='list of comma separated test names/indexes to run')
arg_parser.add_option('-T', '--run-presets', dest='presets',
                      default=','.join([str(s) for s in range(0, len(presets))]),
                      help='list of preset indexes to run')

(options, args) = arg_parser.parse_args()

# Sanity checking
if options.list_tests and options.list_presets:
    arg_parser.error('options -l and -L are mutually exclusive')

# See if we are being asked to output a list of tests/presets
if options.list_tests:
    print 'Available tests:'
    for i, name in zip(range(0, len(tests)), tests.keys()):
        print '[%d] %s' % (i, name)
    sys.exit()
elif options.list_presets:
    print 'Available testing presets:'
    for (i, (fontsize, dpi)) in zip(range(0, len(presets)), presets):
        print '[%d] %.1f pt at %d dpi' % (i, fontsize, dpi)
    sys.exit()

# Otherwise run the tests
results = {}

# See what tests we have been asked to run
actual_tests = {}
for name in options.tests.split(','):
    # Allow for indexes as well as names
    if name.isdigit():
        name = tests.keys()[name]
    actual_tests[name] = tests[name]

actual_presets = [presets[int(i)] for i in options.presets.split(',')]

# For progress reports
total = len(actual_tests) * len(actual_presets)
count = 0

for (name, tex) in actual_tests.iteritems():
    for fontsize, dpi in actual_presets:
        count += 1
        print "Test %d of %d ['%s' at (%.1f, %d)]" % (count, total, name, fontsize, dpi)

        m = Mathtex(tex, fontsize=fontsize, dpi=dpi)

        if options.gen_output:
            m.save(os.path.join(os.path.dirname(__file__),
                                "%s.%dpt.%ddpi.png" % (name, fontsize, dpi)))

        h = md5(m.as_rgba_bitmap()).hexdigest()
        results[(name, fontsize, dpi)] = h

# Compare hashes against a previous run
if os.path.isfile(options.hashfile) and not options.update:
    prev_results = pickle.load(open(options.hashfile, 'rb'))

    for k in results.keys():
        if k in prev_results:
            if results[k] != prev_results[k]:
                print "Test '%s' at (%.1f, %d) failed!" % k
# Update/write new hashes
elif not os.path.isfile(options.hashfile) or options.update:
    pickle.dump(results, open(options.hashfile, 'wb'))
