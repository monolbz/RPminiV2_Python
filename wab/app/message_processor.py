#!/usr/bin/env python3
"""
Message Processor
Processes incoming WhatsApp messages and prepares responses.
Includes GDPR consent management.
"""

from datetime import datetime
from ..utils.logger import setup_logger
from ..utils.conversation_tracker import ConversationTracker
from .address_parser import AddressParser
from .consent_manager import ConsentManager
from ..integration.route_optimizer_bridge import route_bridge
from ..templates import (
    CONSENT_REQUEST,
    CONSENT_ACCEPTED,
    CONSENT_DECLINED,
    CONSENT_REVOKED,
    CONSENT_ALREADY_GIVEN,
    CONSENT_REQUIRED_FOR_ROUTE,
    get_consent_keywords
)

logger = setup_logger(__name__)
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
                    f"Sorry, I don't support {message_type} messages yet. Please send a text message."
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
                    "I received an empty message. Please send me some text."
                )

            logger.info(f"Text message content: '{message_body[:50]}...'")

            # Check for command shortcuts (must be exact match)
            message_lower = message_body.lower().strip()

            # Command: /help or /ayuda
            if message_lower in ['/help', '/ayuda', 'help', 'ayuda']:
                return self._handle_help_command(from_number, phone_number_id, display_name)

            # Command: /example or /ejemplo
            if message_lower in ['/example', '/ejemplo', 'example', 'ejemplo']:
                return self._handle_example_command(from_number, phone_number_id, display_name)

            # Command: /about or /info
            if message_lower in ['/about', '/info', 'about', 'info']:
                return self._handle_about_command(from_number, phone_number_id, display_name)

            # GDPR CONSENT FLOW
            # Check if message is a consent response (accept/decline)
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
                reply_text = f"*¡Hola {display_name}!*\n\n🦜 Soy tu asistente de rutas y te ayudaré a planificar tus entregas de manera eficiente.\n\n📍 *Inicio rápido:*\n¿Listo para empezar? ¡Envíame tus direcciones y te daré la mejor ruta! 🚀\n\n💬 *Comandos:*\n/hola - Bienvenida\n/ayuda - Instrucciones detalladas\n/ejemplo - Formato de direcciones\n/info - Acerca de esta herramienta"
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

            # Format the result for WhatsApp
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

        reply_text = f"Thanks for sharing your location! 📍\n\nLat: {latitude}\nLon: {longitude}\n\nLocation-based routing will be available soon!"

        return self._create_response(from_number, phone_number_id, reply_text)

    def _process_image_message(self, message, from_number, phone_number_id, display_name):
        """Process image messages (placeholder for future features)."""
        logger.info("Image message received")

        reply_text = "Thanks for the image! 📷\n\nImage processing is not available yet. Please send text addresses for route optimization."

        return self._create_response(from_number, phone_number_id, reply_text)

    def _process_document_message(self, message, from_number, phone_number_id, display_name):
        """Process document messages (placeholder for future features)."""
        logger.info("Document message received")

        reply_text = "Thanks for the document! 📄\n\nDocument processing is not available yet. Please send text addresses for route optimization."

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
            "ℹ️ *Acerca de Minubo AI*\n\n"
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

    def _check_consent_response(self, message_text):
        """
        Check if message is a consent accept/decline response.

        Args:
            message_text (str): User's message

        Returns:
            str: 'accept', 'decline', or None
        """
        keywords = get_consent_keywords()
        message_lower = message_text.lower().strip()

        # Check for accept keywords
        if any(keyword in message_lower for keyword in keywords['accept']):
            return 'accept'

        # Check for reject keywords
        if any(keyword in message_lower for keyword in keywords['reject']):
            return 'decline'

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
                    from .consent_manager import format_consent_date
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
                "❌ Error al procesar tu consentimiento. Por favor, contacta soporte."
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
