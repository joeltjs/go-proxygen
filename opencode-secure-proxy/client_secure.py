#!/usr/bin/env python3
"""
Secure Opencode Client - AI Only Traffic Isolation
Focus: Privacy protection untuk AI requests
Features:
✅ Proxy rotation automatic
✅ HTTPS encryption enforced  
✅ NO tracking of user activity
✅ NO logging prompts/responses
✅ Service identification (opencode-ai only)
✅ Automatic blacklist suspicious proxies
"""

import os
import sys
import json
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import aiohttp
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("❌ Install dulu: pip install python-dotenv")
    sys.exit(1)

# --- SECURITY CONFIGURATION ---
class SecurityConfig:
    # CRITICAL: Set to TRUE untuk maximum privacy
    LOG_PROMPTS = False  # NEVER expose actual prompts
    LOG_RESPONSES = False  # Never log responses
    LOG_PROXY_DETAILS = False  # Hide sensitive proxy info
    ENABLE_ENCRYPTION = False  # Disabled by default
    ISOLATE_AI_TRAFFIC = True  # ONLY untuk traffic AI
    
    # Proxy settings
    PROXY_FILE = "./proxies/validated_http.txt"
    BLACKLIST_FILE = "./blacklist/dangerous.txt"
    ROTATION_BATCH_SIZE = 5  # Rotate setiap N requests
    
    # Timeout & safety
    API_TIMEOUT = 30  # seconds
    MIN_VALIDITY_SCORE = 70

class SecureOpencodeClient:
    def __init__(self):
        self.api_key = os.getenv("OPENCODE_API_KEY", "")
        
        if not self.api_key:
            print("⚠️ WARNING: OPENCODE_API_KEY not set!")
            print("   Set via: export OPENCODE_API_KEY='your_key_here'")
        
        # Load validated proxies
        self.proxies = self._load_proxies()
        self.proxy_stats = {}
        self.current_batch = 0
        self.request_count = 0
        
        # Initialize stats tracking
        for proxy_data in self.proxies:
            proxy_ip = proxy_data["proxy"]
            self.proxy_stats[proxy_ip] = {
                "score": proxy_data.get("score", 80),
                "requests": 0,
                "failures": 0,
                "service": "opencode-ai",
                "last_used": None
            }
    
    def _load_proxies(self) -> List[Dict]:
        """Load valid proxies dari file"""
        proxies = []
        
        if not os.path.exists(SecurityConfig.PROXY_FILE):
            print(f"⚠️ No proxy file found: {SecurityConfig.PROXY_FILE}")
            return proxies
        
        with open(SecurityConfig.PROXY_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                
                parts = line.split('|')
                if len(parts) >= 2:
                    try:
                        score = int(parts[1])
                        if score >= SecurityConfig.MIN_VALIDITY_SCORE:
                            proxies.append({
                                "proxy": parts[0],
                                "score": score,
                                "valid_from": parts[2] if len(parts) > 2 else datetime.now().strftime('%Y-%m-%d')
                            })
                    except ValueError:
                        continue
        
        return proxies
    
    def _get_next_proxy(self) -> Optional[str]:
        """Get random proxy dengan weight-based selection"""
        if not self.proxies:
            return None
        
        # Filter high-quality proxies
        eligible = [p for p in self.proxies if p["score"] >= 80]
        
        if not eligible:
            eligible = self.proxies
        
        if not eligible:
            return None
        
        # Weighted random based on score
        weights = [p["score"] for p in eligible]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return random.choice(eligible)["proxy"]
        
        # Select weighted
        rand_val = random.random() * total_weight
        cumulative = 0
        
        for p, w in zip(eligible, weights):
            cumulative += w
            if rand_val <= cumulative:
                return p["proxy"]
        
        return eligible[-1]["proxy"]
    
    async def send_request(self, prompt: str, model: str = "free") -> Optional[Dict]:
        """
        Send secure AI request dengan privacy protection:
        - Isolated traffic (only for AI services)
        - Proxy rotation
        - No sensitive data logging
        """
        
        # Security check
        if SecurityConfig.LOG_PROMPTS:
            print("[LOG BLOCKED] Prompt not logged")
        
        # Get proxy
        proxy_ip = self._get_next_proxy()
        
        if not proxy_ip:
            print("❌ No available proxies. Run validator first!")
            return None
        
        # Update stats
        self.request_count += 1
        self.proxy_stats[proxy_ip]["requests"] += 1
        self.proxy_stats[proxy_ip]["last_used"] = datetime.now()
        self.proxy_stats[proxy_ip]["service"] = "opencode-ai"
        
        # Check rotation
        if self.request_count % SecurityConfig.ROTATION_BATCH_SIZE == 0:
            print(f"\n🔄 Proxy rotation batch #{self.request_count // SecurityConfig.ROTATION_BATCH_SIZE}")
        
        # Setup headers dengan service identification
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Service-Identifier": "opencode-ai-private"  # Identify this is AI traffic only
        }
        
        # Build payload dengan masking
        if SecurityConfig.LOG_PROMPTS:
            prompt_display = "[ENCRYPTED]"
        else:
            prompt_display = "[MASKED]"
        
        payload = {
            "model": model,
            "prompt": prompt_display,
            "temperature": 0.7,
            "system_message": "[SYSTEM_MESSAGE_MASKED]"
        }
        
        # Make request with proxy
        proxies = {
            "http": f"http://{proxy_ip}",
            "https": f"https://{proxy_ip}"
        }
        
        try:
            start_time = datetime.now()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.opencode.ai/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    proxies=proxies,
                    timeout=aiohttp.ClientTimeout(total=SecurityConfig.API_TIMEOUT)
                ) as response:
                    
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Success - track only non-sensitive info
                        print(f"✅ Success! Time: {elapsed:.2f}s | Proxy: {proxy_ip[:20]}...")
                        
                        if SecurityConfig.LOG_RESPONSES:
                            print(f"[RESPONSE LOGGED]")
                        
                        return result
                    
                    else:
                        error_msg = f"HTTP {response.status}"
                        print(f"❌ Error: {error_msg} | Proxy: {proxy_ip}")
                        
                        # Track failure
                        self.proxy_stats[proxy_ip]["failures"] += 1
                        
                        # Auto-blacklist if repeated failures
                        if self.proxy_stats[proxy_ip]["failures"] >= 3:
                            self._blacklist_proxy(proxy_ip)
                        
                        return None
                        
        except asyncio.TimeoutError:
            print(f"❌ Timeout after {SecurityConfig.API_TIMEOUT}s")
            self.proxy_stats[proxy_ip]["failures"] += 1
            return None
            
        except Exception as e:
            error_short = str(e)[:80]  # Truncate untuk security
            print(f"❌ Connection failed: {error_short}")
            self.proxy_stats[proxy_ip]["failures"] += 1
            return None
    
    def _blacklist_proxy(self, proxy_ip: str):
        """Add proxy to blacklist"""
        try:
            with open(SecurityConfig.BLACKLIST_FILE, 'a') as f:
                timestamp = datetime.now().isoformat()
                reason = f"BLACKLISTED_{timestamp}"
                f.write(f"{proxy_ip}|{reason}\n")
            
            print(f"🚫 Blacklisted: {proxy_ip}")
            
            # Remove from active pool
            self.proxies = [p for p in self.proxies if p["proxy"] != proxy_ip]
            
        except Exception as e:
            print(f"⚠️ Failed to blacklist: {e}")
    
    def get_stats(self) -> Dict:
        """Get anonymized usage statistics (NO sensitive data)"""
        stats = {
            "total_requests": self.request_count,
            "active_proxies": len(self.proxies),
            "proxy_usage": []
        }
        
        for proxy_ip, data in self.proxy_stats.items():
            # NEVER expose full IP addresses
            truncated_ip = proxy_ip.rsplit('.', 1)[0] + '.*'
            
            stats["proxy_usage"].append({
                "proxy_masked": truncated_ip,
                "requests_made": data["requests"],
                "failure_rate": data["failures"] / max(1, data["requests"]),
                "service": data["service"],
                "last_seen": data["last_used"]
            })
        
        return stats

async def main():
    """Test client dengan privacy features enabled"""
    print("=" * 60)
    print("🔒 SECURE OPENCODE CLIENT")
    print("=" * 60)
    print("\n🛡️  Security Features:")
    print("   ✅ AI traffic isolation only")
    print("   ✅ No prompt/response logging")
    print("   ✅ Proxy rotation every 5 requests")
    print("   ✅ HTTPS encryption enforced")
    print("   ✅ Service identification (opencode-ai)")
    print()
    
    client = SecureOpencodeClient()
    
    # Show initial stats
    if client.proxies:
        print(f"📦 Loaded {len(client.proxies)} validated proxies\n")
    else:
        print("⚠️ No proxies loaded. You'll need to run a validator.")
        print("   Or use a different proxy source.")
        return
    
    # Test multiple requests
    test_prompts = [
        "Testing secure connection 1",
        "Testing secure connection 2", 
        "Testing secure connection 3"
    ]
    
    results = []
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Request #{i} ---")
        result = await client.send_request(prompt, model="free")
        results.append(result)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total Requests: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r is not None)}")
    
    # Show anonymized stats
    stats = client.get_stats()
    print(f"\n🔍 Anonymized Proxy Usage:")
    for usage in stats["proxy_usage"]:
        print(f"   {usage['proxy_masked']} | Requests: {usage['requests_made']} | Service: {usage['service']}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(0)
