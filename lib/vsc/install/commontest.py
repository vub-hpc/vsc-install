#
# Copyright 2014-2023 Ghent University
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
"""
Module for common project tests

CommonTest usage: make a module 00-import.py in the test/ dir that has only the following line
   from vsc.install.commontest import CommonTest

Running python setup.py test will pick this up and do its magic

@author: Stijn De Weirdt (Ghent University)
"""

import optparse
import os
import pkg_resources
import pprint
import re
import sys
from prospector.run import Prospector
from prospector.config import ProspectorConfig

from distutils import log
from vsc.install.ci import JENKINSFILE, TOX_INI, gen_jenkinsfile, gen_tox_ini
from vsc.install.headers import check_header
from vsc.install.shared_setup import vsc_setup
from vsc.install.testing import TestCase

prospector_version = pkg_resources.get_distribution("prospector").version

# this sets the --uses commandline
PROSPECTOR_USE_LIBS = []


# List of regexps patterns applied to code or message of a prospector.message.Message
#   Blacklist: if match, skip message, do not check whitelist
#   Whitelist: if match, fail test
PROSPECTOR_BLACKLIST = [
    # 'wrong-import-position',  # not sure about this, these usually have a good reason
    'Locally disabling',  # shows up when you locally disable a warning, this is the point
    'Useless suppression',  # shows up when you locally disable/suppress a warning, this is the point
    "Redefining built-in 'reduce'",  # allow importing reduce from functools, required for Python 3 compatibility
    'c-extension-no-member', # run-time inspection of c extensions is disabled by default and gives warnings
]
# to disable any of these warnings in a block, you can do things like add a comment # pylint: disable=C0321
PROSPECTOR_WHITELIST = [
    #'protected-access',
    'E101',  # mixing tabs and spaces
    'E111',  # pep8: E111 / indentation is not a multiple of four
    'E501',  # 'line too long'when a line is longer then 120 chars
    'E713',  # not 'c' in d: -> 'c' not in d:
    'F811',  # redefinition of unused name
    'W291',  # pep8: W291 / trailing whitespace
    'arguments-differ',
    'assignment-from-no-return', # Assigning result of a function call, where the function has no return
    'backtick',  # don't use `variable` to turn a variable in a string, use the str() function
    'bad-indentation',
    'bad-whitespace',
    'bare-except',
    'consider-using-with', # By using 'with' the release of the allocated res is ensured in the case of an exception.
    'dangerous-default-value',
    'duplicate-key',  # when a key appears twice in a dict definition
    'import-star-module-level',  # Import * only allowed at module level
    'inconsistent-return-statements', # Either all or no return statements in a function should return an expression.
    'indexing-exception',  # indexing exceptions doesn't work in python3, use Exc.args[index] instead (but why?)
    'line-too-long', # use fail using pylint as well (not only pep8 above)
    'logging-not-lazy',
    'logging-too-few-args',
    'logging-too-many-args',
    'metaclass-assignment',  # __metaclass__ doesn't exist anymore in python3
    'no-member',
    'no-value-for-parameter',
    'old-ne-operator',  # don't use <> as not equal operator, use !=
    'old-octal-literal',  # use 0o700 instead of 0700
    'old-raise-syntax',  # sed when the alternate raise syntax raise foo, bar is used instead of raise foo(bar) .
    'print-statement',  # use print() and from future import __print__ instead of print
    'raising-string',  # don't raise strings, raise objects extending Exception (python2)
    'raising-bad-type',  # don't raise strings, raise objects extending Exception (python3)
    'redefine-in-handler',  # except A, B -> except (A, B)
    'redefined-builtin',
    'reimported',
    'syntax-error',
    'trailing-whitespace',
    'undefined',
    'unnecessary-semicolon',
    'unpacking-in-except', # will stop working in python3
    'unused-argument',
    'unused-import',
    'unused-variable',
]

# Prospector commandline options (positional path is added automatically)
PROSPECTOR_OPTIONS = [
    '--profile', 'strictness_none.yaml',
    '--max-line-length', '120',
    '--absolute-paths',
    # We want to get messages from different tools even if they mean the same.
    '--no-blending',
    # Do not pick up any config for the tools
    '--no-external-config',
    # If pylint dies, prospector will carry on, so seemingly all pylint tests will pass.
    # pylint py3 checker might get into some kind of recursive import so either
    # it might need higher recursion depth (sys.setrecursionlimit(x>1000),
    # or the problem should be solved in another way.
    '--die-on-tool-error',
]

# prospector ignore paths
PROSPECTOR_IGNORE_PATHS = []

# prospector ignore paths defaults
PROSPECTOR_IGNORE_PATHS_DEFAULTS = [
    'build'
]


def prospector_ignore_paths_add(path):
    """Add a path that should be ignored by prospector"""
    PROSPECTOR_IGNORE_PATHS.append(path)


def run_prospector(base_dir, clear_ignore_patterns=False):
    """Run prospector and apply white/blacklists to the results"""
    orig_expand_default = optparse.HelpFormatter.expand_default

    log.info("Using prosector version %s", prospector_version)

    ignore_dirs = ','.join(PROSPECTOR_IGNORE_PATHS + PROSPECTOR_IGNORE_PATHS_DEFAULTS)
    sys.argv = ['fakename']
    sys.argv.extend(PROSPECTOR_OPTIONS + ['--ignore-paths', ignore_dirs])
    log.debug("Prospector ignoring paths: %s", ignore_dirs)

    if PROSPECTOR_USE_LIBS:
        sys.argv.extend(["--uses", ",".join(PROSPECTOR_USE_LIBS)])

    # add/set REPO_BASE_DIR as positional path
    sys.argv.append(base_dir)
    log.debug("prospector commandline %s" % sys.argv)

    config = ProspectorConfig()
    # prospector will sometimes wrongly autodetect django
    config.libraries = []
    prospector = Prospector(config)

    # Set defaults for prospector:
    config.profile.doc_warnings = False
    config.profile.test_warnings = False
    config.profile.autodetect = True
    config.profile.member_warnings = False
    if clear_ignore_patterns:
        config.profile.ignore_patterns = [r'.^']
        config.ignores = []
    else:
        append_pattern = r'(^|/)\..+'
        config.profile.ignore_patterns.append(append_pattern)
        config.ignores.append(re.compile(append_pattern))

    # Enable pylint Python3 compatibility tests:
    config.profile.pylint['options']['enable'] = 'python3'
    log.debug("prospector argv = %s" % sys.argv)
    log.debug("prospector profile from config = %s" % vars(config.profile))

    prospector.execute()
    log.debug("prospector profile form prospector = %s" % vars(prospector.config.profile))

    # map yields a generator object in Python 3, but since we want to iterate over the whitelist/blacklist
    # multiple times, we need to make sure it's a list (since you can only iterate once over a generator)
    blacklist = list(map(re.compile, PROSPECTOR_BLACKLIST))
    whitelist = list(map(re.compile, PROSPECTOR_WHITELIST))

    failures = []
    for msg in prospector.get_messages():
        # example msg.as_dict():
        #  {'source': 'pylint', 'message': 'Missing function docstring', 'code': 'missing-docstring',
        #   'location': {'function': 'TestHeaders.test_check_header.lgpl', 'path': u'headers.py',
        #                'line': 122, 'character': 8, 'module': 'headers'}}
        log.debug("prospector message %s" % msg.as_dict())

        if any([bool(reg.search(msg.code) or reg.search(msg.message)) for reg in blacklist]):
            continue

        if any([bool(reg.search(msg.code) or reg.search(msg.message)) for reg in whitelist]):
            failures.append(msg.as_dict())

    # There is some ugly monkeypatch code in pylint
    #     (or logilab if no recent enough pylint is installed)
    # Make sure the original is restored
    # (before any errors are reported; no need to put this in setUp/tearDown)
    optparse.HelpFormatter.expand_default = orig_expand_default

    return failures


def check_autogenerated_ci_config_file(testcase_instance, ci_cfg_fn, expected_contents):
    """Test whether specified CI configuration file is in place, and was auto-generated by vsc-install."""

    testcase_instance.assertTrue(os.path.exists(ci_cfg_fn))
    with open(ci_cfg_fn) as fh:
        current_contents = fh.read()

    # allow differing Jenkinsfile if Jenkinsfile.NOT_AUTOGENERATED_YET exists (and likewise for tox.ini)
    # if contents are equal to what's generated, purposely fail the check
    ci_cfg_ignore_fn = ci_cfg_fn + '.NOT_AUTOGENERATED_YET'

    if os.path.exists(ci_cfg_ignore_fn):
        error_msg = "Found %s, so contents of %s is expected to be different " % (ci_cfg_ignore_fn, ci_cfg_fn)
        error_msg += "from what vsc-install generates (but it's not!): %s" % current_contents
        testcase_instance.assertNotEqual(current_contents, expected_contents, error_msg)

        # if the ignore file exists, it should contain the URL of a vsc-install issue
        with open(ci_cfg_ignore_fn) as ignore_file:
            txt = ignore_file.read()
            regex = re.compile(r'https://github.com/hpcugent/vsc-install/issues/[0-9]+')
            error_msg = "Pattern '%s' does not match in contents of %s: %s" % (regex.pattern, ci_cfg_ignore_fn, txt)
            testcase_instance.assertTrue(bool(regex.search(txt)), error_msg)
    else:
        error_msg = "Contents of %s does not match expected contents, " % ci_cfg_fn
        error_msg += "you should run 'python -m vsc.install.ci' again to re-generate %s" % ci_cfg_fn
        testcase_instance.assertEqual(current_contents, expected_contents, error_msg)


class CommonTest(TestCase):
    """
    Test class to group common basic tests such as
        - can a module/script be imported
        - simple prospector test
    """

    EXTRA_PKGS = None  # additional packages to test / try to import
    EXCLUDE_PKGS = None  # list of regexp patters to remove from list of package to test

    EXTRA_MODS = None  # additional modules to test / try to import
    EXCLUDE_MODS = None  # list of regexp patterns to remove from list of modules to test

    EXTRA_SCRIPTS = None  # additional scripts to test / try to import
    EXCLUDE_SCRIPTS = None  # list of regexp patterns to remove from list of scripts to test

    CHECK_HEADER = True

    def setUp(self):
        """Cleanup after running a test."""
        self.orig_sys_argv = sys.argv
        self.setup = vsc_setup()
        super(CommonTest, self).setUp()

    def tearDown(self):
        """Cleanup after running a test."""
        sys.argv = self.orig_sys_argv
        super(CommonTest, self).tearDown()

    def _import(self, pkg):
        try:
            __import__(pkg)
        except ImportError as e:
            log.debug("__path__ %s",
                      ["%s = %s" % (name, getattr(mod, '__path__', 'None')) for name, mod in sys.modules.items()])
            self.assertFalse(e, msg="import %s failed sys.path %s exception %s" % (pkg, sys.path, e))

        self.assertTrue(pkg in sys.modules, msg='%s in sys.modules after import' % pkg)

    def test_import_packages(self):
        """Try to import each namespace"""
        for pkg in self.setup.generate_packages(extra=self.EXTRA_PKGS, exclude=self.EXCLUDE_PKGS):
            self._import(pkg)

            if self.CHECK_HEADER:
                for fn in self.setup.files_in_packages()['packages'][pkg]:
                    self.assertFalse(check_header(os.path.join(self.setup.REPO_BASE_DIR, fn),
                                     script=False, write=False),
                                     msg='check_header of %s' % fn)

    def test_import_modules(self):
        """Try to import each module"""
        for modname in self.setup.generate_modules(extra=self.EXTRA_MODS, exclude=self.EXCLUDE_MODS):
            self._import(modname)

    def test_importscripts(self):
        """Try to import each python script as a module"""
        # sys.path is already setup correctly
        for scr in self.setup.generate_scripts(extra=self.EXTRA_SCRIPTS, exclude=self.EXCLUDE_SCRIPTS):
            if not scr.endswith('.py'):
                continue
            self._import(os.path.basename(scr)[:-len('.py')])

            if self.CHECK_HEADER:
                self.assertFalse(check_header(os.path.join(self.setup.REPO_BASE_DIR, scr), script=True, write=False),
                                 msg='check_header of %s' % scr)

    def test_prospector(self):
        """Test prospector failures"""

        failures = run_prospector(self.setup.REPO_BASE_DIR)
        self.assertFalse(failures, "prospector failures: %s" % pprint.pformat(failures))

    def test_jenkinsfile(self):
        """Test whether Jenkinsfile is in place, and was auto-generated by vsc-install."""
        check_autogenerated_ci_config_file(self, JENKINSFILE, gen_jenkinsfile())

    def test_tox_ini(self):
        """Test whether tox.ini is in place, and was auto-generated by vsc-install."""
        check_autogenerated_ci_config_file(self, TOX_INI, gen_tox_ini())
