# Round Trip Support Documentation

## Overview

The WhatsApp Route Optimizer now supports **round trip routes** where the first and last address are the same, allowing users to plan routes that return to the starting point.

## How It Works

### 1. Address Parsing (address_parser.py)

When addresses are parsed:
- The system detects if the first and last address are the same (case-insensitive)
- If it's a round trip, the last address is **preserved** (not treated as a duplicate)
- Middle waypoints are still deduplicated to prevent routing errors
- Users see a log message: "Round trip detected - keeping return to start"

### 2. Route Optimization (route_optimizer_bridge.py)

When optimizing the route:
- The system detects the round trip condition
- The duplicate last address is **temporarily removed** before sending to Google's API
- Google optimizes the route without the duplicate
- The starting address is **added back** at the end of both original and optimized routes
- This ensures Google treats it as a proper route optimization, not a duplicate waypoint

## Examples

### Valid Round Trip

**Input:**
```
Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle de López de Hoyos 89
Calle del General Pardiñas 45
```

**Result:**
- ✅ All 5 addresses preserved (including return to start)
- ✅ Route starts and ends at Calle del General Pardiñas 45
- ✅ Middle waypoints optimized by Google Maps

**Output:**
```
1. Calle del General Pardiñas 45 (START)
2. [Optimized waypoints...]
5. Calle del General Pardiñas 45 (RETURN)
```

### Round Trip with Duplicate Middle Waypoint

**Input:**
```
Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle Santa Engracia 79          ← Duplicate middle waypoint
Calle de López de Hoyos 89
Calle del General Pardiñas 45    ← Valid round trip return
```

**Result:**
- ✅ Duplicate middle waypoint removed (position 4)
- ✅ Round trip preserved (first and last kept)
- ✅ Final route has 5 addresses

**Output:**
```
1. Calle del General Pardiñas 45 (START)
2. Calle Santa Engracia 79
3. Calle de Bravo Murillo 185
4. Calle de López de Hoyos 89
5. Calle del General Pardiñas 45 (RETURN)
```

### Not a Round Trip (Last Address is Duplicate of Middle)

**Input:**
```
Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle de López de Hoyos 89
Calle de López de Hoyos 89        ← NOT a round trip, just a duplicate
```

**Result:**
- ✅ Duplicate removed (not first address, so not a round trip)
- ✅ Final route has 4 unique addresses

**Output:**
```
1. Calle del General Pardiñas 45
2. Calle Santa Engracia 79
3. Calle de Bravo Murillo 185
4. Calle de López de Hoyos 89
```

## Case Insensitivity

Round trip detection is **case-insensitive**:

**Input:**
```
Calle del General Pardiñas 45
Calle Santa Engracia 79
CALLE DEL GENERAL PARDIÑAS 45    ← Different case, still detected
```

**Result:**
- ✅ Recognized as round trip despite case difference
- ✅ Both addresses preserved

## Rules

### What is Allowed:
1. ✅ **First and last address can be the same** (round trip)
2. ✅ Round trip detection is case-insensitive
3. ✅ Round trips work with any number of middle waypoints (min 1, max 24)

### What is NOT Allowed:
1. ❌ **Duplicate addresses in middle waypoints** (automatically removed)
2. ❌ Duplicate of last address that is NOT the first address (removed as duplicate)

## Implementation Details

### Files Modified:

1. **wab/app/address_parser.py** (Lines 84-123)
   - Detects round trips by comparing first and last normalized addresses
   - Preserves last address if it matches first
   - Removes duplicates from all other positions
   - Logs: "Round trip detected - keeping return to start"

2. **wab/integration/route_optimizer_bridge.py** (Lines 54-86)
   - Detects round trip before calling Google API
   - Temporarily removes duplicate last address
   - Optimizes route with unique addresses only
   - Adds starting address back at the end
   - Logs: "Round trip detected - optimizing X unique stops, will add return to start"

### Why This Approach?

Google's Directions API uses the pattern: `origin → waypoints → destination`

When we send a round trip like this:
```
Origin: Address A
Waypoints: [B, C, D, A]
Destination: A (the last waypoint)
```

Google treats the last waypoint as a separate stop and may place it incorrectly in the optimized route.

**Our solution:**
```
Origin: Address A
Waypoints: [B, C, D]
Destination: D (optimize waypoint order)
Then manually append: A (back at the end)
```

This ensures:
- Google optimizes the middle waypoints correctly
- The route properly starts and ends at the same location
- Distance/duration calculations are accurate

## Testing

Run the test suite to verify round trip functionality:

```bash
# Test address parsing with round trips
python wab/examples/test_round_trip.py

# Test full route optimization with round trips
python wab/examples/test_round_trip_route.py
```

### Test Coverage:

- ✅ Valid round trip (first and last same)
- ✅ Duplicate in middle waypoints (removed, round trip kept)
- ✅ Not a round trip (duplicate last removed)
- ✅ Case insensitive round trip detection
- ✅ Multiple middle duplicates with round trip
- ✅ Normal route (no duplicates)
- ✅ Full end-to-end route optimization with round trip

## User Experience

### WhatsApp Message Example:

**User sends:**
```
Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle de López de Hoyos 89
Calle del General Pardiñas 45
```

**Bot responds:**
```
✅ Optimización de ruta exitosa!

🗺️ Ruta optimizada:
1. Calle del General Pardiñas 45
2. Calle de Príncipe de Vergara 56
3. Calle de Diego de León 47
4. Calle Santa Engracia 79
5. Calle del General Pardiñas 45

📏 Distancia: 14.97 km
⏱️ Tiempo: 25 minutos
⛽ Combustible: 1.20 L
💰 Coste de combustible: €2.40

📍 Ver en Google Maps:
[link]
```

### Logs (for debugging):

```
INFO - Round trip detected - keeping return to start: Calle del General Pardiñas 45
INFO - Successfully parsed 5 addresses (round trip detected)
INFO - Optimizing route for 5 addresses
INFO - Round trip detected - optimizing 4 unique stops, will add return to start
INFO - Added return to start: Calle del General Pardiñas 45
INFO - Route optimized successfully - Distance: 14.97km
```

## Edge Cases Handled

1. **Minimum addresses for round trip:** 2 (same address twice = immediate return)
2. **Maximum addresses:** 26 (25 waypoints + return to start)
3. **All addresses are the same:** Detected and only first kept
4. **Case variations:** "Calle ABC" and "CALLE ABC" detected as same
5. **Extra whitespace:** Normalized before comparison
6. **Mixed duplicates:** Middle duplicates removed, round trip preserved

## Limitations

- Round trips only work when **first and last address are identical**
- Cannot create multi-leg trips (A → B → C → A → D)
- Google's distance/duration doesn't include time to park or reload
- Maximum 26 total stops (Google API limitation)
