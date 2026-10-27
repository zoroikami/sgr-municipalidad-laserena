import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rut import normalize_rut, is_valid_rut, RutError


class RutTests(unittest.TestCase):
    def test_accepts_valid_ruts_and_normalizes_punctuation_and_k(self):
        for supplied, expected in [('12.345.678-5', '12345678-5'), ('123456785', '12345678-5'),
                                   (' 6-k ', '6-K'), ('14-0', '14-0'), ('11.111.111-1', '11111111-1')]:
            with self.subTest(supplied=supplied):
                self.assertTrue(is_valid_rut(supplied))
                self.assertEqual(normalize_rut(supplied), expected)

    def test_rejects_wrong_check_digits_and_malformed_inputs(self):
        for supplied in ('12.345.678-9', '6-0', '14-K', '', '0-0', '00000000-0',
                         '12.34.567-5', '12345678--5', 'ABC123456785', '123456789-2',
                         '12 345 678-5', '١٢٣٤٥٦٧٨-5', None, 123456785):
            with self.subTest(supplied=supplied):
                self.assertFalse(is_valid_rut(supplied))
                with self.assertRaises(RutError):
                    normalize_rut(supplied)


if __name__ == '__main__':
    unittest.main()
