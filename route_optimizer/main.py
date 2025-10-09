#!/usr/bin/env python3
"""
Madrid Route Optimizer - Main Module
Optimizes delivery routes using Google Maps API with fuel cost estimation.
"""

import sys
from .cache import init_cache
from .api import optimize_route
from .utils import format_duration, calculate_fuel_cost, generate_google_maps_url, FUEL_CONSUMPTION_L_PER_100KM
from .input_handler import read_addresses_from_file


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
