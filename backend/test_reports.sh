#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TESTING REPORTS & ANALYTICS API${NC}"
echo -e "${BLUE}================================${NC}\n"

# Get authentication token
echo -e "${BLUE}Step 1: Getting admin token...${NC}"
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@clockout.com&password=password123" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${RED}❌ Failed to get admin token!${NC}"
    echo -e "${YELLOW}💡 Make sure the backend is running: uvicorn app.main:app --reload${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Admin token obtained!${NC}\n"

# Get today's date and dates for testing
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)
WEEK_AGO=$(date -d "7 days ago" +%Y-%m-%d 2>/dev/null || date -v-7d +%Y-%m-%d)

echo -e "${YELLOW}📅 Test Dates:${NC}"
echo -e "   Today: $TODAY"
echo -e "   Yesterday: $YESTERDAY"
echo -e "   Week ago: $WEEK_AGO\n"

# Test 1: Daily Summary (Today)
echo -e "${BLUE}Test 1: Daily Summary - Today${NC}"
curl -s "http://localhost:8000/api/v1/reports/daily-summary?date=$TODAY" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 2: Daily Summary (Yesterday)
echo -e "${BLUE}Test 2: Daily Summary - Yesterday${NC}"
curl -s "http://localhost:8000/api/v1/reports/daily-summary?date=$YESTERDAY" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 3: Daily Summary (Specific site)
echo -e "${BLUE}Test 3: Daily Summary - Site 1 Only${NC}"
curl -s "http://localhost:8000/api/v1/reports/daily-summary?date=$TODAY&site_id=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 4: Worker Status (Real-time)
echo -e "${BLUE}Test 4: Worker Status - Who's on site right now?${NC}"
curl -s "http://localhost:8000/api/v1/reports/worker-status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 5: Worker Status (Specific site)
echo -e "${BLUE}Test 5: Worker Status - Site 1 Only${NC}"
curl -s "http://localhost:8000/api/v1/reports/worker-status?site_id=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 6: Late Arrivals (Last 7 days)
echo -e "${BLUE}Test 6: Late Arrivals Report - Last 7 Days${NC}"
curl -s "http://localhost:8000/api/v1/reports/late-arrivals?start_date=$WEEK_AGO&end_date=$TODAY" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 7: Late Arrivals (Yesterday only)
echo -e "${BLUE}Test 7: Late Arrivals - Yesterday Only${NC}"
curl -s "http://localhost:8000/api/v1/reports/late-arrivals?start_date=$YESTERDAY&end_date=$YESTERDAY" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 8: CSV Export (Last 7 days)
echo -e "${BLUE}Test 8: CSV Export - Last 7 Days (Saving to file)${NC}"
curl -s "http://localhost:8000/api/v1/reports/export/csv?start_date=$WEEK_AGO&end_date=$TODAY" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o "attendance_export_test.csv"

if [ -f "attendance_export_test.csv" ]; then
    echo -e "${GREEN}✅ CSV file created: attendance_export_test.csv${NC}"
    echo -e "${YELLOW}📄 First 10 lines:${NC}"
    head -10 attendance_export_test.csv
    echo -e "\n${YELLOW}📊 Total rows: $(wc -l < attendance_export_test.csv)${NC}"
else
    echo -e "${RED}❌ CSV file not created${NC}"
fi
echo -e "\n"

# Test 9: CSV Export (Specific site)
echo -e "${BLUE}Test 9: CSV Export - Site 1 Only${NC}"
curl -s "http://localhost:8000/api/v1/reports/export/csv?start_date=$WEEK_AGO&end_date=$TODAY&site_id=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o "attendance_site1_test.csv"

if [ -f "attendance_site1_test.csv" ]; then
    echo -e "${GREEN}✅ CSV file created: attendance_site1_test.csv${NC}"
    echo -e "${YELLOW}📊 Total rows: $(wc -l < attendance_site1_test.csv)${NC}"
fi
echo -e "\n"

# Test 10: Analytics Overview (Platform-wide - Super Admin Only)
echo -e "${BLUE}Test 10: Analytics Overview - Platform Stats (Last 30 days)${NC}"
curl -s "http://localhost:8000/api/v1/reports/analytics/overview?days=30" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 11: Analytics Overview (Last 7 days)
echo -e "${BLUE}Test 11: Analytics Overview - Last 7 Days${NC}"
curl -s "http://localhost:8000/api/v1/reports/analytics/overview?days=7" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 12: Test with Manager token (should only see assigned sites)
echo -e "${BLUE}Test 12: Testing Manager Permissions${NC}"
echo -e "${YELLOW}Getting manager1 token...${NC}"

MANAGER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manager1@farm.com&password=password123" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -n "$MANAGER_TOKEN" ]; then
    echo -e "${GREEN}✅ Manager token obtained!${NC}"
    echo -e "${YELLOW}Testing daily summary as manager (should see only assigned sites)...${NC}"
    curl -s "http://localhost:8000/api/v1/reports/daily-summary?date=$TODAY" \
      -H "Authorization: Bearer $MANAGER_TOKEN" | python3 -m json.tool
else
    echo -e "${YELLOW}⚠️  Manager user not found, skipping permission test${NC}"
fi
echo -e "\n"

# Test 13: Error handling - Invalid date format
echo -e "${BLUE}Test 13: Error Handling - Invalid Date Format${NC}"
curl -s "http://localhost:8000/api/v1/reports/daily-summary?date=invalid-date" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 14: Error handling - Invalid date range
echo -e "${BLUE}Test 14: Error Handling - Invalid Date Range (end before start)${NC}"
curl -s "http://localhost:8000/api/v1/reports/late-arrivals?start_date=$TODAY&end_date=$WEEK_AGO" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
echo -e "\n"

# Summary
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}ALL TESTS COMPLETE!${NC}"
echo -e "${GREEN}================================${NC}\n"

echo -e "${YELLOW}📊 Test Summary:${NC}"
echo -e "   ✅ 14 endpoint tests executed"
echo -e "   📁 2 CSV files generated"
echo -e "   🔐 Tested admin & manager permissions"
echo -e "   ⚠️  Tested error handling\n"

echo -e "${YELLOW}📁 Generated Files:${NC}"
ls -lh attendance*.csv 2>/dev/null && echo "" || echo -e "   No CSV files found\n"

echo -e "${BLUE}🎉 Stage 2.4 Testing Complete!${NC}"
echo -e "${YELLOW}Next: Test with real data and move to Stage 2.5${NC}\n"