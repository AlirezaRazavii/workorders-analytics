# unit tests for the excel parsing helpers

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pandas as pd

from load_excel_to_source import normalize, to_int


def test_to_int_handles_numbers_and_strings():
    assert to_int(41) == 41
    assert to_int(0) == 0
    assert to_int("1,446") == 1446
    assert to_int(" 12 ") == 12
    assert to_int(" ") == 0


def test_to_int_handles_missing_values():
    assert to_int(None) == 0
    assert to_int(float("nan")) == 0


def test_normalize_trims_and_collapses_spaces():
    assert normalize("  دردست   اجرا ") == "دردست اجرا"
    assert normalize("لوازم  اندازه گیری") == "لوازم اندازه گیری"


def test_normalize_converts_arabic_chars():
    assert normalize("كابل") == "کابل"
    assert normalize("مصوبه") == "مصوبه"