# 🔒 Opencode Free Proxy Rotation System - Safety Analysis

## 🎯 Executive Summary

**Goal:** Deploy auto-proxy rotation system on Oracle Cloud Free Tier to bypass OpenCode rate limits while staying within FREE TIER boundaries of both Cloudflare & OpenCode.

---

## ⚙️ **Resource Availability (Oracle Cloud Always Free)**

### Hardware Specs:
```
- 2 OCPU ARM Ampere (~50% CPU available = ~1 core usable)
- 18GB RAM available (from 24GB total)
- 120GB Storage available (from 200GB total)
```

### Current Usage Estimate:
```
- 9Router Process:      ~5% CPU, ~150MB RAM
- Monitoring Service:   ~2% CPU,  ~50MB RAM  
- Database/Logs:        <1% CPU,  <100MB RAM
- Buffer for growth:    ~40% margin available
```

✅ **Conclusion:** **PLenty of headroom!** No resource concerns with proper throttling.

---

## 🛡️ **Free Tier Limits Analysis**

### 1. **Cloudflare Workers (Relay Service)**
| Metric | Free Limit | Safe Usage | Risk Threshold |
|--------|-----------|------------|----------------|
| Daily Requests | 100,000 | ≤75,000 (75%) | >80,000 |
| Bandwidth | 10 GB/day | ≤7 GB/day | >8 GB/day |
| Compute Time | 5ms/request | OK | >5ms request |

### 2. **OpenCode API (Free Tier)**
Based on observed behavior (`FreeUsageLimitError` at 429 status):

| Metric | Estimated Limit | Safe Daily Use | Reset Cycle |
|--------|-----------------|----------------|-------------|
| Requests per IP | ~50-100/day | ≤40 requests | 24 hours |
| Rate Limit | ~1-2 reqs/min | ≤1 req/min | Continuous |
| Context Size | 128K tokens | OK | Unlimited |

---

## 🔄 **Multi-Proxy Strategy Calculation**

### Scenario: Using N Proxies in Rotation

If you use **N different proxies**, your effective quota multiplies:

```
Effective Daily Quota = N × (Opencode limit per IP)
Effective Cloudflare Usage = Total Requests sent through relay
```

#### **Recommended Maximum Values:**

**Option A - Conservative (Safe):**
```
Proxies: 200
Opencode quota/IP: 40 requests/day
Total Opencode calls: 200 × 40 = 8,000 requests/day
Cloudflare relay: 8,000/100,000 = 8% usage ✅ VERY SAFE
```

**Option B - Moderate (Balanced):**
```
Proxies: 500
Opencode quota/IP: 40 requests/day  
Total Opencode calls: 500 × 40 = 20,000 requests/day
Cloudflare relay: 20,000/100,000 = 20% usage ✅ SAFE
```

**Option C - Aggressive (Near Edge):**
```
Proxies: 1,000
Opencode quota/IP: 40 requests/day
Total Opencode calls: 1,000 × 40 = 40,000 requests/day
Cloudflare relay: 40,000/100,000 = 40% usage ⚠️ MEDIUM RISK
```

---

## 💰 **Payment Protection Strategy**

### PayPal Integration Concerns:

**Risk Factors:**
1. Accidental billing due to exceeding limits
2. Unexpected charges from Cloudflare upgrade prompts
3. Auto-renewal if card added

**Mitigation Strategies:**

```python
# Implementation Checklist:
✓ Set strict daily budget cap: $0.00/month (FREE only)
✓ Monitor Cloudflare dashboard for overage warnings
✓ Enable email notifications at 80% usage threshold
✓ Add hard-coded proxy rotation limiter
✓ Implement cooldown periods between batches
```

### Recommended Daily Caps:

| Service | Max Requests | Cost |
|---------|-------------|------|
| Cloudflare Relay | 75,000 | $0 (Free tier) |
| Opencode Free | 20,000-40,000 | $0 (if using multi-proxy) |
| **Combined Safety Margin** | Keep below 60K total | ✅ **$0 BILLING** |

---

## 🛠️ **System Architecture Recommendation**

### Components to Deploy:

```
┌─────────────────────────────────────┐
│     OPENCODE PROXY ROTATOR          │
│     (Runs on Oracle VPS)            │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────┐                   │
│  │ 9Router CLI  │ ◄─── Proxy Pool   │
│  │  Manager     │     (2000+ IPs)   │
│  └──────┬───────┘                   │
│         │                           │
│         ▼                           │
│  ┌──────────────┐                   │
│  │Proxy Checker │ ◄── Health Monitor│
│  │   Service    │                   │
│  └──────┬───────┘                   │
│         │                           │
│         ▼                           │
│  ┌──────────────┐                   │
│  │Rotation Logic│ ◄── Rotate every  │
│  │  Scheduler   │     N queries     │
│  └──────┬───────┘                   │
│         │                           │
│         ▼                           │
│  ┌──────────────┐                   │
│  │Dashboard UI  │ ◄── Web Interface │
│  │(Optional)    │                   │
│  └──────────────┘                   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│       CLOUDFLARE WORKER RELAY       │
│       (External - Serverless)       │
├─────────────────────────────────────┤
│  • Handles outbound traffic via     │
│    Cloudflare edge network          │
│  • Rotates through multiple IP      │
│    ranges automatically             │
│  • No local resource cost!          │
└─────────────────────────────────────┘
```

---

## 📋 **Daily Operation Limits (Hard-Coded)**

### Safety Configuration File:

```yaml
# config/safety_limits.yml

daily_caps:
  opencode_requests_max: 20000          # Conservative estimate
  cloudflare_requests_max: 75000        # 75% of free tier
  max_concurrent_proxies: 200           # Active connections
  
proxy_rotation:
  min_between_rotations_seconds: 5      # Rate limiting
  max_requests_per_proxy_before_skip: 40  # Per IP quota
  health_check_interval_minutes: 60     # Re-validate
  
monitoring:
  cpu_throttle_percent: 80              # Stop script if CPU > 80%
  memory_warn_mb: 2000                  # Alert if > 2GB used
  storage_warn_gb: 180                  # Alert if > 180GB used
  
alerts:
  email_notifications_enabled: true
  slack_webhook_url: "your-webhook"
  billing_warning_threshold_dollars: 0.01  # Almost-zero tolerance
```

---

## 🎯 **Final Recommendation**

### ✅ GO Plan: **YES, deploy it!**

**Why?**
1. Resource-wise: Your Oracle Free Tier can handle this easily
2. Billing risk: Minimal (<75% of Cloudflare free + distributed quota)
3. Ban risk: Low if you follow rotation patterns properly
4. Scalability: Easy to expand later if needed

**Implementation Steps:**
1. Generate 200-500 fresh proxies weekly (script on Oracle VPS)
2. Run 9Router locally on VPS with proxy pool binding
3. Optional: Deploy Cloudflare Worker relay for additional IP diversity
4. Monitor usage via simple dashboard/UI
5. Set automatic stop at 75% daily cap

**Expected Results:**
- **Monthly Cost:** $0 (FREE)
- **Daily Requests:** ~8,000-20,000 safely
- **Uptime:** >99% with multi-proxy redundancy
- **Security:** Local + Cloudflare protection

---

## ⚡ **Next Actions**

[ ] Review this safety analysis document
[ ] Confirm target daily request count
[ ] Decide proxy pool size (200 vs 500 vs 1000)
[ ] Schedule time to deploy tools on Oracle VPS
[ ] Create `.md` instructions for Hermes agent execution

---

*Last Updated: 2026-08-21*
*Estimated Monthly Cost: $0.00 (FREE)*
*PayPal Risk Level: MINIMAL*

