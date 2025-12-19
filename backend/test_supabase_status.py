#!/usr/bin/env python3
"""
Test if your Supabase project is active and accessible
Run from backend directory: python3 test_supabase_status.py
"""
import socket
import urllib.request
import urllib.error
import json

PROJECT_ID = "poozqsmqjkmyyugibbfv"
HOST = "aws-0-eu-central-1.pooler.supabase.com"
PORT = 5432

print("🔍 Testing Supabase Project Status")
print("="*70)
print(f"Project ID: {PROJECT_ID}")
print(f"Host: {HOST}")
print(f"Port: {PORT}")
print()

# Test 1: Check if host is reachable
print("1️⃣ Testing network connectivity...")
try:
    socket.create_connection((HOST, PORT), timeout=5)
    print(f"✅ Can reach {HOST}:{PORT}")
except socket.timeout:
    print(f"❌ Timeout connecting to {HOST}:{PORT}")
    print("   → Check your internet connection")
except socket.error as e:
    print(f"❌ Cannot connect to {HOST}:{PORT}")
    print(f"   → Error: {e}")

print()

# Test 2: Check if Supabase project is active via API
print("2️⃣ Checking if Supabase project exists...")
try:
    # Try to access the Supabase project health endpoint
    health_url = f"https://{PROJECT_ID}.supabase.co/rest/v1/"
    req = urllib.request.Request(health_url, method='HEAD')
    response = urllib.request.urlopen(req, timeout=5)
    print(f"✅ Project is active and responding")
except urllib.error.HTTPError as e:
    if e.code == 401 or e.code == 403:
        print(f"✅ Project exists (got {e.code} - normal without API key)")
    else:
        print(f"⚠️  Got HTTP {e.code} - project might be inactive")
except urllib.error.URLError as e:
    print(f"❌ Cannot reach project endpoint")
    print(f"   → Project might be paused or deleted")
    print(f"   → Error: {e}")
except Exception as e:
    print(f"⚠️  Could not verify project status: {e}")

print()
print("="*70)
print()

# Instructions
print("🔧 NEXT STEPS:")
print()
print("If project is paused:")
print("  1. Go to: https://supabase.com/dashboard/project/poozqsmqjkmyyugibbfv")
print("  2. Click 'Resume Project' if you see that option")
print("  3. Wait 1-2 minutes for it to wake up")
print()
print("If project is active but still failing:")
print("  1. Go to: https://supabase.com/dashboard/project/poozqsmqjkmyyugibbfv/database/settings")
print("  2. Click 'Reset Database Password'")
print("  3. Copy the NEW password")
print("  4. Update backend/.env with the new password")
print("  5. Try starting the server again")
print()
print("OR switch to your GitHub-connected Supabase:")
print("  → Follow the instructions in MIGRATE_TO_NEW_SUPABASE.md")