# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#!/usr/bin/env python
"""
This script is a trick to setup a fake Django environment, since this reusable
app will be developed and tested outside any specifiv Django project.

Via ``settings.configure`` you will be able to set all necessary settings
for your app and run the tests as if you were calling ``./manage.py test``.

"""
import sys

import re
import django
from django.conf import settings
import coverage
from fabric.api import abort, lcd, local
from fabric.colors import green, red
from silver.tests import test_settings


if not settings.configured:
    settings.configure(**test_settings.__dict__)

if '1.7' in django.get_version():
    django.setup()


from django_coverage.coverage_runner import CoverageRunner
from django_nose import NoseTestSuiteRunner


class NoseCoverageTestRunner(CoverageRunner, NoseTestSuiteRunner):
    """Custom test runner that uses nose and coverage"""
    def run_tests(self, *args, **kwargs):
        results = super(NoseCoverageTestRunner, self).run_tests(
            *args, **kwargs)
        coverage._the_coverage.data.write_file('.coverage')
        return results


def runtests(*test_args):
    failures = NoseCoverageTestRunner(verbosity=2, interactive=True).run_tests(
        test_args)

    with lcd(settings.COVERAGE_REPORT_HTML_OUTPUT_DIR):
        total_line = local('grep -n Total index.html', capture=True)
        match = re.search(r'^(\d+):', total_line)
        total_line_number = int(match.groups()[0])
        percentage_line_number = total_line_number + 4
        percentage_line = local(
            'awk NR=={0} index.html'.format(percentage_line_number),
            capture=True)
        match = re.search(r'<td>(\d.+)%</td>', percentage_line)
        percentage = float(match.groups()[0])
    if percentage < 100:
        abort(red('Coverage is {0}%'.format(percentage)))
    print(green('Coverage is {0}%'.format(percentage)))

    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])
