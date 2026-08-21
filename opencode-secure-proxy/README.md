# 🔒 Opencode Secure Proxy Pool System with 9Router

## 🎯 Overview

Sistem proxy pool complete untuk automatic AI requests rotation ke Opencode API melalui multiple proxies, dengan intelligent routing menggunakan 9Router.

### Key Features

✅ **Smart Proxy Rotation** - Automatic failover ketika quota/limit hit  
✅ **Privacy Protection** - NO logging prompts/responses, encrypted traffic  
✅ **AI-Only Traffic** - Proxies hanya digunakan untuk AI services (tidak track user activity)  
✅ **Quota Detection** - Auto-detect rate limit & rotate ke proxy baru  
✅ **Health Monitoring** - Track setiap proxy performance & auto-blacklist bad ones  
✅ **Integration Ready** - Support multiple AI APIs (Opencode, dll)  

---

## 📁 Project Structure

```
opencode-secure-proxy/
├── config/              # Configuration files
│   ├── settings.ini     # Main configuration
│   └── settings.json    # JSON format settings
├── proxies/             # Validated proxy lists
│   ├── validated_http.txt      # HTTP proxies with scores
│   ├── validated_socks.txt     # SOCKS5 proxies with scores
│   ├── proxifly_raw.txt        # Raw proxifly source
│   └── thespeedx_raw.txt      # Raw TheSpeedX source
├── blacklist/           # Blacklisted problematic proxies
│   └── dangerous.txt
├── data/                # Session statistics & logs
│   └── client_stats.json
├── logs/                # Application logs
├── main_client.py       # Main entry point
├── proxy_pool_manager.py  # Central proxy pool management
├── nine_router.py       # Intelligent router logic
├── validator_enhanced.py  # Advanced proxy validation
├── .env                 # Environment variables (API keys)
└── README.md           # This file
```

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
cd opencode-secure-proxy
pip install -r requirements.txt
# Or manually:
pip install aiohttp python-dotenv
```

### Step 2: Configure API Key

Create `.env` file:

```bash
export OPENCODE_API_KEY='your_actual_api_key_here'
```

Or add to `.env`:
```
OPENCODE_API_KEY=your_api_key_here
ENVIRONMENT=production
LOG_LEVEL=WARNING
```

### Step 3: Load Proxies

If you already have validated proxies:
```bash
# Copy your proxies to:
./proxies/validated_http.txt
Format: IP:PORT|SCORE|YYYY-MM-DD
Example: 192.168.1.1:8080|95|2024-01-15
```

Or run validator:
```bash
python3 validator_enhanced.py
```

### Step 4: Run Client

```bash
python3 main_client.py
```

---

## 🔄 How It Works

### Architecture Flow

```
User Prompt → [main_client.py]
              ↓
         [nine_router.py] ← Smart Routing Logic
              ↓
    [proxy_pool_manager.py] ← Pool Management
              ↓
    [Validated Proxy] → HTTPS Request → Opencode API
              ↓
    Response Analysis → Quota Detection → Success/Fail Handling
              ↓
    Update Pool Stats → Rotate if needed
```

### Proxy Selection Algorithm

1. **Filter Active Proxies** - Only usable ones from pool
2. **Calculate Score** = Base Score + Freshness Bonus
3. **Weighted Random** - Pick from top candidates
4. **Track Usage** - Monitor requests/failures per proxy
5. **Auto-Failover** - On quota/rate limit errors

### Quota Detection & Rotation

```python
# When API returns 429 or "quota exceeded" message:
→ Mark current proxy as temporarily blocked
→ Auto-unblock after 1 hour
→ Select new fresh proxy automatically
→ Continue request with new proxy
→ Success without user interruption
```

---

## 🛡️ Security & Privacy

### What We Protect

✅ **Prompt Privacy** - NEVER logged or exposed  
✅ **Response Privacy** - Encrypted storage option  
✅ **Proxy Details** - Masked in statistics  
✅ **Traffic Isolation** - ONLY for AI services  
✅ **No Telemetry** - No tracking user behavior  

### What Gets Tracked (Anonymized)

- ✅ Number of requests per proxy
- ✅ Success/failure counts
- ✅ Performance metrics (response time)
- ✅ Service identifier (to identify AI traffic only)

### What's NEVER Tracked

❌ User prompts content  
❌ Response text details  
❌ Personal information  
❌ Other application traffic (WhatsApp, Google Chat, etc)  

---

## ⚙️ Configuration Options

### settings.ini Examples

```ini
[API]
OPENCODE_API_KEY = your_key_here
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

[PROXY]
ROTATION_BATCH_SIZE = 5
MIN_VALIDITY_SCORE = 70
CHECK_INTERVAL_MINUTES = 30

[SECURITY]
# CRITICAL SECURITY SETTING
LOG_PROMPTS = false           # NEVER log prompts
LOG_RESPONSES = false         # NEVER log responses  
ENABLE_ENCRYPTION = true      # Enable encryption for stored data
ISOLATE_AI_TRAFFIC = true     # Only route AI traffic through proxies

[MONITORING]
ANOMALY_THRESHOLD = 100
MAX_REQUESTS_PER_HOUR = 1000
QUOTA_BLOCK_DURATION_HOURS = 1
```

---

## 🧪 Testing & Validation

### Validate New Proxies

```bash
python3 validator_enhanced.py --source proxifly,thespeedx
python3 validator_fast.py --batch-size 20 --timeout 8
```

### Test Client

```bash
# Run with default prompts
python3 main_client.py

# Run custom test
python3 main_client.py --prompts "test1","test2","test3"
```

### Check Proxy Health

```bash
python3 proxy_pool_manager.py  # Show pool stats
python3 nine_router.py         # Show router status
```

---

## 📊 Statistics & Monitoring

### Live Stats Command

```python
from main_client import client
stats = client.get_session_stats()
print(stats)
```

Output Example:
```json
{
  "total_requests": 150,
  "successful": 142,
  "failed": 8,
  "success_rate": 94.7,
  "rotations": 23,
  "uptime_seconds": 3600,
  "pool_stats": {
    "total_proxies": 50,
    "active": 45,
    "blacklisted": 3,
    "average_score": 87.5
  }
}
```

---

## 🆘 Troubleshooting

### Issue: "No valid proxies found"

**Solution:**
1. Run proxy validator first
2. Check file path: `./proxies/validated_http.txt`
3. Ensure format is correct: `IP:PORT|SCORE|DATE`

### Issue: "Quota exceeded frequently"

**Solution:**
1. Increase ROTATION_BATCH_SIZE in config
2. Add more high-score proxies to pool
3. Reduce MAX_REQUESTS_PER_HOUR temporarily

### Issue: "All requests failed via proxy"

**Solution:**
1. Verify proxies are actually working
2. Try disabling proxy routing: `use_router=False`
3. Check network/firewall restrictions

### Issue: "Import error: no module named..."

**Solution:**
```bash
pip install -r requirements.txt
# Should include:
# - aiohttp
# - python-dotenv
# - geoip2 (optional for location tracking)
```

---

## 🤝 Contributing

### Adding New Proxy Sources

Edit `validator_enhanced.py` and add to `PROXY_SOURCES` list:
```python
PROXY_SOURCES = [
    ("new_source", "https://github.com/user/list.txt")
]
```

### Custom Routing Logic

Override in `nine_router.py`:
```python
def select_optimal_proxy(self, route_name):
    # Your custom selection logic
    return custom_proxy
```

---

## 📝 License

MIT License - Use at your own discretion for legitimate testing purposes.

---

## ⚠️ Disclaimer

This tool is designed for:
- ✅ Rate limit bypass testing
- ✅ Load testing AI APIs
- ✅ Research purposes
- ✅ Educational use

NOT for:
- ❌ Malicious activities
- ❌ Unauthorized access attempts
- ❌ Terms of service violations
- ❌ Illegal activities

Use responsibly and respect API terms of service.

---

## 🆘 Support

For issues, questions, or improvements:
1. Check troubleshooting section above
2. Review code comments
3. Inspect `logs/` directory for detailed error messages

---

**Created by Engineer for secure AI API testing**
*Privacy-first, proxy-based rotation system*
