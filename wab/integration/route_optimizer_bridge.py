#!/usr/bin/env python3
"""
Route Optimizer Bridge
Integrates WhatsApp webhook with the route_optimizer module.
"""

import sys
from pathlib import Path

# Add project root to path to import route_optimizer
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from route_optimizer.api import optimize_route
from route_optimizer.utils import format_duration, calculate_fuel_cost, generate_google_maps_url, FUEL_CONSUMPTION_L_PER_100KM
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class RouteOptimizerBridge:
    """
    Bridge between WhatsApp webhook and route optimizer.
    Handles calling the route optimizer and formatting results for WhatsApp.
    """

    def __init__(self):
        """Initialize the route optimizer bridge."""
        pass

    def optimize_route(self, addresses):
        """
        Optimize a route using the route_optimizer module.

        Args:
            addresses (list): List of addresses to optimize

        Returns:
            dict: Route optimization results containing:
                - success (bool): Whether optimization succeeded
                - original_route (dict): Original route data
                - optimized_route (dict): Optimized route data
                - error_message (str): Error message if failed
        """
        try:
            logger.info(f"Optimizing route for {len(addresses)} addresses")

            # Validate minimum addresses
            if len(addresses) < 2:
                return {
                    'success': False,
                    'error_message': "Necesito al menos 2 direcciones para optimizar una ruta."
                }

            # Call the route optimizer with ALL addresses
            # The API handles round trips correctly (when first and last address are the same)
            original_route, optimized_route = optimize_route(addresses)

            logger.info(f"Route optimized successfully - Distance: {optimized_route['distance_m']/1000:.2f}km")

            return {
                'success': True,
                'original_route': original_route,
                'optimized_route': optimized_route,
                'addresses': addresses
            }

        except ValueError as e:
            # API errors (invalid addresses, API key missing, etc.)
            error_msg = str(e)
            logger.error(f"Route optimization failed: {error_msg}")

            return {
                'success': False,
                'error_message': self._format_error_message(error_msg)
            }

        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error during route optimization: {e}", exc_info=True)

            return {
                'success': False,
                'error_message': "Ocurrió un error inesperado al optimizar la ruta. Por favor, intenta nuevamente."
            }

    def format_route_result_for_whatsapp(self, result, phone_number=None):
        """
        Format route optimization result for WhatsApp message.

        Args:
            result (dict): Route optimization result from optimize_route()
            phone_number (str): User's phone number for logging (optional)

        Returns:
            str: Formatted message text for WhatsApp
        """
        if not result['success']:
            return f"❌ *Optimización de ruta fallida*\n\n{result['error_message']}"

        try:
            original = result['original_route']
            optimized = result['optimized_route']

            # Calculate fuel costs and savings
            original_fuel_cost = calculate_fuel_cost(original['distance_m'])
            optimized_fuel_cost = calculate_fuel_cost(optimized['distance_m'])
            fuel_savings = original_fuel_cost - optimized_fuel_cost

            # Calculate savings
            distance_saved = (original['distance_m'] - optimized['distance_m']) / 1000
            time_saved = original['duration_s'] - optimized['duration_s']
            savings_percent = (distance_saved / (original['distance_m'] / 1000) * 100) if original['distance_m'] > 0 else 0

            # Auto-fallback: if optimized route is worse, use original route instead
            used_fallback = False
            if distance_saved < 0:  # Optimized is longer than original
                phone_log = f" [User: {phone_number}]" if phone_number else ""
                logger.warning(f"Optimized route is longer by {abs(distance_saved):.2f} km. Using original route instead.{phone_log}")
                optimized = original  # Fallback to original
                optimized_fuel_cost = original_fuel_cost
                distance_saved = 0
                time_saved = 0
                savings_percent = 0
                used_fallback = True

            # Build the message
            message = "✅ *Ruta calculada!*\n\n"

            # Show note if we used fallback
            if used_fallback:
                message += "⚠️ *La optimización no mejoró tu ruta original. Verifica tus direcciones.* \n\n"

            # Optimized route details
            message += "🗺️ *Nueva ruta:*\n"
            for i, addr in enumerate(optimized['addresses'], 1):
                message += f"{i}. {addr}\n"

            # message += f"\n📏 *Distancia:* {optimized['distance_m'] / 1000:.2f} km\n"
            # message += f"⏱️ *Tiempo:* {format_duration(optimized['duration_s'])}\n"
            # message += f"⛽ *Combustible:* {(optimized['distance_m'] / 1000 / 100) * FUEL_CONSUMPTION_L_PER_100KM:.2f} L\n"
            # message += f"💰 *Coste de combustible:* €{optimized_fuel_cost:.2f}\n"

            # Savings (if any)
            if distance_saved > 0:
                message += f"\n💚 *Ahorros vs Ruta original:*\n"
                message += f"  • Distancia: {distance_saved:.2f} km ({savings_percent:.1f}%)\n"
                message += f"  • Tiempo: {format_duration(abs(time_saved))}\n"
                message += f"  • Coste de combustible: €{fuel_savings:.2f}\n"

            # Savings (if zero)
            if distance_saved == 0:
                message += f"\n💚 *Tu ruta original ya es la más óptima*\n"

            # Google Maps link
            google_maps_url = generate_google_maps_url(optimized)
            message += f"\n📍 *Ver en Google Maps:*\n{google_maps_url}\n"

            return message

        except Exception as e:
            logger.error(f"Error formatting route result: {e}", exc_info=True)
            return "✅ Ruta optimizada exitosamente, pero ocurrió un error al formatear los resultados. Por favor, intenta nuevamente."

    def format_route_result_parts(self, result, phone_number=None):
        """
        Format route result as two separate parts for two-message delivery (e.g. Twilio).

        Args:
            result (dict): Route optimization result from optimize_route()
            phone_number (str): User's phone number for logging (optional)

        Returns:
            tuple: (summary_text, maps_url) on success, (error_text, None) on failure
        """
        if not result['success']:
            return f"❌ *Optimización de ruta fallida*\n\n{result['error_message']}", None

        try:
            original = result['original_route']
            optimized = result['optimized_route']

            # Calculate fuel costs and savings
            original_fuel_cost = calculate_fuel_cost(original['distance_m'])
            optimized_fuel_cost = calculate_fuel_cost(optimized['distance_m'])
            fuel_savings = original_fuel_cost - optimized_fuel_cost

            # Calculate savings
            distance_saved = (original['distance_m'] - optimized['distance_m']) / 1000
            time_saved = original['duration_s'] - optimized['duration_s']
            savings_percent = (distance_saved / (original['distance_m'] / 1000) * 100) if original['distance_m'] > 0 else 0

            # Auto-fallback: if optimized route is worse, use original route instead
            used_fallback = False
            if distance_saved < 0:
                phone_log = f" [User: {phone_number}]" if phone_number else ""
                logger.warning(f"Optimized route is longer by {abs(distance_saved):.2f} km. Using original route instead.{phone_log}")
                optimized = original
                optimized_fuel_cost = original_fuel_cost
                distance_saved = 0
                time_saved = 0
                savings_percent = 0
                used_fallback = True

            # Build the summary message (addresses + savings, no Maps URL)
            message = "✅ *Ruta calculada!*\n\n"

            if used_fallback:
                message += "⚠️ *La optimización no mejoró tu ruta original. Verifica tus direcciones.* \n\n"

            message += "🗺️ *Nueva ruta:*\n"
            for i, addr in enumerate(optimized['addresses'], 1):
                message += f"{i}. {addr}\n"

            if distance_saved > 0:
                message += f"\n💚 *Ahorros vs Ruta original:*\n"
                message += f"  • Distancia: {distance_saved:.2f} km ({savings_percent:.1f}%)\n"
                message += f"  • Tiempo: {format_duration(abs(time_saved))}\n"
                message += f"  • Coste de combustible: €{fuel_savings:.2f}\n"

            if distance_saved == 0:
                message += f"\n💚 *Tu ruta original ya es la más óptima*\n"

            # Google Maps URL as second part
            google_maps_url = generate_google_maps_url(optimized)
            maps_message = f"📍 *Ver en Google Maps:*\n{google_maps_url}" if google_maps_url else None

            return message, maps_message

        except Exception as e:
            logger.error(f"Error formatting route result parts: {e}", exc_info=True)
            return "✅ Ruta optimizada exitosamente, pero ocurrió un error al formatear los resultados. Por favor, intenta nuevamente.", None

    def format_route_summary_short(self, result):
        """
        Format a short summary of route optimization (for quick replies).

        Args:
            result (dict): Route optimization result

        Returns:
            str: Short formatted message
        """
        if not result['success']:
            return f"❌ Fallo: {result['error_message']}"

        optimized = result['optimized_route']
        distance_km = optimized['distance_m'] / 1000
        duration_str = format_duration(optimized['duration_s'])

        return f"✅ Ruta optimizada! {distance_km:.1f}km, {duration_str}, {len(optimized['addresses'])} paradas"

    def _format_error_message(self, error_msg):
        """
        Format error message for user-friendly display.

        Args:
            error_msg (str): Raw error message

        Returns:
            str: Formatted error message
        """
        # Clean up technical error messages
        if "GOOGLE_MAPS_API_KEY not found" in error_msg:
            return "Error de configuración del servicio. Por favor, contacta al soporte."

        if "Google Maps API error" in error_msg:
            if "ZERO_RESULTS" in error_msg:
                return "No se pudo encontrar una ruta entre estas direcciones. Por favor, verifica que todas las direcciones sean válidas y accesibles. Para más detalles, escribe /ayuda o /elemplo."

            if "NOT_FOUND" in error_msg or "INVALID" in error_msg:
                # Extract which addresses failed if available
                if "Invalid or not found addresses:" in error_msg:
                    return error_msg  # Already formatted nicely
                else:
                    return "No se pudo encontrar una o más direcciones. Por favor, verifica tus direcciones y vuelve a intentarlo."

            if "REQUEST_DENIED" in error_msg:
                return "Error del servicio: No se puede acceder al servicio de mapas. Por favor, intenta nuevamente más tarde."

            if "OVER_QUERY_LIMIT" in error_msg:
                return "El servicio no está disponible temporalmente debido a la alta demanda. Por favor, intenta nuevamente en unos minutos."

        # For other errors, return a generic message
        return "No se pudo optimizar la ruta. Por favor, verifica tus direcciones y vuelve a intentarlo."


# Create a singleton instance
route_bridge = RouteOptimizerBridge()
