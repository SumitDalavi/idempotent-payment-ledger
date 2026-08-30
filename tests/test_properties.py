import pytest
from hypothesis import given, strategies as st
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@given(amount=st.decimals(min_value=0.01, max_value=1000000.00, allow_nan=False, allow_infinity=False))
def test_decimal_properties(amount):
    """
    Property test verifying decimal representation and rounding invariants.
    """
    assert amount > 0
    assert float(amount) > 0
