# Known Issues and Technical Debt

This document tracks known issues, technical debt, and recommended improvements for the OpenMesh platform.

**Status:** Updated after Phase 4A/4B completion and comprehensive code review
**Date:** 2024-11-16

---

## 🔴 CRITICAL - Security Issues (Phase 5)

### 1. WebSocket Authentication
**File:** `backend/api/v1/websocket.py`
**Severity:** CRITICAL
**Impact:** Anyone can connect and subscribe to any device/network data

**Problem:**
- No authentication required to connect to WebSocket endpoint
- No authorization check for subscriptions
- Attackers can enumerate device IDs and subscribe to their metrics
- No validation that device_id/network_id exists

**Recommendation for Phase 5:**
```python
# Add JWT authentication
from backend.core.auth import verify_token

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),  # Require token
):
    # Verify token before accepting connection
    user = await verify_token(token)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await manager.connect(websocket, user)  # Track user with connection
```

### 2. No Input Validation on WebSocket Messages
**File:** `backend/api/v1/websocket.py`
**Severity:** HIGH
**Impact:** Type errors, crashes, unexpected behavior

**Problem:**
- `subscription_id` not validated (could be string, negative, None)
- No check if device_id/network_id exists in database
- Malformed JSON crashes the connection

**Recommendation:**
```python
# Validate subscription_id
subscription_id = data.get("id")
if not isinstance(subscription_id, int) or subscription_id < 1:
    await manager.send_personal_message(
        {"type": "error", "message": "Invalid subscription ID"},
        websocket
    )
    return

# Verify entity exists
device = await service.get_device(subscription_id)
if not device:
    await manager.send_personal_message(
        {"type": "error", "message": "Device not found"},
        websocket
    )
    return
```

### 3. No Rate Limiting
**Files:** `backend/api/v1/websocket.py`, `backend/core/websocket.py`
**Severity:** MEDIUM (Security)
**Impact:** DoS attacks possible

**Problem:**
- No limit on subscriptions per connection
- No limit on subscription requests per second
- Single connection could subscribe to thousands of devices

**Recommendation:**
- Implement rate limiting middleware
- Limit subscriptions per connection (e.g., max 100)
- Track subscription requests per minute

---

## 🔴 CRITICAL - Thread Safety Issues

### 4. Non-Thread-Safe Collections in ConnectionManager
**File:** `backend/core/websocket.py`
**Severity:** HIGH
**Impact:** Data corruption, crashes in production with concurrent connections

**Problem:**
```python
# Uses regular Python set() and dict() - not thread-safe!
self.active_connections: Set[WebSocket] = set()
self.device_subscriptions: Dict[int, Set[WebSocket]] = {}
```

Multiple async coroutines can modify these concurrently, causing:
- `RuntimeError: Set changed size during iteration`
- Lost subscriptions
- Corrupted data structures

**Recommendation:**
```python
import asyncio

class ConnectionManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.active_connections: Set[WebSocket] = set()
        # ... rest of initialization

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    # Apply lock to all methods that modify collections
```

---

## 🟠 HIGH - React Hooks Violations

### 5. Stale Closures in useWebSocket
**File:** `frontend/src/hooks/useWebSocket.js`
**Severity:** HIGH
**Impact:** Wrong callbacks executed, stale data referenced

**Problem:**
```javascript
useEffect(() => {
    connect()
    return () => disconnect()
}, [])  // ❌ MISSING connect and disconnect dependencies!
```

If parent component passes new `onMessage` callback, the effect doesn't re-run, so WebSocket uses stale callback.

**Recommendation:**
```javascript
// Use refs for callbacks
const callbacksRef = useRef({ onMessage, onConnect, onError, onDisconnect })

useEffect(() => {
    callbacksRef.current = { onMessage, onConnect, onError, onDisconnect }
})

const connect = useCallback(() => {
    // Use callbacksRef.current.onMessage instead of onMessage
    // ...
}, [/* other deps except callbacks */])

useEffect(() => {
    connect()
    return () => disconnect()
}, [connect, disconnect])  // Now includes dependencies
```

---

## 🟠 HIGH - Data Validation Issues

### 6. Unsafe Data Access in DeviceMetrics
**File:** `frontend/src/components/DeviceMetrics.jsx` (lines 82-92)
**Severity:** HIGH
**Impact:** Runtime errors if API returns malformed data

**Problem:**
```javascript
data.data.forEach((point) => {
    // No validation of point.field, point.time, or point.value
    metricsData[point.field].push({
        time: point.time,  // Could be invalid
        value: point.value, // Could be null/undefined
    })
})
```

**Recommendation:**
```javascript
if (data && Array.isArray(data.data)) {
    data.data.forEach((point) => {
        if (point && point.field && point.time && point.value !== undefined) {
            if (!metricsData[point.field]) {
                metricsData[point.field] = []
            }
            metricsData[point.field].push({
                time: point.time,
                value: point.value,
            })
        }
    })
}
```

### 7. Missing Data Validation in MetricsChart
**File:** `frontend/src/components/MetricsChart.jsx` (lines 38, 42, 95, 128)
**Severity:** HIGH
**Impact:** Chart crashes on invalid data

**Problems:**
- No validation that `d.time` is a valid date
- No validation that `d.value` is a number
- `toFixed()` crashes if value is null/undefined/NaN

**Recommendation:**
```javascript
const chartData = {
    labels: data.map(d => {
        const date = new Date(d.time)
        return isNaN(date.getTime()) ? new Date() : date
    }),
    datasets: [{
        data: data.map(d => {
            const val = Number(d.value)
            return isNaN(val) ? 0 : val
        }),
    }]
}

// In tooltip callback:
if (context.parsed.y !== null && !isNaN(context.parsed.y)) {
    label += context.parsed.y.toFixed(2) + (unit ? ` ${unit}` : '')
}
```

---

## 🟡 MEDIUM - Performance Issues

### 8. Chart Data Recreated on Every Render
**File:** `frontend/src/components/MetricsChart.jsx`
**Severity:** MEDIUM
**Impact:** Unnecessary re-renders, lag with real-time updates

**Problem:**
```javascript
// These objects are recreated on every render
const chartData = { ... }
const options = { ... }
```

**Recommendation:**
```javascript
import { useMemo } from 'react'

const chartData = useMemo(() => ({
    labels: data.map(d => new Date(d.time)),
    // ...
}), [data, title, color])

const options = useMemo(() => ({
    // ...
}), [title, yAxisLabel, unit])
```

### 9. Full D3 Visualization Recreated on Data Changes
**File:** `frontend/src/components/NetworkTopology.jsx`
**Severity:** MEDIUM
**Impact:** Poor performance for large networks

**Problem:**
Entire D3 visualization is destroyed and recreated on every data change.

**Recommendation:**
Implement D3's update pattern with enter/exit selections for better performance.

---

## 🟡 MEDIUM - Missing Features

### 10. No Data Sorting in DeviceMetrics
**File:** `frontend/src/components/DeviceMetrics.jsx`
**Severity:** MEDIUM
**Impact:** Charts may display incorrectly if API returns unordered data

Chart.js time scale expects chronological data, but data isn't sorted.

**Recommendation:**
```javascript
// After grouping, sort each metric array
Object.keys(metricsData).forEach(key => {
    metricsData[key].sort((a, b) => new Date(a.time) - new Date(b.time))
})
```

### 11. Missing Additional Metrics
**File:** `frontend/src/components/DeviceMetrics.jsx`
**Current metrics:** CPU, Memory (free), Load, Uptime, Babel neighbors/routes/RTT

**Missing useful metrics:**
- Memory usage percentage
- Disk usage/free
- Network throughput (bytes in/out)
- Packet loss
- Load average (5min, 15min)
- Temperature
- Swap usage
- Network interface errors

### 12. No Chart Decimation for Large Datasets
**File:** `frontend/src/components/MetricsChart.jsx`
**Impact:** Performance degradation with 7-30 day time ranges

**Recommendation:**
```javascript
plugins: {
    decimation: {
        enabled: true,
        algorithm: 'lttb',  // Largest-Triangle-Three-Buckets
        samples: 50
    }
}
```

---

## 🟡 MEDIUM - Incomplete Cleanup

### 13. DeviceMetrics Cleanup Depends on isConnected
**File:** `frontend/src/components/DeviceMetrics.jsx` (lines 37-47)
**Severity:** MEDIUM
**Impact:** Ghost subscriptions on server

**Problem:**
```javascript
return () => {
    if (isConnected && deviceId) {  // ❌ Problem
        unsubscribe('device', deviceId)
    }
}
```

If WebSocket disconnects before component unmounts, cleanup doesn't unsubscribe.

**Recommendation:**
```javascript
const subscribedRef = useRef(false)

useEffect(() => {
    if (isConnected && deviceId) {
        subscribe('device', deviceId)
        subscribedRef.current = true
    }

    return () => {
        if (subscribedRef.current && deviceId) {
            unsubscribe('device', deviceId)
            subscribedRef.current = false
        }
    }
}, [isConnected, deviceId, subscribe, unsubscribe])
```

---

## 🔵 LOW - Minor Issues

### 14. No Tooltip Boundary Checking
**File:** `frontend/src/components/NetworkTopology.jsx` (lines 148-152)
**Impact:** Tooltips can overflow viewport

### 15. No Link Reference Validation
**File:** `frontend/src/components/NetworkTopology.jsx`
**Impact:** Broken links if source/target IDs don't exist

### 16. Hard-coded Chart Values
**Files:** All chart components
**Impact:** Less flexible, harder to customize

---

## Testing Gaps

### Missing Tests:
1. **WebSocket Integration Tests**
   - Subscribe/unsubscribe lifecycle
   - Concurrent connections (thread safety)
   - Reconnection scenarios
   - Memory cleanup validation

2. **Frontend Component Tests**
   - NetworkTopology.jsx
   - MetricsChart.jsx
   - DeviceMetrics.jsx
   - useWebSocket.js hook

3. **Edge Case Tests**
   - Invalid/malformed data handling
   - Empty datasets
   - Large datasets (performance)
   - Network disconnections during operations

---

## Monitoring Recommendations

### Add Metrics For:
1. Active WebSocket connections count
2. Subscription dictionary sizes
3. Failed message send attempts
4. Memory usage trends
5. Chart render times

### Add Alerts For:
1. WebSocket connection count > threshold
2. Subscription dictionary growth
3. High message send failure rate
4. Memory growth patterns

---

## Priority Recommendations

### Phase 5 - Security (IMMEDIATE):
1. ✅ Add JWT authentication to WebSocket
2. ✅ Add input validation for all WebSocket messages
3. ✅ Verify entity existence before subscriptions
4. ✅ Add rate limiting

### Phase 5 - Stability (HIGH):
1. Fix thread safety in ConnectionManager (use asyncio.Lock)
2. Fix React Hooks violations in useWebSocket
3. Add data validation throughout metrics pipeline
4. Add comprehensive error handling

### Phase 5 - Performance (MEDIUM):
1. Memoize chart data and options
2. Implement D3 update pattern
3. Add chart decimation for large datasets
4. Optimize data sorting and processing

### Phase 5 - Features (LOW):
1. Add missing metrics (disk, network throughput, etc.)
2. Add chart export functionality
3. Add multi-device comparison
4. Add alert thresholds
5. Add search/filter for topology

---

## Notes

- **Security issues** are documented but deferred to Phase 5 (Production Hardening)
- **Critical bugs** (memory leaks) have been fixed as of 2024-11-16
- **Thread safety** issues require testing under concurrent load
- **Performance issues** may not be noticeable until production scale

---

**Last Updated:** 2024-11-16
**Next Review:** Before Phase 5 implementation
