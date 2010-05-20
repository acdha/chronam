import sys

import django
from django.test import TestCase

class SystemTests(TestCase):

    def test_django_version(self):
        self.assertEqual(django.get_version(), '1.1.1')

    def test_python_version(self):
        self.assertEqual(sys.version_info[0:3], (2,6,5))

