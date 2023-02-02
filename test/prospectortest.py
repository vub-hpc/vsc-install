#
# Copyright 2016-2023 Ghent University
#
# This file is part of vsc-install,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/hpcugent/vsc-install
#
# vsc-install is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# vsc-install is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with vsc-install. If not, see <http://www.gnu.org/licenses/>.
#
"""Test ProspectorTest"""

import glob
import os
import sys

from vsc.install import commontest
from vsc.install.shared_setup import log, vsc_setup
from vsc.install.testing import TestCase


class ProspectorTest(TestCase):
    """Test ProspectorTest """

    def setUp(self):
        """create a self.setup.instance for every test"""
        super(ProspectorTest, self).setUp()
        self.setup = vsc_setup()

    def test_prospectorfail(self):
        """Test that whitelisted warnings actually fails"""

        base_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'prospectortest')
        test_files = glob.glob(os.path.join(base_dir, 'lib', 'vsc', 'mockinstall', "*.py"))
        test_files = [x for x in test_files if '__init__.py' not in x]
        log.debug("test_files = %s" % test_files)
        log.debug("base_dir = %s" % base_dir)

        failures = commontest.run_prospector(base_dir, clear_ignore_patterns=True)
        log.debug("Failures = %s" % failures)

        detected_tests = []
        all_tests = []
        for testfile in test_files:
            testfile_base = os.path.splitext(os.path.basename(testfile))[0].replace("_", "-")
            all_tests.append(testfile_base)
            for failure in failures:
                if failure['location']['path'] == testfile and testfile_base in [failure['code'], failure['message']]:
                    detected_tests.append(testfile_base)

        log.debug("All tests = %s" % all_tests)
        log.info("Detected prospector tests = %s" % detected_tests)
        undetected_tests = [x for x in all_tests if x not in detected_tests]

        if sys.version_info[0] < 3:
            # some of the prospector test cases don't exist in Python 2
            py2_invalid_tests = ['raising-bad-type']
            undetected_tests = [x for x in undetected_tests if x not in py2_invalid_tests]


        if sys.version_info[0] >= 3:
            # some of the prospector test cases don't make sense in Python 3 because they yield syntax errors,
            # or are no longer a problem in Python 3
            py3_invalid_tests = ['backtick', 'old-octal-literal', 'import-star-module-level', 'redefine-in-handler',
                                 'indexing-exception', 'old-raise-syntax', 'print-statement', 'unpacking-in-except',
                                 'old-ne-operator', 'raising-string', 'metaclass-assignment']
            undetected_tests = [x for x in undetected_tests if x not in py3_invalid_tests]

        self.assertFalse(undetected_tests, "\nprospector did not detect %s\n" % undetected_tests)
