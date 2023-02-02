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
"""Test shared_setup"""

from __future__ import print_function

import os
import re

from vsc.install import shared_setup
from vsc.install.shared_setup import action_target, vsc_setup, _fvs

from vsc.install.testing import TestCase


class TestSetup(TestCase):
    """Test shared_setup"""

    def setUp(self):
        """create a self.setup.instance for every test"""
        super(TestSetup, self).setUp()
        self.setup = vsc_setup()

    def test_get_name_url(self):
        """Test naming function"""
        res = {
            'name': 'vsc-install',
            'url': 'https://github.com/hpcugent/vsc-install',
            'download_url': 'https://github.com/hpcugent/vsc-install/archive/0.1.2.tar.gz',
        }
        for fn in ['PKG-INFO', 'git_config', 'git_config_1', 'git_config_2', 'git_config_3', 'git_config_4',
                   'git_config_5']:
            self.assertEqual(self.setup.get_name_url(os.path.join(self.setup.REPO_TEST_DIR, 'setup', fn),
                             version='0.1.2'), res,
                             msg='determined name and url from %s file' % fn)

        res.pop('download_url')
        fn = 'git_config'
        self.assertEqual(self.setup.get_name_url(os.path.join(self.setup.REPO_TEST_DIR, 'setup', fn), version='0.1.2',
                         license_name='LGPLv2+'), res,
                         msg='determined name and url from %s file with license' % fn)

        fn = 'git_config_6'
        res_brussel = {
            'name': 'vsc-jobs-brussel',
            'url': 'https://github.com/vub-hpc/vsc-jobs-brussel',
            'download_url': 'https://github.com/vub-hpc/vsc-jobs-brussel/archive/0.1.0.tar.gz',
        }
        self.assertEqual(self.setup.get_name_url(os.path.join(self.setup.REPO_TEST_DIR, 'setup', fn), version='0.1.0'),
                         res_brussel,
                         msg='determined name and url from %s file with license' % fn)

    def test_sanitize(self):
        """Test sanitize function"""
        os.environ['VSC_RPM_PYTHON'] = '1'
        self.assertEqual(self.setup.sanitize('anything >= 5'), 'python-anything >= 5',
                         msg='all packages are prefixed with VSC_RPM_PYTHON set')

        self.assertEqual(self.setup.sanitize('vsc-xyz >= 10'), 'python-vsc-xyz >= 10',
                         msg='vsc packages are prefixed with VSC_RPM_PYTHON set')

        self.assertEqual(self.setup.sanitize('python-ldap == 11'), 'python-ldap == 11',
                         msg='packages starting with python- are not prefixed again with VSC_RPM_PYTHON set')

        self.assertEqual(shared_setup.PYTHON_BDIST_RPM_PREFIX_MAP, {'pycrypto': 'python%s-crypto', 'psycopg2': 'python%s-psycopg2'},
                         msg='PYTHON_BDIST_RPM_PREFIX_MAP is hardcoded mapping')
        self.assertEqual(self.setup.sanitize('pycrypto == 12'), 'python-crypto == 12',
                         msg='packages in PYTHON_BDIST_RPM_PREFIX_MAP are repalced with value with VSC_RPM_PYTHON set')

        self.assertEqual(shared_setup.NO_PREFIX_PYTHON_BDIST_RPM, ['pbs_python'],
                         msg='NO_PREFIX_PYTHON_BDIST_RPM is list of packages that are not modified')
        self.assertEqual(self.setup.sanitize('pbs_python <= 13'), 'pbs_python <= 13',
                         msg='packages in PYTHON_BDIST_RPM_PREFIX_MAP are not prefixed with VSC_RPM_PYTHON set')
        self.assertEqual(self.setup.sanitize('pbs_python <= 16, > 14'), 'pbs_python <= 16, pbs_python > 14',
                         msg='multiple requirements to package requirement per version with VSC_RPM_PYTHON set')
        self.assertEqual(self.setup.sanitize(['anything >= 5', 'vsc-xyz >= 10', 'pycrypto == 12', 'pbs_python <= 13']),
                         'python-anything >= 5\n    python-vsc-xyz >= 10\n    python-crypto == 12\n    pbs_python <= 13',
                         msg='list is newline-joined and replaced/prefixed with VSC_RPM_PYTHON set')

        os.environ['VSC_RPM_PYTHON'] = '2'
        self.assertEqual(self.setup.sanitize('anything >= 5'), 'python2-anything >= 5',
                         msg='all packages are prefixed with python2 if VSC_RPM_PYTHON set to 2')
        self.assertEqual(self.setup.sanitize('pycrypto == 12'), 'python2-crypto == 12',
                         msg='packages in PYTHON_BDIST_RPM_PREFIX_MAP are replaced with value with VSC_RPM_PYTHON set to 2')

        os.environ['VSC_RPM_PYTHON'] = '3'
        self.assertEqual(self.setup.sanitize('anything >= 5'), 'python3-anything >= 5',
                         msg='all packages are prefixed with python3 if VSC_RPM_PYTHON set to 3')
        self.assertEqual(self.setup.sanitize('pycrypto == 12'), 'python3-crypto == 12',
                         msg='packages in PYTHON_BDIST_RPM_PREFIX_MAP are replaced with value with VSC_RPM_PYTHON set to 3')

        os.environ['VSC_RPM_PYTHON'] = '0'
        self.assertEqual(self.setup.sanitize('anything >= 5'), 'anything >= 5',
                         msg='no prefixing with VSC_RPM_PYTHON not set')
        self.assertEqual(self.setup.sanitize('vsc-xyz >= 10'), 'vsc-xyz >= 10',
                         msg='vsc packages are not prefixed with VSC_RPM_PYTHON not set')
        self.assertEqual(self.setup.sanitize('pycrypto == 12'), 'pycrypto == 12',
                         msg='packages in PYTHON_BDIST_RPM_PREFIX_MAP are not repalced with value with VSC_RPM_PYTHON'
                         'not set')
        self.assertEqual(self.setup.sanitize('pbs_python <= 13'), 'pbs_python <= 13',
                         msg='packages in PYTHON_BDIST_RPM_PREFIX_MAP are not prefixed with VSC_RPM_PYTHON not set')
        self.assertEqual(self.setup.sanitize('pbs_python <= 16, > 14'), 'pbs_python <= 16, pbs_python > 14',
                         msg='multiple requirements to package requirement per version with VSC_RPM_PYTHON not set')
        self.assertEqual(self.setup.sanitize(['anything >= 5', 'vsc-xyz >= 10', 'pycrypto == 12', 'pbs_python <= 13']),
                         "anything >= 5\n    vsc-xyz >= 10\n    pycrypto == 12\n    pbs_python <= 13",
                         msg='list is newline-joined and nothing replaced/prefixed with VSC_RPM_PYTHON not set')

    def test_rel_gitignore(self):
        """
        Test the rel_gitignore function
        it should fail, since we don't specify a path for .pyc files in our gitignore
        """
        # when testing with a base_dir that has a .git folder, and a .gitignore file, we should get an error mentioning
        # .pyc
        base_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), './testdata')
        try:
            self.setup.rel_gitignore(['testdata'], base_dir=base_dir)
        except Exception as err:
            self.assertTrue('.pyc' in str(err))
        else:
            self.assertTrue(False, 'rel_gitignore should have raised an exception, but did not!')
        # it should not fail if base_dir does not contain a .git folder
        base_dir = os.path.dirname(os.path.realpath(__file__))
        self.assertEqual(self.setup.rel_gitignore(['testdata'], base_dir=base_dir), ['../testdata'])

    def test_import(self):
        """Test importing things from shared_setup.py, these should not be broken for backward compatibility."""
        from vsc.install.shared_setup import SHARED_TARGET
        from vsc.install.shared_setup import ag, eh, jt, kh, kw, lm, sdw, wdp, wp, sm

    def test_action_target(self):
        """Test action_target function, mostly w.r.t. backward compatibility."""
        def fake_setup(*args, **kwargs):
            """Fake setup function to test action_target with."""
            print('args: %s' % str(args))
            print('kwargs: %s' % kwargs)

        self.mock_stdout(True)
        action_target({'name': 'vsc-test', 'version': '1.0.0'}, setupfn=fake_setup)
        txt = self.get_stdout()
        self.mock_stdout(False)
        self.assertTrue(re.search(r"^args:\s*\(\)", txt, re.M))
        self.assertTrue(re.search(r"^kwargs:\s*\{.*'name':\s*'vsc-test'", txt, re.M))

        self.mock_stdout(True)
        action_target({'name': 'vsc-test', 'version': '1.0.0'}, setupfn=fake_setup, urltemplate='http://example.com/%(name)s')
        txt = self.get_stdout()
        self.mock_stdout(False)
        self.assertTrue(re.search(r"^args:\s*\(\)", txt, re.M))
        # this doesn't seem to test what you think it does? stdout is nog mocked correctly
        # self.assertTrue(re.search(r"^kwargs:\s*\{.*'url':\s*'http://example.com/vsc-test'", txt, re.M))

    def test_prepare_rpm(self):
        """
        Test the prepare rpm function
        especially in effect to generating correct package list wrt excluded_pkgs_rpm
        we assume the order of the lists doesn't matter (and sort to compare)
        """
        package = {
            'name': 'vsc-test',
            'excluded_pkgs_rpm': [],
            'version': '1.0',
        }
        setup = vsc_setup()

        libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), './testdata')
        setup.REPO_LIB_DIR = libdir
        setup.prepare_rpm(package)

        self.assertEqual(sorted(setup.SHARED_TARGET['packages']), ['vsc', 'vsc.test'])
        package = {
            'name': 'vsc-test',
            'excluded_pkgs_rpm': ['vsc', 'vsc.test'],
            'version': '1.0',
        }
        setup = vsc_setup()
        setup.REPO_LIB_DIR = libdir
        setup.prepare_rpm(package)

        self.assertEqual(sorted(setup.SHARED_TARGET['packages']), ['vsc', 'vsc.test'])

    def test_parse_target(self):
        """Test for parse target"""
        package = {
            'name': 'vsc-test',
            'excluded_pkgs_rpm': [],
            'version': '1.0',
        }
        setup = vsc_setup()
        klass = _fvs('vsc_bdist_rpm egg_info')
        # test to see if we don't fail on unknown/new cmdclasses
        orig_target = klass.SHARED_TARGET
        klass.SHARED_TARGET['cmdclass']['easy_install'] = object
        new_target = setup.parse_target(package)

        self.assertEqual(new_target['name'], 'vsc-test')
        self.assertEqual(new_target['version'], '1.0')
        self.assertEqual(new_target['long_description_content_type'], 'text/markdown')
        self.assertTrue(new_target['long_description'].startswith("Description\n==========="))

        klass.SHARED_TARGET = orig_target

    def test_parse_target_dependencies(self):
        """Test injecting dependency_links in parse_target"""
        package = {
            'name': 'vsc-test',
            'excluded_pkgs_rpm': [],
            'version': '1.0',
            'install_requires': [
                'vsc-config >= 2.0.0',
                'vsc-accountpage-clients',
                'vsc-base > 1.0.0'
            ],
        }
        setup = vsc_setup()
        # this is needed to pass the tests on Travis: travis will clone vsc-install through
        # https and it will be marked as non private repo, causing the dependency_links to be injected
        # with git+https, which is not correct in this test case.
        setup.private_repo = True
        new_target = setup.parse_target(package)

        dep_links_urls = [
            'git+ssh://git@github.com/hpcugent/vsc-accountpage-clients.git#egg=vsc-accountpage-clients',
            'git+ssh://git@github.ugent.be/hpcugent/vsc-accountpage-clients.git#egg=vsc-accountpage-clients',
            'git+ssh://git@github.com/hpcugent/vsc-config.git#egg=vsc-config-2.0.0',
            'git+ssh://git@github.ugent.be/hpcugent/vsc-config.git#egg=vsc-config-2.0.0',
            'git+ssh://git@github.com/hpcugent/vsc-base.git#egg=vsc-base-1.0.0',
            'git+ssh://git@github.ugent.be/hpcugent/vsc-base.git#egg=vsc-base-1.0.0',
        ]

        for url in dep_links_urls:
            self.assertIn(url, new_target['dependency_links'])

        package['install_requires'].append('vsc-utils<=1.0.0')
        self.assertRaises(ValueError, setup.parse_target, package)

    def test_parse_vsc_filter(self):
        """Test injecting dependency_links in parse_target"""
        inst_req = [
            'vsc-config >= 2.0.0',
            'vsc-accountpage-clients',
            'vsc-base > 1.0.0',
        ]

        def pkg(vfr):
            pkg = {
                'name': 'vsc-test',
                'excluded_pkgs_rpm': [],
                'version': '1.0',
                'install_requires': inst_req[:],
            }
            if vfr:
                pkg.update(vfr)
            return pkg

        def test_target(vfr, expected):
            setup = vsc_setup()
            new_target = setup.parse_target(pkg(vfr))
            self.assertEqual(new_target['install_requires'], expected)

        vfr = {
            'vsc_filter_rpm': {
                'install_requires': [
                    ['vsc-base.*', ''],
                    ['^(vsc-config).*', '\g<1>'], # strip version info for vsc-config
                ],
            },
        }

        os.environ.pop('VSC_RPM_PYTHON', None)

        # nothing in env, nothing passed as vfr
        test_target({}, inst_req)
        # nothing set in env
        test_target(vfr, inst_req)

        os.environ['VSC_RPM_PYTHON'] = '3'
        # something in env, nothing passed as vfr
        test_target({}, inst_req)
        # something in env
        test_target(vfr, ['vsc-config', 'vsc-accountpage-clients'])

    def test_setup_cfg(self):
        """Test generating of setup.cfg."""

        def read_setup_cfg():
            with open('setup.cfg') as fp:
                return fp.read().strip()

        os.chdir(self.tmpdir)

        # test with minimal target
        vsc_setup.build_setup_cfg_for_bdist_rpm({})
        expected = '\n'.join([
            '[bdist_rpm]',
            '',
            '[metadata]',
            '',
            'description-file = README.md',
        ])
        self.assertEqual(read_setup_cfg(), expected)

        # realistic target
        target = {
            'install_requires': ['vsc-base >= 3.1.0', 'vsc-ldap', 'requests', 'foobar < 1.0'],
            'setup_requires': ['vsc-install >= 0.17.11'],
        }
        vsc_setup.build_setup_cfg_for_bdist_rpm(target)
        expected = '\n'.join([
            '[bdist_rpm]',
            'requires = vsc-base >= 3.1.0',
            '    vsc-ldap',
            '    requests',
            '    foobar < 1.0',
            'build_requires = vsc-install >= 0.17.11',
            '',
            '[metadata]',
            '',
            'description-file = README.md',
        ])
        self.assertEqual(read_setup_cfg(), expected)

        # provides is rare, but it happens (see icinga-checks)
        target['provides'] = 'perl(utils)'
        vsc_setup.build_setup_cfg_for_bdist_rpm(target)
        expected_provides = expected.replace('build_requires', 'provides = perl(utils)\nbuild_requires')
        self.assertEqual(read_setup_cfg(), expected_provides)

        # provides is filtered out after calling build_setup_cfg_for_bdist_rpm
        self.assertFalse('provides' in target)

        # alternate location of scripts/binaries also specified
        target['install-scripts'] = '/path/to/scripts'
        vsc_setup.build_setup_cfg_for_bdist_rpm(target)
        expected = '\n'.join([
            '[install]',
            'install-scripts = /path/to/scripts',
            '',
            expected,
        ])
        self.assertEqual(read_setup_cfg(), expected)

        # install-scripts is filtered out after calling build_setup_cfg_for_bdist_rpm
        self.assertFalse('install-scripts' in target)

        # if makesetupcfg is set to False, existing setup.cfg is left untouched
        setup_cfg_txt = 'thisdoesnotreallymatter'
        with open('setup.cfg', 'w') as fp:
            fp.write(setup_cfg_txt)

        target['makesetupcfg'] = False
        vsc_setup.build_setup_cfg_for_bdist_rpm(target)
        self.assertEqual(read_setup_cfg(), setup_cfg_txt)

        self.assertFalse('makesetupcfg' in target)
