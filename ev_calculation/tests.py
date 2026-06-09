from decimal import Decimal

from django.test import SimpleTestCase

from .services import calculate_kwh_per_100km


class EvCalculationTest(SimpleTestCase):
    def test_kwh_per_100km(self):
        self.assertEqual(calculate_kwh_per_100km(50, 250), Decimal("20.00"))
