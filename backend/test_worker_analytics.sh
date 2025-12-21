#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TESTING WORKER ANALYTICS API${NC}"
echo -e "${BLUE}================================${NC}\n"

# Get authentication token
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

# Test 1: Get worker performance
echo -e "${BLUE}Test 1: Get Worker Performance (Worker ID 1, last 30 days)${NC}"
curl -s "http://localhost:8000/api/v1/workers/1/performance?days=30" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 2: Get worker performance (60 days)
echo -e "${BLUE}Test 2: Get Worker Performance (Worker ID 1, last 60 days)${NC}"
curl -s "http://localhost:8000/api/v1/workers/1/performance?days=60" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 3: Get attendance history
echo -e "${BLUE}Test 3: Get Attendance History (Worker ID 1, last 30 days)${NC}"
curl -s "http://localhost:8000/api/v1/workers/1/attendance?days=30" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 4: Get activity log
echo -e "${BLUE}Test 4: Get Activity Log (Worker ID 1, last 30 days)${NC}"
curl -s "http://localhost:8000/api/v1/workers/1/activity?days=30&limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 5: Search workers by name
echo -e "${BLUE}Test 5: Search Workers (query='John')${NC}"
curl -s "http://localhost:8000/api/v1/workers/search?query=John&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 6: Search active workers only
echo -e "${BLUE}Test 6: Search Active Workers Only${NC}"
curl -s "http://localhost:8000/api/v1/workers/search?is_active=true&limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 7: Search workers by site
echo -e "${BLUE}Test 7: Search Workers by Site (Site ID 1)${NC}"
curl -s "http://localhost:8000/api/v1/workers/search?site_id=1&limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 8: Bulk create workers
echo -e "${BLUE}Test 8: Bulk Create Workers (3 workers)${NC}"
curl -s -X POST "http://localhost:8000/api/v1/workers/bulk-create" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workers": [
      {
        "site_id": 1,
        "first_name": "Bulk",
        "last_name": "Worker1",
        "employee_id": "BULK001",
        "phone": "+2348011111111",
        "email": "bulk1@farm.com",
        "skills": "Harvesting, Planting",
        "is_active": true
      },
      {
        "site_id": 1,
        "first_name": "Bulk",
        "last_name": "Worker2",
        "employee_id": "BULK002",
        "phone": "+2348022222222",
        "email": "bulk2@farm.com",
        "skills": "Irrigation, Maintenance",
        "is_active": true
      },
      {
        "site_id": 2,
        "first_name": "Bulk",
        "last_name": "Worker3",
        "employee_id": "BULK003",
        "phone": "+2348033333333",
        "email": "bulk3@farm.com",
        "skills": "Equipment Operation",
        "is_active": true
      }
    ]
  }' | python3 -m json.tool
echo -e "\n"

# Test 9: Search for bulk-created workers
echo -e "${BLUE}Test 9: Search for Bulk-Created Workers${NC}"
curl -s "http://localhost:8000/api/v1/workers/search?query=Bulk" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 10: Bulk update workers
echo -e "${BLUE}Test 10: Bulk Update Workers (Update skills for all bulk workers)${NC}"
# Get IDs of bulk workers
BULK_WORKER_IDS=$(curl -s "http://localhost:8000/api/v1/workers/search?query=Bulk" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "
import sys, json
try:
    workers = json.load(sys.stdin)
    if isinstance(workers, list) and len(workers) > 0:
        ids = [str(w['id']) for w in workers]
        print(','.join(ids))
    else:
        print('none')
except:
    print('none')
" 2>/dev/null)

if [ "$BULK_WORKER_IDS" != "none" ] && [ -n "$BULK_WORKER_IDS" ]; then
    # Convert comma-separated IDs to JSON array
    IDS_ARRAY="[${BULK_WORKER_IDS}]"
    
    curl -s -X PUT "http://localhost:8000/api/v1/workers/bulk-update" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"worker_ids\": ${IDS_ARRAY},
        \"updates\": {
          \"skills\": \"Updated: Multi-skilled farmhand\"
        }
      }" | python3 -m json.tool
else
    echo "No bulk workers found to update"
fi
echo -e "\n"

# Test 11: Verify bulk update worked
echo -e "${BLUE}Test 11: Verify Bulk Update (Search bulk workers again)${NC}"
curl -s "http://localhost:8000/api/v1/workers/search?query=Bulk" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}ALL TESTS COMPLETE!${NC}"
echo -e "${GREEN}================================${NC}"