import sys
from pathlib import Path

import pytest

TASK_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_DIR))

from src.median import median


def test_median_odd_length():
    assert median([3, 1, 2]) == 2


def test_median_even_length():
    assert median([1, 3, 5, 7]) == 4


def test_median_unsorted_even_length():
    assert median([10, 2, 4, 8]) == 6


def test_median_empty_list():
    with pytest.raises(ValueError):
        median([])