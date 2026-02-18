#!/usr/bin/env python3
"""
API Key Test Script
Tests if the API key is loaded correctly and working with Gemini API.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
print(f"[*] Loading .env from: {env_path}")
print(f"[*] .env exists: {env_path.exists()}")

if env_path.exists():
    load_dotenv(env_path, override=True)  # Force override environment variables
    print("[+] .env loaded successfully (with override)\n")
else:
    print("[!] .env file not found!")
    sys.exit(1)

# Check API keys
print("=" * 60)
print("API KEY CHECK")
print("=" * 60)

# Clear any existing env vars to avoid conflicts
if 'GOOGLE_API_KEY' in os.environ:
    del os.environ['GOOGLE_API_KEY']
    print("[*] Cleared GOOGLE_API_KEY from environment")

# Reload .env to ensure we get the right key
load_dotenv(env_path, override=True)

gemini_key = os.getenv("GEMINI_API_KEY", "")
deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
dashscope_key = os.getenv("DASHSCOPE_API_KEY", "")

print(f"\n1. GEMINI_API_KEY:")
print(f"   Loaded: {bool(gemini_key)}")
print(f"   Length: {len(gemini_key)} chars")
print(f"   Preview: {gemini_key[:15]}...{gemini_key[-5:] if len(gemini_key) > 20 else ''}")

print(f"\n2. DEEPSEEK_API_KEY:")
print(f"   Loaded: {bool(deepseek_key)}")
print(f"   Length: {len(deepseek_key)} chars")
print(f"   Preview: {deepseek_key[:10]}...{deepseek_key[-5:] if len(deepseek_key) > 15 else ''}")

print(f"\n3. DASHSCOPE_API_KEY:")
print(f"   Loaded: {bool(dashscope_key)}")
print(f"   Length: {len(dashscope_key)} chars")
print(f"   Preview: {dashscope_key[:10]}...{dashscope_key[-5:] if len(dashscope_key) > 15 else ''}")

# Test Gemini API
print("\n" + "=" * 60)
print("GEMINI API TEST")
print("=" * 60)

if not gemini_key:
    print("\n[!] GEMINI_API_KEY is empty!")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types

    print("\n[*] Initializing Gemini client...")
    # Clear GOOGLE_API_KEY to avoid conflicts
    if 'GOOGLE_API_KEY' in os.environ:
        del os.environ['GOOGLE_API_KEY']
    
    client = genai.Client(api_key=gemini_key)

    print("[*] Sending test request to Gemini API...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Reply with only the word SUCCESS if you can read this.",
        config=types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=10,
        )
    )

    result = response.text.strip().upper() if response.text else ""
    print(f"\n[+] API Response: {result}")

    if "SUCCESS" in result:
        print("\n✅ GEMINI API KEY IS WORKING!")
    else:
        print("\n⚠️  API responded but unexpected result")

except Exception as e:
    print(f"\n[!] API Test Failed: {e}")

    if "PERMISSION_DENIED" in str(e) or "403" in str(e):
        print("\n❌ API KEY IS INVALID OR LEAKED!")
        print("   Please get a new API key from: https://aistudio.google.com/apikey")
    elif "API_KEY_NOT_FOUND" in str(e):
        print("\n❌ API KEY NOT FOUND!")
        print("   Check your .env file")
    else:
        print("\n⚠️  Unknown error - check your internet connection")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
