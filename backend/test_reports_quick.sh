#!/bin/bash

echo "🔑 Getting authentication token..."
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@clockout.com&password=password123" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get token!"
    exit 1
fi

echo "✅ Token obtained!"
echo ""

# Set dates
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
WEEK_AGO=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d "7 days ago" +%Y-%m-%d)

echo "📅 Testing with dates:"
echo "   Today: $TODAY"
echo "   Yesterday: $YESTERDAY"
echo "   Week ago: $WEEK_AGO"
echo ""

echo "📊 Test 1: Daily Summary (Yesterday - should have data)"
curl -s "http://127.0.0.1:8000/api/v1/reports/daily-summary?date=$YESTERDAY" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "👥 Test 2: Worker Status (Real-time)"
curl -s "http://127.0.0.1:8000/api/v1/reports/worker-status" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "⏰ Test 3: Late Arrivals (Last 7 days)"
curl -s "http://127.0.0.1:8000/api/v1/reports/late-arrivals?start_date=$WEEK_AGO&end_date=$TODAY" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -50
echo ""

echo "📁 Test 4: CSV Export"
curl -s "http://127.0.0.1:8000/api/v1/reports/export/csv?start_date=$WEEK_AGO&end_date=$TODAY" \
  -H "Authorization: Bearer $TOKEN" \
  -o attendance_test.csv

if [ -f "attendance_test.csv" ]; then
    echo "✅ CSV created! First 10 rows:"
    head -10 attendance_test.csv
else
    echo "❌ CSV not created"
fi
echo ""

echo "🎉 All tests complete!"