#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TESTING ORGANIZATIONS API${NC}"
echo -e "${BLUE}================================${NC}\n"

# Get authentication token
echo -e "${BLUE}Step 1: Getting authentication token...${NC}"
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@clockout.com&password=password123" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to get token!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Token obtained!${NC}\n"

# Test 1: Get organization
echo -e "${BLUE}Test 1: Get Organization Details${NC}"
curl -s "http://localhost:8000/api/v1/organizations/1" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 2: Update organization info
echo -e "${BLUE}Test 2: Update Organization Info${NC}"
curl -s -X PUT "http://localhost:8000/api/v1/organizations/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "owner_name": "John Administrator",
    "owner_email": "john@testfarm.com",
    "owner_phone": "+2348012345678"
  }' | python3 -m json.tool
echo -e "\n"

# Test 3: Get stats BEFORE upgrade
echo -e "${BLUE}Test 3: Get Stats (BEFORE upgrade)${NC}"
curl -s "http://localhost:8000/api/v1/organizations/1/stats" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 4: Upgrade to starter plan
echo -e "${BLUE}Test 4: Upgrade to Starter Plan${NC}"
curl -s -X PUT "http://localhost:8000/api/v1/organizations/1/plan" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "starter",
    "status": "active"
  }' | python3 -m json.tool
echo -e "\n"

# Test 5: Get stats AFTER upgrade
echo -e "${BLUE}Test 5: Get Stats (AFTER upgrade - should show new limits)${NC}"
curl -s "http://localhost:8000/api/v1/organizations/1/stats" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 6: Try upgrading to PRO
echo -e "${BLUE}Test 6: Upgrade to Pro Plan${NC}"
curl -s -X PUT "http://localhost:8000/api/v1/organizations/1/plan" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "pro",
    "status": "active"
  }' | python3 -m json.tool
echo -e "\n"

# Test 7: Final stats check
echo -e "${BLUE}Test 7: Final Stats (Should show PRO limits)${NC}"
curl -s "http://localhost:8000/api/v1/organizations/1/stats" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}ALL TESTS COMPLETE!${NC}"
echo -e "${GREEN}================================${NC}"