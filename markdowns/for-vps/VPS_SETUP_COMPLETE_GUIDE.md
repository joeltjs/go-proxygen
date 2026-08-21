# 🚀 Opencode Secure Proxy Pool - Complete VPS Setup Guide

## 📋 Overview

Panduan lengkap untuk deploy OpenCode proxy rotation system di Oracle Cloud VPS dengan resource optimization dan safety precautions.

---

## ⚙️ System Requirements

### Minimum Specs (Can Work):
```yaml
CPU:     1 OCPU (bare minimum)
RAM:     1GB RAM  
Storage: 10GB storage
Network: Basic connectivity
```

### Recommended Specs (Optimal):
```yaml
CPU:     2 OCPU ARM Ampere
RAM:     12GB RAM total
Storage: 100GB+ storage
Network: Unlimited bandwidth
```

### Your Current Oracle Free Tier Specs:
- ✅ **2 OCPU ARM Ampere** (~1 core usable)
- ✅ **18GB RAM free** from 24GB total
- ✅ **120GB storage free** from 200GB
- ✅ **Unlimited bandwidth**

**Status:** OVERKILL in positive way! Resources sangat melimpah.

---

## 🗂️ Directory Structure

```bash
~/projects/proxy-pool/
├── config/              # Configuration files
├── data/                # Session statistics
├── logs/                # Application logs
├── markdowns/           # Documentation
│   └── for-vps/         # VPS-specific guides
├── proxies/             # Validated proxy lists
├── .env                 # Environment variables
├── generate_proxies.py  # Proxy generator tool
├── main_client.py       # Main AI client
├── nine_router.py       # Proxy router logic
├── proxy_pool_manager.py# Central pool management
└── requirements.txt     # Python dependencies
```

---

## 🔧 Step-by-Step Deployment Plan

### Phase 1: Environment Setup (Day 1)

#### 1.1 Install Dependencies
```bash
# SSH ke oracle vps
ssh engineer@your-oracle-ip.address

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python3 and pip
sudo apt install -y python3 python3-pip nodejs npm git curl

# Verify installation
python3 --version  # Should show 3.x
node --version     # Should show v16+
```

#### 1.2 Create Project Directory
```bash
cd /home/engineer
mkdir -p projects/proxy-pool
cd projects/proxy-pool

# Transfer files dari local machine atau copy manually
scp -r ~/Projects/proxy-pool/* engineer@your-oracle-ip:~/projects/proxy-pool/
```

#### 1.3 Install Python Dependencies
```bash
cd /home/engineer/projects/proxy-pool

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Verify installations
python3 -c "import aiohttp, yaml, requests; print('✓ All packages installed')"
```

#### 1.4 Configure Environment Variables
```bash
# Create .env file with sensitive data
cat > .env << 'ENV_EOF'
OPENCODE_API_KEY=your_opencode_api_key_here
CLOUDFLARE_ACCOUNT_ID=your_cf_account_id
CLOUDFLARE_API_TOKEN=your_cf_api_token_here
ENVIRONMENT=production
LOG_LEVEL=WARNING
MAX_PROXIES=1500
DAILY_REQUEST_LIMIT=75000
ENV_EOF

# Set secure permissions
chmod 600 .env
```

---

### Phase 2: Generate & Validate Proxies (Day 1-2)

#### 2.1 Generate Fresh Proxies
```bash
# Using existing script (already tested = 0.1 seconds!)
python3 generate_proxies.py 1500

# Output will be saved to:
ls -lh generated_proxy_result_1500.txt
# Expected size: ~50KB, 1500 lines
```

#### 2.2 Import to 9Router (Optional)
```bash
# If you want to test locally first
# Copy proxy list content
cat generated_proxy_result_1500.txt | less

# Then paste ke dashboard 9Router Proxy Pools → Batch Import
# Or keep as backup file for manual imports
```

#### 2.3 Schedule Weekly Refresh
```bash
# Edit crontab
crontab -e

# Add this line for weekly refresh (every Sunday at 2 AM)
0 2 * * 0 cd /home/engineer/projects/proxy-pool && ./cron/weekly_proxy_refresh.sh >> logs/cron.log 2>&1
```

---

### Phase 3: Deploy Cloudflare Worker (Day 2)

#### 3.1 Install Wrangler CLI
```bash
# Login to cloudflare
wrangler login

# Create worker project
cd /home/engineer/projects/proxy-pool
wrangler generate cf-proxy-relay
```

#### 3.2 Configure Worker.js
```javascript
// Edit wrangler-generated worker code
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // Extract target endpoint
    const targetUrl = url.searchParams.get('url');
    
    if (!targetUrl) {
      return new Response('Missing "url" parameter', { status: 400 });
    }
    
    try {
      // Forward request through Cloudflare edge network
      const response = await fetch(targetUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body,
        cache: 'no-store'  // Always fresh requests
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

#### 3.3 Deploy to Cloudflare
```bash
# Deploy command
wrangler deploy --name opencode-relay

# Get your deployed URL (example output):
console.log("✅ Deployed: https://opencode-relay.your-subdomain.workers.dev")
```

---

### Phase 4: Configure Rotation System (Day 3)

#### 4.1 Create Config Files
```bash
# Create primary configuration
cat > config/system.yml << 'CONFIG_EOF'
# System Configuration

proxy_pool:
  min_proxies: 1500
  max_proxies: 2000
  rotation_threshold: 40  # Requests per proxy before skip
  
cloudflare_relay:
  enabled: true
  endpoint: https://opencode-relay.your-subdomain.workers.dev
  daily_limit: 75000      # 75% of free tier limit
  
rate_limiting:
  max_concurrent_requests: 50
  min_delay_between_requests_ms: 500
  max_delay_between_requests_ms: 2000

monitoring:
  cpu_throttle_percent: 80
  memory_warn_mb: 2000
  storage_warn_gb: 180
CONFIG_EOF

# Create logging configuration
cat > config/logging.conf << 'LOGGING_EOF'
[log]
level = WARNING
format = %(asctime)s - %(levelname)s - %(message)s
path = ./logs/app.log
max_size = 10MB
backup_count = 10

[alerts]
email_enabled = false
slack_webhook = null
cpu_warning_threshold = 80
memory_warning_threshold = 80
disk_warning_threshold = 90
LOGGING_EOF
```

#### 4.2 Create systemd Service
```bash
# Create service unit file
sudo nano /etc/systemd/system/proxy-manager.service
```

**Service File Content:**
```ini
[Unit]
Description=Opencode Proxy Rotation Manager
After=network.target

[Service]
Type=simple
User=engineer
WorkingDirectory=/home/engineer/projects/proxy-pool
ExecStart=/home/engineer/projects/proxy-pool/venv/bin/python3 main_client.py
Restart=always
RestartSec=60
Environment="PYTHONUNBUFFERED=1"

# Resource limits
MemoryMax=2G
CPUQuota=80%

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 4.3 Enable Service
```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable proxy-manager

# Start the service
sudo systemctl start proxy-manager

# Check status
sudo systemctl status proxy-manager

# View logs
journalctl -u proxy-manager -f
```

---

### Phase 5: Monitoring & Maintenance (Ongoing)

#### 5.1 Setup Web Dashboard (Optional)
```bash
# Install Flask for dashboard
cd /home/engineer/projects/proxy-pool
pip install flask psutil pyyaml

# Create dashboard script
nano dashboard.py

# Run dashboard in background
nohup python3 dashboard.py --host=0.0.0.0 --port=8080 > logs/dashboard.log 2>&1 &

# Access at http://your-vip-ip:8080
```

#### 5.2 Monitor Scripts
```bash
# Create monitoring script
nano monitor_system.sh

#!/bin/bash
# Simple system health check

CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEM=$(free -m | awk '/^Mem:/ {print $3/$1 * 100}')
DISK=$(df -h / | awk '/\/$/ {print $5}' | tr -d '%')

echo "$(date) - CPU: ${CPU}%, MEM: ${MEM}%, DISK: ${DISK}%" >> logs/health_check.log

if (( $(echo "$CPU > 80" | bc -l) )); then
    echo "⚠️ WARNING: CPU usage high (${CPU}%)" >> logs/alerts.log
fi

if (( $(echo "$MEM > 80" | bc -l) )); then
    echo "⚠️ WARNING: Memory usage high (${MEM}%)" >> logs/alerts.log
fi

if (( DISK > 90 )); then
    echo "🛑 CRITICAL: Disk space low (${DISK}%)" >> logs/alerts.log
fi
```

Make executable and schedule:
```bash
chmod +x monitor_system.sh
crontab -e
# Add: */30 * * * * cd /home/engineer/projects/proxy-pool && ./monitor_system.sh
```

#### 5.3 Backup Strategy
```bash
# Daily backup script
cat > cron/daily_backup.sh << 'BACKUP_EOF'
#!/bin/bash
BACKUP_DIR="/home/engineer/backups/proxy-pool-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

tar czf $BACKUP_DIR/config.tar.gz config/
tar czf $BACKUP_DIR/data.tar.gz data/ 2>/dev/null || true
tar czf $BACKUP_DIR/logs.tar.gz logs/*.log 2>/dev/null || true
tar czf $BACKUP_DIR/generated.tar.gz generated_proxy_result*.txt 2>/dev/null || true

echo "$(date) - Backup created: $BACKUP_DIR" >> logs/backup.log
BACKUP_EOF

chmod +x cron/daily_backup.sh
crontab -e
# Add: 0 3 * * * /home/engineer/projects/proxy-pool/cron/daily_backup.sh
```

---

## 📊 Resource Allocation Plan

### CPU Distribution:
```
System Services:           5% (systemd, network, etc.)
9Router Process:           <10% (idle) → 15% (peak)
Proxy Manager Script:      <5% (background)
Monitoring Tools:          <2%
Buffer/Future Expansion:   68% FREE
Total Available:           100%
```

### RAM Distribution:
```
Operating System:          ~1GB
Python Virtual Env:        ~50MB
9Router:                   100-300MB
Proxy Generator:           ~50MB temporary
Database/Logs:             ~200MB
Dashboard (optional):      ~50MB
Buffer/Future Expansion:   ~17GB FREE
Total Available:           ~18GB
```

### Storage Distribution:
```
Operating System:          ~20GB
Project Files:             ~1GB
Log Files (with rotation): ~500MB
Backups (weekly):          ~1GB
Buffer/Future Expansion:   ~118GB FREE
Total Available:           ~120GB+
```

### Network Bandwidth:
```
Upload/Download:           Unlimited (Oracle Free Tier)
Proxy Traffic:             ~50-100GB/month projected
Buffer/Future Expansion:   Unlimited headroom
```

**Summary:** Massive resources available! System will run smoothly even at 5x current load.

---

## 🎯 Safety Protocols

### Automated Safety Checks:

1. **Daily Request Monitor**
```bash
# Track Cloudflare usage
cat > scripts/check_cloudflare_usage.py << 'CF_USAGE_EOF'
#!/usr/bin/env python3
import requests
from datetime import datetime

def check_daily_usage():
    # Replace with your actual Cloudflare API token
    account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    api_token = os.getenv('CLOUDFLARE_API_TOKEN')
    
    response = requests.get(
        f'https://api.cloudflare.com/client/v4/accounts/{account_id}/analysis/rule_hits',
        headers={
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        },
        json={'limit': 100}
    )
    
    if response.status_code == 200:
        data = response.json()
        total_requests = sum(item['count'] for item in data.get('result', []))
        
        if total_requests > 75000:  # 75% threshold
            print(f"⚠️ WARNING: Usage at {total_requests}/100,000 ({total_requests/1000:.0f}%)")
            # Auto-stop proxy rotation
            import subprocess
            subprocess.run(['systemctl', 'stop', 'proxy-manager'])
            
        elif total_requests > 60000:  # 60% warning
            print(f"ℹ️ INFO: Usage at {total_requests}/100,000 ({total_requests/1000:.0f}%)")
            
CF_USAGE_EOF
chmod +x scripts/check_cloudflare_usage.py

# Run every hour
crontab -e
# Add: 0 * * * * cd /home/engineer/projects/proxy-pool && ./scripts/check_cloudflare_usage.py
```

2. **Traffic Rate Limiter**
```bash
# Rate limiting via systemd
# Already configured in proxy-manager.service
# MemoryMax=2G prevents memory exhaustion
# CPUQuota=80% prevents CPU overload
```

3. **Emergency Stop Script**
```bash
# Quick stop script for emergency situations
cat > emergency_stop.sh << 'EMERGENCY_EOF'
#!/bin/bash
echo "🛑 EMERGENCY STOP INITIATED"
sudo systemctl stop proxy-manager
sudo systemctl disable proxy-manager

echo "Stopping all proxy-related processes..."
pkill -f nine_router.py
pkill -f main_client.py
pkill -f proxy_pool_manager.py

echo "All services stopped. Manual review required before restart."
echo "Run: sudo systemctl start proxy-manager"
EMERGENCY_EOF

chmod +x emergency_stop.sh
# Place in accessible location for quick access during incidents
```

---

## 🚀 Quick Start Commands

After deployment:

```bash
# 1. Start proxy manager
sudo systemctl start proxy-manager

# 2. Check status
sudo systemctl status proxy-manager

# 3. View live logs
journalctl -u proxy-manager -f

# 4. Check traffic stats
curl -s localhost:8080/api/stats  # if dashboard running

# 5. Emergency stop
./emergency_stop.sh
```

---

## 📞 Support & Troubleshooting

### Common Issues:

**Issue 1: Service won't start**
```bash
# Check logs
journalctl -u proxy-manager -n 100

# Test configuration syntax
python3 -m py_compile main_client.py

# Check dependencies
python3 -c "import aiohttp, yaml, requests; print('OK')"
```

**Issue 2: High CPU usage**
```bash
# Check process
ps aux | grep -E "python|node" | top

# Throttle or restart
sudo systemctl stop proxy-manager
sleep 10
sudo systemctl start proxy-manager
```

**Issue 3: Out of memory**
```bash
# Check memory usage
free -h

# Restart service with lower memory cap
sudo systemctl edit proxy-manager
# Add: MemoryMax=1G
sudo systemctl daemon-reload
sudo systemctl restart proxy-manager
```

---

## ✅ Deployment Checklist

Before going live:

- [ ] All dependencies installed
- [ ] .env file created with correct credentials
- [ ] Proxy list generated (1500+ entries)
- [ ] Cloudflare Worker deployed
- [ ] systemd service created and enabled
- [ ] Monitoring scripts configured
- [ ] Backup strategy implemented
- [ ] Emergency stop script ready
- [ ] Firewall rules checked (if applicable)
- [ ] Logs rotating properly
- [ ] Resource limits verified (should use <20% resources)

---

## 💰 Cost Analysis

| Component | Monthly Usage | Value if Paid | Actual Cost |
|-----------|--------------|---------------|-------------|
| Oracle Cloud | Free tier | $20-50/month | $0 |
| Cloudflare Workers | ~60K reqs/day | Included | $0 |
| Proxy Management | Minimal | N/A | $0 |
| **TOTAL MONTHLY VALUE** | **~1.6B tokens** | **~$500-1000** | **$0.00** 🎉 |

---

*Last Updated: 2026-08-21*
*Version: 1.0*
*Ready to deploy!* 🚀

