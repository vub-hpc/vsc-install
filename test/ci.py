#
# Copyright 2019-2023 Ghent University
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
Test CI functionality

@author: Kenneth Hoste (Ghent University)
"""
import os
import re

from vsc.install.ci import gen_jenkinsfile, gen_tox_ini, parse_vsc_ci_cfg
from vsc.install.testing import TestCase


JENKINSFILE_INIT = """// Jenkinsfile: scripted Jenkins pipefile
// This file was automatically generated using 'python -m vsc.install.ci'
// DO NOT EDIT MANUALLY

node {
    stage('checkout git') {
        checkout scm
        // remove untracked files (*.pyc for example)
        sh 'git clean -fxd'
    }
"""

EASY_INSTALL_TOX = "        sh 'python -m easy_install -U --user tox'\n"
PIP_INSTALL_TOX = """        sh 'pip install --user --upgrade pip'
        sh 'export PATH=$HOME/.local/bin:$PATH && pip install --ignore-installed --prefix $PWD/.vsc-tox "zipp<3.0" tox'
"""
PIP3_INSTALL_TOX = "        sh 'pip3 install --ignore-installed --prefix $PWD/.vsc-tox tox'\n"

TOX_RUN_PY3 = """        sh 'export PATH=$PWD/.vsc-tox/bin:$PATH && export PYTHONPATH=$PWD/.vsc-tox/lib/python$(python3 -c "import sys; print(\\\\"%s.%s\\\\" % sys.version_info[:2])")/site-packages:$PYTHONPATH && tox -v -c tox.ini'
        sh 'rm -r $PWD/.vsc-tox'\n"""
TOX_RUN_PY2 = TOX_RUN_PY3.replace('python3', 'python')

JENKINSFILE_TEST_START = """    stage('test') {
        sh 'python2.7 -V'
"""
JENKINSFILE_END_STAGE = "    }\n"

JENKINSFILE_TEST_STAGE = JENKINSFILE_TEST_START + EASY_INSTALL_TOX + TOX_RUN_PY2 + JENKINSFILE_END_STAGE
JENKINSFILE_TEST_STAGE_PIP = JENKINSFILE_TEST_START + PIP_INSTALL_TOX + TOX_RUN_PY2 + JENKINSFILE_END_STAGE
JENKINSFILE_TEST_STAGE_PIP3 = JENKINSFILE_TEST_START + PIP3_INSTALL_TOX + TOX_RUN_PY3 + JENKINSFILE_END_STAGE

EXPECTED_JENKINSFILE_DEFAULT = JENKINSFILE_INIT + JENKINSFILE_TEST_STAGE + '}\n'
EXPECTED_JENKINSFILE_PIP_INSTALL_TOX = JENKINSFILE_INIT + JENKINSFILE_TEST_STAGE_PIP + '}\n'
EXPECTED_JENKINSFILE_PIP3_INSTALL_TOX = JENKINSFILE_INIT + JENKINSFILE_TEST_STAGE_PIP3 + '}\n'

EXPECTED_JENKINSFILE_JIRA = JENKINSFILE_INIT + JENKINSFILE_TEST_STAGE + """    stage('PR title JIRA link') {
        if (env.CHANGE_ID) {
            if (env.CHANGE_TITLE =~ /\s+\(?HPC-\d+\)?/) {
                echo "title ${env.CHANGE_TITLE} seems to contain JIRA ticket number."
            } else {
                echo "ERROR: title ${env.CHANGE_TITLE} does not end in 'HPC-number'."
                error("malformed PR title ${env.CHANGE_TITLE}.")
            }
        }
    }
}
"""

JENKINSFILE_SHELLCHECK_STAGE = """    stage ('shellcheck') {
        sh 'curl -L --silent https://github.com/koalaman/shellcheck/releases/download/latest/shellcheck-latest.linux.x86_64.tar.xz --output - | tar -xJv'
        sh 'cp shellcheck-latest/shellcheck .'
        sh 'rm -r shellcheck-latest'
        sh './shellcheck --version'
        sh './shellcheck bin/*.sh'
    }
"""

EXPECTED_JENKINSFILE_SHELLCHECK = JENKINSFILE_INIT + JENKINSFILE_SHELLCHECK_STAGE + JENKINSFILE_TEST_STAGE + '}\n'

EXPECTED_TOX_INI = """# tox.ini: configuration file for tox
# This file was automatically generated using 'python -m vsc.install.ci'
# DO NOT EDIT MANUALLY

[tox]
envlist = py27,py36
skipsdist = true

[testenv]
commands_pre =
    pip install 'setuptools<42.0'
    python -m easy_install -U vsc-install
commands = python setup.py test
passenv = USER
"""

EXPECTED_TOX_INI_PY36_IGNORE = """
[testenv:py36]
ignore_outcome = true
"""


class CITest(TestCase):
    """License related tests"""

    def setUp(self):
        """Test setup."""
        super(CITest, self).setUp()

        os.chdir(self.tmpdir)

    def write_vsc_ci_ini(self, txt):
        """Write vsc-ci.ini file in current directory with specified contents."""
        fh = open('vsc-ci.ini', 'w')
        fh.write('[vsc-ci]\n')
        fh.write(txt)
        fh.write('\n')
        fh.close()

    def test_parse_vsc_ci_cfg(self):
        """Test parse_vsc_ci_cfg function."""

        default = {
            'additional_test_commands': None,
            'home_install': False,
            'inherit_site_packages': False,
            'install_scripts_prefix_override': False,
            'jira_issue_id_in_pr_title': False,
            'move_setup_cfg': False,
            'pip_install_test_deps': None,
            'pip_install_tox': False,
            'pip3_install_tox': False,
            'py3_only': False,
            'py3_tests_must_pass': True,
            'run_shellcheck': False,
        }

        # (basically) empty vsc-ci.ini
        self.write_vsc_ci_ini('')
        self.assertEqual(parse_vsc_ci_cfg(), default)

        # vsc-ci.ini with unknown keys is trouble
        self.write_vsc_ci_ini("unknown_key=1")
        error_msg = "Unknown key in vsc-ci.ini: unknown_key"
        self.assertErrorRegex(ValueError, error_msg, parse_vsc_ci_cfg)

        vsc_ini_txt_lines = []
        for key in default.keys():
            # special treatment needed for non-boolean keys like additional_test_commands
            if default[key] is None:
                vsc_ini_txt_lines.append('%s=foo' % key)
            else:
                vsc_ini_txt_lines.append('%s=1' % key)

        self.write_vsc_ci_ini('\n'.join(vsc_ini_txt_lines))
        expected = dict((key, True) for key in default.keys())
        for key in default.keys():
            if default[key] is None:
                expected[key] = 'foo'
        self.assertEqual(parse_vsc_ci_cfg(), expected)

    def test_gen_jenkinsfile(self):
        """Test generating of Jenkinsfile."""
        self.assertEqual(gen_jenkinsfile(), EXPECTED_JENKINSFILE_DEFAULT)

    def test_gen_jenkinsfile_jira_issue_id_in_pr_title(self):
        """Test generating of Jenkinsfile incl. check for JIRA issue in PR title."""

        self.write_vsc_ci_ini('jira_issue_id_in_pr_title=1')

        jenkinsfile_txt = gen_jenkinsfile()
        self.assertEqual(jenkinsfile_txt, EXPECTED_JENKINSFILE_JIRA)

    def test_gen_jenkinsfile_pip_install_tox(self):
        """Test generating of Jenkinsfile incl. install tox with 'pip install."""

        self.write_vsc_ci_ini('pip_install_tox=1')
        jenkinsfile_txt = gen_jenkinsfile()
        self.assertEqual(jenkinsfile_txt, EXPECTED_JENKINSFILE_PIP_INSTALL_TOX)

    def test_gen_jenkinsfile_pip3_install_tox(self):
        """Test generating of Jenkinsfile incl. install tox with 'pip3 install."""

        self.write_vsc_ci_ini('pip3_install_tox=1')
        jenkinsfile_txt = gen_jenkinsfile()
        self.assertEqual(jenkinsfile_txt, EXPECTED_JENKINSFILE_PIP3_INSTALL_TOX)

    def test_gen_jenkinsfile_home_pip3_install_tox(self):
        """Test generating of Jenkinsfile incl. install tox with 'pip3 install."""

        self.write_vsc_ci_ini('home_install=1\npip3_install_tox=1')
        jenkinsfile_txt = gen_jenkinsfile()

        expected = EXPECTED_JENKINSFILE_PIP3_INSTALL_TOX
        expected = expected.replace('pip3 install', 'export PREFIX=$PWD && cd $HOME && pip3 install')
        expected = expected.replace('--prefix $PWD', '--prefix $PREFIX')
        self.assertEqual(jenkinsfile_txt, expected)

    def test_gen_jenkinsfile_shellcheck(self):
        """Test generating of Jenkinsfile incl. running of shellcheck."""

        self.write_vsc_ci_ini('run_shellcheck=1')
        jenkinsfile_txt = gen_jenkinsfile()
        self.assertEqual(jenkinsfile_txt, EXPECTED_JENKINSFILE_SHELLCHECK)

    def test_tox_ini_additional_test_commands(self):
        """Test use of 'additional_test_commands' in vsc-ci.ini."""

        self.write_vsc_ci_ini('additional_test_commands=./more_tests.sh')
        expected = JENKINSFILE_INIT + JENKINSFILE_TEST_START + EASY_INSTALL_TOX + TOX_RUN_PY2 + '\n'.join([
            "        sh './more_tests.sh'",
            "    }",
            "}",
            '',
        ])
        self.assertEqual(gen_jenkinsfile(), expected)

        self.write_vsc_ci_ini('\n'.join([
            'additional_test_commands=',
            '    ./more_tests.sh',
            '    another-command',
            '    test -f foo.txt',
            "    echo 'this command uses single quotes'",
        ]))
        expected = JENKINSFILE_INIT + JENKINSFILE_TEST_START + EASY_INSTALL_TOX + TOX_RUN_PY2 + '\n'.join([
            "        sh './more_tests.sh'",
            "        sh 'another-command'",
            "        sh 'test -f foo.txt'",
            '        sh """echo \'this command uses single quotes\'"""',
            "    }",
            "}",
            '',
        ])
        self.assertEqual(gen_jenkinsfile(), expected)

    def test_tox_ini(self):
        """Test generating of tox.ini."""
        self.assertEqual(gen_tox_ini(), EXPECTED_TOX_INI)

    def test_tox_ini_inherit_site_packages(self):
        """Test generation of tox.ini with inheriting of site packages enabled."""

        self.write_vsc_ci_ini('inherit_site_packages=1')

        expected = EXPECTED_TOX_INI + 'sitepackages = true\n'
        self.assertEqual(gen_tox_ini(), expected)

    def test_tox_ini_py3_tests(self):
        """Test generation of tox.ini when Python 3 tests are ignored."""

        self.write_vsc_ci_ini('py3_tests_must_pass=0')

        expected = EXPECTED_TOX_INI.replace('skipsdist = true', 'skipsdist = true\nskip_missing_interpreters = true')
        expected += EXPECTED_TOX_INI_PY36_IGNORE
        self.assertEqual(gen_tox_ini(), expected)

    def test_tox_ini_py3_only(self):
        """Test generation of tox.ini when tests should only be run with Python 3."""

        self.write_vsc_ci_ini('py3_only=1')

        expected = EXPECTED_TOX_INI.replace('envlist = py27,py36', 'envlist = py36')
        self.assertEqual(gen_tox_ini(), expected)

    def test_install_scripts_prefix_override(self):
        """Test generating of tox.ini when install_scripts_prefix_override is set."""

        self.write_vsc_ci_ini('install_scripts_prefix_override=1\npip3_install_tox=1')

        expected_tox_ini = EXPECTED_TOX_INI
        pip_regex = re.compile('pip install')
        pip_install_scripts = 'pip install --install-option="--install-scripts={envdir}/bin"'
        expected_tox_ini = pip_regex.sub(pip_install_scripts, expected_tox_ini)
        easy_install_regex = re.compile('easy_install -U')
        expected_tox_ini = easy_install_regex.sub('easy_install -U --script-dir={envdir}/bin', expected_tox_ini)

        self.assertEqual(gen_tox_ini(), expected_tox_ini)

        self.assertEqual(gen_jenkinsfile(), EXPECTED_JENKINSFILE_PIP3_INSTALL_TOX)

    def test_move_setup_cfg(self):
        """Test moving setup.cfg out of the way while installing test deps."""

        self.write_vsc_ci_ini('move_setup_cfg=1')

        expected_tox_ini = EXPECTED_TOX_INI
        expected_tox_ini = expected_tox_ini.replace('commands_pre =', '\n'.join([
            'commands_pre =',
            '    mv setup.cfg setup.cfg.moved',
        ]))
        expected_tox_ini = expected_tox_ini.replace('commands =', '\n'.join([
            '    mv setup.cfg.moved setup.cfg',
            'commands =',
        ]))

        self.assertEqual(gen_tox_ini(), expected_tox_ini)

    def test_pip_install_test_deps(self):
        """Test specifying dependencies to pre-install for tests in tox.ini."""
        self.write_vsc_ci_ini('\n'.join([
            'pip_install_test_deps =',
            '    foo',
            '    bar<1.0',
        ]))

        expected_tox_ini = EXPECTED_TOX_INI
        expected_tox_ini = expected_tox_ini.replace('commands_pre =', '\n'.join([
            'commands_pre =',
            "    pip install 'foo'",
            "    pip install 'bar<1.0'",
        ]))

        self.assertEqual(gen_tox_ini(), expected_tox_ini)
