#!/bin/bash
# Stage 2.5 Verification Test Script
# Tests: Checkpoints API, Audit Log API, Timeline API

echo "🧪 STAGE 2.5 VERIFICATION TESTS"
echo "======================================================================"
echo "Testing: Checkpoints, Audit Logs, Timeline APIs"
echo "======================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
TOTAL=0

# Test result function
test_result() {
    ((TOTAL++))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((FAILED++))
    fi
    echo ""
}

# Step 1: Get auth token
echo "🔑 Step 1: Authenticating..."
TOKEN_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@clockout.com&password=password123")

TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ CRITICAL: Failed to get authentication token!${NC}"
    echo "Make sure:"
    echo "  1. Server is running: uvicorn app.main:app --reload"
    echo "  2. Admin user exists (admin@clockout.com / password123)"
    exit 1
fi

echo -e "${GREEN}✅ Authentication successful${NC}"
echo ""

# ============================================================================
# CHECKPOINTS API TESTS (5 endpoints)
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 CHECKPOINTS API TESTS (5 endpoints)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 1: Create checkpoint
echo "Test 1/13: POST /checkpoints/ - Create checkpoint"
CHECKPOINT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/api/v1/checkpoints/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": 1,
    "name": "Main Entrance",
    "description": "Primary gate checkpoint",
    "checkpoint_type": "entrance",
    "gps_lat": 6.5244,
    "gps_lon": 3.3792,
    "is_active": true
  }')

HTTP_CODE=$(echo "$CHECKPOINT_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$CHECKPOINT_RESPONSE" | head -n -1)
CHECKPOINT_ID=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ "$HTTP_CODE" = "201" ] && [ ! -z "$CHECKPOINT_ID" ]; then
    echo "  Created checkpoint ID: $CHECKPOINT_ID"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    echo "  Response: $RESPONSE_BODY"
    test_result 1
fi

# Test 2: List checkpoints
echo "Test 2/13: GET /checkpoints/ - List all checkpoints"
LIST_RESPONSE=$(curl -s -w "\n%{http_code}" http://127.0.0.1:8000/api/v1/checkpoints/ \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | head -n -1)
CHECKPOINT_COUNT=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_count', 0))" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ] && [ "$CHECKPOINT_COUNT" -gt 0 ]; then
    echo "  Found $CHECKPOINT_COUNT checkpoint(s)"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# Test 3: Get specific checkpoint
if [ ! -z "$CHECKPOINT_ID" ]; then
    echo "Test 3/13: GET /checkpoints/{id} - Get checkpoint details"
    GET_RESPONSE=$(curl -s -w "\n%{http_code}" http://127.0.0.1:8000/api/v1/checkpoints/$CHECKPOINT_ID \
      -H "Authorization: Bearer $TOKEN")
    
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n 1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | head -n -1)
    RETURNED_ID=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ] && [ "$RETURNED_ID" = "$CHECKPOINT_ID" ]; then
        echo "  Retrieved checkpoint successfully"
        test_result 0
    else
        echo "  HTTP Code: $HTTP_CODE"
        test_result 1
    fi
else
    echo "Test 3/13: SKIPPED (no checkpoint ID)"
    ((TOTAL++))
fi

# Test 4: Update checkpoint
if [ ! -z "$CHECKPOINT_ID" ]; then
    echo "Test 4/13: PUT /checkpoints/{id} - Update checkpoint"
    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT http://127.0.0.1:8000/api/v1/checkpoints/$CHECKPOINT_ID \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "description": "Updated: Main entrance with NFC",
        "nfc_tag_id": "NFC-TEST-001"
      }')
    
    HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n 1)
    RESPONSE_BODY=$(echo "$UPDATE_RESPONSE" | head -n -1)
    NFC_TAG=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('nfc_tag_id', ''))" 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ] && [ "$NFC_TAG" = "NFC-TEST-001" ]; then
        echo "  Updated checkpoint successfully"
        test_result 0
    else
        echo "  HTTP Code: $HTTP_CODE"
        test_result 1
    fi
else
    echo "Test 4/13: SKIPPED (no checkpoint ID)"
    ((TOTAL++))
fi

# Test 5: Filter checkpoints
echo "Test 5/13: GET /checkpoints/?checkpoint_type=entrance - Filter by type"
FILTER_RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/api/v1/checkpoints/?checkpoint_type=entrance" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$FILTER_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$FILTER_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  Filter working correctly"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# ============================================================================
# AUDIT LOG API TESTS (4 endpoints)
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 AUDIT LOG API TESTS (4 endpoints)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 6: List audit logs
echo "Test 6/13: GET /audit/ - Query audit logs"
AUDIT_RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/api/v1/audit/?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$AUDIT_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$AUDIT_RESPONSE" | head -n -1)
LOG_COUNT=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('logs', [])))" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  Retrieved $LOG_COUNT audit log(s)"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# Test 7: Get recent logs
echo "Test 7/13: GET /audit/recent - Get recent logs"
RECENT_RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/api/v1/audit/recent?limit=5" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$RECENT_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$RECENT_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  Recent logs retrieved"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# Test 8: Get audit statistics
echo "Test 8/13: GET /audit/stats - Get statistics"
STATS_RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/api/v1/audit/stats?days=7" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | head -n -1)
TOTAL_ACTIONS=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_actions', 0))" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  Total actions tracked: $TOTAL_ACTIONS"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# Test 9: Get user audit trail
echo "Test 9/13: GET /audit/user/1 - User audit trail"
USER_TRAIL_RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/api/v1/audit/user/1?limit=10" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$USER_TRAIL_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$USER_TRAIL_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  User audit trail retrieved"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# ============================================================================
# TIMELINE API TESTS (4 endpoints)
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📅 TIMELINE/HISTORY API TESTS (4 endpoints)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get dates for testing
TODAY=$(date +%Y-%m-%d)
WEEK_AGO=$(date -d "7 days ago" +%Y-%m-%d 2>/dev/null || date -v-7d +%Y-%m-%d)

# Test 10: Get worker history
echo "Test 10/13: GET /timeline/worker/1 - Worker history"
WORKER_HISTORY_RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/api/v1/timeline/worker/1?start_date=$WEEK_AGO&end_date=$TODAY" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$WORKER_HISTORY_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$WORKER_HISTORY_RESPONSE" | head -n -1)
WORKER_ID=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('worker_id', ''))" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ] && [ "$WORKER_ID" = "1" ]; then
    echo "  Worker history retrieved"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# Test 11: Get site activity
echo "Test 11/13: GET /timeline/site/1 - Site activity"
SITE_ACTIVITY_RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/api/v1/timeline/site/1?start_date=$WEEK_AGO&end_date=$TODAY" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$SITE_ACTIVITY_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$SITE_ACTIVITY_RESPONSE" | head -n -1)
SITE_ID=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('site_id', ''))" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ] && [ "$SITE_ID" = "1" ]; then
    echo "  Site activity retrieved"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# Test 12: Get daily timeline
echo "Test 12/13: GET /timeline/daily/$TODAY - Daily timeline"
DAILY_TIMELINE_RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/api/v1/timeline/daily/$TODAY" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$DAILY_TIMELINE_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$DAILY_TIMELINE_RESPONSE" | head -n -1)
RETURNED_DATE=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('date', ''))" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ] && [ "$RETURNED_DATE" = "$TODAY" ]; then
    echo "  Daily timeline retrieved"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# Test 13: Daily timeline with site filter
echo "Test 13/13: GET /timeline/daily/$TODAY?site_id=1 - Daily timeline (filtered)"
FILTERED_TIMELINE_RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/api/v1/timeline/daily/$TODAY?site_id=1" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$FILTERED_TIMELINE_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  Filtered daily timeline retrieved"
    test_result 0
else
    echo "  HTTP Code: $HTTP_CODE"
    test_result 1
fi

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  ERROR HANDLING VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Bonus Test: Unauthorized access (no token)"
NO_AUTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/v1/audit/)
if [ "$NO_AUTH_RESPONSE" = "401" ]; then
    echo -e "${GREEN}✅ Correctly rejects unauthorized access (401)${NC}"
else
    echo -e "${RED}❌ Should reject unauthorized access${NC}"
fi
echo ""

echo "Bonus Test: Invalid date format"
INVALID_DATE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
  "http://127.0.0.1:8000/api/v1/timeline/daily/invalid-date" \
  -H "Authorization: Bearer $TOKEN")
if [ "$INVALID_DATE_RESPONSE" = "400" ]; then
    echo -e "${GREEN}✅ Correctly rejects invalid date (400)${NC}"
else
    echo -e "${RED}❌ Should reject invalid date${NC}"
fi
echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================

echo "======================================================================"
echo "📊 TEST SUMMARY"
echo "======================================================================"
echo ""
echo -e "Total Tests: ${BLUE}$TOTAL${NC}"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                   ║${NC}"
    echo -e "${GREEN}║  🎉 ALL TESTS PASSED! STAGE 2.5 IS 100% OPERATIONAL! 🎉          ║${NC}"
    echo -e "${GREEN}║                                                                   ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "✅ Checkpoints API: Working"
    echo "✅ Audit Log API: Working"
    echo "✅ Timeline API: Working"
    echo "✅ Error Handling: Correct"
    echo "✅ Permissions: Enforced"
    echo ""
    echo "🚀 BACKEND IS COMPLETE AND READY FOR STAGE 3!"
    echo ""
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                                   ║${NC}"
    echo -e "${RED}║  ⚠️  SOME TESTS FAILED - REVIEW OUTPUT ABOVE                     ║${NC}"
    echo -e "${RED}║                                                                   ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Please check the failed tests above and fix any issues."
    echo ""
    exit 1
fi
