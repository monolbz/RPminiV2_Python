"""
Google Maps API integration module.
Handles communication with Google Maps Directions API.
"""

import os
import requests
from dotenv import load_dotenv
from .cache import generate_cache_key, get_from_cache, save_to_cache

# Load environment variables
load_dotenv()

# API configuration
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')


def get_route_with_waypoints(origin, waypoints, optimize=False):
    """
    Get route from Google Maps Directions API using waypoints.
    Uses caching to reduce API calls.

    Args:
        origin: Starting address
        waypoints: List of intermediate addresses
        optimize: If True, Google will optimize the waypoint order

    Returns:
        Dictionary containing route information with keys:
        - addresses: List of addresses in route order
        - distance_m: Total distance in meters
        - duration_s: Total duration in seconds
        - waypoint_order: Optimized waypoint order (if optimize=True)

    Raises:
        ValueError: If API returns an error status
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
        print("  Using cached data")
        return cached_result

    # Not in cache, make API call
    print("  Making API call...")
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
        # Enhanced error handling - identify which address failed
        error_msg = f"Google Maps API error: {data['status']}"

        # Try to identify which address failed
        if 'geocoded_waypoints' in data and data['geocoded_waypoints']:
            failed_addresses = []
            all_addresses = [origin] + waypoints

            for i, waypoint in enumerate(data['geocoded_waypoints']):
                # Safely check if index is within bounds
                if i < len(all_addresses):
                    geocoder_status = waypoint.get('geocoder_status', 'UNKNOWN')
                    if geocoder_status != 'OK':
                        failed_addresses.append(f"  - Address {i+1}: {all_addresses[i]}")
                        failed_addresses.append(f"    Geocoder Status: {geocoder_status}")

            if failed_addresses:
                error_msg += "\n\nInvalid or not found addresses:\n" + "\n".join(failed_addresses)
        else:
            # If no geocoded_waypoints, show all input addresses for reference
            error_msg += "\n\nInput addresses:"
            error_msg += f"\n  - Origin: {origin}"
            for i, wp in enumerate(waypoints, 1):
                error_msg += f"\n  - Waypoint {i}: {wp}"

        # Add API error message if available
        if 'error_message' in data:
            error_msg += f"\n\nAPI Message: {data['error_message']}"

        raise ValueError(error_msg)


def optimize_route(addresses):
    """
    Optimize route using Google Maps waypoint optimization.
    First address is the origin, rest are waypoints to be optimized.

    Args:
        addresses: List of addresses, first is origin, rest are waypoints

    Returns:
        Tuple of (original_route_info, optimized_route_info)

    Raises:
        ValueError: If API key not found or less than 2 addresses provided
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
