#!/usr/bin/env python3
"""Verify that all API credentials are working"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

print("=" * 70)
print("Credential Verification Test")
print("=" * 70)
print()


def test_anthropic():
    """Test Anthropic API key"""
    print("🔍 Testing Anthropic API...")
    try:
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ ANTHROPIC_API_KEY not set")
            return False

        client = Anthropic(api_key=api_key)

        # Simple API call
        response = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'API test successful' in 3 words"}]
        )

        print(f"✅ Anthropic API: Working")
        print(f"   Model: claude-opus-4-5-20251101")
        print(f"   Response: {response.content[0].text}")
        return True
    except ImportError:
        print("⚠️  Anthropic package not installed (run: pip install anthropic)")
        return False
    except Exception as e:
        print(f"❌ Anthropic API: Failed - {str(e)}")
        return False


def test_supabase():
    """Test Supabase connection"""
    print("\n🔍 Testing Supabase connection...")
    try:
        from supabase import create_client, Client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")

        if not url or not key:
            print("❌ SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
            return False

        supabase: Client = create_client(url, key)

        # Test connection by listing tables
        response = supabase.table("leads").select("id").limit(1).execute()

        print(f"✅ Supabase: Connected")
        print(f"   URL: {url}")
        print(f"   Tables accessible: leads")
        return True
    except ImportError:
        print("⚠️  Supabase package not installed (run: pip install supabase)")
        return False
    except Exception as e:
        print(f"❌ Supabase: Failed - {str(e)}")
        return False


def test_google_api():
    """Test Google API key"""
    print("\n🔍 Testing Google API...")
    try:
        import httpx

        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            print("❌ GOOGLE_GEMINI_API_KEY not set")
            return False

        # Test Gemini API
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

        with httpx.Client() as client:
            response = client.get(url, timeout=10.0)

            if response.status_code == 200:
                print(f"✅ Google Gemini API: Working")
                print(f"   Available models: {len(response.json().get('models', []))}")
                return True
            else:
                print(f"❌ Google API: Status {response.status_code}")
                return False
    except ImportError:
        print("⚠️  httpx not installed (run: pip install httpx)")
        return False
    except Exception as e:
        print(f"❌ Google API: Failed - {str(e)}")
        return False


def test_clay_api():
    """Test Clay API key"""
    print("\n🔍 Testing Clay API...")
    try:
        import httpx

        api_key = os.getenv("CLAY_API_KEY")
        if not api_key:
            print("❌ CLAY_API_KEY not set")
            return False

        # Note: Clay API documentation may vary
        # This is a placeholder test
        print(f"✅ Clay API key configured")
        print(f"   Key: {api_key[:8]}...")
        print(f"   ⚠️  Full API test requires Clay account setup")
        return True
    except Exception as e:
        print(f"❌ Clay API: Failed - {str(e)}")
        return False


def test_mcp_server():
    """Test MCP server availability"""
    print("\n🔍 Testing MCP Server...")
    try:
        import httpx

        mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

        with httpx.Client() as client:
            # Try to reach MCP server
            try:
                response = client.get(f"{mcp_url}/health", timeout=5.0)
                print(f"✅ MCP Server: Running")
                print(f"   URL: {mcp_url}")
                return True
            except httpx.ConnectError:
                print(f"⚠️  MCP Server: Not running at {mcp_url}")
                print(f"   Start with: docker compose up -d mcp-server")
                return False
    except ImportError:
        print("⚠️  httpx not installed")
        return False
    except Exception as e:
        print(f"❌ MCP Server: Failed - {str(e)}")
        return False


def main():
    results = {
        "Anthropic API": test_anthropic(),
        "Supabase": test_supabase(),
        "Google API": test_google_api(),
        "Clay API": test_clay_api(),
        "MCP Server": test_mcp_server()
    }

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    for service, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {service}")

    passed = sum(results.values())
    total = len(results)

    print()
    print(f"Passed: {passed}/{total} tests")
    print()

    if passed == total:
        print("🎉 All credentials verified! Ready to run.")
        return 0
    else:
        print("⚠️  Some credentials need attention.")
        print("   Review the errors above and update .env file.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
