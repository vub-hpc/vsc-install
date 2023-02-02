#
# Copyright 2015-2023 Ghent University
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
Generate and verify headers from scripts and modules

This module has a very primitive main routine:
    REPO_BASE_DIR=$PWD python -m vsc.install.headers path/to/file [script_or_not]

    Will write the header to the file as it is supposed to be
    (the optional script or not is a simple 1 or 0).

    REPO_BASE_DIR=$PWD assumes you run this from the base repo

@author: Stijn De Weirdt (Ghent University)
"""

import difflib
import os
import re
import sys

from datetime import date
from vsc.install.shared_setup import SHEBANG_BIN_BASH, SHEBANG_ENV_PYTHON, log, vsc_setup

HEADER_REGEXP = re.compile(r'\A(.*?)^(?:\'\'\'|"""|### END OF HEADER)', re.M | re.S)
ENCODING_REGEXP = re.compile(r'^(\s*#\s*.*?coding[:=]\s*([-\w.]+).*).*$', re.M)  # PEP0263, 1st or 2nd line


def nicediff(txta, txtb, offset=5):
    """
    generate unified diff style output
        ndiff has nice indicators what is different, but prints the whole content
            each line that is interesting starts with non-space
        unified diff only prints changes and some offset around it

    return list with diff (one per line) (not a generator like ndiff or unified_diff)
    """
    diff = list(difflib.ndiff(txta.splitlines(1), txtb.splitlines(1)))
    different_idx = [idx for idx, line in enumerate(diff) if not line.startswith(' ')]
    res_idx = []
    # very bruteforce
    for didx in different_idx:
        for idx in range(max(didx - offset, 0), min(didx + offset, len(diff) - 1)):
            if idx not in res_idx:
                res_idx.append(idx)
    res_idx.sort()
    # insert linenumbers too? what are the linenumbers in ndiff?
    newdiff = [diff[idx] for idx in res_idx]

    return newdiff


# tools to determine current header
# generate new header based on license
# allow easy tool to fixup headers

def get_header(filename, script=False):
    """
    Given filename, retrieve header.
    If script is true, retrieve the shebang

    Header is start of file up to (not incl)
        docstring (first 3 ' or " at begin of line)
        magic comment '### END OF HEADER' at begin of line
    Anything can be part of the header, does not require starting # or something like that

    Return tuple: first element is header, 2nd element shebang if script
    """

    if not os.path.isfile(filename):
        raise Exception('get_header filename %s not found' % filename)

    with open(filename) as fh:
        txt = fh.read()

    blocks = HEADER_REGEXP.split(txt)
    if len(blocks) == 1:
        # no headers, fake blocks with empty header
        blocks = ['', '']
    elif blocks[0] != '':
        # the block before the begin of text is always empty
        raise Exception('unexpected non-empty block with get_header %s: %s' % (filename, blocks))

    header = blocks[1]

    shebang = None
    if script:
        log.info('get_header for script %s', filename)
        lines = header.split("\n")
        if lines[0].startswith('#!/'):
            shebang = lines[0]
            header = "\n".join(lines[1:])

    return header, shebang


def gen_license_header(license_name, **kwargs):
    """
    Create an appropriate license header for this project

    license is the license to use
    kwargs is a dict with templating data
        beginyear: copyright beginyear
        endyear: copyright endyear
        name: project name
        url: project url
    """
    template_name = "%s_TEMPLATE" % license_name.replace('+', '_plus_')
    template = globals().get(template_name, None)
    if template is None:
        raise Exception('gen_license_header cannot find template name %s' % template_name)

    found = False
    for github_organ in institute_details.keys():
        if github_organ in kwargs.get('url', '').lower():
            kwargs.update(institute_details[github_organ])
            found = True
            break

    if not found:
        raise Exception('Unable to find a known github organization in url %s' % kwargs.get('url'))

    return template.format(**kwargs)


def _this_year():
    """Simple wrapper around date.today().year for unittesting"""
    return date.today().year


def begin_end_from_header(header):
    """
    Return begin and endyear from header.

    Begin is extracted from begin of copyright
    End is current year
    """
    thisyear = _this_year()
    endyear = thisyear

    reg_begin_endyear = re.search(r'^#\s*Copyright\s+(?P<beginyear>\d+)(?:-(?P<endyear>\d+))?($|\s+)', header, re.M)
    if reg_begin_endyear:
        beginyear = int(reg_begin_endyear.groupdict()['beginyear'])
    else:
        log.error('No begin/endyear found, using this year as begin (and end)')
        beginyear = thisyear

    return beginyear, endyear


def _write(filename, content):
    """Simple wrapper around open().write for unittesting"""
    with open(filename, 'w') as fh:
        fh.write(content)


def check_header(filename, script=False, write=False):
    """
    Given filename, extract the header, verify it

    if script: treat first line as shebang
    if write: adapt file to new header

    If the header contains line '### External compatible license',
    one assumes the license is correct and should not be controlled by check_header

    Return if header is different from expected or not
    """

    header, orig_shebang = get_header(filename, script=script)
    header_end_pos = len(header)

    changed = False

    shebang = None
    if script:
        # scripts must have an appropriate shebang
        shebang = orig_shebang
        file_ext = os.path.splitext(filename)[1]
        log.info("Shebang found in %s (ext: %s): %s", filename, file_ext, shebang)

        if file_ext == '.py':
            if shebang != SHEBANG_ENV_PYTHON:
                log.info("Wrong shebang for Python script %s: found '%s', should be '%s'",
                         filename, shebang, SHEBANG_ENV_PYTHON)
                shebang = SHEBANG_ENV_PYTHON

        elif file_ext in ['.sh', '']:
            if shebang != SHEBANG_BIN_BASH:
                log.info("Wrong shebang for shell script %s: found '%s', should be '%s'",
                         filename, shebang, SHEBANG_BIN_BASH)
                shebang = SHEBANG_BIN_BASH

        else:
            log.warn("Don't know expected shebang based on extension '%s' for script '%s', assuming it's OK...",
                     file_ext, filename)

        changed = shebang != orig_shebang

    if orig_shebang is not None:
        # original position
        header_end_pos += 1 + len(orig_shebang)  # 1 is from splitted newline

        if 'python' in shebang and shebang != SHEBANG_ENV_PYTHON:
            log.info('python in shebang, forcing env python (header modified)')
            changed = True
            shebang = SHEBANG_ENV_PYTHON

    if re.search(r'^### External compatible license\s*$', header, re.M):
        log.info('Header is an external compatible license. Leaving the header as-is.')
        return changed

    # genheader
    # version is irrelevant
    setup = vsc_setup()
    name_url = setup.get_name_url(version='ALL_VERSIONS')
    license_name, _ = setup.get_license()

    # begin and endyear from copyright rule
    beginyear, endyear = begin_end_from_header(header)

    data = {
        'beginyear': beginyear,
        'endyear': endyear,
        'name': name_url['name'],
        'url': name_url['url'],
    }

    # reconstruct original header, incl. shebang (if any)
    if orig_shebang:
        orig_header = orig_shebang + '\n' + header
    else:
        orig_header = header

    # generate header like it should be
    gen_header = gen_license_header(license_name, **data)

    # force encoding?
    reg_enc = ENCODING_REGEXP.search(header)
    if reg_enc:
        enc_line = reg_enc.group(1) + "\n"  # matches full line, but not newline
        gen_header = enc_line + gen_header

    # compose header like it should be, incl. shebang
    if shebang:
        new_header = shebang + '\n' + gen_header
    else:
        new_header = gen_header

    if orig_header != new_header:
        log.info("Diff orig_header vs new_header for %s\n" % filename + ''.join(nicediff(orig_header, new_header)))
        changed = True

    if write and changed:
        log.info('write enabled and different header. Going to modify file %s' % filename)
        with open(filename) as fh:
            wholetext = fh.read()
        _write(filename, new_header + wholetext[header_end_pos:])

    # return different or not
    return changed


# mapping of the github organization to the details
# to fill in the license templates
institute_details = {
    'hpcugent': {
        'university_name': 'Ghent University',
        'university_url': 'http://ugent.be/hpc',
        'university_team_url': 'http://ugent.be/hpc/en',
    },
    'vub': {
        'university_name': 'Vrije Universiteit Brussel',
        'university_url': 'https://www.vub.be',
        'university_team_url': 'https://hpc.vub.be',
    },
}

#
# Only template headers below
#

LGPLv2_plus__TEMPLATE = """#
# Copyright {beginyear}-{endyear} {university_name}
#
# This file is part of {name},
# originally created by the HPC team of {university_name} ({university_team_url}),
# with support of {university_name} ({university_url}),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# {url}
#
# {name} is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# {name} is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with {name}. If not, see <http://www.gnu.org/licenses/>.
#
"""

GPLv2_TEMPLATE = """#
# Copyright {beginyear}-{endyear} {university_name}
#
# This file is part of {name},
# originally created by the HPC team of {university_name} ({university_team_url}),
# with support of {university_name} ({university_url}),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# {url}
#
# {name} is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# {name} is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with {name}.  If not, see <http://www.gnu.org/licenses/>.
#
"""

ARR_TEMPLATE = """#
# Copyright {beginyear}-{endyear} {university_name}
#
# This file is part of {name},
# originally created by the HPC team of {university_name} ({university_team_url}),
# with support of {university_name} ({university_url}),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# {url}
#
# All rights reserved.
#
"""

if __name__ == '__main__':
    args = sys.argv[1:]
    try:
        is_script = int(args[-1]) == 1
    except (IndexError, ValueError):
        is_script = False

    if is_script:
        args.pop(-1)

    for fn in args:
        log.info('Going to check_header for file %s (is_script=%s)' % (fn, is_script))
        check_header(fn, script=is_script, write=True)
