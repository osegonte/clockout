#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TESTING USERS & MANAGERS API${NC}"
echo -e "${BLUE}================================${NC}\n"

# Get authentication token (as admin)
echo -e "${BLUE}Step 1: Getting admin token...${NC}"
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@clockout.com&password=password123" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${RED}❌ Failed to get admin token!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Admin token obtained!${NC}\n"

# Test 1: List existing users
echo -e "${BLUE}Test 1: List All Users (Before creating new ones)${NC}"
curl -s "http://localhost:8000/api/v1/users/?organization_id=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 2: Create new manager
echo -e "${BLUE}Test 2: Create New Manager (manager3@farm.com)${NC}"
curl -s -X POST "http://localhost:8000/api/v1/users/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manager3@farm.com",
    "password": "password123",
    "full_name": "Manager Three",
    "role": "manager",
    "user_mode": "manager",
    "assigned_site_ids": [1, 2]
  }' | python3 -m json.tool
echo -e "\n"

# Test 3: List users again (should see new manager)
echo -e "${BLUE}Test 3: List All Users (After creating manager3)${NC}"
curl -s "http://localhost:8000/api/v1/users/?organization_id=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 4: Get specific user (manager1)
echo -e "${BLUE}Test 4: Get Specific User (manager1 - ID 2)${NC}"
curl -s "http://localhost:8000/api/v1/users/2" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 5: Update user
echo -e "${BLUE}Test 5: Update manager1's Full Name${NC}"
curl -s -X PUT "http://localhost:8000/api/v1/users/2" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Manager One (Updated)"
  }' | python3 -m json.tool
echo -e "\n"

# Test 6: Assign sites (change manager2's assignments)
# FIX: Changed from ID 3 to ID 4 (manager2's actual ID)
echo -e "${BLUE}Test 6: Reassign manager2 (ID 4) to both sites${NC}"
curl -s -X POST "http://localhost:8000/api/v1/users/4/assign-sites" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "site_ids": [1, 2]
  }' | python3 -m json.tool
echo -e "\n"

# Test 7: Create another manager
echo -e "${BLUE}Test 7: Create Manager 4 (assigned to site 2 only)${NC}"
curl -s -X POST "http://localhost:8000/api/v1/users/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manager4@farm.com",
    "password": "password123",
    "full_name": "Manager Four",
    "role": "manager",
    "user_mode": "manager",
    "assigned_site_ids": [2]
  }' | python3 -m json.tool
echo -e "\n"

# Test 8: Test login with new manager
echo -e "${BLUE}Test 8: Test Login with manager3${NC}"
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manager3@farm.com&password=password123" | python3 -m json.tool
echo -e "\n"

# Test 9: Delete a user (soft delete)
echo -e "${BLUE}Test 9: Delete manager4 (Soft Delete)${NC}"
# Dynamically get manager4's ID from the list
MANAGER4_ID=$(curl -s "http://localhost:8000/api/v1/users/?organization_id=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; users = json.load(sys.stdin); print(next((u['id'] for u in users if u['email'] == 'manager4@farm.com'), 'not_found'))")

if [ "$MANAGER4_ID" != "not_found" ]; then
    curl -s -X DELETE "http://localhost:8000/api/v1/users/$MANAGER4_ID" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
else
    echo "Manager4 not found"
fi
echo -e "\n"

# Test 10: Final user list (should not show deleted user)
echo -e "${BLUE}Test 10: Final User List (manager4 should be gone)${NC}"
curl -s "http://localhost:8000/api/v1/users/?organization_id=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}ALL TESTS COMPLETE!${NC}"
echo -e "${GREEN}================================${NC}"