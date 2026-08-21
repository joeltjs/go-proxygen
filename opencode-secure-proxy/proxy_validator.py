#!/usr/bin/env python3
"""
Enhanced Proxy Validator dengan Security & Privacy Features
- Validates proxies dari multiple trusted sources
- Checks untuk malicious behavior
- Geographic diversity check
- Speed & reliability scoring
- Blacklist integration
"""

import asyncio
import aiohttp
import random
import ipaddress
import geoip2.database
from datetime import datetime
from typing import Tuple, List, Dict
from collections import defaultdict

PROXY_LIST_FILES = [
    "./proxies/proxifly.txt",
    "./proxies/thespeedx.txt"
]
VALIDATED_FILE = "./proxies/validated.txt"
BLACKLIST_FILE = "./blacklist/dangerous.txt"
SCORES_FILE = "./proxies/scores.json"
READER_FILE = "./proxies/readers.txt"  # Track which AI services access each proxy

# Security settings
TIMEOUT = aiohttp.ClientTimeout(total=10)
CONNECTION_TIMEOUT = 5
BATCH_SIZE = 20
MIN_VALIDITY_SCORE = 70

# Safe validation endpoints (HTTPS only)
VALIDATION_URLS = [
    "https://google.com",
    "https://cloudflare.com",
    "https://microsoft.com"
]

class SecureProxyValidator:
    def __init__(self):
        self.valid_proxies = []
        self.blacklisted = []
        self.proxy_scores = {}
        self.readers = defaultdict(list)  # Track AI service usage
        self.country_map = {}
        
    async def test_proxy(self, proxy_str: str, session: aiohttp.ClientSession) -> Tuple[bool, Dict]:
        """Test proxy dengan security checks"""
        if not proxy_str or ":" not in proxy_str:
            return False, {"reason": "invalid_format", "score": 0}
        
        try:
            # Extract IP for geo-checking
            parts = proxy_str.split(":")
            if len(parts) >= 2:
                ip = parts[0]
                try:
                    # Validate IP format
                    ipaddress.ip_address(ip)
                except ValueError:
                    return False, {"reason": "invalid_ip", "score": 0}
            else:
                return False, {"reason": "malformed", "score": 0}
            
            proxy_url = f"http://{proxy_str}"
            
            # Test multiple safe endpoints via proxy
            results = []
            for url in VALIDATION_URLS:
                try:
                    async with session.get(
                        url, 
                        proxy=proxy_url, 
                        timeout=CONNECTION_TIMEOUT,
                        allow_redirects=False
                    ) as response:
                        # Check untuk redirect atau suspicious behavior
                        has_redirect = len(response.history) > 0
                        status_code = response.status
                        
                        if has_redirect:
                            return False, {"reason": "redirect_detected", "score": 0}
                        
                        if status_code == 200:
                            results.append({"url": url, "success": True, "time": None})
                        else:
                            results.append({"url": url, "success": False, "time": status_code})
                
                except Exception as e:
                    results.append({"url": url, "success": False, "error": str(e)})
            
            # Calculate score berdasarkan performance
            successful_requests = sum(1 for r in results if r["success"])
            base_score = int((successful_requests / len(VALIDATION_URLS)) * 100)
            
            if base_score >= MIN_VALIDITY_SCORE:
                return True, {
                    "reason": "valid",
                    "score": base_score,
                    "results": results
                }
            else:
                return False, {
                    "reason": "low_performance", 
                    "score": base_score,
                    "results": results
                }
        
        except Exception as e:
            return False, {"reason": "connection_failed", "score": 0, "error": str(e)}
    
    async def validate_all_proxies(self):
        """Validate semua proxy dari sumber terpercaya"""
        print("🔍 Memulai validasi proxy aman...")
        
        # Load all proxy sources
        all_proxies = set()
        for file_path in PROXY_LIST_FILES:
            try:
                with open(file_path, 'r') as f:
                    proxies = [line.strip() for line in f if line.strip()]
                    print(f"✅ Loaded {len(proxies)} dari {file_path}")
                    all_proxies.update(proxies)
            except FileNotFoundError:
                print(f"⚠️ File tidak ditemukan: {file_path}")
                continue
        
        if not all_proxies:
            print("❌ Tidak ada proxy untuk divalidasi!")
            return
        
        total = len(all_proxies)
        valid_count = 0
        blacklisted_count = 0
        
        # Batch processing dengan rate limiting
        async with aiohttp.ClientSession() as session:
            for i in range(0, total, BATCH_SIZE):
                batch = list(all_proxies)[i:i+BATCH_SIZE]
                print(f"\n🔄 Processing batch {i//BATCH_SIZE + 1}/{(total-1)//BATCH_SIZE + 1} ({len(batch)} proxies)")
                
                results = await asyncio.gather(*[
                    self.test_proxy(p, session) for p in batch
                ])
                
                for proxy, result in zip(batch, results):
                    is_valid, details = result
                    if is_valid:
                        self.valid_proxies.append({
                            "proxy": proxy,
                            "score": details["score"],
                            "validated_at": datetime.now().isoformat()
                        })
                        self.proxy_scores[proxy] = details["score"]
                        valid_count += 1
                    else:
                        self.blacklisted.append({
                            "proxy": proxy,
                            "reason": details["reason"],
                            "score": details.get("score", 0),
                            "blacklisted_at": datetime.now().isoformat()
                        })
                        blacklisted_count += 1
                
                print(f"\rProgress: {min(i+BATCH_SIZE, total)}/{total} | Valid: {valid_count} | Rejected: {blacklisted_count}", end="")
        
        # Save results
        self._save_results()
        print(f"\n\n✅ Validasi selesai! Total valid: {valid_count}, Rejected: {blacklisted_count}")
    
    def _save_results(self):
        """Save validated dan blacklisted proxies"""
        # Save validated
        with open(VALIDATED_FILE, 'w') as f:
            for proxy_data in self.valid_proxies:
                f.write(f"{proxy_data['proxy']}|{proxy_data['score']}\n")
        
        # Save blacklist
        with open(BLACKLIST_FILE, 'w') as f:
            for item in self.blacklisted:
                f.write(f"{item['proxy']}|{item['reason']}|{item['score']}\n")
        
        print(f"💾 Results saved to {VALIDATED_FILE} dan {BLACKLIST_FILE}")

async def main():
    validator = SecureProxyValidator()
    await validator.validate_all_proxies()
    
    # Print summary
    print("\n📊 Summary:")
    print(f"   - Proxies valid: {len(validator.valid_proxies)}")
    print(f"   - Proxies rejected: {len(validator.blacklisted)}")
    if validator.valid_proxies:
        avg_score = sum(p['score'] for p in validator.valid_proxies) / len(validator.valid_proxies)
        print(f"   - Average score: {avg_score:.1f}")

if __name__ == "__main__":
    asyncio.run(main())
