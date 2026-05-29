#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Short Privacy Policy for WhatsApp Display

This is a condensed version that fits in WhatsApp messages.
For the full legal text, see: docs/PRIVACY_POLICY.md
"""

from ..config.constants import SUPPORT_EMAIL, PRIVACY_EMAIL, PRIVACY_POLICY_URL

# =============================================================================
# SHORT PRIVACY POLICY (For /privacy command)
# =============================================================================

PRIVACY_POLICY_SHORT = f"""📋 *POLÍTICA DE PRIVACIDAD*
_Versión 1.0 - 28 de octubre de 2025_

*Responsable del Tratamiento:*
Jorge Blanco / Monowai.es
Email: {PRIVACY_EMAIL}

━━━━━━━━━━━━━━━━━━━━━━━━━━

*📊 ¿QUÉ DATOS RECOPILAMOS?*
• Tu número de teléfono de WhatsApp
• Las direcciones que nos envías
• Fecha y hora de las consultas

*🎯 ¿PARA QUÉ LOS USAMOS?*
• Calcular rutas optimizadas
• Estimar distancias, tiempos y costes
• Cumplir con obligaciones legales

*⏱️ ¿CUÁNTO TIEMPO LOS GUARDAMOS?*
• Direcciones: *24 horas* (eliminación automática)
• Datos de sesión: *24 horas*
• Registro de consentimiento: *3 años* (obligación legal)

*🔒 ¿CÓMO LOS PROTEGEMOS?*
• Cifrado HTTPS/TLS en todas las comunicaciones
• Eliminación automática tras 24 horas
• Acceso restringido solo a personal autorizado
• Cumplimiento RGPD y LOPDGDD

*🤝 ¿CON QUIÉN LOS COMPARTIMOS?*
• *Google:* Para calcular rutas (Google Maps API)
• *Meta/WhatsApp:* Para enviarte mensajes
• *Nadie más* - No vendemos ni compartimos tus datos

━━━━━━━━━━━━━━━━━━━━━━━━━━

*✅ TUS DERECHOS (RGPD):*

1️⃣ *Acceso:* Ver qué datos tenemos
   → Comando: `/misdatos`
2️⃣ *Rectificación:* Corregir datos incorrectos
   → Envía las direcciones correctas
3️⃣ *Supresión:* Eliminar tus datos
   → Comando: `/eliminar`
4️⃣ *Portabilidad:* Exportar tus datos
   → Comando: `/exportdata`
5️⃣ *Oposición/Revocación:* Retirar consentimiento
   → Comando: `/revocar`
6️⃣ *Reclamación:* Ante la autoridad de control
   → AEPD: https://www.aepd.es | 901 100 099

━━━━━━━━━━━━━━━━━━━━━━━━━━

*⚖️ BASE LEGAL:*
• Consentimiento (Art. 6.1.a RGPD)
• Obligación legal (Art. 6.1.c RGPD)
• Interés legítimo (Art. 6.1.f RGPD)

*📜 NORMATIVA:*
• RGPD (UE) 2016/679
• LOPDGDD (Ley Orgánica 3/2018)

━━━━━━━━━━━━━━━━━━━━━━━━━━

*📞 CONTACTO:*
Email: {PRIVACY_EMAIL}

*📄 Política completa:*
{PRIVACY_POLICY_URL}

o solicítala por email

━━━━━━━━━━━━━━━━━━━━━━━━━━

*⚠️ IMPORTANTE:*
• Puedes retirar tu consentimiento en cualquier momento: `/revocar`
• Eliminamos tus direcciones automáticamente tras 24h
• No compartimos tus datos con terceros (salvo Google/WhatsApp para el servicio)
• Tienes derecho a reclamar ante la AEPD

Para más detalles, solicita la política completa por email."""


# =============================================================================
# PRIVACY POLICY SUMMARY (Ultra-short version)
# =============================================================================

PRIVACY_SUMMARY = f"""🔒 *Resumen de Privacidad*

*Datos:* Teléfono + direcciones + fechas
*Uso:* Optimizar rutas
*Conservación:* 24 horas (direcciones)
*Terceros:* Google, Meta, Twilio, Railway, Stripe
*Tus derechos:* Acceso, supresión, portabilidad

Comandos:
• `/misdatos` - Ver tus datos
• `/eliminar` - Eliminar datos
• `/revocar` - Retirar consentimiento
• `/privacidad` - Resumen política de privacidad

Para ver la política completa, visita: {PRIVACY_POLICY_URL}"""


# =============================================================================
# PRIVACY POLICY - KEY POINTS (for consent flow)
# =============================================================================

PRIVACY_KEY_POINTS = f"""📋 *Puntos Clave de Privacidad*

✅ *Qué procesamos:*
   • Direcciones que envías
   • Tu número de teléfono
   • Hora y fecha de consultas

✅ *Cuánto tiempo:*
   • Direcciones: 24 horas máximo
   • Luego se borran automáticamente

✅ *Con quién compartimos:*
   • Google (calcular rutas)
   • WhatsApp (enviar respuestas)
   • Nadie más

✅ *Tus derechos:*
   • Acceder, corregir, eliminar tus datos
   • Retirar consentimiento en cualquier momento
   • Reclamar ante AEPD

✅ *Cómo protegemos:*
   • Cifrado HTTPS
   • Eliminación automática
   • Cumplimiento RGPD

*¿Dudas?* Escribe /privacy o contacta: {PRIVACY_EMAIL}"""


# =============================================================================
# AEPD CONTACT INFO
# =============================================================================

AEPD_INFO = """⚖️ *Agencia Española de Protección de Datos (AEPD)*

Si consideras que tus derechos no han sido atendidos, puedes reclamar:

*Web:* https://www.aepd.es
*Sede electrónica:* https://sedeagpd.gob.es
*Teléfono:* 901 100 099
*Dirección:* C/ Jorge Juan, 6, 28001 Madrid

*¿Cómo presentar una reclamación?*
1. Accede a la sede electrónica de la AEPD
2. Completa el formulario de reclamación
3. Adjunta documentación (emails, capturas, etc.)
4. Espera respuesta (plazo medio: 3-6 meses)

La reclamación es *gratuita*."""


# =============================================================================
# HELPER FUNCTION
# =============================================================================

def get_privacy_message(version="short"):
    """
    Get the appropriate privacy policy message.

    Args:
        version: "short", "summary", "key_points", or "aepd"

    Returns:
        str: The requested privacy policy message
    """
    versions = {
        "short": PRIVACY_POLICY_SHORT,
        "summary": PRIVACY_SUMMARY,
        "key_points": PRIVACY_KEY_POINTS,
        "aepd": AEPD_INFO
    }

    return versions.get(version, PRIVACY_POLICY_SHORT)
