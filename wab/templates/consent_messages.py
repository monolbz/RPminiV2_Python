#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GDPR Consent Messages for WhatsApp Interface
Spanish language, EU/Spain compliant

These messages comply with:
- GDPR (EU Regulation 2016/679)
- Spanish LOPDGDD (Ley Orgánica 3/2018)
- Article 7 GDPR: Conditions for consent
- Article 13 GDPR: Information to be provided
"""

# =============================================================================
# CONSENT REQUEST MESSAGE
# =============================================================================

CONSENT_REQUEST = """👋 *¡Hola!*

Para poder ayudarte a optimizar tus rutas, necesito tu *consentimiento* para procesar tus datos personales.

📋 *¿Qué datos procesamos?*
• Las direcciones que nos envías
• Tu número de teléfono
• Fecha y hora de las consultas

🎯 *¿Para qué los usamos?*
• Calcular rutas optimizadas
• Estimar distancias, tiempos y costes
• Mejorar nuestro servicio

🔒 *¿Cómo protegemos tus datos?*
• Tus direcciones se borran automáticamente después de *24 horas*
• No compartimos tus datos con terceros
• Usamos conexiones seguras (HTTPS)
• Cumplimos con el RGPD y la LOPDGDD

⏱️ *Conservación de datos:*
• Direcciones: 24 horas máximo
• Datos de sesión: 24 horas
• Registro de consentimiento: 3 años (obligación legal)

✅ *Tus derechos:*
• Acceso: Ver qué datos tenemos (/mydata)
• Rectificación: Corregir datos incorrectos
• Supresión: Borrar todos tus datos (/deletedata)
• Portabilidad: Exportar tus datos (/exportdata)
• Revocación: Retirar tu consentimiento (/revokeconsent)

📄 Lee nuestra política de privacidad completa: /privacy

*¿Das tu consentimiento?*

Responde:
✅ *"Acepto"* para dar tu consentimiento
❌ *"No acepto"* para rechazar

Puedes retirar tu consentimiento en cualquier momento escribiendo /revokeconsent"""


# =============================================================================
# CONSENT ACCEPTED MESSAGE
# =============================================================================

CONSENT_ACCEPTED = """✅ *¡Gracias por tu consentimiento!*

Ya puedes usar el servicio. Para empezar, escribe: *hola*"""


# =============================================================================
# CONSENT DECLINED MESSAGE
# =============================================================================

CONSENT_DECLINED = """❌ *Consentimiento no otorgado*

Entendemos tu decisión. Sin tu consentimiento, no podemos procesar tus direcciones.

ℹ️ *¿Qué significa esto?*
• No procesaremos ninguna dirección que envíes
• No guardaremos ningún dato personal
• Puedes leer nuestra política de privacidad: /privacy

💭 *¿Has cambiado de opinión?*
Escribe *"Acepto"* en cualquier momento para dar tu consentimiento.

📧 *¿Tienes preguntas?*
Contacta con nosotros en: [TU_EMAIL_DE_CONTACTO]

Gracias por tu tiempo. 🙏"""


# =============================================================================
# CONSENT REVOKED MESSAGE
# =============================================================================

CONSENT_REVOKED = """🔓 *Consentimiento retirado*

Has retirado tu consentimiento exitosamente.

✅ *¿Qué hemos hecho?*
• Marcado tu consentimiento como retirado
• Programado la eliminación de tus datos

⏱️ *¿Cuándo se borran tus datos?*
• Tus direcciones y datos de sesión se borrarán en las próximas 24 horas
• El registro de tu consentimiento se conservará 3 años (obligación legal de demostrar que tuvimos tu consentimiento)

ℹ️ *¿Qué significa esto?*
• Ya no podremos procesar tus direcciones
• No recibirás más optimizaciones de rutas

💭 *¿Has cambiado de opinión?*
Puedes dar tu consentimiento de nuevo escribiendo *"Acepto"*

Gracias por haber usado nuestro servicio. 🙏"""


# =============================================================================
# CONSENT ALREADY GIVEN MESSAGE
# =============================================================================

CONSENT_ALREADY_GIVEN = """✅ *Ya has dado tu consentimiento*

Tienes el servicio de optimización de rutas activo desde el *{consent_date}*.

📍 *¿Quieres optimizar una ruta?*
Envíame tus direcciones, una por línea.

💡 *Comandos útiles:*
/ayuda - Ver instrucciones
/mydata - Ver tus datos
/privacy - Ver política de privacidad
/revokeconsent - Retirar consentimiento"""


# =============================================================================
# CONSENT REQUIRED FOR ACTION MESSAGE
# =============================================================================

CONSENT_REQUIRED_FOR_ROUTE = """⚠️ *Se requiere consentimiento*

Para optimizar rutas, necesito tu consentimiento para procesar tus direcciones.

📋 *¿Qué necesito?*
Tu autorización para:
• Procesar las direcciones que envías
• Calcular rutas optimizadas
• Guardar datos temporalmente (máx. 24 horas)

✅ *¿Das tu consentimiento?*

Responde:
• *"Acepto"* para dar tu consentimiento y ver la información completa
• /privacy para leer nuestra política de privacidad primero"""


# =============================================================================
# PENDING CONSENT RESPONSE MESSAGE
# =============================================================================

PENDING_CONSENT_RESPONSE = """⏳ *Esperando tu respuesta...*

Te he enviado la solicitud de consentimiento.

Por favor, responde:
✅ *"Acepto"* para dar tu consentimiento
❌ *"No acepto"* para rechazar

También puedes:
• /privacy - Leer la política de privacidad
• /ayuda - Ver información sobre el servicio"""


# =============================================================================
# HELPER FUNCTION: Get consent keywords
# =============================================================================

def get_consent_keywords():
    """
    Returns keywords that indicate consent acceptance or rejection.

    Returns:
        dict: Keywords for 'accept' and 'reject' in Spanish
    """
    return {
        'accept': [
            'acepto',
            'acepto',
            'si',
            'sí',
            'ok',
            'vale',
            'de acuerdo',
            'consiento',
            'autorizo',
            'confirmo',
            'yes'  # In case someone replies in English
        ],
        'reject': [
            'no acepto',
            'no acepto',
            'rechazo',
            'niego',
            'no',
            'no quiero',
            'no autorizo',
            'no consiento',
            'cancel',
            'cancelar'
        ]
    }


# =============================================================================
# DATA CONTROLLER INFORMATION (Required by GDPR Article 13)
# =============================================================================

DATA_CONTROLLER_INFO = """
📋 *Responsable del Tratamiento de Datos*

*Identidad:* [TU_NOMBRE_O_EMPRESA]
*NIF/CIF:* [TU_NIF_O_CIF]
*Dirección:* [TU_DIRECCIÓN]
*Email:* [TU_EMAIL]
*Teléfono:* [TU_TELÉFONO]

*Autoridad de Control:*
Agencia Española de Protección de Datos (AEPD)
Web: https://www.aepd.es
Teléfono: 901 100 099
"""


# =============================================================================
# NOTES FOR DEVELOPER
# =============================================================================

"""
GDPR COMPLIANCE CHECKLIST:

✅ Article 7: Conditions for consent
   - Clear and distinguishable request
   - Separate from other matters
   - Easy to withdraw as to give
   - Burden of proof on controller (keep records)

✅ Article 13: Information to be provided
   - Identity of controller
   - Purpose of processing
   - Legal basis (consent)
   - Data retention periods
   - Rights of data subject
   - Right to withdraw consent
   - Right to lodge complaint

✅ Article 5: Principles
   - Lawfulness, fairness, transparency
   - Purpose limitation
   - Data minimisation
   - Accuracy
   - Storage limitation (24h for addresses!)
   - Integrity and confidentiality

⚠️ BEFORE PRODUCTION:
1. Replace [TU_NOMBRE_O_EMPRESA] with your actual company name
2. Replace [TU_EMAIL_DE_CONTACTO] with real contact email
3. Fill in DATA_CONTROLLER_INFO with real data
4. Consider having a lawyer review the texts
5. Ensure consent records are properly stored (see ConsentManager)
"""
