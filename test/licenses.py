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
"""Test licenses"""
import os

from vsc.install.testing import TestCase
from vsc.install.shared_setup import KNOWN_LICENSES, vsc_setup
from vsc.install.shared_setup import PYPI_LICENSES


class LicenseTest(TestCase):
    """License related tests"""

    def setUp(self):
        """Create a vsc_setup instance for each test"""
        super(LicenseTest, self).setUp()
        self.setup = vsc_setup()

    def test_known_licenses(self):
        """Test the KNOWN_LICENSES"""

        total_licenses = len(KNOWN_LICENSES)
        self.assertEqual(total_licenses, 3,
                         msg='shared_setup has %s licenses' % total_licenses)

        md5sums = []
        for short, data in KNOWN_LICENSES.items():
            # the known text must be in known_licenses dir with the short name
            fn = os.path.join(self.setup.REPO_BASE_DIR, 'known_licenses', short)
            self.assertTrue(os.path.isfile(fn),
                            msg='license %s is in known_licenses directory' % short)

            md5sum = self.setup.get_md5sum(fn)
            self.assertEqual(data[0], md5sum,
                             msg='md5sum from KNOWN_LICENSES %s matches the one in known_licenses dir %s for %s' %
                             (data[0], md5sum, short))
            self.assertFalse(md5sum in md5sums,
                             msg='md5sum for license %s is unique' % md5sum)

            lic_name, classifier = self.setup.get_license(license_name=fn)
            self.assertEqual(lic_name, os.path.basename(fn),
                             msg='file %s is license %s' % (fn, lic_name))
            self.assertTrue(classifier.startswith('License :: OSI Approved :: ') or
                            classifier == 'License :: Other/Proprietary License',
                            msg='classifier as expected for %s' % short)

    def test_release_on_pypi(self):
        """Release on pypi or not"""

        self.assertEqual(PYPI_LICENSES, ['LGPLv2+', 'GPLv2'], 'Expected licenses that allow releasing on pypi')

        for short in KNOWN_LICENSES.keys():
            self.assertEqual(self.setup.release_on_pypi(short), short in PYPI_LICENSES,
                             msg='can %s be usd to release on pypi' % short)
