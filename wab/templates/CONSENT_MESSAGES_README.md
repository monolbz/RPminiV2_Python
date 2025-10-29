# GDPR Consent Messages - Documentation

## ✅ Completed: Consent Request Messages

This document explains the GDPR-compliant consent messages created for WhatsApp interface.

---

## 📋 What Was Created

### **Files:**
1. `wab/templates/consent_messages.py` - All consent message templates
2. `wab/templates/__init__.py` - Package initialization
3. `wab/examples/test_consent_messages.py` - Testing and demonstration

---

## 📱 Messages Included

### **1. CONSENT_REQUEST**
- **When:** First time user tries to use route optimization (after greeting/help)
- **Purpose:** Ask for GDPR consent
- **Contains:**
  - What data is collected (addresses, phone number, timestamps)
  - Purpose of processing (route optimization)
  - How data is protected (24h deletion, no third parties, HTTPS)
  - Data retention periods (24h for addresses, 3 years for consent records)
  - User rights (access, deletion, portability, revocation)
  - Clear accept/reject options

**Length:** ~1200 characters (fits in one WhatsApp message)

---

### **2. CONSENT_ACCEPTED**
- **When:** User replies "acepto" / "si" / "ok" etc.
- **Purpose:** Confirm consent and guide user to start using service
- **Contains:**
  - Thank you message
  - How to use the service (example addresses)
  - Useful commands (/ayuda, /privacy, /mydata, /revokeconsent)

---

### **3. CONSENT_DECLINED**
- **When:** User replies "no acepto" / "rechazo" / "no" etc.
- **Purpose:** Respect user's decision, explain consequences
- **Contains:**
  - Acknowledgment of decision
  - What this means (no data processing)
  - Option to change mind later
  - Contact information for questions

---

### **4. CONSENT_REVOKED**
- **When:** User sends `/revokeconsent` command
- **Purpose:** Confirm revocation and explain data deletion
- **Contains:**
  - Confirmation of revocation
  - What happens to their data (deletion timeline)
  - Why consent record is kept (legal obligation)
  - Option to consent again

---

### **5. CONSENT_ALREADY_GIVEN**
- **When:** User tries to consent again when already consented
- **Purpose:** Inform they already have access
- **Contains:**
  - Confirmation with consent date
  - Reminder of how to use service
  - Useful commands

---

### **6. CONSENT_REQUIRED_FOR_ROUTE**
- **When:** User tries to optimize route without consent
- **Purpose:** Short reminder that consent is needed
- **Contains:**
  - Brief explanation of need
  - Quick accept option
  - Link to full privacy policy

---

### **7. PENDING_CONSENT_RESPONSE**
- **When:** User sent addresses but hasn't responded to consent request
- **Purpose:** Gentle reminder
- **Contains:**
  - Reminder to respond
  - Accept/reject options
  - Links to privacy policy and help

---

### **8. DATA_CONTROLLER_INFO**
- **When:** Part of privacy policy or on request
- **Purpose:** GDPR Article 13 requirement (controller identification)
- **Contains:**
  - Company/individual identity
  - NIF/CIF
  - Contact details (address, email, phone)
  - DPO information (if applicable)
  - Control authority (AEPD in Spain)

**⚠️ MUST BE FILLED IN WITH REAL DATA BEFORE PRODUCTION**

---

## 🔑 Consent Keywords

### **Accept Keywords (Spanish):**
- acepto
- si / sí
- ok
- vale
- de acuerdo
- consiento
- autorizo
- confirmo
- yes (English fallback)

### **Reject Keywords (Spanish):**
- no acepto
- rechazo
- niego
- no
- no quiero
- no autorizo
- no consiento
- cancel / cancelar

---

## 📏 Message Length Analysis

| Message | Length | Status |
|---------|--------|--------|
| CONSENT_REQUEST | ~1200 chars | ✓ Fits in one screen |
| CONSENT_ACCEPTED | ~500 chars | ✓ Short and clear |
| CONSENT_DECLINED | ~450 chars | ✓ Short and clear |
| CONSENT_REVOKED | ~650 chars | ✓ Fits in one screen |

All messages are under WhatsApp's 4096 character limit.

---

## ✅ GDPR Compliance Checklist

### **Article 7: Conditions for Consent**
- ✅ Clear and distinguishable request
- ✅ Separate from other matters (shown after help/greeting)
- ✅ Easy to withdraw as to give (`/revokeconsent` command)
- ✅ Burden of proof on controller (consent records kept 3 years)

### **Article 13: Information to be Provided**
- ✅ Identity of controller (in DATA_CONTROLLER_INFO)
- ✅ Purpose of processing (route optimization)
- ✅ Legal basis (consent)
- ✅ Data retention periods (24h for addresses, 3y for consent)
- ✅ Rights of data subject (all listed)
- ✅ Right to withdraw consent (clearly stated)
- ✅ Right to lodge complaint (AEPD contact provided)

### **Article 5: Principles**
- ✅ Lawfulness, fairness, transparency (clear language)
- ✅ Purpose limitation (only for route optimization)
- ✅ Data minimisation (only addresses, phone, timestamps)
- ✅ Accuracy (user sends data directly)
- ✅ Storage limitation (24h for addresses!)
- ✅ Integrity and confidentiality (HTTPS mentioned)

---

## ⚠️ BEFORE PRODUCTION - ACTION REQUIRED

### **1. Fill in Placeholders:**

Replace these placeholders in the files:

```python
[TU_NOMBRE_O_EMPRESA]      → Your company name or personal name
[TU_NIF_O_CIF]             → Your tax ID (NIF for individuals, CIF for companies)
[TU_DIRECCIÓN]             → Your registered address
[TU_EMAIL]                 → Your contact email
[TU_TELÉFONO]              → Your phone number
[TU_EMAIL_DE_CONTACTO]     → Support email address
[EMAIL_DPO]                → DPO email (if applicable)
```

### **2. Legal Review:**

**⚠️ STRONGLY RECOMMENDED:**
- Have a Spanish lawyer review all consent texts
- Ensure compliance with:
  - GDPR (EU Regulation 2016/679)
  - LOPDGDD (Spanish Ley Orgánica 3/2018)
  - ePrivacy Directive (for electronic communications)

### **3. DPO (Data Protection Officer):**

**Required if:**
- Your company has > 250 employees, OR
- You process data on a large scale, OR
- You process special categories of data

**If NOT required:**
- Remove DPO section from DATA_CONTROLLER_INFO

### **4. Register with AEPD:**

- Most data processing activities must be registered with AEPD
- Check requirements at: https://www.aepd.es

---

## 🔄 User Journey Flow

```
1. User: "/ayuda" or "hola"
   ↓
2. Bot: [Help message]
   ↓
3. Bot: CONSENT_REQUIRED_FOR_ROUTE
   ↓
4. User: "acepto"
   ↓
5. Bot: CONSENT_REQUEST (full details)
   ↓
6. User: "acepto" (confirms)
   ↓
7. Bot: CONSENT_ACCEPTED
   ↓
8. User: [Sends addresses]
   ↓
9. Bot: [Processes route optimization]
```

---

## 🧪 Testing

Run the test script to see all messages:

```bash
python wab/examples/test_consent_messages.py
```

This will:
- Display all consent messages
- Test keyword detection
- Check GDPR compliance elements
- Show typical conversation flow
- Analyze message lengths

---

## 📚 Reference Documents

### **GDPR (EU):**
- Full text: https://gdpr-info.eu/
- Article 7: Conditions for consent
- Article 13: Information to be provided
- Article 15-22: Rights of data subjects

### **LOPDGDD (Spain):**
- Full text: https://www.boe.es/eli/es/lo/2018/12/05/3
- Complements and adapts GDPR to Spanish law

### **AEPD (Spanish DPA):**
- Website: https://www.aepd.es
- Guidelines: https://www.aepd.es/guias
- Contact: 901 100 099

---

## 🎯 Next Steps

1. ✅ **DONE:** Consent messages created
2. **TODO:** Create ConsentManager class (storage)
3. **TODO:** Create full privacy policy document
4. **TODO:** Integrate into message_processor.py
5. **TODO:** Add GDPR commands implementation
6. **TODO:** Test end-to-end flow
7. **TODO:** Fill in placeholders with real data
8. **TODO:** Legal review (CRITICAL!)
9. **TODO:** Register with AEPD if required
10. **TODO:** Deploy to production

---

## 📞 Support

For questions about GDPR compliance in Spain:
- AEPD: 901 100 099
- AEPD Web: https://www.aepd.es
- Consult a Spanish data protection lawyer

---

**Last Updated:** October 24, 2025
**Version:** 1.0
**Status:** Draft - Requires legal review before production
