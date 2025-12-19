#!/usr/bin/env python3
"""
Diagnose .env DATABASE_URL issues
Run from backend directory: python diagnose_env.py
"""
import os
from pathlib import Path
from urllib.parse import urlparse

# Load .env file
env_path = Path('.env')
if not env_path.exists():
    print("❌ .env file not found!")
    print("   Expected location: backend/.env")
    exit(1)

# Parse .env
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key] = value

if 'DATABASE_URL' not in env_vars:
    print("❌ DATABASE_URL not found in .env file!")
    exit(1)

db_url = env_vars['DATABASE_URL']

print("🔍 Analyzing your DATABASE_URL...")
print("="*70)
print()

# Parse the URL
try:
    parsed = urlparse(db_url)
    
    print(f"Protocol: {parsed.scheme}")
    print(f"Username: {parsed.username}")
    print(f"Password: {'*' * len(parsed.password) if parsed.password else '[MISSING]'}")
    print(f"Host: {parsed.hostname}")
    print(f"Port: {parsed.port}")
    print(f"Database: {parsed.path[1:] if parsed.path else '[MISSING]'}")
    print()
    print("="*70)
    print()
    
    # Check for common issues
    issues = []
    fixes = []
    
    # Check username format
    if parsed.username and not parsed.username.startswith('postgres.'):
        issues.append("❌ Username should be 'postgres.poozqsmqjkmyyugibbfv' not just 'postgres'")
        fixes.append("Change username to: postgres.poozqsmqjkmyyugibbfv")
    elif parsed.username == 'postgres.poozqsmqjkmyyugibbfv':
        print("✅ Username format is correct!")
    else:
        issues.append(f"❌ Username '{parsed.username}' doesn't look right")
        fixes.append("Change username to: postgres.poozqsmqjkmyyugibbfv")
    
    # Check password
    if not parsed.password or parsed.password in ['password', 'your-password', '[YOUR-PASSWORD]', 'xxxxx']:
        issues.append("❌ Password appears to be a placeholder")
        fixes.append("Go to Supabase Dashboard → Database → Reset Database Password")
    else:
        print("✅ Password is set (not a placeholder)")
    
    # Check port
    if parsed.port != 5432:
        issues.append(f"❌ Port should be 5432, not {parsed.port}")
        fixes.append("Change port to: 5432")
    else:
        print("✅ Port is correct (5432)")
    
    # Check host
    if parsed.hostname != 'aws-0-eu-central-1.pooler.supabase.com':
        issues.append(f"⚠️  Host '{parsed.hostname}' might be incorrect")
        fixes.append("Expected host: aws-0-eu-central-1.pooler.supabase.com")
    else:
        print("✅ Host is correct")
    
    # Check database name
    db_name = parsed.path[1:] if parsed.path else ''
    if db_name != 'postgres':
        issues.append(f"❌ Database should be 'postgres', not '{db_name}'")
        fixes.append("Change database to: postgres")
    else:
        print("✅ Database name is correct")
    
    print()
    
    if issues:
        print("🔴 ISSUES FOUND:")
        print("="*70)
        for issue in issues:
            print(issue)
        print()
        print("🔧 FIXES NEEDED:")
        print("="*70)
        for fix in fixes:
            print(f"  • {fix}")
        print()
        print("="*70)
        print()
        print("📝 CORRECT FORMAT:")
        print("="*70)
        print("DATABASE_URL=postgresql://postgres.poozqsmqjkmyyugibbfv:YOUR-ACTUAL-PASSWORD@aws-0-eu-central-1.pooler.supabase.com:5432/postgres")
        print()
        print("Get YOUR-ACTUAL-PASSWORD from:")
        print("  Supabase Dashboard → Project Settings → Database")
        print("  Click 'Reset Database Password' if you forgot it")
        print()
    else:
        print("✅ All format checks passed!")
        print()
        print("If you're still getting 'Tenant or user not found':")
        print("  1. Your password might be wrong → Reset it in Supabase")
        print("  2. Try copying the connection string directly from Supabase:")
        print("     Dashboard → Database → Connection string → URI → Session mode")
        print()

except Exception as e:
    print(f"❌ Error parsing DATABASE_URL: {e}")
    print()
    print("Your DATABASE_URL might be malformed.")
    print()
    print("📝 CORRECT FORMAT:")
    print("DATABASE_URL=postgresql://postgres.poozqsmqjkmyyugibbfv:YOUR-PASSWORD@aws-0-eu-central-1.pooler.supabase.com:5432/postgres")
    print()