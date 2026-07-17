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
Envíame tus direcciones en cualquier momento para continuar usando el servicio.

Gracias por haber usado nuestro servicio."""


# =============================================================================
# DATA CONTROLLER INFORMATION (Required by GDPR Article 13)
# =============================================================================

DATA_CONTROLLER_INFO = """
📋 *Responsable del Tratamiento de Datos*

*Identidad:* Jorge Blanco / Monowai.es
*NIF/CIF:* 02571328C
*Dirección:* Paseo de Santa María de la Cabeza, 21, 28045 Madrid, España
*Email:* privacy@monowai.es

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
