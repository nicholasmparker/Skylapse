"""
White Balance Curve Definitions and Interpolation

Shared WB curves and EV compensation curves for both backend (profile creation)
and Pi (profile execution). Eliminates duplication and ensures consistency.
"""

from typing import Dict, List, Tuple

# WB Curve Definitions
# Each curve is a list of (lux, wb_temp) control points in descending lux order
WB_CURVES: Dict[str, List[Tuple[float, int]]] = {
    "balanced": [
        # Profile E: Balanced - matches B when bright, gradual warmth as dims
        (10000, 5500),  # Very bright daylight
        (8000, 5500),  # Bright (matches Profile B)
        (6000, 5450),  # Still bright, barely warmer
        (4000, 5300),  # Softening light
        (3000, 5100),  # Transitioning
        (2000, 4800),  # Golden hour starting
        (1500, 4600),  # Golden hour
        (1000, 4300),  # Dusk
        (700, 4100),  # Deep dusk
        (500, 3900),  # Twilight
        (300, 3700),  # Deep twilight
        (100, 3500),  # Very dark
    ],
    "conservative": [
        # Profile C: Conservative - cooler overall, protects highlights
        (10000, 5600),  # Slightly cooler than B
        (8000, 5600),  # Cooler baseline
        (6000, 5550),  # Very subtle warmth
        (4000, 5400),  # Still conservative
        (3000, 5250),  # Modest warmth
        (2000, 5000),  # Golden hour but restrained
        (1500, 4800),  #
        (1000, 4500),  # Dusk but not too warm
        (700, 4300),  #
        (500, 4100),  # Twilight
        (300, 3900),  #
        (100, 3700),  # Dark but not too warm
    ],
    "warm": [
        # Profile D: Warm/dramatic - embraces golden tones earlier
        (10000, 5500),  # Same bright baseline
        (8000, 5500),  # Match B when bright
        (6000, 5350),  # Warmer sooner
        (4000, 5100),  # More aggressive warmth
        (3000, 4800),  # Golden earlier
        (2000, 4500),  # Rich golden
        (1500, 4300),  # Dramatic sunset
        (1000, 4000),  # Deep warm dusk
        (700, 3800),  # Very warm
        (500, 3600),  # Rich twilight
        (300, 3500),  # Maximum warmth
        (100, 3400),  # Very dark/warm
    ],
}

# EV Compensation Curves
# Each curve is a list of (lux, ev_compensation) control points in descending lux order
# Negative EV = darker (protects highlights), Positive EV = brighter (lifts shadows)
EV_CURVES: Dict[str, List[Tuple[float, float]]] = {
    "adaptive": [
        # Adaptive EV - protects highlights in bright conditions, lifts shadows in low light
        (40000, -0.7),  # Very bright/cloudy - strong highlight protection
        (30000, -0.5),  # Bright clouds - moderate protection
        (20000, -0.3),  # Bright day - mild protection
        (10000, 0.0),  # Normal bright - neutral
        (6000, 0.0),  # Softening - neutral
        (3000, +0.3),  # Golden hour starting - lift shadows slightly
        (1500, +0.5),  # Golden hour - boost exposure
        (1000, +0.7),  # Dusk - strong boost
        (500, +1.0),  # Twilight - maximum boost
        (100, +1.0),  # Very dark - maximum boost
    ],
}


def interpolate_wb_from_lux(lux: float, lux_table: List[Tuple[float, int]]) -> int:
    """
    Linear interpolation of WB temp from lux value.

    This is the SINGLE SOURCE OF TRUTH for WB interpolation.
    Used by both backend (profile creation) and Pi (profile execution).

    Args:
        lux: Current light level
        lux_table: List of (lux, wb_temp) control points in descending lux order

    Returns:
        Interpolated white balance temperature in Kelvin
    """
    if not lux_table:
        return 5500  # Default daylight

    # Handle edge cases
    if lux >= lux_table[0][0]:
        return lux_table[0][1]

    if lux <= lux_table[-1][0]:
        return lux_table[-1][1]

    # Find bracketing points and interpolate
    for i in range(len(lux_table) - 1):
        lux_high, temp_high = lux_table[i]
        lux_low, temp_low = lux_table[i + 1]

        if lux_low <= lux <= lux_high:
            # Linear interpolation
            progress = (lux_high - lux) / (lux_high - lux_low)
            wb_temp = int(temp_high - (progress * (temp_high - temp_low)))
            return wb_temp

    # Fallback
    return 5500


def interpolate_ev_from_lux(lux: float, lux_table: List[Tuple[float, float]]) -> float:
    """
    Linear interpolation of EV compensation from lux value.

    This is the SINGLE SOURCE OF TRUTH for EV interpolation.
    Used by both backend (profile creation) and Pi (profile execution).

    Args:
        lux: Current light level
        lux_table: List of (lux, ev_compensation) control points in descending lux order

    Returns:
        Interpolated EV compensation value (-2.0 to +2.0)
    """
    if not lux_table:
        return 0.0  # Default neutral

    # Handle edge cases
    if lux >= lux_table[0][0]:
        return lux_table[0][1]

    if lux <= lux_table[-1][0]:
        return lux_table[-1][1]

    # Find bracketing points and interpolate
    for i in range(len(lux_table) - 1):
        lux_high, ev_high = lux_table[i]
        lux_low, ev_low = lux_table[i + 1]

        if lux_low <= lux <= lux_high:
            # Linear interpolation
            progress = (lux_high - lux) / (lux_high - lux_low)
            ev_comp = ev_high - (progress * (ev_high - ev_low))
            return round(ev_comp, 2)

    # Fallback
    return 0.0


def get_wb_curve(curve_name: str) -> List[Tuple[float, int]]:
    """
    Get WB curve by name.

    Args:
        curve_name: Name of curve ("balanced", "conservative", "warm")

    Returns:
        List of (lux, wb_temp) control points

    Raises:
        ValueError: If curve name is invalid
    """
    if curve_name not in WB_CURVES:
        raise ValueError(
            f"Invalid curve name: {curve_name}. Valid options: {list(WB_CURVES.keys())}"
        )
    return WB_CURVES[curve_name]


def get_ev_curve(curve_name: str) -> List[Tuple[float, float]]:
    """
    Get EV curve by name.

    Args:
        curve_name: Name of curve ("adaptive")

    Returns:
        List of (lux, ev_compensation) control points

    Raises:
        ValueError: If curve name is invalid
    """
    if curve_name not in EV_CURVES:
        raise ValueError(
            f"Invalid curve name: {curve_name}. Valid options: {list(EV_CURVES.keys())}"
        )
    return EV_CURVES[curve_name]
