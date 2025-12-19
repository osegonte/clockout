#!/usr/bin/env python3
"""
Debug backend configuration step by step
Run from backend directory: python3 debug_backend.py
"""
import os
import sys
from pathlib import Path

print("🔍 Backend Configuration Debugger")
print("="*70)
print()

# Step 1: Check .env file exists
print("1️⃣ Checking .env file...")
env_path = Path('.env')
if env_path.exists():
    print(f"   ✅ .env file found at: {env_path.absolute()}")
    print(f"   📏 File size: {env_path.stat().st_size} bytes")
else:
    print(f"   ❌ .env file NOT FOUND at: {env_path.absolute()}")
    print("   → Create .env file in backend/ directory")
    sys.exit(1)

print()

# Step 2: Read .env file raw
print("2️⃣ Reading .env file (raw)...")
with open(env_path, 'r') as f:
    content = f.read()
    lines = content.split('\n')
    print(f"   📄 Total lines: {len(lines)}")
    print(f"   📝 Content preview:")
    for i, line in enumerate(lines[:10], 1):  # Show first 10 lines
        if line.strip() and not line.startswith('#'):
            if 'DATABASE_URL' in line:
                # Mask password
                if '=' in line:
                    key, value = line.split('=', 1)
                    print(f"      Line {i}: {key}=[VALUE HIDDEN]")
            elif 'SECRET_KEY' in line or 'PASSWORD' in line:
                print(f"      Line {i}: [SENSITIVE - HIDDEN]")
            else:
                print(f"      Line {i}: {line}")

print()

# Step 3: Load environment with dotenv
print("3️⃣ Loading environment variables...")
try:
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print("   ✅ dotenv loaded successfully")
except ImportError:
    print("   ❌ python-dotenv not installed")
    print("   → Run: pip install python-dotenv")
    sys.exit(1)

print()

# Step 4: Check DATABASE_URL
print("4️⃣ Checking DATABASE_URL...")
db_url = os.getenv('DATABASE_URL')
if db_url:
    print("   ✅ DATABASE_URL is set")
    print(f"   📏 Length: {len(db_url)} characters")
    
    # Check for common issues
    issues = []
    
    # Check for leading/trailing whitespace
    if db_url != db_url.strip():
        issues.append("⚠️  DATABASE_URL has leading/trailing whitespace")
        db_url = db_url.strip()
    
    # Check for quotes
    if db_url.startswith('"') or db_url.startswith("'"):
        issues.append("⚠️  DATABASE_URL is wrapped in quotes")
    
    # Parse URL
    from urllib.parse import urlparse
    try:
        parsed = urlparse(db_url)
        print(f"   🔗 Protocol: {parsed.scheme}")
        print(f"   👤 Username: {parsed.username}")
        print(f"   🔑 Password: {'*' * min(len(parsed.password), 20) if parsed.password else '[MISSING]'}")
        print(f"   🌐 Host: {parsed.hostname}")
        print(f"   🔌 Port: {parsed.port}")
        print(f"   💾 Database: {parsed.path[1:] if parsed.path else '[MISSING]'}")
        
        # Additional checks
        if parsed.scheme != 'postgresql':
            issues.append(f"⚠️  Protocol should be 'postgresql', not '{parsed.scheme}'")
        
        if not parsed.username or not parsed.username.startswith('postgres.'):
            issues.append("⚠️  Username should start with 'postgres.'")
        
        if parsed.port != 5432:
            issues.append(f"⚠️  Port should be 5432, not {parsed.port}")
        
        if not parsed.password or parsed.password in ['password', '[YOUR-PASSWORD]', 'xxxxx']:
            issues.append("❌ Password is a placeholder")
    
    except Exception as e:
        issues.append(f"❌ Failed to parse DATABASE_URL: {e}")
    
    if issues:
        print()
        print("   🔴 ISSUES FOUND:")
        for issue in issues:
            print(f"      {issue}")
else:
    print("   ❌ DATABASE_URL not set in environment")
    sys.exit(1)

print()

# Step 5: Check other required variables
print("5️⃣ Checking other environment variables...")
required_vars = ['SECRET_KEY', 'ALGORITHM']
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"   ✅ {var}: Set ({len(value)} chars)")
    else:
        print(f"   ⚠️  {var}: Not set (will use default)")

print()

# Step 6: Test pydantic-settings loading
print("6️⃣ Testing pydantic-settings (how FastAPI loads config)...")
try:
    sys.path.insert(0, str(Path('.').absolute()))
    from app.core.config import settings
    
    print("   ✅ Settings loaded successfully")
    print(f"   📊 PROJECT_NAME: {settings.PROJECT_NAME}")
    print(f"   🔗 API_V1_STR: {settings.API_V1_STR}")
    print(f"   🔑 SECRET_KEY: {'*' * 10} ({len(settings.SECRET_KEY)} chars)")
    print(f"   💾 DATABASE_URL: {'*' * 20}... ({len(settings.DATABASE_URL)} chars)")
    
    # Check if loaded URL matches env URL
    if settings.DATABASE_URL == db_url:
        print("   ✅ DATABASE_URL matches environment")
    else:
        print("   ⚠️  DATABASE_URL differs from environment!")
        print(f"      Env length: {len(db_url)}")
        print(f"      Settings length: {len(settings.DATABASE_URL)}")
        
except Exception as e:
    print(f"   ❌ Failed to load settings: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Step 7: Test database connection
print("7️⃣ Testing database connection...")
try:
    import psycopg2
    print("   🔌 Attempting connection...")
    conn = psycopg2.connect(settings.DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"   ✅ CONNECTION SUCCESSFUL!")
    print(f"   📊 PostgreSQL: {version[:60]}...")
    cursor.close()
    conn.close()
except psycopg2.OperationalError as e:
    print(f"   ❌ CONNECTION FAILED!")
    print(f"   📋 Error: {str(e)[:200]}")
    
    if "Tenant or user not found" in str(e):
        print()
        print("   💡 This error means:")
        print("      • Username is wrong (should be postgres.PROJECT-ID)")
        print("      • OR password is wrong")
        print("      • OR Supabase project doesn't exist")
        print()
        print("   🔧 Try this:")
        print("      1. Go to Supabase dashboard")
        print("      2. Reset database password")
        print("      3. Copy the Session mode connection string")
        print("      4. Update backend/.env")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Unexpected error: {e}")
    sys.exit(1)

print()

# Step 8: Test SQLAlchemy engine
print("8️⃣ Testing SQLAlchemy engine (how FastAPI uses database)...")
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_database();"))
        db_name = result.scalar()
        print(f"   ✅ SQLAlchemy connection successful!")
        print(f"   💾 Database: {db_name}")
except Exception as e:
    print(f"   ❌ SQLAlchemy failed: {e}")
    sys.exit(1)

print()
print("="*70)
print("✅ ALL CHECKS PASSED!")
print("="*70)
print()
print("🎉 Your backend configuration is correct!")
print()
print("🚀 Next steps:")
print("   1. Run: python3 seed.py")
print("   2. Run: uvicorn app.main:app --reload")
print()