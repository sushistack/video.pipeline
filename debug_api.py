#!/usr/bin/env python3
"""Debug API Key Issue"""

import os
from dotenv import load_dotenv
load_dotenv('.env', override=True)

gemini_key = os.getenv("GEMINI_API_KEY")
print(f"API Key: {gemini_key[:15]}...{gemini_key[-5:]}")
print(f"Key Length: {len(gemini_key)}")

# Check key format
if gemini_key.startswith("AIza"):
    print("✓ Key format looks correct (starts with AIza)")
else:
    print("✗ Key format unusual (should start with AIza)")

# Try with explicit client initialization
from google import genai
print("\nInitializing client with explicit key...")
client = genai.Client(api_key=gemini_key)

print("Testing with simple content...")
try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Hello",
    )
    print(f"✓ Success! Response: {response.text[:50]}")
except Exception as e:
    print(f"✗ Failed: {e}")
    if "expired" in str(e).lower():
        print("\n⚠️  This API key is expired/invalid")
        print("   Possible reasons:")
        print("   1. Key was revoked")
        print("   2. Key has usage restrictions")
        print("   3. Key is for a different Google Cloud project")
        print("   4. Billing is not enabled")
        print("   5. API is not enabled for your project")
