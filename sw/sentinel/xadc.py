"""XADC temperature conversion (ADR-018, ADR-023).

UG480 v1.11, Equation 2-6: degrees Celsius = code * 503.975 / 4096 - 273.15, where code is the
12-bit result of status register 00h. DS189 Table 50 gives the sensor error as +-4 C between
-40 C and 100 C. On a board these are [HW] readings; from the device model they are [SIM].
"""
from __future__ import annotations

from sentinel import regmap as rm


def code_to_celsius(code: int) -> float:
    if not 0 <= code <= 0xFFF:
        raise ValueError(f"XADC code must be 12 bits, got {code}")
    return code * 503.975 / 4096 - 273.15


def temperature_from_register(word: int) -> float | None:
    """TEMP register word to degrees Celsius; None while VALID is clear."""
    if not (word >> rm.TEMP_VALID_LSB) & 1:
        return None
    return code_to_celsius((word >> rm.TEMP_CODE_LSB) & ((1 << rm.TEMP_CODE_WIDTH) - 1))
