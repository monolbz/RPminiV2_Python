#!/usr/bin/env python3
"""
Madrid Route Optimizer
Optimizes delivery routes using Google Maps API with fuel cost estimation.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
FUEL_CONSUMPTION_L_PER_100KM = 8.5  # Typical small urban delivery truck
FUEL_PRICE_EUR_PER_L = 1.50  # Average diesel price in Madrid
CACHE_DIR = Path('.cache')
CACHE_EXPIRY_DAYS = 30  # Cache entries expire after 30 days


def init_cache():
    """Initialize cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(exist_ok=True)


def generate_cache_key(params):
    """Generate a unique cache key from API parameters."""
    # Sort params for consistent hashing
    sorted_params = json.dumps(params, sort_keys=True)
    return hashlib.md5(sorted_params.encode()).hexdigest()


def get_from_cache(cache_key):
    """
    Retrieve data from cache if it exists and is not expired.

    Returns:
        Cached data or None if not found or expired
    """
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)

        # Check if cache entry has expired
        cached_time = datetime.fromisoformat(cached_data['timestamp'])
        expiry_time = cached_time + timedelta(days=CACHE_EXPIRY_DAYS)

        if datetime.now() > expiry_time:
            # Cache expired, delete it
            cache_file.unlink()
            return None

        return cached_data['data']

    except (json.JSONDecodeError, KeyError, ValueError):
        # Invalid cache file, delete it
        cache_file.unlink()
        return None


def save_to_cache(cache_key, data):
    """Save data to cache with current timestamp."""
    cache_file = CACHE_DIR / f"{cache_key}.json"

    cache_entry = {
        'timestamp': datetime.now().isoformat(),
        'data': data
    }

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_entry, f, indent=2)


def get_route_with_waypoints(origin, waypoints, optimize=False):
    """
    Get route from Google Maps Directions API using waypoints.
    Uses caching to reduce API calls.

    Args:
        origin: Starting address
        waypoints: List of intermediate addresses
        optimize: If True, Google will optimize the waypoint order

    Returns:
        Dictionary containing route information
    """
    # Format waypoints parameter
    waypoints_param = '|'.join(waypoints)
    if optimize:
        waypoints_param = 'optimize:true|' + waypoints_param

    # Create cache key from request parameters (excluding API key)
    cache_params = {
        'origin': origin,
        'destination': waypoints[-1],
        'waypoints': waypoints_param,
        'mode': 'driving'
    }
    cache_key = generate_cache_key(cache_params)

    # Try to get from cache
    cached_result = get_from_cache(cache_key)
    if cached_result is not None:
        print("  ✓ Using cached data")
        return cached_result

    # Not in cache, make API call
    print("  → Making API call...")
    url = 'https://maps.googleapis.com/maps/api/directions/json'

    params = {
        **cache_params,
        'key': GOOGLE_MAPS_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data['status'] == 'OK':
        route = data['routes'][0]

        # Calculate total distance and duration
        total_distance_m = 0
        total_duration_s = 0

        for leg in route['legs']:
            total_distance_m += leg['distance']['value']
            total_duration_s += leg['duration']['value']

        # Get optimized waypoint order if optimization was requested
        waypoint_order = None
        if optimize and 'waypoint_order' in route:
            waypoint_order = route['waypoint_order']

        # Build the full route with addresses
        route_addresses = [origin]
        if waypoint_order:
            # Reorder waypoints according to optimization
            for idx in waypoint_order:
                route_addresses.append(waypoints[idx])
        else:
            # Use original order
            route_addresses.extend(waypoints)

        result = {
            'addresses': route_addresses,
            'distance_m': total_distance_m,
            'duration_s': total_duration_s,
            'waypoint_order': waypoint_order
        }

        # Save to cache
        save_to_cache(cache_key, result)

        return result
    else:
        raise ValueError(f"Google Maps API error: {data['status']}")


def optimize_route(addresses):
    """
    Optimize route using Google Maps waypoint optimization.
    First address is the origin, rest are waypoints to be optimized.

    Returns:
        Tuple of (original_route_info, optimized_route_info)
    """
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY not found. Please set it in .env file")

    if len(addresses) < 2:
        raise ValueError("Need at least 2 addresses to optimize route")

    origin = addresses[0]
    waypoints = addresses[1:]

    print(f"Starting point: {origin}")
    print(f"Optimizing route for {len(waypoints)} waypoint(s)...")
    print()

    # Get original route (input order)
    print("Calculating original route (input order)...")
    original_route = get_route_with_waypoints(origin, waypoints, optimize=False)

    # Get optimized route
    print("Calculating optimized route...")
    optimized_route = get_route_with_waypoints(origin, waypoints, optimize=True)

    return original_route, optimized_route


def format_duration(seconds):
    """Convert seconds to HH:mm format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def calculate_fuel_cost(distance_m):
    """Calculate fuel cost in EUR for given distance."""
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
        String URL that can be opened in browser or shared
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


def read_addresses_from_file(filename='input.txt'):
    """
    Read addresses from a text file.

    Args:
        filename: Path to the input file (default: 'input.txt')

    Returns:
        List of addresses (strings)

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file is empty or has less than 2 addresses
    """
    filepath = Path(filename)

    if not filepath.exists():
        raise FileNotFoundError(f"Input file '{filename}' not found")

    addresses = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            # Strip whitespace and skip empty lines
            line = line.strip()
            if line:
                addresses.append(line)

    if len(addresses) < 2:
        raise ValueError(f"Input file must contain at least 2 addresses (found {len(addresses)})")

    if len(addresses) > 26:
        raise ValueError(f"Input file cannot contain more than 26 addresses (found {len(addresses)}). Google Maps API supports a maximum of 25 waypoints plus 1 origin.")

    # Check for duplicate addresses (case-insensitive, whitespace-normalized)
    normalized_addresses = {}
    duplicates = []

    for i, addr in enumerate(addresses, 1):
        # Normalize: lowercase and strip extra whitespace
        normalized = ' '.join(addr.lower().split())

        if normalized in normalized_addresses:
            # Found duplicate
            original_line = normalized_addresses[normalized]
            duplicates.append(f"  - Line {original_line}: {addresses[original_line - 1]}")
            duplicates.append(f"  - Line {i}: {addr}")
        else:
            normalized_addresses[normalized] = i

    if duplicates:
        duplicates_str = '\n'.join(duplicates)
        raise ValueError(f"Duplicate addresses found in input file:\n{duplicates_str}")

    return addresses


def main():
    """Main function to run the route optimizer."""
    # Initialize cache directory
    init_cache()

    print("=" * 60)
    print("Madrid Route Optimizer")
    print("=" * 60)
    print()

    # Priority: Command line arguments > input.txt file
    if len(sys.argv) > 1:
        # Use command line arguments
        addresses = sys.argv[1:]
        print("Using addresses from command line arguments")
    else:
        # Read from input.txt file
        try:
            addresses = read_addresses_from_file('input.txt')
            print("Using addresses from input.txt")
        except FileNotFoundError:
            print("Error: input.txt file not found")
            print("Please create an input.txt file with one address per line,")
            print("or provide addresses as command line arguments.")
            sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    print()
    print("Input addresses:")
    for i, addr in enumerate(addresses, 1):
        print(f"  {i}. {addr}")
    print()

    try:
        # Get both original and optimized routes
        original_route, optimized_route = optimize_route(addresses)

        # Calculate fuel costs
        original_fuel_cost = calculate_fuel_cost(original_route['distance_m'])
        optimized_fuel_cost = calculate_fuel_cost(optimized_route['distance_m'])
        fuel_savings = original_fuel_cost - optimized_fuel_cost

        # Display original route
        print()
        print("=" * 60)
        print("ORIGINAL ROUTE (Input Order)")
        print("=" * 60)
        for i, addr in enumerate(original_route['addresses'], 1):
            print(f"  {i}. {addr}")

        print()
        print(f"Total Distance:      {original_route['distance_m'] / 1000:.2f} km")
        print(f"Total Time:          {format_duration(original_route['duration_s'])}")
        print(f"Fuel Consumption:    {(original_route['distance_m'] / 1000 / 100) * FUEL_CONSUMPTION_L_PER_100KM:.2f} L")
        print(f"Estimated Fuel Cost: €{original_fuel_cost:.2f}")

        # Display optimized route
        print()
        print("=" * 60)
        print("OPTIMIZED ROUTE (Google Maps Optimized)")
        print("=" * 60)
        for i, addr in enumerate(optimized_route['addresses'], 1):
            print(f"  {i}. {addr}")

        print()
        print(f"Total Distance:      {optimized_route['distance_m'] / 1000:.2f} km")
        print(f"Total Time:          {format_duration(optimized_route['duration_s'])}")
        print(f"Fuel Consumption:    {(optimized_route['distance_m'] / 1000 / 100) * FUEL_CONSUMPTION_L_PER_100KM:.2f} L")
        print(f"Estimated Fuel Cost: €{optimized_fuel_cost:.2f}")

        # Display savings
        print()
        print("=" * 60)
        print("SAVINGS")
        print("=" * 60)
        distance_saved = (original_route['distance_m'] - optimized_route['distance_m']) / 1000
        time_saved = original_route['duration_s'] - optimized_route['duration_s']

        print(f"Distance Saved:      {distance_saved:.2f} km ({distance_saved / (original_route['distance_m'] / 1000) * 100:.1f}%)")
        print(f"Time Saved:          {format_duration(abs(time_saved))} ({'saved' if time_saved > 0 else 'added'})")
        print(f"Fuel Cost Saved:     €{fuel_savings:.2f} ({fuel_savings / original_fuel_cost * 100:.1f}%)")
        print("=" * 60)

        # Generate and display Google Maps URL for optimized route
        print()
        print("=" * 60)
        print("GOOGLE MAPS LINK (Optimized Route)")
        print("=" * 60)
        google_maps_url = generate_google_maps_url(optimized_route)
        print(f"Open this link to view the optimized route in Google Maps:")
        print()
        print(google_maps_url)
        print()
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
