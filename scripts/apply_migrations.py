#!/usr/bin/env python3
"""Apply database migrations to Supabase"""

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
    print("Applying Database Migrations to Supabase")
    print("=" * 70)
    print()

    # Load credentials
    env_vars = load_env()
    supabase_url = env_vars.get('SUPABASE_URL', os.getenv('SUPABASE_URL'))
    service_key = env_vars.get('SUPABASE_SERVICE_KEY', os.getenv('SUPABASE_SERVICE_KEY'))

    if not supabase_url or not service_key:
        print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not found")
        print()
        print("Please ensure .env file contains:")
        print("  SUPABASE_URL=https://your-project.supabase.co")
        print("  SUPABASE_SERVICE_KEY=your-service-key")
        sys.exit(1)

    print(f"📡 Supabase URL: {supabase_url}")
    print()

    # Read migration file
    migration_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'supabase/migrations/000_combined_migrations.sql'
    )

    if not os.path.exists(migration_path):
        print(f"❌ Migration file not found: {migration_path}")
        sys.exit(1)

    with open(migration_path, 'r') as f:
        migration_sql = f.read()

    print(f"📄 Migration file: {len(migration_sql)} bytes")
    print()

    # Apply migrations via Supabase SQL API
    print("🔄 Attempting to apply migrations...")
    print()

    # Note: Supabase doesn't have a direct REST API endpoint for running arbitrary SQL
    # The best approach is via the Supabase Dashboard SQL Editor

    print("⚠️  Supabase doesn't support direct SQL execution via REST API")
    print("    (This is a security feature)")
    print()
    print("✅ MANUAL APPLICATION REQUIRED")
    print()
    print("Please follow these steps:")
    print()
    print("1. Go to Supabase Dashboard:")
    print(f"   {supabase_url.replace('https://', 'https://supabase.com/dashboard/project/')}")
    print()
    print("2. Navigate to: SQL Editor")
    print()
    print("3. Click: 'New Query'")
    print()
    print("4. Copy the migration SQL:")
    print(f"   cat {migration_path}")
    print()
    print("5. Paste into SQL Editor")
    print()
    print("6. Click: 'Run'")
    print()
    print("7. Verify tables created:")
    print("   SELECT tablename FROM pg_tables")
    print("   WHERE schemaname = 'public'")
    print("   AND tablename IN ('agent_jobs', 'agent_decisions', 'audit_log', 'rate_limits');")
    print()
    print("=" * 70)
    print()
    print("📋 Alternative: Copy SQL to clipboard")
    print()

    # Try to copy to clipboard if possible
    try:
        import pyperclip
        pyperclip.copy(migration_sql)
        print("✅ Migration SQL copied to clipboard!")
        print("   Just paste it into the Supabase SQL Editor")
    except ImportError:
        print("💡 Install pyperclip to auto-copy SQL:")
        print("   pip install pyperclip")

    print()
    print("=" * 70)

    return 0

if __name__ == "__main__":
    sys.exit(main())
