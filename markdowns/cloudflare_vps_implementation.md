# ☁️ Cloudflare Workers + Oracle VPS Implementation Guide

## 🎯 Overview

This guide covers deploying:
1. **Cloudflare Worker Relay** (serverless proxy)
2. **Local Proxy Pool Manager** (on Oracle VPS)
3. **Integration with Hermes Agent** for automatic rotation

---

## 📋 Prerequisites

### Hardware Requirements (Oracle Free Tier):
```
- CPU: ≥1 core available (you have 2 cores, ~50% usable)
- RAM: ≥2GB free (you have 18GB available)
- Storage: ≥10GB free (you have 120GB free)
```

✅ **Your specs are MORE than enough!**

---

## 🔧 Step-by-Step Implementation

### Phase 1: Local Setup (First Time)

#### 1. Install Dependencies on Oracle VPS

```bash
# SSH into your Oracle instance
ssh engineer@your-oracle-vip.ip.address

# Install Python and tools
sudo apt update
sudo apt install -y python3 python3-pip nodejs npm git curl

# Verify installation
python3 --version  # Should show 3.x
node --version     # Should show v16+

# Create project directory
mkdir -p ~/projects/proxy-pool && cd ~/projects/proxy-pool

# Clone existing scripts from GitHub or copy manually
# (Assuming you've already transferred files)
```

#### 2. Deploy Cloudflare Worker

```bash
# Install Cloudflare CLI
npm install -g wrangler

# Login to Cloudflare account
wrangler login

# Create new worker project
cd ~/projects/proxy-pool
wrangler generate cf-relay

# Edit worker.js to add relay logic
nano ../proxy-pool/worker/worker.js
```

**Worker.js Content:**
```javascript
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // Extract target URL parameter
    const targetUrl = url.searchParams.get('url');
    
    if (!targetUrl) {
      return new Response('Missing "url" query parameter', { status: 400 });
    }
    
    try {
      // Forward request through Cloudflare edge network
      const response = await fetch(targetUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body,
        // No caching - always fresh requests
        cache: 'no-store'
      });
      
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers
      });
      
    } catch (error) {
      return new Response(
        JSON.stringify({ error: error.message }),
        { 
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }
  }
};
```

#### 3. Deploy the Worker

```bash
# Deploy to Cloudflare
cd worker
wrangler deploy --name my-proxy-relay

# Get your deployed URL (e.g., https://my-proxy-relay.your-subdomain.workers.dev)
```

**Output Example:**
```
👉 Your worker is now available at:
   https://my-proxy-relay.your-subdomain.workers.dev

✅ Deployed successfully!
```

---

### Phase 2: Configure Proxy Pool Manager on VPS

#### 4. Create Configuration File

```bash
cd ~/projects/proxy-pool
nano config.yml
```

**config.yml Content:**
```yaml
# Proxy Pool Configuration
proxy_pool:
  min_proxies: 499
  max_proxies: 1000
  rotation_threshold: 40  # Requests per proxy before skip
  
cloudflare_relay:
  enabled: true
  endpoint: https://my-proxy-relay.your-subdomain.workers.dev
  daily_limit: 75000      # 75% of free tier
  
rate_limiting:
  max_concurrent_requests: 50
  min_delay_between_requests_ms: 500
  max_delay_between_requests_ms: 2000

monitoring:
  cpu_throttle_percent: 80
  memory_warn_mb: 2000
  storage_warn_gb: 180
```

#### 5. Install Proxy Pool Manager

```bash
# Copy scripts to VPS (if not already there)
# Or create them directly

# Make sure all scripts exist
ls -la *.py

# Test run with small batch
python3 generate_proxies.py 50
```

---

### Phase 3: Integration with Hermes Agent

#### 6. Create Hermes Integration Script

```bash
nano hermes_integration.py
```

**hermes_integration.py Content:**
```python
#!/usr/bin/env python3
"""
Hermes Agent Integration for Proxy Rotation
"""

import asyncio
import aiohttp
import yaml
import os
from datetime import datetime
from typing import Dict, List, Optional

class ProxyRotationManager:
    def __init__(self, config_path='config.yml'):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.proxy_pool = []
        self.request_counts = {}
        self.cloudflare_endpoint = None
        
        if self.config['cloudflare_relay']['enabled']:
            self.cloudflare_endpoint = self.config['cloudflare_relay']['endpoint']
    
    async def load_proxies(self):
        """Load proxies from file"""
        proxy_file = 'generated_proxy_result.txt'
        
        if not os.path.exists(proxy_file):
            print("Proxy file not found!")
            return False
        
        with open(proxy_file) as f:
            lines = f.readlines()
        
        self.proxy_pool = [line.strip() for line in lines if line.strip()]
        
        # Initialize counters
        for proxy in self.proxy_pool[:self.config['proxy_pool']['max_proxies']]:
            self.request_counts[proxy] = 0
        
        print(f"Loaded {len(self.proxy_pool)} proxies")
        return True
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy from pool with rotation logic"""
        if not self.proxy_pool:
            return None
        
        # Find proxy with lowest usage
        best_proxy = min(self.request_counts.keys(), 
                        key=lambda p: self.request_counts[p])
        
        # Check threshold
        if self.request_counts[best_proxy] >= self.config['proxy_pool']['rotation_threshold']:
            self.request_counts[best_proxy] = 0  # Reset after threshold
            return best_proxy
        
        self.request_counts[best_proxy] += 1
        return best_proxy
    
    async def make_request(self, prompt: str, model: str = "deepseek-v4-flash-free") -> Dict:
        """Make API request through selected proxy"""
        
        proxy_url = self.get_next_proxy()
        if not proxy_url:
            raise Exception("No proxies available")
        
        # Build full URL
        full_url = f"{proxy_url}"
        
        try:
            if self.cloudflare_endpoint:
                # Use Cloudflare relay for extra anonymity
                async with aiohttp.ClientSession() as session:
                    relay_url = f"{self.cloudflare_endpoint}?url={full_url}"
                    
                    payload = {
                        "model": model,
                        "prompt": prompt,
                        "temperature": 0.7
                    }
                    
                    async with session.post(relay_url, json=payload) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            return {"success": True, "result": result}
                        else:
                            return {"success": False, "error": f"HTTP {resp.status}"}
            else:
                # Direct proxy connection
                raise Exception("Cloudflare relay not configured")
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_stats(self) -> Dict:
        """Get current usage statistics"""
        total_requests = sum(self.request_counts.values())
        active_proxies = len([p for p, c in self.request_counts.items() if c > 0])
        
        return {
            "total_requests_made": total_requests,
            "active_proxies_used": active_proxies,
            "proxies_available": len(self.proxy_pool),
            "rotation_threshold": self.config['proxy_pool']['rotation_threshold'],
            "usage_percentage": round(total_requests / (len(self.proxy_pool) * 40) * 100, 2)
        }

async def main():
    manager = ProxyRotationManager()
    
    # Load proxies
    success = await manager.load_proxies()
    if not success:
        return
    
    # Make test request
    result = await manager.make_request("Hello, test request via proxy")
    
    print(f"Request result: {result}")
    print(f"\nStats: {manager.get_stats()}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Phase 4: Scheduled Tasks & Monitoring

#### 7. Set up Systemd Service

```bash
sudo nano /etc/systemd/system/proxy-manager.service
```

**Service Unit:**
```ini
[Unit]
Description=Proxy Pool Manager for OpenCode API
After=network.target

[Service]
Type=simple
User=engineer
WorkingDirectory=/home/engineer/projects/proxy-pool
ExecStart=/usr/bin/python3 proxy_rotator.py
Restart=always
RestartSec=60
Environment="PYTHONUNBUFFERED=1"

# Resource limits
MemoryMax=2G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
```

#### 8. Enable & Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable proxy-manager

# Start service
sudo systemctl start proxy-manager

# Check status
sudo systemctl status proxy-manager

# View logs
journalctl -u proxy-manager -f
```

---

### Phase 5: Web Dashboard (Optional)

#### 9. Create Simple Dashboard

```bash
nano dashboard.py
```

**dashboard.py Content:**
```python
from flask import Flask, render_template_string, jsonify
import yaml
import psutil

app = Flask(__name__)

with open('config.yml') as f:
    config = yaml.safe_load(f)

@app.route('/')
def dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head><title>Proxy Rotator Dashboard</title></head>
<body>
  <h1>🚀 Proxy Rotation Status</h1>
  
  <div id="stats">Loading...</div>
  
  <button onclick="refresh()">Refresh</button>
  
  <script>
    function refresh() {
      fetch('/api/stats').then(r => r.json()).then(data => {
        document.getElementById('stats').innerHTML = 
          `<pre>${JSON.stringify(data, null, 2)}</pre>`;
      });
    }
    
    // Auto-refresh every 10 seconds
    setInterval(refresh, 10000);
    refresh();
  </script>
</body>
</html>
    ''')

@app.route('/api/stats')
def stats():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/home').percent
    
    return jsonify({
        'cpu_usage': f'{cpu:.1f}%',
        'memory_usage': f'{mem:.1f}%',
        'disk_usage': f'{disk:.1f}%',
        'proxies_config': config['proxy_pool']['min_proxies'],
        'cloudflare_enabled': config['cloudflare_relay']['enabled'],
        'system_time': str(datetime.now())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

#### 10. Run Dashboard

```bash
pip install flask psutil pyyaml

# In separate terminal
python3 dashboard.py &

# Access at http://your-vip-ip:8080
```

---

## 🎨 Final Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│         HERMES AGENT ON ORACLE VPS                      │
│                                                         │
│  ┌──────────────┐                                        │
│  │Proxy Manager │ ◄── Generates & rotates              │
│  │   Script     │       proxies automatically          │
│  └──────┬───────┘                                        │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐                                        │
│  │ 9Router CLI  │ ◄── Routes traffic through           │
│  │   Runner     │       proxy pool                     │
│  └──────┬───────┘                                        │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐                                        │
│  │Cloudflare    │ ◄── Optional relay for extra         │
│  │   Worker     │       anonymity                       │
│  │  (Relay)     │                                        │
│  └──────┬───────┘                                        │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐                                        │
│  │OpenCode API  │ ◄── Receives requests                │
│  │  (Free)      │       from different IPs             │
│  └──────────────┘                                        │
└─────────────────────────────────────────────────────────┘

Monitoring:
┌─────────────────────────────────────────────────────────┐
│                 WEB DASHBOARD                           │
│                                                         │
│  http://localhost:8080                                  │
│  • Real-time CPU/RAM/Disk usage                         │
│  • Active proxy count                                   │
│  • Daily request counter                                │
│  • Alert notifications                                  │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Deployment Checklist

Before going live:

- [ ] All dependencies installed on VPS
- [ ] Cloudflare Worker deployed and functional
- [ ] Config.yml created with proper settings
- [ ] Proxy list loaded (500+ proxies)
- [ ] Systemd service created and enabled
- [ ] Web dashboard accessible (optional)
- [ ] Email/slack alerts configured (optional)
- [ ] Backup mechanism tested
- [ ] Health check scheduled (weekly recommended)

---

## 🚀 Quick Start Commands

After setup complete:

```bash
# Start proxy rotator
systemctl start proxy-manager

# Monitor logs
journalctl -u proxy-manager -f

# View dashboard
echo "Dashboard: http://YOUR_VIP_IP:8080"

# Check status
systemctl status proxy-manager

# Stop if needed
systemctl stop proxy-manager
```

---

## 💰 Cost Analysis

| Component | Monthly Cost |
|-----------|--------------|
| Oracle Cloud Free Tier | $0.00 |
| Cloudflare Workers | $0.00 (free tier) |
| Scripts/Software | $0.00 (open source) |
| Internet Bandwidth | Included in free tier |
| **TOTAL** | **$0.00/month** 🎉 |

---

*Implementation Complete!* 🚀
*Ready to deploy and start using!*

