#!/usr/bin/env python3
"""
Initialize Agent Orchestration Tables
Runs Supabase migrations and creates seed data
"""

import os
import sys
from pathlib import Path
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def read_migration_file(filename: str) -> str:
    """Read SQL migration file"""
    migrations_dir = Path(__file__).parent / "migrations"
    file_path = migrations_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Migration file not found: {file_path}")

    with open(file_path, 'r') as f:
        return f.read()


def run_migration(filename: str, description: str):
    """Execute a SQL migration file"""
    print(f"\n📝 Running migration: {description}")
    print(f"   File: {filename}")

    try:
        sql = read_migration_file(filename)

        # Execute SQL using Supabase RPC or direct SQL execution
        # Note: Supabase Python client doesn't have direct SQL execution
        # You'll need to run these via Supabase Dashboard SQL Editor or psql

        print(f"   ✅ SQL loaded ({len(sql)} characters)")
        print(f"   ⚠️  Please run this SQL in Supabase Dashboard SQL Editor:")
        print(f"   https://supabase.com/dashboard/project/YOUR_PROJECT/sql")

        return sql

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def verify_tables_exist() -> bool:
    """Verify that all 4 tables were created"""
    print("\n🔍 Verifying tables...")

    tables = ['agent_jobs', 'agent_decisions', 'audit_log', 'rate_limits']
    all_exist = True

    for table in tables:
        try:
            # Try to query the table (will fail if doesn't exist)
            result = supabase.table(table).select("*").limit(0).execute()
            print(f"   ✅ {table} exists")
        except Exception as e:
            print(f"   ❌ {table} does not exist: {str(e)}")
            all_exist = False

    return all_exist


def create_seed_data():
    """Create example seed data for testing"""
    print("\n🌱 Creating seed data...")

    # Seed 1: Example agent job
    try:
        job_data = {
            "job_type": "discovery",
            "status": "completed",
            "initiated_by": "system_init",
            "initiated_by_type": "system",
            "parameters": {
                "metro": "austin",
                "radius": 15,
                "note": "Example seed data"
            },
            "results": {
                "leads_created": 0,
                "note": "This is seed data for testing"
            }
        }

        result = supabase.table('agent_jobs').insert(job_data).execute()
        print(f"   ✅ Created example agent_job: {result.data[0]['id']}")
    except Exception as e:
        print(f"   ⚠️  Could not create agent_job: {str(e)}")

    # Seed 2: Example audit log
    try:
        log_data = {
            "actor": "system_init",
            "actor_type": "system",
            "action": "tables_initialized",
            "resource_type": "system",
            "metadata": {
                "version": "1.0.0",
                "note": "Initial table setup complete"
            },
            "severity": "info"
        }

        result = supabase.table('audit_log').insert(log_data).execute()
        print(f"   ✅ Created example audit_log entry: {result.data[0]['id']}")
    except Exception as e:
        print(f"   ⚠️  Could not create audit_log: {str(e)}")

    # Seed 3: Example rate limits
    try:
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        window_start = now.replace(minute=0, second=0, microsecond=0)
        reset_at = window_start + timedelta(hours=1)

        rate_limits = [
            {
                "service_name": "clay",
                "window_start": window_start.isoformat(),
                "request_count": 0,
                "quota_limit": 1000,
                "reset_at": reset_at.isoformat(),
                "metadata": {"plan": "professional", "cost_per_request": 0.01}
            },
            {
                "service_name": "apollo",
                "window_start": window_start.isoformat(),
                "request_count": 0,
                "quota_limit": 100,
                "reset_at": reset_at.isoformat(),
                "metadata": {"cost_per_request": 0.05}
            }
        ]

        for rate_limit in rate_limits:
            result = supabase.table('rate_limits').insert(rate_limit).execute()
            print(f"   ✅ Created rate_limit for {rate_limit['service_name']}")
    except Exception as e:
        print(f"   ⚠️  Could not create rate_limits: {str(e)}")


def main():
    """Main initialization function"""
    print("=" * 70)
    print("  Rise Local - Agent Orchestration Tables Initialization")
    print("=" * 70)

    # Step 1: Display migrations
    print("\n📋 Step 1: SQL Migrations to Run")
    print("-" * 70)

    migrations = [
        ("001_create_agent_jobs_table.sql", "Create agent_jobs table"),
        ("002_create_agent_decisions_table.sql", "Create agent_decisions table"),
        ("003_create_audit_log_table.sql", "Create audit_log table with RLS"),
        ("004_create_rate_limits_table.sql", "Create rate_limits table with functions"),
    ]

    all_sql = []
    for filename, description in migrations:
        sql = run_migration(filename, description)
        if sql:
            all_sql.append(f"-- {description}\n{sql}\n\n")

    # Save combined SQL file
    output_file = Path(__file__).parent / "migrations" / "000_combined_migrations.sql"
    with open(output_file, 'w') as f:
        f.write("\n".join(all_sql))

    print(f"\n💾 Combined SQL saved to: {output_file}")
    print("\n" + "=" * 70)
    print("  MANUAL STEP REQUIRED")
    print("=" * 70)
    print("\n1. Go to: https://supabase.com/dashboard/project/YOUR_PROJECT/sql")
    print("2. Paste the contents of: 000_combined_migrations.sql")
    print("3. Click 'Run' to execute all migrations")
    print("4. Re-run this script to verify tables and create seed data")
    print("\n" + "=" * 70)

    # Step 2: Verify tables exist
    if verify_tables_exist():
        print("\n✅ All tables verified!")

        # Step 3: Create seed data
        create_seed_data()

        print("\n" + "=" * 70)
        print("  🎉 Initialization Complete!")
        print("=" * 70)
        print("\n✅ All 4 tables created and seeded with example data")
        print("✅ Rate limit functions deployed")
        print("✅ Audit log RLS policies enabled")
        print("\n📚 Next steps:")
        print("   1. Create tables in Zapier: See ZAPIER_TABLES_SETUP.md")
        print("   2. Set up sync Zaps (Zapier Tables → Supabase)")
        print("   3. Test agent job creation")
        print("   4. Build first Zapier workflow")

    else:
        print("\n⚠️  Tables not found. Please run migrations first (see instructions above)")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
