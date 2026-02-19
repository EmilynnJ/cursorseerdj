#!/usr/bin/env python
"""
Fly.io deployment script.
Handles migrations and static files collection.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soulseer.settings')
django.setup()

from django.core.management import call_command


def main():
    """Run deployment tasks."""
    print("=" * 50)
    print("SoulSeer Fly.io Deployment")
    print("=" * 50)
    
    # Run migrations
    print("\n[1/3] Running database migrations...")
    try:
        call_command('migrate', '--noinput', verbosity=2)
        print("✓ Migrations completed successfully")
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)
    
    # Collect static files
    print("\n[2/3] Collecting static files...")
    try:
        call_command('collectstatic', '--noinput', verbosity=2)
        print("✓ Static files collected successfully")
    except Exception as e:
        print(f"✗ Static collection failed: {e}")
        sys.exit(1)
    
    # Verify database connection
    print("\n[3/3] Verifying database connection...")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        print("✓ Database connection verified")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Deployment preparation complete!")
    print("=" * 50)
    return 0


if __name__ == '__main__':
    sys.exit(main())