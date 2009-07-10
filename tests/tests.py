#! /usr/bin/env python
# Mathtex unit tests
import sys, os
from mathtex import Mathtex
from optparse import OptionParser
from hashlib import md5
import pickle

tests = {
    'basic_dots' : r'$a+b+\dots+\dot{s}+\ldots$',
    'equal'      : r'$x \doteq y$',
    'basic_esc'  : r'\$100.00 $\alpha \_$'
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
                      default='test-hashes.pickle',
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
        m = Mathtex(tex, fontsize=fontsize, dpi=dpi)

        if options.gen_output:
            m.save("%s.%dpt.%ddpi.png" % (name, fontsize, dpi))

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
