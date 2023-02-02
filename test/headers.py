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
"""Test headers"""
import glob
import os

import vsc.install.headers
import vsc.install.shared_setup
from vsc.install.headers import get_header, gen_license_header, begin_end_from_header, check_header
from vsc.install.shared_setup import KNOWN_LICENSES, log, vsc_setup

from vsc.install.testing import TestCase

orig_this_year = vsc.install.headers._this_year
orig_write = vsc.install.headers._write
orig_get_license = vsc_setup.get_license


class TestHeaders(TestCase):
    """Test vsc.install.headers"""

    def setUp(self):
        """Restore some possibly mocked functions"""
        vsc.install.headers._this_year = orig_this_year
        vsc.install.headers._write = orig_write
        vsc.install.shared_setup.get_license = orig_get_license
        self.setup = vsc_setup()
        super(TestHeaders, self).setUp()

    def _get_header(self, filename, name, script, expected):
        """Convenience method to help test get_header"""

        header, shebang = get_header(filename, script=script)

        if shebang is None:
            shebang_len = -1
        else:
            shebang_len = len(shebang)

        self.assertEqual(len(header), expected[name][0],
                         msg="header for %s (filename %s, len %s): %s\nENDOFMSG" %
                         (name, filename, len(header), header))
        self.assertEqual(shebang_len, expected[name][1],
                         msg="shebang for %s (filename %s, len %s): %s\nENDOFMSG" %
                         (name, filename, shebang_len, shebang))

    def test_get_header(self):
        """Test get_header function from .get_header files"""

        self.assertTrue(vsc.install.headers.HEADER_REGEXP.pattern.startswith('\A'),
                        msg='header regexp patterns starts with start of string: %s' %
                        vsc.install.headers.HEADER_REGEXP.pattern)

        # tuple, number of characters in header and shebang (-1 is None)
        # prefix _script_ to run with script=True
        expected = {
            'f1': (20, -1),  # split with special comment
            '_script_f1': (20, -1),  # because it's not a script
            'f2': (41, -1),  # split with docstring
            '_script_f2': (25, 15),  # fake shebang
            'f3': (0, -1),  # no header
        }

        for filename in glob.glob(os.path.join(self.setup.REPO_TEST_DIR, 'headers', "*.get_header")):
            log.info('test_get_header filename %s' % filename)

            found = False
            name = os.path.basename(filename[:-len('.get_header')])
            if name in expected:
                found = True
                self._get_header(filename, name, False, expected)

            name = '_script_%s' % name
            if name in expected:
                found = True
                self._get_header(filename, name, True, expected)

            self.assertTrue(found, msg='filename %s is expected')

    def test_gen_license_header(self):
        """Test the generation of headers for all supported/known licenses"""

        data = {
            'name': 'projectname',
            'beginyear': 1234,
            'endyear': 5678,
            'url': 'https://github.com/hpcugent/projectname',
        }
        data_brussel = {
            'name': 'projectname',
            'beginyear': 1234,
            'endyear': 5678,
            'url': 'https://github.com/vub-hpc/projectname',
        }
        for license in KNOWN_LICENSES.keys():
            res_fn = os.path.join(self.setup.REPO_TEST_DIR, 'headers', license)
            with open(res_fn) as fh:
                result = fh.read()
            gen_txt = gen_license_header(license, **data)
            self.assertEqual(gen_txt, result, msg='generated header for license %s as expected' % license)
            log.info('generated license header %s' % license)

            gen_txt_bru = gen_license_header(license, **data_brussel)
            self.assertNotRegexpMatches(gen_txt_bru, 'Ghent University',
                                        msg='No reference to Ghent University in header')
            self.assertNotRegexpMatches(gen_txt_bru, r'ugent\.be',
                                        msg='No reference to ugent.be University in header')
            self.assertRegexpMatches(gen_txt_bru, r'the HPC team of Vrije Universiteit Brussel \(https://hpc.vub.be\)',
                                     msg='generted header for Brussel is correct for %s' % license)
            self.assertRegexpMatches(gen_txt_bru, r'support of Vrije Universiteit Brussel \(https://www.vub.be\)',
                                     msg='generted header for Brussel is correct for %s' % license)

    def test_begin_end_from_header(self):
        """Test begin_end_from_header method"""

        THIS_YEAR = 2345

        def this_year():
            return THIS_YEAR

        vsc.install.headers._this_year = this_year

        self.assertEqual(list(begin_end_from_header("#\n# Copyright 1234-5678 something\n#\n")),
                         [1234, THIS_YEAR], msg='extracted beginyear from copyright, set thisyear as endyear')

        self.assertEqual(list(begin_end_from_header("#\n# Copyright 1234 something\n#\n")),
                         [1234, THIS_YEAR],
                         msg='extracted beginyear from copyright no endyear, set thisyear as endyear')

        self.assertEqual(list(begin_end_from_header("#\n# no Copyright something\n#\n")),
                         [THIS_YEAR, THIS_YEAR], msg='no beginyear found, set thisyear as begin and endyear')

    def test_check_header(self):
        """Test begin_end_from_header method
        Compares files with .check against ones with .fixed
        """

        THIS_YEAR = 2345

        def this_year():
            return THIS_YEAR

        vsc.install.headers._this_year = this_year

        # fake this repo as lgpv2+
        def lgpl():
            log.info('mocked get_license returns LGPLv2+')
            return 'LGPLv2+', ''
        vsc.install.shared_setup.get_license = lgpl

        # don't actually write, just compare with a .fixed file
        compares = []

        def compare(filename, content):
            log.info('mocked write does compare for %s ' % filename)
            name = filename.replace('.check', '')
            compares.append(name)
            new_filename = filename.replace('.check', '.fixed')
            self.assertEqual(content, open(new_filename).read(),
                             msg='new content is as expected for %s' % filename)

        vsc.install.headers._write = compare

        # filename without .check or .fixed, tuple with script or not and , changed or not
        expected = {
            't1': (False, True),
            't2': (True, True),
            't3': (True, False),
            't4-external': (False, False),  # external license
            't5': (True, True),  # encoding
            't6': (True, True),  # python + header
            't7': (True, True),  # python only
            't8.py': (True, True),  # python script with missing shebang
            't9.sh': (True, True),  # shell script with missing shebang/license header
        }

        for filename in glob.glob(os.path.join(self.setup.REPO_TEST_DIR, 'headers', "*.check*")):
            name = os.path.basename(filename).replace('.check', '')
            self.assertEqual(check_header(filename, script=expected[name][0], write=True),
                             expected[name][1], msg='checked headers for filename %s' % filename)

        not_changed = [k for k, v in expected.items() if not v[1]]
        self.assertEqual(len(compares), len(expected) - len(not_changed),
                         msg='number of mocked writes/compares as expected')
        for ext in not_changed:
            self.assertFalse(ext in compares, msg='not changed %s not compared' % ext)
