"""Checksum comparator and corrector (SPEC 6.2, 6.4) and injection semantics (SPEC 11).

Lane numbers follow the SPEC: data lanes are 1..K and checksum lanes are K+1..K+3 for
injection addressing. The RTL in rtl/checker.v must decide identically.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

UNPROTECTED = 0
DETECT_C1_RECOMPUTE = 1
CORRECT = 2

ACC_W_DEFAULT = 32
ACC_CS_W_DEFAULT = 48


class Outcome(IntEnum):
    NONE = 0
    CLEAN = 1
    CORRECTED = 2
    CSUM_LANE = 3
    RECOMPUTE = 4


@dataclass
class CheckResult:
    outcome: Outcome
    lane: int  # CORRECTED: data lane j; CSUM_LANE: checksum 1..3; otherwise 0
    y: list[int]
    d1: int
    d2: int
    d3: int


def checksums(y: list[int]) -> tuple[int, int, int]:
    """Error-free values of S1, S2 and S3 for lane accumulators y[0..K-1]."""
    s1 = sum(y)
    s2 = sum((k + 1) * v for k, v in enumerate(y))
    s3 = sum((k + 1) * (k + 1) * v for k, v in enumerate(y))
    return s1, s2, s3


def check(y: list[int], s1: int, s2: int, s3: int, mode: int, c3_en: bool, trust_csum_lane: bool) -> CheckResult:
    """SPEC 6.2, line by line."""
    sums = checksums(y)
    d1 = sums[0] - s1
    d2 = sums[1] - s2
    d3 = (sums[2] - s3) if c3_en else 0
    out = list(y)

    if mode == UNPROTECTED:
        return CheckResult(Outcome.NONE, 0, out, d1, d2, d3)
    if mode == DETECT_C1_RECOMPUTE:
        return CheckResult(Outcome.RECOMPUTE if d1 != 0 else Outcome.CLEAN, 0, out, d1, d2, d3)

    if d1 == 0 and d2 == 0 and d3 == 0:
        return CheckResult(Outcome.CLEAN, 0, out, d1, d2, d3)
    if d1 != 0:
        for j in range(1, len(y) + 1):
            if d2 == j * d1 and (not c3_en or d3 == j * j * d1):
                out[j - 1] = out[j - 1] - d1
                return CheckResult(Outcome.CORRECTED, j, out, d1, d2, d3)
    if trust_csum_lane:
        if d1 != 0 and d2 == 0 and d3 == 0:
            return CheckResult(Outcome.CSUM_LANE, 1, out, d1, d2, d3)
        if d1 == 0 and d2 != 0 and d3 == 0:
            return CheckResult(Outcome.CSUM_LANE, 2, out, d1, d2, d3)
        if c3_en and d1 == 0 and d2 == 0 and d3 != 0:
            return CheckResult(Outcome.CSUM_LANE, 3, out, d1, d2, d3)
    return CheckResult(Outcome.RECOMPUTE, 0, out, d1, d2, d3)


def to_signed(value: int, width: int) -> int:
    value &= (1 << width) - 1
    return value - (1 << width) if value >> (width - 1) else value


def xor_inject(value: int, mask: int, width: int) -> int:
    """SPEC 11.1: XOR the two's-complement register with MASK truncated to the lane width."""
    unsigned = (value & ((1 << width) - 1)) ^ (mask & ((1 << width) - 1))
    return to_signed(unsigned, width)
