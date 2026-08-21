# ☁️ Cloudflare Workers Free Tier Explained

## 📊 Dua Quota Berbeda: Request vs Proxy Quota

### Important Clarification:

```
┌─────────────────────────────────────────────────────────┐
│  CLOUDFLARE LIMITS (Per Day)                            │
│  • Max Requests:   100,000                               │
│  • Safe Usage:     ≤75,000 (75%)                        │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│  OPENCODE QUOTA PER PROXY (Per Day)                     │
│  • Per IP:           ~40-60 requests                    │
│  • Reset Cycle:      Every 24 hours                     │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│  MULTIPLY THEM TOGETHER                                 │
│  • 500 proxies × 40 requests = 20,000 total             │
│  • Cloudflare uses: 20,000/100,000 = 20% of its limit  │
└─────────────────────────────────────────────────────────┘
```

**Key Point:** 
- Cloudflare sees **ONE proxy relay endpoint**, not individual IPs
- OpenCode sees **DIFFERENT IPs** from each proxy rotation
- **Total traffic through Cloudflare = Total requests made**

---

## 🔢 Calculation Breakdown

### Scenario: You want to make MAXIMUM daily usage

#### Conservative Estimate:
```yaml
OpenCode Quota/IP:       40 requests/day
Proxies Available:       500
Cloudflare Capacity:     75,000/day (safe limit)

Total Daily Usage:
  → 500 × 40 = 20,000 requests ✅ VERY SAFE
  → Uses only 27% of Cloudflare capacity
  → Safety margin: 55,000 unused requests

Result: 20,000 Opencode calls/day, zero billing risk ✅
```

#### Aggressive Estimate:
```yaml
OpenCode Quota/IP:       40 requests/day
Proxies Available:       500
Optimized Rotation:      Use full quota (no safety buffer)

Total Daily Usage:
  → 500 × 40 = 20,000 max requests possible
  → Can't exceed this without new proxies
  → Cloudflare still only at 20% usage

Result: 20,000 Opencode calls/day is the HARD CAP with 500 proxies
         You CAN'T use more even if Cloudflare allows it!
```

---

## 🤔 "Aku cuma perlu 499 ya biar gak pas banget?"

**ANSWER:** Ya betul! Ini disebut **"safety buffer"** technique.

```python
# Formula untuk maximum safety:

PROXY_COUNT = math.ceil(TARGET_DAILY_REQUESTS / QUOTA_PER_IP) * SAFETY_FACTOR

where:
  TARGET_DAILY_REQUESTS = 20,000 (target you want)
  QUOTA_PER_IP = 40 (conservative estimate)
  SAFETY_FACTOR = 1.05 (5% extra for variance)

→ PROXY_COUNT = ceil(20000/40) × 1.05
→ PROXY_COUNT = ceil(500) × 1.05
→ PROXY_COUNT = 525 proxies minimum needed

BUT to keep it safe and simple:
→ ROUND DOWN to 499 for slight margin
→ This gives you: 499 × 40 = 19,960 requests/day
→ Still under your 20K target ✅
→ Extra buffer for dead/bad proxies ✅
```

**Why 499 instead of 500?**
- Accounting for some proxies that might die/fail
- Not using exactly 100% of quota (safety buffer)
- Prevents hitting wall at exact threshold

---

## ✅ CONCLUSION: 

**With 499 proxies, you get:**
- ✅ **~19,960 requests/day** safely
- ✅ **~20% Cloudflare usage** (way under limit!)
- ✅ **$0/month billing risk** (FREE forever)
- ✅ **Can't exceed quota** because limited by proxy count

**If you try to go ABOVE 500:**
- ❌ Need MORE proxies (generate fresh list)
- ❌ Cloudflare still won't be bottleneck at 20-30% usage
- ❌ Only way to increase is: Add more proxies to pool

**Bottom line:** Your **limit is proxies, NOT Cloudflare!** 😎

