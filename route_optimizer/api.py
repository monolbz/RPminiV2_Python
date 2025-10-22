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
        waypoints: List of intermediate addresses (last one will be used as destination)
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
    # Separate destination from intermediate waypoints to avoid double-counting
    # Google's API expects: origin -> waypoints -> destination
    # where destination is separate from the waypoints list
    if len(waypoints) > 1:
        # Multiple waypoints: last one is destination, rest are intermediate stops
        intermediate_waypoints = waypoints[:-1]
        destination = waypoints[-1]
        waypoints_param = '|'.join(intermediate_waypoints)
        if optimize:
            waypoints_param = 'optimize:true|' + waypoints_param
    else:
        # Only one waypoint: it's the destination, no intermediate stops
        destination = waypoints[0]
        waypoints_param = ''

    # Create cache key from request parameters (excluding API key)
    cache_params = {
        'origin': origin,
        'destination': destination,
        'waypoints': waypoints_param if waypoints_param else None,
        'mode': 'driving'
    }
    # Remove None values from cache params
    cache_params = {k: v for k, v in cache_params.items() if v is not None}
    cache_key = generate_cache_key(cache_params)

    # Try to get from cache
    cached_result = get_from_cache(cache_key)
    if cached_result is not None:
        print("  Using cached data")
        return cached_result

    # Not in cache, make API call
    print("  Making API call...")
    print(f"  Origin: {cache_params['origin']}")
    print(f"  Destination: {cache_params['destination']}")
    if 'waypoints' in cache_params:
        print(f"  Waypoints: {cache_params['waypoints']}")
    else:
        print(f"  Waypoints: (none - direct route)")

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

        print(f"  API returned {len(route['legs'])} leg(s)")
        for i, leg in enumerate(route['legs'], 1):
            leg_dist_km = leg['distance']['value'] / 1000
            leg_duration_min = leg['duration']['value'] / 60
            print(f"    Leg {i}: {leg_dist_km:.2f} km, {leg_duration_min:.0f} min")
            total_distance_m += leg['distance']['value']
            total_duration_s += leg['duration']['value']
        print(f"  Total: {total_distance_m/1000:.2f} km, {total_duration_s/60:.0f} min")

        # Get optimized waypoint order if optimization was requested
        waypoint_order = None
        if optimize and 'waypoint_order' in route:
            waypoint_order = route['waypoint_order']

        # Build the full route with addresses
        route_addresses = [origin]

        if len(waypoints) > 1:
            # Multiple waypoints: reconstruct route with intermediate stops + destination
            intermediate_waypoints = waypoints[:-1]
            destination = waypoints[-1]

            if waypoint_order:
                # Reorder intermediate waypoints according to optimization
                for idx in waypoint_order:
                    route_addresses.append(intermediate_waypoints[idx])
            else:
                # Use original order for intermediate waypoints
                route_addresses.extend(intermediate_waypoints)

            # Add destination at the end
            route_addresses.append(destination)
        else:
            # Only one waypoint: it's the destination
            route_addresses.append(waypoints[0])

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
