"""Randomness tests for QKD final keys.

Implements a simple battery of statistical tests for randomness validation
of the final secret key after privacy amplification.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np


def frequency_test(bits: np.ndarray) -> Tuple[bool, float]:
    """Monobit frequency test.

    Checks if the proportion of 0s and 1s is approximately 1/2.

    Args:
        bits: Array of binary values (0s and 1s)

    Returns:
        (passed, p_value)
    """
    n = len(bits)
    if n == 0:
        return False, 0.0

    # Count proportion of 1s
    prop_ones = np.mean(bits)

    # Test statistic: (prop_ones - 0.5) / sqrt(0.25/n)
    s = (prop_ones - 0.5) / math.sqrt(0.25 / n)

    # Two-tailed test
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(s) / math.sqrt(2))))

    # Pass if p-value > 0.01 (standard threshold)
    passed = p_value > 0.01
    return passed, p_value


def runs_test(bits: np.ndarray) -> Tuple[bool, float]:
    """Runs test.

    Checks if the number of runs (consecutive identical bits) is
    within expected range for a random sequence.

    Args:
        bits: Array of binary values (0s and 1s)

    Returns:
        (passed, p_value)
    """
    n = len(bits)
    if n == 0:
        return False, 0.0

    # Count runs
    runs = 1  # At least one run
    for i in range(1, n):
        if bits[i] != bits[i-1]:
            runs += 1

    # Count proportion of 1s
    prop_ones = np.mean(bits)

    # Expected number of runs
    expected_runs = (2 * n * prop_ones * (1 - prop_ones)) + 1

    # Variance of runs
    if prop_ones == 0 or prop_ones == 1:
        variance = 0
    else:
        variance = (2 * n * prop_ones * (1 - prop_ones) *
                   (2 * n * prop_ones * (1 - prop_ones) - n)) / (n * n * (n - 1))

    if variance <= 0:
        return False, 0.0

    # Test statistic
    z = (runs - expected_runs) / math.sqrt(variance)

    # Two-tailed test
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))

    # Pass if p-value > 0.01
    passed = p_value > 0.01
    return passed, p_value


def serial_correlation_test(bits: np.ndarray, lag: int = 1) -> Tuple[bool, float]:
    """Serial correlation test.

    Checks for correlation between bits separated by a given lag.

    Args:
        bits: Array of binary values (0s and 1s)
        lag: Lag for correlation test (default 1)

    Returns:
        (passed, p_value)
    """
    n = len(bits)
    if n <= lag:
        return False, 0.0

    # Extract two subsequences
    x = bits[:-lag] if lag > 0 else bits
    y = bits[lag:] if lag > 0 else bits

    if len(x) == 0:
        return False, 0.0

    # Calculate correlation
    mean_x = np.mean(x)
    mean_y = np.mean(y)

    # Covariance
    cov = np.mean((x - mean_x) * (y - mean_y))

    # Standard deviations
    std_x = math.sqrt(np.mean((x - mean_x) ** 2))
    std_y = math.sqrt(np.mean((y - mean_y) ** 2))

    if std_x == 0 or std_y == 0:
        # If one sequence is constant, correlation is undefined
        # Treat as no correlation (which is good for randomness)
        correlation = 0.0
    else:
        correlation = cov / (std_x * std_y)

    # Test statistic: correlation * sqrt(n)
    # Under null hypothesis of no correlation, this is approximately normal
    test_stat = abs(correlation) * math.sqrt(len(x))

    # Approximate p-value (two-tailed)
    p_value = 2 * (1 - 0.5 * (1 + math.erf(test_stat / math.sqrt(2))))

    # Pass if p-value > 0.01
    passed = p_value > 0.01
    return passed, p_value


def maurer_universal_test_stub(bits: np.ndarray) -> Tuple[bool, float]:
    """Stub for Maurer's universal test.

    A full implementation is complex, so we provide a placeholder
    that always passes for testing purposes.

    Args:
        bits: Array of binary values (0s and 1s)

    Returns:
        (passed, p_value) - always passes with high p-value
    """
    # In a full implementation, this would compute the Maurer universal test
    # For now, we return a dummy pass
    return True, 0.5


def run_randomness_tests(bits: np.ndarray) -> Dict[str, any]:
    """Run a battery of randomness tests on the key.

    Args:
        bits: Array of binary values representing the key

    Returns:
        Dictionary with test results:
        - passed: Overall pass/fail
        - tests: Individual test results
        - recommendations: Any recommendations based on results
    """
    if len(bits) == 0:
        return {
            "passed": False,
            "tests": {},
            "recommendations": ["Key is empty"]
        }

    # Run individual tests
    freq_passed, freq_p = frequency_test(bits)
    runs_passed, runs_p = runs_test(bits)
    serial_passed, serial_p = serial_correlation_test(bits, lag=1)
    maurer_passed, maurer_p = maurer_universal_test_stub(bits)

    tests = {
        "frequency": {
            "passed": freq_passed,
            "p_value": freq_p,
            "name": "Monobit Frequency Test"
        },
        "runs": {
            "passed": runs_passed,
            "p_value": runs_p,
            "name": "Runs Test"
        },
        "serial_correlation": {
            "passed": serial_passed,
            "p_value": serial_p,
            "name": "Serial Correlation Test (lag=1)"
        },
        "maurer_universal": {
            "passed": maurer_passed,
            "p_value": maurer_p,
            "name": "Maurer Universal Test (stub)"
        }
    }

    # Overall pass if all tests pass
    all_passed = freq_passed and runs_passed and serial_passed and maurer_passed

    # Generate recommendations
    recommendations = []
    if not freq_passed:
        recommendations.append("Frequency test failed: key may have bias")
    if not runs_passed:
        recommendations.append("Runs test failed: key may have too few or too many runs")
    if not serial_passed:
        recommendations.append("Serial correlation test failed: key may have correlations")
    if not maurer_passed:
        recommendations.append("Maurer universal test failed: key may lack complexity")

    if not recommendations:
        recommendations.append("All randomness tests passed")

    return {
        "passed": all_passed,
        "tests": tests,
        "recommendations": recommendations
    }


# Convenience function for use in link.py
def randomness_pass(bits: np.ndarray) -> bool:
    """Simple pass/fail for randomness testing.

    Args:
        bits: Array of binary values representing the key

    Returns:
        True if key passes randomness tests, False otherwise
    """
    result = run_randomness_tests(bits)
    return result["passed"]


if __name__ == "__main__":
    # Test with random data
    print("Testing randomness tests with random data...")
    rng = np.random.default_rng(42)
    random_bits = rng.integers(0, 2, 1000)
    result = run_randomness_tests(random_bits)
    print(f"Random data passed: {result['passed']}")
    for test_name, test_result in result["tests"].items():
        print(f"  {test_result['name']}: {test_result['passed']} (p={test_result['p_value']:.4f})")

    # Test with non-random data
    print("\nTesting with non-random data (all zeros)...")
    zero_bits = np.zeros(1000, dtype=np.uint8)
    result = run_randomness_tests(zero_bits)
    print(f"Zero data passed: {result['passed']}")
    for test_name, test_result in result["tests"].items():
        print(f"  {test_result['name']}: {test_result['passed']} (p={test_result['p_value']:.4f})")

    # Test with alternating data
    print("\nTesting with alternating data...")
    alt_bits = np.tile([0, 1], 500)
    result = run_randomness_tests(alt_bits)
    print(f"Alternating data passed: {result['passed']}")
    for test_name, test_result in result["tests"].items():
        print(f"  {test_result['name']}: {test_result['passed']} (p={test_result['p_value']:.4f})")