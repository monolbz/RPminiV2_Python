#!/usr/bin/env python3
"""
Message Processor
Processes incoming WhatsApp messages and prepares responses.
Includes GDPR consent management.
"""

import os
from datetime import datetime
from ..utils.logger import setup_logger
from ..utils.conversation_tracker_db import ConversationTracker
from .address_parser import AddressParser
from .consent_manager_db import ConsentManager
from . import usage_manager
from .feedback_manager import feedback_manager
from ..config.config import Config
from ..integration.route_optimizer_bridge import route_bridge
from ..templates import (
    CONSENT_REQUEST,
    CONSENT_ACCEPTED,
    CONSENT_DECLINED,
    CONSENT_REVOKED,
    CONSENT_ALREADY_GIVEN,
    CONSENT_REQUIRED_FOR_ROUTE,
    get_consent_keywords,
    get_privacy_message
)

logger = setup_logger(__name__)
config = Config()
conversation_tracker = ConversationTracker()
address_parser = AddressParser()
consent_manager = ConsentManager()


class MessageProcessor:
    """Processes incoming WhatsApp messages."""

    def __init__(self):
        self.supported_message_types = ['text', 'image', 'location', 'document']

    def process_message(self, message, value):
        """
        Process an incoming WhatsApp message.

        Args:
            message (dict): Message data from webhook
            value (dict): Additional metadata from webhook

        Returns:
            dict: Processed message data ready for reply, or None if processing failed
        """
        try:
            # Extract basic message info
            message_id = message.get('id')
            from_number = message.get('from')
            timestamp = message.get('timestamp')
            message_type = message.get('type')

            # Extract metadata
            phone_number_id = value.get('metadata', {}).get('phone_number_id')
            display_name = value.get('contacts', [{}])[0].get('profile', {}).get('name', 'User')

            logger.info(f"Processing {message_type} message from {display_name} ({from_number})")

            # Update conversation tracker - user has messaged us
            conversation_tracker.update_conversation(from_number)

            # Check if message type is supported
            if message_type not in self.supported_message_types:
                logger.warning(f"Unsupported message type: {message_type}")
                return self._create_response(
                    from_number,
                    phone_number_id,
                    "Lo siento, solo proceso mensajes de texto. Por favor, envíame tus direcciones en texto."
                )

            # Process based on message type
            if message_type == 'text':
                return self._process_text_message(message, from_number, phone_number_id, display_name)
            elif message_type == 'location':
                return self._process_location_message(message, from_number, phone_number_id, display_name)
            elif message_type == 'image':
                return self._process_image_message(message, from_number, phone_number_id, display_name)
            elif message_type == 'document':
                return self._process_document_message(message, from_number, phone_number_id, display_name)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return None

    def _process_text_message(self, message, from_number, phone_number_id, display_name):
        """
        Process text messages.

        Args:
            message (dict): Message data
            from_number (str): Sender's phone number
            phone_number_id (str): WhatsApp Business phone number ID
            display_name (str): Sender's display name

        Returns:
            dict: Response data
        """
        try:
            # Extract message text
            message_body = message.get('text', {}).get('body', '').strip()

            if not message_body:
                return self._create_response(
                    from_number,
                    phone_number_id,
                    "El mensaje está vacío. Por favor, asegúrate de incluir texto."
                )

            logger.info(f"Text message content: '{message_body[:50]}...'")

            # Check for command shortcuts (must be exact match)
            message_lower = message_body.lower().strip()

            # FEEDBACK SURVEY INTERCEPT
            # GDPR commands always bypass the survey so users can revoke/delete
            # at any time, even mid-survey.
            _gdpr_commands = {
                '/privacy', 'privacy', '/privacidad', 'privacidad',
                '/mydata', 'mydata', '/misdatos', 'misdatos',
                '/exportdata', 'exportdata', '/exportar', 'exportar',
                '/deletedata', 'deletedata', '/borrar', 'borrar', '/eliminar', 'eliminar',
                '/revokeconsent', 'revokeconsent', '/revocar', 'revocar',
                '/pagos', 'pagos', '/pago', 'pago',
                '/precios', 'precios',
                'premium', 'plus',
                'cancelar suscripción', 'cancelar suscripcion',
            }
            if message_lower not in _gdpr_commands:
                survey_reply = feedback_manager.handle_incoming(
                    from_number, message_body, phone_number_id
                )
                if survey_reply is not None:
                    return self._create_response(from_number, phone_number_id, survey_reply)

            # Command: /help or /ayuda
            if message_lower in ['/help', '/ayuda', 'help', 'ayuda']:
                return self._handle_help_command(from_number, phone_number_id, display_name)

            # Command: /example or /ejemplo
            if message_lower in ['/example', '/ejemplo', 'example', 'ejemplo']:
                return self._handle_example_command(from_number, phone_number_id, display_name)

            # Command: /about or /info
            if message_lower in ['/about', '/info', 'about', 'info']:
                return self._handle_about_command(from_number, phone_number_id, display_name)

            # Command: /precios (show plan descriptions)
            if message_lower in ['/precios', 'precios']:
                return self._handle_precios_command(from_number, phone_number_id)

            # Command: /pagos (show plan + payment options)
            if message_lower in ['/pagos', 'pagos', '/pago', 'pago']:
                return self._handle_pagos_command(from_number, phone_number_id, display_name)

            # Commands: premium / plus (return single checkout link)
            if message_lower in ['premium', 'plus']:
                return self._handle_plan_link_command(from_number, phone_number_id, message_lower)

            # Command: cancelar suscripción
            if message_lower in ['cancelar suscripción', 'cancelar suscripcion',
                                  '/cancelar suscripción', '/cancelar suscripcion']:
                return self._handle_cancel_subscription_command(from_number, phone_number_id, display_name)

            # GDPR COMMANDS
            # Command: /privacy (show privacy policy)
            if message_lower in ['/privacy', 'privacy', '/privacidad', 'privacidad']:
                return self._handle_privacy_command(from_number, phone_number_id, display_name)

            # Command: /mydata (show user's data - GDPR Art. 15)
            if message_lower in ['/mydata', 'mydata', '/misdatos', 'misdatos']:
                return self._handle_mydata_command(from_number, phone_number_id, display_name)

            # Command: /exportdata (export user data - GDPR Art. 20)
            if message_lower in ['/exportdata', 'exportdata', '/exportar', 'exportar']:
                return self._handle_exportdata_command(from_number, phone_number_id, display_name)

            # Command: /deletedata (delete all user data - GDPR Art. 17)
            if message_lower in ['/deletedata', 'deletedata', '/borrar', 'borrar', '/eliminar', 'eliminar']:
                return self._handle_deletedata_command(from_number, phone_number_id, display_name)

            # Command: /revokeconsent (withdraw consent - GDPR Art. 7.3)
            if message_lower in ['/revokeconsent', 'revokeconsent', '/revocar', 'revocar']:
                return self._handle_revokeconsent_command(from_number, phone_number_id, display_name)

            # GDPR CONSENT FLOW
            # Check if message is a consent response (accept/decline)
            # IMPORTANT: Only check for consent responses if user doesn't have consent yet
            # This prevents accidental consent changes from casual messages containing "no", "si", etc.
            if not consent_manager.has_consent(from_number):
                consent_response = self._check_consent_response(message_body)
                if consent_response:
                    return self._handle_consent_response(
                        from_number,
                        phone_number_id,
                        display_name,
                        consent_response
                    )

            # PHASE 2: Route optimization integration
            # Try to parse addresses - let the parser decide if it's valid
            addresses, error = address_parser.parse_addresses(message_body)

            if addresses or error:
                # Either we got valid addresses or a parsing error - process as route request
                # But first, check if user has given consent
                if not consent_manager.has_consent(from_number):
                    logger.info(f"User {from_number} attempted route request without consent")
                    return self._create_response(from_number, phone_number_id, CONSENT_REQUIRED_FOR_ROUTE)

                logger.info("Processing as route request (valid addresses or parsing error)")
                return self._process_route_request(message_body, from_number, phone_number_id, display_name)

            # Check for common greetings
            greetings = ['hello', 'hi', 'hey', 'hola', 'buenos dias', 'buenas tardes']
            if any(greeting in message_body.lower() for greeting in greetings):
                # Check if user needs to consent
                if not consent_manager.has_consent(from_number):
                    logger.info(f"New user {from_number} greeted - showing consent request")
                    return self._create_response(from_number, phone_number_id, CONSENT_REQUEST)

                # User has consent, show normal greeting
                reply_text = f"*¡Hola {display_name}!*\n\n🦜 Soy tu asistente de rutas y te ayudaré a planificar tus entregas de manera eficiente.\n\n📍 *Inicio rápido:*\n¿Listo para empezar? ¡Envíame tus direcciones y te daré la mejor ruta! 🚀\n\n💬 *Comandos:*\n/hola - Bienvenida\n/ayuda - Ver instrucciones\n/ejemplo - Formato de direcciones\n/info - Acerca de esta herramienta\n/privacy - Política de privacidad\n/mydata - Ver tus datos\n/revokeconsent - Retirar consentimiento"
                return self._create_response(from_number, phone_number_id, reply_text)

            # Check for help requests
            help_keywords = ['help', 'ayuda', 'how', 'como']
            if any(keyword in message_body.lower() for keyword in help_keywords):
                # Check if user needs to consent
                if not consent_manager.has_consent(from_number):
                    logger.info(f"User {from_number} requested help without consent - showing consent request")
                    return self._create_response(from_number, phone_number_id, CONSENT_REQUEST)

                # User has consent, show normal help
                reply_text = "🗺️ *Ayuda para optimizar rutas*\n\n¡Puedo optimizar tus rutas de entrega!\n\n*Cómo se usa:*\n1. Escribe tu lista de direcciones (una por línea)\n2. Te daré la ruta más eficiente\n3. Te daré estimaciones de distancia, tiempo y costes de combustible\n\n*Ejemplo:*\nCalle Mayor 1, Madrid\nPlaza España, Madrid\nGran Via 50, Madrid\n\n¡Envíame tus direcciones para empezar!"
                return self._create_response(from_number, phone_number_id, reply_text)

            # Default response - acknowledge message
            reply_text = (
                f"Gracias por tu mensaje, {display_name}! 📍\n\n"
                "No entendí lo que me dijiste. Prueba con:\n\n"
                "*Comandos rápidos:*\n"
                "/hola - Bienvenida\n"
                "/ayuda - Instrucciones detalladas\n"
                "/ejemplo - Formato de direcciones\n"
                "/info - Acerca de esta herramienta\n\n"
                "*O simplemente envíame tus direcciones:*\n"
                "Calle Mayor 1, Madrid\n"
                "Plaza España, Madrid\n"
                "Gran Via 50, Madrid"
            )

            return self._create_response(from_number, phone_number_id, reply_text)

        except Exception as e:
            logger.error(f"Error processing text message: {e}", exc_info=True)
            return None

    def _format_error_for_user(self, error_message):
        """
        Format error messages consistently for user display.

        Args:
            error_message (str): The error message

        Returns:
            str: Formatted message for WhatsApp
        """
        # Add ❌ prefix if not present
        if not error_message.startswith("❌"):
            error_message = f"❌ {error_message}"

        # Add format example only for "could not find addresses" error
        if "No fue posible encontrar las direcciones" in error_message:
            error_message += "\n\n*Formato ejemplo:*\nCalle Mayor 1, 28013 Madrid\nPlaza España, Madrid\nGran Via 50, Madrid"

        return error_message

    def _process_route_request(self, message_body, from_number, phone_number_id, display_name):
        """
        Process a route optimization request.

        Args:
            message_body (str): Message text containing addresses
            from_number (str): Sender's phone number
            phone_number_id (str): WhatsApp Business phone number ID
            display_name (str): Sender's display name

        Returns:
            dict: Response data
        """
        try:
            logger.info(f"Processing route request from {display_name}")

            # Check tier/usage gate before hitting Google Maps API
            allowed, block_message = usage_manager.check_route_allowed(from_number)
            if not allowed:
                return self._create_response(from_number, phone_number_id, block_message)

            # Parse addresses from message
            addresses, error = address_parser.parse_addresses(message_body)

            if error:
                # Failed to parse addresses - use consolidated error formatter
                logger.warning(f"Failed to parse addresses: {error}")
                reply_text = self._format_error_for_user(error)
                return self._create_response(from_number, phone_number_id, reply_text)

            # Send initial acknowledgment
            logger.info(f"Parsed {len(addresses)} addresses, optimizing route...")

            # For WhatsApp, we can't send progress messages easily,
            # so we'll just optimize and send the result
            # In future, we could send a "processing..." message first

            # Optimize the route
            result = route_bridge.optimize_route(addresses)

            # Only record usage on successful optimization (never on error/bad addresses)
            if result.get('success'):
                usage_manager.record_route_used(from_number)

            # Twilio: split into two messages to stay within the 1600-char outgoing limit.
            # Summary (addresses + savings) first, Google Maps URL second.
            if os.getenv('MESSAGING_PROVIDER', 'meta').lower() == 'twilio':
                summary, maps_url = route_bridge.format_route_result_parts(result, phone_number=from_number)
                if maps_url:
                    from .message_sender import MessageSender
                    MessageSender().send_reply(self._create_response(from_number, phone_number_id, summary))
                    return self._create_response(from_number, phone_number_id, maps_url)
                # Error or no URL — fall through to single message
                return self._create_response(from_number, phone_number_id, summary)

            # Meta (and any other provider): single combined message
            reply_text = route_bridge.format_route_result_for_whatsapp(result, phone_number=from_number)
            return self._create_response(from_number, phone_number_id, reply_text)

        except Exception as e:
            logger.error(f"Error processing route request: {e}", exc_info=True)
            reply_text = "❌ Ocurrió un error al optimizar tu ruta. Por favor, intenta nuevamente más tarde."
            return self._create_response(from_number, phone_number_id, reply_text)

    def _process_location_message(self, message, from_number, phone_number_id, display_name):
        """Process location messages (for future integration)."""
        logger.info("Location message received")

        location = message.get('location', {})
        latitude = location.get('latitude')
        longitude = location.get('longitude')

        reply_text = f"Gracias por compartir tu ubicación! 📍\n\nLat: {latitude}\nLon: {longitude}\n\nEl procesamiento de ubicaciones no está disponible aun. Por favor, envíame el texto con las direcciones para optimizar la ruta."

        return self._create_response(from_number, phone_number_id, reply_text)

    def _process_image_message(self, message, from_number, phone_number_id, display_name):
        """Process image messages (placeholder for future features)."""
        logger.info("Image message received")

        reply_text = "Gracias por la imagen! 📷\n\nEl procesamiento de imágenes no está disponible aun. Por favor, envíame el texto con las direcciones para optimizar la ruta."

        return self._create_response(from_number, phone_number_id, reply_text)

    def _process_document_message(self, message, from_number, phone_number_id, display_name):
        """Process document messages (placeholder for future features)."""
        logger.info("Document message received")

        reply_text = "Gracias por el documento! 📄\n\nEl procesamiento de documentos no está disponible aun. Por favor, envíame el texto con las direcciones para optimizar la ruta."

        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_help_command(self, from_number, phone_number_id, display_name):
        """Handle /help command."""
        # Check if user needs to consent
        if not consent_manager.has_consent(from_number):
            logger.info(f"User {from_number} requested /help without consent - showing consent request")
            return self._create_response(from_number, phone_number_id, CONSENT_REQUEST)

        # User has consent, show normal help
        reply_text = (
            "🗺️ *Optimizador de rutas - Ayuda*\n\n"
            "*Cómo se usa:*\n"
            "1️⃣ Envíame tus direcciones\n"
            "2️⃣ Optimizaré la ruta automáticamente\n"
            "3️⃣ Te daré estimación de ahorros en distancia, tiempo y combustible\n"
            "4️⃣ Obtendrás un enlace de la ruta detallada para Google Maps\n\n"
            "*Requisitos:*\n"
            "• Número de direcciones: mínimo 2, máximo 26\n"
            "• Primera dirección = punto de inicio\n"
            "• Última dirección = fin de la ruta (puedes poner el punto de inicio si es el caso)\n\n"
            "*Tips:*\n"
            "✅ Comprueba bien tus direcciones al ingresarlas para evitar errores\n"
            "✅ Sé específico (calle + número + CP + ciudad)\n"
            "✅ Para mejores resultados, incluye el código postal (CP) y la ciudad\n\n"
            "¿Necesitas un ejemplo? Envía /ejemplo"
        )
        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_example_command(self, from_number, phone_number_id, display_name):
        """Handle /example command."""
        reply_text = (
            "📝 *Ejemplos de formato:*\n\n"
            "*Ejemplo 1 - Separado por línea:*\n"
            "Paseo de la Castellana 50, 28046 Madrid\n"
            "Calle Mayor 14, 28013 Madrid\n"
            "Avenida del General Perón 25, 28020 Madrid\n\n"
            "*Ejemplo 2 - Lista numerada:*\n"
            "1. Calle Alcalá 100, 28028 Madrid\n"
            "2. Paseo de la Castellana 50, 28046 Madrid\n"
            "3. Calle Serrano 20, 28001 Madrid\n\n"
            "*¡Ambos formatos funcionan!* 🎯\n"
            "Si lo deseas, copia uno de estos ejemplos, cambia las direcciones a las tuyas, y envíalo!"
        )
        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_about_command(self, from_number, phone_number_id, display_name):
        """Handle /about command."""
        reply_text = (
            "ℹ️ *Acerca de Mi Ruta Pro*\n\n"
            "*¿Qué es esta herramienta?*\n"
            "Un asistente inteligente que optimiza rutas de entrega potenciado por IA.\n\n"
            "*Características clave:*\n"
            "🗺️ Optimización inteligente de rutas\n"
            "📏 Cálculo de distancias y tiempo\n"
            "⛽ Estimación de costes de combustible\n"
            "💰 Comparación de ahorros\n"
            "🔗 Integración con Google Maps\n\n"
            "*¿Cómo funciona?*\n"
            "1. Envías tus direcciones\n"
            "2. Calcula la ruta más eficiente\n"
            "3. ¡Ahorras tiempo y combustible! 🚗💨\n\n"
            "*¿Necesitas ayuda?*\n"
            "Envía /ayuda para instrucciones\n\n"
            "Versión: 3.0.0"
        )
        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_precios_command(self, from_number, phone_number_id):
        """Handle /precios command — static description of all plans."""
        reply_text = (
            "💳 *Mi Ruta Pro — Precios*\n\n"
            "📦 *Pago por uso* — €1,99 por ruta\n"
            "Sin suscripción. Pagas solo cuando necesites optimizar.\n"
            "Sin fecha de caducidad.\n\n"
            "⭐ *Premium* — €29,99/mes\n"
            "Hasta 2 rutas optimizadas al día.\n"
            "Ideal para uso regular. ¡Ahorra hasta un 60% al mes!\n\n"
            "🚀 *Plus* — €49,99/mes\n"
            "Hasta 4 rutas optimizadas al día.\n"
            "Perfecto para uso profesional. ¡Ahorra hasta 180€ al mes!\n\n"
            "Escribe *pagos* para contratar un plan."
        )
        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_pagos_command(self, from_number, phone_number_id, display_name):
        """Handle /pagos command — show current plan + payment options."""
        if not consent_manager.has_consent(from_number):
            return self._create_response(from_number, phone_number_id, CONSENT_REQUEST)

        from database.db_manager import get_db_manager
        from database.models import User
        from .stripe_manager import StripeManager, TIER_DISPLAY

        db = get_db_manager()
        try:
            with db.get_session() as session:
                user = session.query(User).filter_by(
                    phone_number=from_number, deleted_at=None
                ).first()

                if not user:
                    return self._create_response(from_number, phone_number_id,
                                                 "❌ No encontré tu cuenta. Intenta de nuevo.")

                tier = user.tier
                tier_expires_at = user.tier_expires_at
                routes_today = user.routes_used_today or 0
                routes_lifetime = user.routes_used_lifetime or 0
                ppu_credits = user.ppu_credits or 0

        except Exception as e:
            logger.error(f"_handle_pagos_command DB error for {from_number}: {e}", exc_info=True)
            return self._create_response(from_number, phone_number_id,
                                         "❌ No pude acceder a tu cuenta. Intenta de nuevo.")

        # Build current plan section
        TIER_LIMITS = {'btester': '3/día', 'free': '3 totales', 'ppu': 'pago por uso',
                       'premium': '2/día', 'plus': '4/día'}
        plan_section = ""
        if tier == 'ppu':
            plan_section = (
                f"💳 *Mi Ruta Pro — Tu plan*\n\n"
                f"📦 *Plan:* Pago por uso\n"
                f"🎫 *Créditos disponibles:* {ppu_credits}\n"
                f"🔄 *Rutas totales:* {routes_lifetime}\n\n"
                f"{'─' * 20}\n"
                f"💡 *Recargar créditos:*\n\n"
            )
        elif tier in {'premium', 'plus'}:
            display_name_tier, price, _ = TIER_DISPLAY.get(tier, (tier, '', ''))
            if tier_expires_at:
                valid_until = tier_expires_at.strftime("%d %b %Y")
                validity_line = f"📅 *Válido hasta:* {valid_until}\n"
            else:
                validity_line = "📅 *Validez:* sin límite de tiempo\n"
            plan_section = (
                f"💳 *Mi Ruta Pro — Tu plan actual*\n\n"
                f"📦 *Plan:* {display_name_tier}\n"
                f"{validity_line}"
                f"🗺️ *Rutas hoy:* {routes_today}\n"
                f"🔄 *Rutas totales:* {routes_lifetime}\n\n"
                f"{'─' * 20}\n"
                f"💡 *Cambiar plan:*\n\n"
            )
        else:
            plan_section = (
                f"💳 *Mi Ruta Pro — Planes disponibles*\n\n"
                f"📦 *Plan actual:* {tier} ({TIER_LIMITS.get(tier, '')})\n"
                f"🔄 *Rutas totales:* {routes_lifetime}\n\n"
                f"{'─' * 20}\n"
                f"💡 *Elige un plan para continuar:*\n\n"
            )

        # Always show only 1 URL (PPU) to stay under Twilio's 1600-char limit.
        # Premium/Plus are shown as text only; user replies with plan name to get link.
        try:
            stripe_mgr = StripeManager()
            ppu_link = stripe_mgr.get_checkout_link_message(from_number, 'ppu')
        except Exception as e:
            logger.error(f"_handle_pagos_command: Stripe unavailable for {from_number}: {e}", exc_info=True)
            ppu_link = ""

        if ppu_link:
            if tier == 'ppu':
                # PPU user: top-up + option to switch to subscription
                reply_text = (
                    f"{plan_section}"
                    f"{ppu_link}\n\n"
                    "💡 *O suscríbete a un plan:*\n\n"
                    "⭐ *Premium* — €29,99/mes (2 rutas/día) ¡Ahorra hasta un 60%!\n"
                    "Responde *premium* para obtener el enlace de pago.\n\n"
                    "🚀 *Plus* — €49,99/mes (4 rutas/día) ¡Ahorra hasta 180€/mes!\n"
                    "Responde *plus* para obtener el enlace de pago.\n\n"
                    "_Pago seguro con Stripe 🔒_"
                )
            else:
                # Free/expired/btester: show all plans, PPU with link, others as text
                reply_text = (
                    f"{plan_section}"
                    f"{ppu_link}\n\n"
                    "⭐ *Premium* — €29,99/mes (2 rutas/día) ¡Ahorra hasta un 60%!\n"
                    "Responde *premium* para obtener el enlace de pago.\n\n"
                    "🚀 *Plus* — €49,99/mes (4 rutas/día) ¡Ahorra hasta 180€/mes!\n"
                    "Responde *plus* para obtener el enlace de pago.\n\n"
                    "_Precios con IVA. Pago seguro con Stripe 🔒_"
                )
        else:
            reply_text = (
                f"{plan_section}"
                "💳 Los pagos estarán disponibles muy pronto."
            )

        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_plan_link_command(self, from_number, phone_number_id, tier: str):
        """Return a single checkout link for 'premium' or 'plus' plan."""
        if not consent_manager.has_consent(from_number):
            return self._create_response(from_number, phone_number_id, CONSENT_REQUEST)

        from .stripe_manager import StripeManager, TIER_DISPLAY
        try:
            link = StripeManager().get_checkout_link_message(from_number, tier)
        except Exception as e:
            logger.error(f"_handle_plan_link_command: Stripe error for {from_number} tier={tier}: {e}")
            link = ""

        if link:
            reply_text = (
                f"{link}\n\n"
                "_Precio con IVA incluido. Pago seguro con Stripe 🔒_"
            )
        else:
            reply_text = "❌ No pude generar el enlace de pago. Intenta de nuevo en unos segundos."

        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_cancel_subscription_command(self, from_number, phone_number_id, display_name):
        """Handle 'cancelar suscripción' — cancel Stripe subscription immediately."""
        if not consent_manager.has_consent(from_number):
            return self._create_response(from_number, phone_number_id, CONSENT_REQUEST)

        from database.db_manager import get_db_manager
        from database.models import User
        import stripe

        db = get_db_manager()
        try:
            with db.get_session() as session:
                user = session.query(User).filter_by(
                    phone_number=from_number, deleted_at=None
                ).first()
                if not user or not user.stripe_subscription_id:
                    return self._create_response(
                        from_number, phone_number_id,
                        "ℹ️ No tienes una suscripción activa para cancelar.\n\n"
                        "Escribe *pagos* para ver los planes disponibles."
                    )
                sub_id = user.stripe_subscription_id

            stripe.api_key = config.STRIPE_SECRET_KEY
            stripe.Subscription.cancel(sub_id)

            return self._create_response(
                from_number, phone_number_id,
                "✅ *Suscripción cancelada.*\n\n"
                "Has vuelto al plan gratuito. Puedes reactivar tu plan cuando quieras "
                "escribiendo *pagos*."
            )

        except Exception as e:
            logger.error(f"Cancel subscription error for {from_number}: {e}", exc_info=True)
            return self._create_response(
                from_number, phone_number_id,
                "❌ No pude cancelar tu suscripción. Por favor, inténtalo de nuevo más tarde."
            )

    def _handle_privacy_command(self, from_number, phone_number_id, display_name):
        """Handle /privacy command - show privacy policy."""
        logger.info(f"User {from_number} requested privacy policy")
        # Twilio has a 1600-char limit; Meta allows up to 4096
        version = "summary" if config.MESSAGING_PROVIDER == 'twilio' else "short"
        reply_text = get_privacy_message(version=version)
        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_mydata_command(self, from_number, phone_number_id, display_name):
        """Handle /mydata command - GDPR Article 15 (Right to access)."""
        logger.info(f"User {from_number} requested their data")

        # Get consent data (use get_consent_info for raw record format)
        consent_data = consent_manager.get_consent_info(from_number)

        if not consent_data:
            reply_text = (
                "📊 *Tus Datos Personales*\n\n"
                "No tenemos ningún dato tuyo registrado.\n\n"
                "ℹ️ Cuando des tu consentimiento, podrás ver aquí:\n"
                "• Tu número de teléfono\n"
                "• Fecha de consentimiento\n"
                "• Estado del consentimiento\n"
                "• Idioma de preferencia"
            )
        else:
            # Format consent data
            from .consent_manager_db import format_consent_date
            formatted_date = format_consent_date(consent_data.get('consent_date', ''), "es")
            status = "✅ Activo" if consent_data.get('consent_given') else "❌ Rechazado"

            if consent_data.get('consent_withdrawn'):
                withdrawal_date = format_consent_date(consent_data.get('withdrawal_date', ''), "es")
                status = f"🔓 Retirado el {withdrawal_date}"

            reply_text = (
                f"📊 *Tus Datos Personales*\n\n"
                f"*Número de teléfono:* {from_number}\n"
                f"*Consentimiento:* {status}\n"
                f"*Fecha de consentimiento:* {formatted_date}\n"
                f"*Versión de consentimiento:* {consent_data.get('consent_version', 'N/A')}\n"
                f"*Idioma:* {consent_data.get('language', 'N/A')}\n\n"
                f"*Direcciones guardadas:* Ninguna (se borran automáticamente después de 24h)\n\n"
                f"💡 *Comandos disponibles:*\n"
                f"/exportdata - Exportar tus datos\n"
                f"/deletedata - Eliminar todos tus datos\n"
                f"/revokeconsent - Retirar consentimiento"
            )

        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_exportdata_command(self, from_number, phone_number_id, display_name):
        """Handle /exportdata command - GDPR Article 20 (Data portability)."""
        logger.info(f"User {from_number} requested data export")

        import json
        consent_data = consent_manager.export_user_consent_data(from_number)

        if not consent_data:
            reply_text = (
                "📦 *Exportación de Datos*\n\n"
                "No tenemos ningún dato tuyo para exportar.\n\n"
                "ℹ️ Cuando des tu consentimiento y uses el servicio, "
                "podrás exportar tus datos en formato JSON."
            )
        else:
            # Create export data
            export_data = {
                "phone_number": from_number,
                "display_name": display_name,
                "consent_data": consent_data,
                "export_date": datetime.now().isoformat(),
                "note": "Addresses are automatically deleted after 24 hours and are not included in this export"
            }

            # Format as readable JSON
            json_data = json.dumps(export_data, indent=2, ensure_ascii=False)

            reply_text = (
                f"📦 *Exportación de Datos*\n\n"
                f"Aquí están todos tus datos en formato JSON:\n\n"
                f"```\n{json_data}\n```\n\n"
                f"✅ Esta información cumple con el derecho a la portabilidad de datos (Art. 20 RGPD)\n\n"
                f"💡 Puedes copiar estos datos y guardarlos o transferirlos a otro servicio."
            )

        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_deletedata_command(self, from_number, phone_number_id, display_name):
        """Handle /deletedata command - GDPR Article 17 (Right to erasure)."""
        logger.info(f"User {from_number} requested data deletion")

        consent_data = consent_manager.export_user_consent_data(from_number)

        if not consent_data:
            reply_text = (
                "🗑️ *Eliminación de Datos*\n\n"
                "No tenemos ningún dato tuyo que eliminar.\n\n"
                "ℹ️ Ya no apareces en nuestro sistema."
            )
        else:
            # Step 1: Revoke consent (while phone still findable by original number)
            consent_revoked = consent_manager.revoke_consent(from_number)

            # Step 2: Anonymize PII immediately (GDPR Art. 17 - Right to Erasure)
            # Must run after revoke_consent() but before any further lookups by phone
            data_anonymized = consent_manager.anonymize_user(from_number)

            if consent_revoked and data_anonymized:
                reply_text = (
                    "🗑️ *Datos Eliminados*\n\n"
                    "✅ Tu solicitud de eliminación ha sido procesada.\n\n"
                    "*¿Qué se ha eliminado?*\n"
                    "• Tu número de teléfono (anonimizado)\n"
                    "• Tu nombre de perfil (eliminado)\n"
                    "• Tus datos de sesión (eliminados en 24h)\n\n"
                    "*⚠️ Nota importante:*\n"
                    "El registro de tu consentimiento se conservará 3 años por obligación legal "
                    "(para demostrar que tuviste nuestro consentimiento), pero sin tus datos personales.\n\n"
                    "Gracias por haber usado nuestro servicio."
                )
                logger.info(f"GDPR Art. 17 erasure completed for {from_number}")
            else:
                reply_text = "❌ Error al procesar tu solicitud. Por favor, intenta de nuevo o contacta con soporte en support@monowai.es"

        return self._create_response(from_number, phone_number_id, reply_text)

    def _handle_revokeconsent_command(self, from_number, phone_number_id, display_name):
        """Handle /revokeconsent command - GDPR Article 7.3 (Withdraw consent)."""
        logger.info(f"User {from_number} requested consent revocation")

        if not consent_manager.has_consent(from_number):
            reply_text = (
                "ℹ️ *Retirar Consentimiento*\n\n"
                "No tienes un consentimiento activo que retirar.\n\n"
                "💡 Si quieres dar tu consentimiento, escribe *\"Acepto\"*"
            )
        else:
            # Revoke consent
            success = consent_manager.revoke_consent(from_number)

            if success:
                reply_text = CONSENT_REVOKED
                logger.info(f"Consent revoked by {from_number} ({display_name})")
            else:
                reply_text = "❌ Error al retirar tu consentimiento. Por favor, intenta de nuevo."

        return self._create_response(from_number, phone_number_id, reply_text)

    def _check_consent_response(self, message_text):
        """
        Check if message is a consent accept/decline response.

        Args:
            message_text (str): User's message

        Returns:
            str: 'accept', 'decline', or None
        """
        # Consent responses are always short (e.g. "sí", "acepto", "no").
        # A list of addresses or any other content will never qualify.
        # This prevents substring false-positives (e.g. 'si' inside 'residencia').
        if len(message_text.strip()) > 50:
            return None

        keywords = get_consent_keywords()
        message_lower = message_text.lower().strip()

        # IMPORTANT: Check reject keywords FIRST to avoid false positives
        # (e.g., "no acepto" contains "acepto" but should be treated as reject)
        if any(keyword in message_lower for keyword in keywords['reject']):
            return 'decline'

        # Check for accept keywords
        if any(keyword in message_lower for keyword in keywords['accept']):
            return 'accept'

        return None

    def _handle_consent_response(self, from_number, phone_number_id, display_name, response):
        """
        Handle user's consent response (accept or decline).

        Args:
            from_number (str): User's phone number
            phone_number_id (str): WhatsApp Business phone number ID
            display_name (str): User's display name
            response (str): 'accept' or 'decline'

        Returns:
            dict: Response data
        """
        try:
            if response == 'accept':
                # Check if user already has consent
                if consent_manager.has_consent(from_number):
                    # Already has consent
                    consent_date = consent_manager.get_consent_date(from_number)
                    from .consent_manager_db import format_consent_date
                    formatted_date = format_consent_date(consent_date, "es")
                    reply_text = CONSENT_ALREADY_GIVEN.format(consent_date=formatted_date)
                else:
                    # Save new consent
                    success = consent_manager.save_consent(
                        from_number,
                        consent_given=True,
                        language="es"
                    )

                    if success:
                        logger.info(f"Consent granted by {from_number} ({display_name})")
                        reply_text = CONSENT_ACCEPTED
                    else:
                        logger.error(f"Failed to save consent for {from_number}")
                        reply_text = "❌ Error al guardar tu consentimiento. Por favor, intenta de nuevo."

            elif response == 'decline':
                # Save consent decline
                success = consent_manager.save_consent(
                    from_number,
                    consent_given=False,
                    language="es"
                )

                if success:
                    logger.info(f"Consent declined by {from_number} ({display_name})")
                    reply_text = CONSENT_DECLINED
                else:
                    logger.error(f"Failed to save consent decline for {from_number}")
                    reply_text = "❌ Error al procesar tu respuesta. Por favor, intenta de nuevo."

            return self._create_response(from_number, phone_number_id, reply_text)

        except Exception as e:
            logger.error(f"Error handling consent response: {e}", exc_info=True)
            return self._create_response(
                from_number,
                phone_number_id,
                "❌ Error al procesar tu consentimiento. Por favor, contacta con soporte en support@monowai.es"
            )

    def _create_response(self, to_number, phone_number_id, message_text):
        """
        Create a response data structure.

        Args:
            to_number (str): Recipient's phone number
            phone_number_id (str): WhatsApp Business phone number ID
            message_text (str): Reply message text

        Returns:
            dict: Response data structure
        """
        return {
            'to_number': to_number,
            'phone_number_id': phone_number_id,
            'message_text': message_text,
            'timestamp': datetime.now().isoformat()
        }
