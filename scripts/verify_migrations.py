#!/usr/bin/env python3
"""Verify that database migrations were applied successfully"""

import os
import sys

def load_env():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_vars = {}

    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

    return env_vars

def main():
    print("=" * 70)
    print("Verifying Database Migrations")
    print("=" * 70)
    print()

    # Load credentials
    env_vars = load_env()
    supabase_url = env_vars.get('SUPABASE_URL', os.getenv('SUPABASE_URL'))
    service_key = env_vars.get('SUPABASE_SERVICE_KEY', os.getenv('SUPABASE_SERVICE_KEY'))

    if not supabase_url or not service_key:
        print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not found")
        sys.exit(1)

    print(f"📡 Connecting to: {supabase_url}")
    print()

    # Test with httpx (simpler than supabase-py for REST)
    try:
        import httpx
    except ImportError:
        print("⚠️  httpx not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
        import httpx

    # Expected tables
    expected_tables = ['agent_jobs', 'agent_decisions', 'audit_log', 'rate_limits']

    print("🔍 Checking for required tables...")
    print()

    # Try to query each table
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }

    found_tables = []
    missing_tables = []

    with httpx.Client(timeout=10.0) as client:
        for table in expected_tables:
            url = f"{supabase_url}/rest/v1/{table}?limit=0"

            try:
                response = client.get(url, headers=headers)

                if response.status_code == 200:
                    print(f"  ✅ {table:20s} - EXISTS")
                    found_tables.append(table)
                elif response.status_code == 404:
                    print(f"  ❌ {table:20s} - NOT FOUND")
                    missing_tables.append(table)
                else:
                    print(f"  ⚠️  {table:20s} - Status {response.status_code}")
                    missing_tables.append(table)

            except Exception as e:
                print(f"  ❌ {table:20s} - Error: {str(e)[:50]}")
                missing_tables.append(table)

    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    if len(found_tables) == len(expected_tables):
        print("🎉 SUCCESS! All migrations applied")
        print()
        print("Tables created:")
        for table in found_tables:
            print(f"  ✅ {table}")
        print()
        print("✅ Your database is ready!")
        print("✅ You can now use the qualification API")
        print()
        print("Test it:")
        print("  curl http://localhost:8080/api/agents/claude/invoke-sync \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{...}'")
        print()
        return 0

    else:
        print("⚠️  INCOMPLETE - Some tables are missing")
        print()

        if found_tables:
            print("Found:")
            for table in found_tables:
                print(f"  ✅ {table}")
            print()

        if missing_tables:
            print("Missing:")
            for table in missing_tables:
                print(f"  ❌ {table}")
            print()

        print("📋 To apply migrations:")
        print()
        print("1. Go to: https://supabase.com/dashboard/project/bvnllbpqstcrynehjvan/editor")
        print("2. Run: python3 scripts/apply_migrations.py")
        print("   (Follow the instructions)")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
