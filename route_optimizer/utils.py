"""
Utility functions for route optimizer.
Includes calculations, formatting, and URL generation.
"""

from urllib.parse import quote


# Configuration constants
FUEL_CONSUMPTION_L_PER_100KM = 8.5  # Typical small urban delivery truck
FUEL_PRICE_EUR_PER_L = 1.50  # Average diesel price in Madrid


def format_duration(seconds):
    """
    Convert seconds to HH:mm format.

    Args:
        seconds: Duration in seconds

    Returns:
        String formatted as HH:mm
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def calculate_fuel_cost(distance_m):
    """
    Calculate fuel cost in EUR for given distance.

    Args:
        distance_m: Distance in meters

    Returns:
        Float fuel cost in EUR
    """
    distance_km = distance_m / 1000
    fuel_liters = (distance_km / 100) * FUEL_CONSUMPTION_L_PER_100KM
    fuel_cost = fuel_liters * FUEL_PRICE_EUR_PER_L
    return fuel_cost


def generate_google_maps_url(route_info):
    """
    Generate a Google Maps URL that opens the route in Google Maps app/web.

    Args:
        route_info: Dictionary containing 'addresses' list from the route

    Returns:
        String URL that can be opened in browser or shared, or None if insufficient addresses
    """
    addresses = route_info['addresses']

    if len(addresses) < 2:
        return None

    # URL-encode addresses for safe URL inclusion
    origin = quote(addresses[0])
    destination = quote(addresses[-1])

    # Build waypoints parameter (all addresses between first and last)
    waypoints = []
    if len(addresses) > 2:
        for addr in addresses[1:-1]:
            waypoints.append(quote(addr))

    # Construct the Google Maps URL
    base_url = "https://www.google.com/maps/dir/?api=1"
    url = f"{base_url}&origin={origin}&destination={destination}&travelmode=driving"

    if waypoints:
        waypoints_param = '|'.join(waypoints)
        url += f"&waypoints={waypoints_param}"

    return url
