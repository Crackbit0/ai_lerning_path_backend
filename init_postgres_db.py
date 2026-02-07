"""
Initialize PostgreSQL database with all tables.
Run this once after setting up your Neon/Supabase PostgreSQL database.

Usage:
    1. Set DATABASE_URL environment variable
    2. Run: python init_postgres_db.py
"""
from web_app import create_app, db
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("❌ DATABASE_URL environment variable is not set!")
    print("\nTo set up a free PostgreSQL database:")
    print("1. Go to https://neon.tech (or https://supabase.com)")
    print("2. Create a free account and new project")
    print("3. Copy the connection string")
    print("4. Set it as DATABASE_URL in your environment or .env file")
    print("\nExample:")
    print("DATABASE_URL=postgresql://user:password@hostname/database?sslmode=require")
    sys.exit(1)

# Fix postgres:// to postgresql:// if needed
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
    os.environ['DATABASE_URL'] = database_url

print(f"🔗 Connecting to database...")
print(
    f"   Host: {database_url.split('@')[1].split('/')[0] if '@' in database_url else 'local'}")

# Now import Flask app

app = create_app()

with app.app_context():
    print("📦 Creating all database tables...")

    # Import models to ensure they're registered
    from web_app.models import (
        User, UserLearningPath, LearningProgress,
        ResourceProgress, MilestoneProgress,
        ChatMessage, PathModification, ConversationSession, OAuth
    )

    # Create all tables
    db.create_all()

    print("✅ Database tables created successfully!")

    # Show created tables
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"\n📋 Tables in database ({len(tables)}):")
    for table in tables:
        print(f"   - {table}")

    # Check if there are any users
    user_count = User.query.count()
    print(f"\n👥 Current users in database: {user_count}")

    if user_count == 0:
        print("\n💡 No users yet. Users will be created when they register via the app.")

    print("\n🎉 Database initialization complete!")
    print("   Your app is now ready to use persistent PostgreSQL storage.")
