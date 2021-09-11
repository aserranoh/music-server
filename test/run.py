#!/usr/bin/env python

import coverage
import glob
import os
import sys
import unittest

if __name__ == '__main__':
    # The path to the directory that contains the python test files and the cov
    # directory
    test_path = os.path.dirname(sys.argv[0])
    # The path to the music-server module
    src_path = os.path.join(test_path, '..', 'src')
    # The path to the directory that contains the coverage information
    cov_path = os.path.join(test_path, 'cov')
    # Create the coverage object
    sources = ['musicserver']
    cov = coverage.coverage(source=sources)

    # Start coverage capture
    cov.start()
    # Import the test modules. If an argument is given, use that test file.
    # Otherwise, import all the files that start with 'test'.
    if len(sys.argv) > 1:
        test_files = sys.argv[1:]
    else:
        test_files = glob.glob(os.path.join(test_path, 'test*.py'))
    modules = [__import__(os.path.basename(t).split('.')[0])
        for t in test_files]
    # Create the test suite
    alltests = unittest.TestSuite([unittest.TestLoader().loadTestsFromModule(m)
        for m in modules])
    # Run the tests
    unittest.TextTestRunner(verbosity=2).run(alltests)
    # End of coverage capture
    cov.stop()
    # Save coverage information
    cov.save()
    # Generate coverage report
    if not os.path.exists(cov_path):
        os.mkdir(cov_path)
    cov.html_report(directory=cov_path)

