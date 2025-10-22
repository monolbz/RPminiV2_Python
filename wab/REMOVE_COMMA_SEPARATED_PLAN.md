# Plan: Remove Comma-Separated Address Support

## Summary
This document outlines all code sections that need to be modified to remove comma-separated address parsing support, keeping only:
- ✅ Line-separated addresses
- ✅ Numbered lists (1. Address, 2. Address, etc.)

---

## Files Affected

### 1. **wab/app/address_parser.py** (PRIMARY FILE)

#### Section 1: Docstring (Lines 27-42)
**Location:** `parse_addresses()` method docstring

**Current:**
```python
def parse_addresses(self, message_text):
    """
    Parse addresses from message text.
    Supports multiple formats:
    - One address per line
    - Comma-separated addresses    ← REMOVE THIS LINE
    - Numbered addresses

    Args:
        message_text (str): Message text containing addresses

    Returns:
        tuple: (addresses_list, error_message)
               Returns (list of addresses, None) on success
               Returns (None, error string) on failure
    """
```

**Change to:**
```python
def parse_addresses(self, message_text):
    """
    Parse addresses from message text.
    Supports multiple formats:
    - One address per line
    - Numbered addresses

    Args:
        message_text (str): Message text containing addresses

    Returns:
        tuple: (addresses_list, error_message)
               Returns (list of addresses, None) on success
               Returns (None, error string) on failure
    """
```

---

#### Section 2: Parsing Logic (Lines 50-62)
**Location:** `parse_addresses()` method - parsing attempts

**Current:**
```python
# Try different parsing methods
addresses = None

# Method 1: Line-separated addresses
addresses = self._parse_line_separated(text)

# Method 2: If method 1 failed, try comma-separated
if not addresses or len(addresses) < self.min_addresses:
    addresses = self._parse_comma_separated(text)    ← REMOVE THESE 2 LINES

# Method 3: If still failed, try numbered list
if not addresses or len(addresses) < self.min_addresses:
    addresses = self._parse_numbered_list(text)
```

**Change to:**
```python
# Try different parsing methods
addresses = None

# Method 1: Line-separated addresses
addresses = self._parse_line_separated(text)

# Method 2: If method 1 failed, try numbered list
if not addresses or len(addresses) < self.min_addresses:
    addresses = self._parse_numbered_list(text)
```

---

#### Section 3: Error Message (Line 66)
**Location:** `parse_addresses()` method - validation error message

**Current:**
```python
if not addresses:
    return None, "Could not find any addresses. Please send addresses (one per line or separated by commas)."
```

**Change to:**
```python
if not addresses:
    return None, "Could not find any addresses. Please send addresses one per line or as a numbered list."
```

---

#### Section 4: Delete Method (Lines 138-146)
**Location:** `_parse_comma_separated()` method

**Current:**
```python
def _parse_comma_separated(self, text):
    """Parse addresses separated by commas."""
    # Split by comma
    parts = [part.strip() for part in text.split(',') if part.strip()]

    # Filter out parts that are too short
    addresses = [part for part in parts if len(part) > 5]

    return addresses if len(addresses) >= self.min_addresses else None
```

**Action:** **DELETE THIS ENTIRE METHOD** (Lines 138-146)

---

#### Section 5: Route Request Detection (Line 242)
**Location:** `is_route_request()` method

**Current:**
```python
# Check if message has multiple lines or commas (likely addresses)
has_multiple_parts = '\n' in message_text or ',' in message_text
```

**Change to:**
```python
# Check if message has multiple lines (likely addresses)
has_multiple_parts = '\n' in message_text
```

---

### 2. **wab/app/message_processor.py**

#### Section 1: Example Command (Lines 272-289)
**Location:** `_handle_example_command()` method

**Current:**
```python
def _handle_example_command(self, from_number, phone_number_id, display_name):
    """Handle /example command."""
    reply_text = (
        "📝 *Ejemplos de formatos:*\n\n"
        "*Ejemplo 1 - Separado por línea:*\n"
        "Paseo de la Castellana 50, 28046 Madrid\n"
        "Calle Mayor 14, 28013 Madrid\n"
        "Avenida del General Perón 25, 28020 Madrid\n\n"
        "*Ejemplo 2 - Separado por comas:*\n"                          ← REMOVE THIS
        "Calle Mayor 1, 28013 Madrid, Plaza España, 28005, Madrid, Gran Via 50, 28013, Madrid\n\n"  ← REMOVE THIS
        "*Ejemplo 3 - Lista numerada:*\n"
        "1. Calle Alcalá 100, Madrid\n"
        "2. Paseo de la Castellana 50, Madrid\n"
        "3. Calle Serrano 20, Madrid\n\n"
        "*¡Todos los formatos funcionan!* 🎯\n"
        "Si lo deseas, copia uno de estos ejemplos, cambia las direcciones a las tuyas, y envíalo!"
    )
    return self._create_response(from_number, phone_number_id, reply_text)
```

**Change to:**
```python
def _handle_example_command(self, from_number, phone_number_id, display_name):
    """Handle /example command."""
    reply_text = (
        "📝 *Ejemplos de formatos:*\n\n"
        "*Ejemplo 1 - Separado por línea:*\n"
        "Paseo de la Castellana 50, 28046 Madrid\n"
        "Calle Mayor 14, 28013 Madrid\n"
        "Avenida del General Perón 25, 28020 Madrid\n\n"
        "*Ejemplo 2 - Lista numerada:*\n"
        "1. Calle Alcalá 100, Madrid\n"
        "2. Paseo de la Castellana 50, Madrid\n"
        "3. Calle Serrano 20, Madrid\n\n"
        "*¡Ambos formatos funcionan!* 🎯\n"
        "Si lo deseas, copia uno de estos ejemplos, cambia las direcciones a las tuyas, y envíalo!"
    )
    return self._create_response(from_number, phone_number_id, reply_text)
```

---

### 3. **wab/MESSAGES_REFERENCE.md** (Documentation)

#### Section 1: Help Command Reference (Line 111)
**Location:** Lines 102-127

**Current:**
```markdown
### Lines 253-277: /help Command

**Purpose:** Detailed instructions for using the route optimizer

**Message:**
```
🗺️ *Optimizador de rutas - Ayuda*

*Cómo se usa:*
1️⃣ Envíame tus direcciones
2️⃣ Optimizaré la ruta automáticamente
3️⃣ Te daré distancia, tiempo y estimación de ahorros
4️⃣ Obtendrás un enlace de la ruta detallada para Google Maps

*Requisitos:*
• Número de direcciones: mínimo 2, máximo 26
• Primera dirección = punto de inicio
• Última dirección = fin de la ruta (puedes poner el punto de inicio si es el caso)

*Formatos aceptados:*
• Separado por línea
• Comma-separated       ← REMOVE THIS LINE
• Lista numerada
```

**Change to:**
```markdown
*Formatos aceptados:*
• Separado por línea
• Lista numerada
```

---

#### Section 2: Example Command Reference (Lines 137-138)
**Location:** Lines 128-150

**Current:**
```markdown
### Lines 281-302: /example Command

**Purpose:** Show address format examples

**Message:**
```
📝 *Ejemplos de formatos:*

*Ejemplo 1 - Separado por línea:*
Paseo de la Castellana 50, 28046 Madrid
Calle Mayor 14, 28013 Madrid
Avenida del General Perón 25, 28020 Madrid

*Ejemplo 2 - Comma separated:*                                     ← REMOVE THIS
Calle Mayor 1, 28013 Madrid, Plaza España, 28005, Madrid, ...    ← REMOVE THIS

*Ejemplo 3 - Lista numerada:*
1. Calle Alcalá 100, Madrid
2. Paseo de la Castellana 50, Madrid
3. Calle Serrano 20, Madrid
```

**Change to:**
```markdown
*Ejemplo 1 - Separado por línea:*
Paseo de la Castellana 50, 28046 Madrid
Calle Mayor 14, 28013 Madrid
Avenida del General Perón 25, 28020 Madrid

*Ejemplo 2 - Lista numerada:*
1. Calle Alcalá 100, Madrid
2. Paseo de la Castellana 50, Madrid
3. Calle Serrano 20, Madrid
```

---

#### Section 3: Error Messages Reference (Line 182)
**Location:** Lines 180-190

**Current:**
```markdown
**Context:** Validation - no addresses found

**Message:**
```
"Could not find any addresses. Please send addresses (one per line or separated by commas)."
```

**Change to:**
```markdown
**Message:**
```
"Could not find any addresses. Please send addresses one per line or as a numbered list."
```

---

### 4. **wab/examples/test_route_integration.py** (Test File - OPTIONAL)

**Note:** This file may have test cases for comma-separated addresses. Review and update or remove those tests if they exist.

**Action:** Search for comma-related tests and either:
- Remove them, OR
- Update them to use line-separated or numbered format

---

## Summary of Changes

| File | Lines | Action |
|------|-------|--------|
| **address_parser.py** | 27-42 | Update docstring - remove comma mention |
| **address_parser.py** | 56-58 | Remove comma parsing attempt |
| **address_parser.py** | 66 | Update error message - remove comma mention |
| **address_parser.py** | 138-146 | **DELETE** `_parse_comma_separated()` method |
| **address_parser.py** | 242 | Remove comma check in `is_route_request()` |
| **message_processor.py** | 280-281 | Remove "Ejemplo 2" (comma-separated example) |
| **message_processor.py** | 286 | Change "Todos los formatos" → "Ambos formatos" |
| **MESSAGES_REFERENCE.md** | 111 | Remove comma mention from /help reference |
| **MESSAGES_REFERENCE.md** | 137-138 | Remove comma example from /example reference |
| **MESSAGES_REFERENCE.md** | 182 | Update error message reference |

---

## Reason for This Change

**User's concern:** Comma-separated parsing might induce errors because:
1. **Ambiguous parsing:** Spanish addresses often contain commas within the address itself
   - Example: "Calle Mayor, 14, 28013 Madrid"
   - Comma could be part of address or separator
2. **User confusion:** Two different separators (commas and newlines) can be confusing
3. **Parsing conflicts:** Hard to distinguish between address commas and separator commas
4. **Simpler is better:** Line-separated and numbered lists are clearer and less error-prone

**Example of potential error:**
```
Input: "Calle Mayor, 14, Madrid, Plaza España, 5, Madrid"

Could be interpreted as:
1. "Calle Mayor, 14, Madrid" + "Plaza España, 5, Madrid" (2 addresses) ✓
   OR
2. "Calle Mayor" + "14" + "Madrid" + "Plaza España" + "5" + "Madrid" (6 addresses) ✗
```

---

## Testing After Changes

After making these changes, test with:

1. **Line-separated (should work):**
   ```
   Calle Mayor 14, Madrid
   Plaza España, Madrid
   Gran Via 50, Madrid
   ```

2. **Numbered list (should work):**
   ```
   1. Calle Mayor 14, Madrid
   2. Plaza España, Madrid
   3. Gran Via 50, Madrid
   ```

3. **Comma-separated (should fail gracefully):**
   ```
   Calle Mayor 14, Madrid, Plaza España, Madrid, Gran Via 50, Madrid
   ```
   Expected error: "Could not find any addresses. Please send addresses one per line or as a numbered list."

---

## Implementation Order

1. ✅ **address_parser.py** - Core parsing logic (most important)
2. ✅ **message_processor.py** - User-facing example command
3. ✅ **MESSAGES_REFERENCE.md** - Documentation update
4. ✅ **Test files** - Update or remove comma tests (optional)

---

## Approval Checklist

Before implementing, verify:
- [ ] All affected files identified
- [ ] All line numbers confirmed
- [ ] Replacement text reviewed
- [ ] Testing plan clear
- [ ] User approves changes

**Status:** ⏳ **AWAITING USER APPROVAL**
