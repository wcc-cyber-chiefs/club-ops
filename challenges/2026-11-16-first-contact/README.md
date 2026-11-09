# First Contact

We intercepted a message dropped for a field agent. It's been wrapped in two layers of encoding, neither of which is real encryption. Peel both layers and you'll find the proof-of-contact flag.

**File:** `files/intercepted.txt`

**Flag format:** `WCC{...}`

**Hints (try without them first):**
- The block of text ends with `=` characters. What encoding pads like that?
- After the first layer, the words look like English that's been shifted. How far?
- [CyberChef](https://gchq.github.io/CyberChef/) can do both layers without writing any code.
