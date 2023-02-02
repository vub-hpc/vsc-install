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
Shared module for vsc software testing

TestCase: use instead of unittest TestCase
   from vsc.install.testing import TestCase

@author: Stijn De Weirdt (Ghent University)
@author: Kenneth Hoste (Ghent University)
"""
import pprint
import os
import re
import shutil
import sys
import tempfile

try:
    from cStringIO import StringIO  # Python 2
except ImportError:
    from io import StringIO  # Python 3

from copy import deepcopy
from unittest import TestCase as OrigTestCase
from vsc.install.headers import nicediff
from vsc.install.methodinspector import MethodInspector
from mock import patch


class TestCase(OrigTestCase):
    """Enhanced test case, provides extra functionality (e.g. an assertErrorRegex method)."""

    longMessage = True # print both standard messgae and custom message

    LOGCACHE = {}

    ASSERT_MAX_DIFF = 100
    DIFF_OFFSET = 5 # lines of text around changes

    def is_string(self, x):
        """test if the variable x is a string)"""
        try:
            return isinstance(x, basestring)
        except NameError:
            return isinstance(x, str)

    # pylint: disable=arguments-differ
    def assertEqual(self, a, b, msg=None):
        """Make assertEqual always print useful messages"""

        try:
            super(TestCase, self).assertEqual(a, b)
        except AssertionError as e:
            if msg is None:
                msg = str(e)
            else:
                msg = "%s: %s" % (msg, e)

            if self.is_string(a):
                txta = a
            else:
                txta = pprint.pformat(a)
            if self.is_string(b):
                txtb = b
            else:
                txtb = pprint.pformat(b)

            diff = nicediff(txta, txtb, offset=self.DIFF_OFFSET)
            if len(diff) > self.ASSERT_MAX_DIFF:
                limit = ' (first %s lines)' % self.ASSERT_MAX_DIFF
            else:
                limit = ''

            raise AssertionError("%s:\nDIFF%s:\n%s" % (msg, limit, ''.join(diff[:self.ASSERT_MAX_DIFF])))

    def setUp(self):
        """Prepare test case."""
        super(TestCase, self).setUp()

        self.maxDiff = None
        self.longMessage = True

        self.orig_sys_stdout = sys.stdout
        self.orig_sys_stderr = sys.stderr

        self.orig_sys_argv = sys.argv
        sys.argv = deepcopy(self.orig_sys_argv)

        self.orig_workdir = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()

    def convert_exception_to_str(self, err):
        """Convert an Exception instance to a string."""
        msg = err
        if hasattr(err, 'msg'):
            msg = err.msg
        elif hasattr(err, 'message'):
            msg = err.message
            if not msg:
                # rely on str(msg) in case err.message is empty
                msg = err
        elif hasattr(err, 'args'):  # KeyError in Python 2.4 only provides message via 'args' attribute
            msg = err.args[0]
        else:
            msg = err
        try:
            res = str(msg)
        except UnicodeEncodeError:
            res = msg.encode('utf8', 'replace')

        return res

    def assertErrorRegex(self, error, regex, call, *args, **kwargs):
        """
        Convenience method to match regex with the expected error message.
        Example: self.assertErrorRegex(OSError, "No such file or directory", os.remove, '/no/such/file')
        """
        try:
            call(*args, **kwargs)
            str_kwargs = ['='.join([k, str(v)]) for (k, v) in kwargs.items()]
            str_args = ', '.join(list(map(str, args)) + str_kwargs)
            self.assertTrue(False, "Expected errors with %s(%s) call should occur" % (call.__name__, str_args))
        except error as err:
            msg = self.convert_exception_to_str(err)
            if self.is_string(regex):
                regex = re.compile(regex)
            self.assertTrue(regex.search(msg), "Pattern '%s' is found in '%s'" % (regex.pattern, msg))

    def mock_stdout(self, enable):
        """Enable/disable mocking stdout."""
        sys.stdout.flush()
        if enable:
            sys.stdout = StringIO()
        else:
            sys.stdout = self.orig_sys_stdout

    def mock_stderr(self, enable):
        """Enable/disable mocking stdout."""
        sys.stderr.flush()
        if enable:
            sys.stderr = StringIO()
        else:
            sys.stderr = self.orig_sys_stderr

    def get_stdout(self):
        """Return output captured from stdout until now."""
        return sys.stdout.getvalue()

    def get_stderr(self):
        """Return output captured from stderr until now."""
        return sys.stderr.getvalue()

    def mock_logmethod(self, logmethod_func):
        """
        Intercept the logger logmethod. Use as
            mylogger = logging.getLogger
            mylogger.error = self.mock_logmethod(mylogger.error)
        """
        def logmethod(*args, **kwargs):
            if hasattr(logmethod_func, 'func_name'):
                funcname = logmethod_func.func_name
            elif hasattr(logmethod_func, 'im_func'):
                funcname = logmethod_func.im_func.__name__
            elif hasattr(logmethod_func, '__name__'):
                funcname = logmethod_func.__name__
            else:
                raise Exception("Unknown logmethod %s" % (dir(logmethod_func)))
            logcache = self.LOGCACHE.setdefault(funcname, [])
            logcache.append({'args': args, 'kwargs': kwargs})
            logmethod_func(*args, **kwargs)

        return logmethod

    def reset_logcache(self, funcname=None):
        """
        Reset the LOGCACHE
        @param: funcname: if set, only reset the cache for this log function
                (default is to reset the whole chache)
        """
        if funcname:
            self.LOGCACHE[funcname] = []
        else:
            self.LOGCACHE = {}

    def count_logcache(self, funcname):
        """
        Return the number of log messages for funcname in the logcache
        """
        return len(self.LOGCACHE.get(funcname, []))

    def gen_inspector(self, *args, **kwargs):
        """
        Convenience method to generate MethodInspector instance.
        All args are passed to the MethodInspector
        """
        return MethodInspector(*args, **kwargs)

    def create_patch(self, *args, **kwargs):
        """
        Create patch and return mocked whatever. Patch is added to tearDown
        All args are passed to patch
        """
        patcher = patch(*args, **kwargs)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing

    def tearDown(self):
        """Cleanup after running a test."""
        self.mock_stdout(False)
        self.mock_stderr(False)
        self.reset_logcache()
        sys.argv = self.orig_sys_argv
        os.chdir(self.orig_workdir)
        shutil.rmtree(self.tmpdir)

        super(TestCase, self).tearDown()


# backwards incompatible change
class VSCImportTest(TestCase):
    def test_deprecated_fail(self):
        """
        VSCImportTest is now deprecated and will always fail, use
            from vsc.install.commontest import CommonTest
        """
        self.assertTrue(False, msg='Use "from vsc.install.commontest import CommonTest" instead of VSCImportTest.')
