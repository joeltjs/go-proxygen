#!/usr/bin/env python3
"""
Enhanced Proxy Validator - Supports HTTP dan SOCKS5
Dari GitHub repositories terpercaya:
1. https://github.com/proxifly/free-proxy-list
2. https://github.com/TheSpeedX/PROXY-List
3. https://github.com/rix4uni/fresh-proxy-list
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Tuple, List, Dict
import re

# File paths
VALIDATED_HTTP = "./proxies/validated_http.txt"
VALIDATED_SOCKS = "./proxies/validated_socks.txt"
BLACKLIST_FILE = "./blacklist/dangerous.txt"

TIMEOUT = aiohttp.ClientTimeout(total=8)
BATCH_SIZE = 20
MAX_PROXIES = 1000  # Limit untuk validasi cepat

async def test_http_proxy(proxy_str: str, session: aiohttp.ClientSession) -> Tuple[bool, int, str]:
    """Test HTTP proxy dengan timeout ketat"""
    if not proxy_str or ":" not in proxy_str:
        return False, 0, "invalid_format"
    
    try:
        # Format: IP:PORT
        parts = proxy_str.split(":")
        if len(parts) < 2:
            return False, 0, "malformed"
        
        ip_port = proxy_str
        
        async with session.get(
            "https://cloudflare.com",
            proxy=f"http://{ip_port}",
            timeout=TIMEOUT,
            allow_redirects=False,
            ssl=True  # Force HTTPS validation
        ) as resp:
            
            status = resp.status
            has_redirect = len(resp.history) > 0
            
            if status == 200 and not has_redirect:
                return True, 90, "valid_fast"
            elif status == 200:
                return True, 75, "valid_with_redirect"
            else:
                return False, 0, f"status_{status}"
                
    except asyncio.TimeoutError:
        return False, 0, "timeout"
    except Exception as e:
        error = str(e)[:30]
        return False, 0, f"error_{error}"

async def test_socks5_proxy(proxy_str: str, session: aiohttp.ClientSession) -> Tuple[bool, int, str]:
    """Test SOCKS5 proxy"""
    if not proxy_str or "socks5://" not in proxy_str:
        return False, 0, "invalid_socks_format"
    
    try:
        # Extract IP:PORT dari socks5:// URL
        url_match = re.match(r'socks5://([^/]+)', proxy_str)
        if not url_match:
            return False, 0, "parse_error"
        
        ip_port = url_match.group(1)
        
        # Test dengan SOCKS5 proxy
        connector = aiohttp.TCPConnector()
        proxy_url = f"socks5://{ip_port}"
        
        async with session.get(
            "https://cloudflare.com",
            proxy=proxy_url,
            timeout=TIMEOUT,
            connector=connector
        ) as resp:
            if resp.status == 200 and len(resp.history) == 0:
                return True, 90, "valid"
            elif resp.status == 200:
                return True, 75, "redirect"
            else:
                return False, 0, f"status_{resp.status}"
                
    except Exception as e:
        error = str(e)[:30]
        return False, 0, f"socks_error_{error}"

def load_proxies_from_files():
    """Load proxies dari semua sumber file"""
    all_proxies = {
        "http": [],
        "socks5": []
    }
    
    # Source 1: proxifly (SOCKS5)
    proxifly_path = "./proxies/proxifly_raw.txt"
    if os.path.exists(proxifly_path):
        with open(proxifly_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith("socks5://"):
                    all_proxies["socks5"].append(line)
        print(f"✅ Loaded {len(all_proxies['socks5'])} SOCKS5 proxies dari proxifly")
    
    # Source 2: TheSpeedX (HTTP)
    thespeedx_path = "./proxies/thespeedx_raw.txt"
    if os.path.exists(thespeedx_path):
        with open(thespeedx_path, 'r') as f:
            for line in f:
                line = line.strip()
                if ":" in line and not line.startswith(("http://", "https://")):
                    all_proxies["http"].append(line)
        print(f"✅ Loaded {len(all_proxies['http'])} HTTP proxies dari TheSpeedX")
    
    # Combine dan limit
    total_http = len(all_proxies["http"])
    total_socks = len(all_proxies["socks5"])
    
    if total_http + total_socks > MAX_PROXIES:
        scale_http = max(1, int(MAX_PROXIES * 0.7))
        scale_socks = max(1, int(MAX_PROXIES * 0.3))
        
        if total_http > scale_http:
            random.shuffle(all_proxies["http"])
            all_proxies["http"] = all_proxies["http"][:scale_http]
        
        if total_socks > scale_socks:
            random.shuffle(all_proxies["socks5"])
            all_proxies["socks5"] = all_proxies["socks5"][:scale_socks]
    
    return all_proxies

async def main():
    print("🔐 Enhanced Secure Proxy Validator")
    print("=" * 50)
    
    # Import needed modules
    global os, random
    import os
    import random
    
    # Load proxies
    proxies = load_proxies_from_files()
    
    http_count = len(proxies["http"])
    socks_count = len(proxies["socks5"])
    
    print(f"\n📦 Total: {http_count + socks_count} proxies")
    print(f"   HTTP: {http_count}")
    print(f"   SOCKS5: {socks_count}")
    
    if http_count == 0 and socks_count == 0:
        print("❌ No proxies found!")
        return
    
    valid_http = []
    valid_socks = []
    blacklisted = []
    
    # Validate HTTP proxies
    if http_count > 0:
        print(f"\n🔄 Validating HTTP proxies...")
        
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(proxies["http"]), BATCH_SIZE):
                batch = proxies["http"][i:i+BATCH_SIZE]
                results = await asyncio.gather(*[
                    test_http_proxy(p, session) for p in batch
                ], return_exceptions=True)
                
                for j, result in enumerate(results):
                    proxy = batch[j]
                    
                    if isinstance(result, Exception):
                        blacklisted.append((proxy, str(result)))
                        continue
                    
                    is_valid, score, reason = result
                    if is_valid:
                        valid_http.append(f"{proxy}|{score}|{datetime.now().strftime('%Y-%m-%d')}")
                    else:
                        blacklisted.append((proxy, reason))
                
                progress = min(i + len(batch), http_count)
                current_valid = len([v for v in valid_http])
                print(f"\rHTTP [{progress}/{http_count}] ✓ {current_valid}", end="")
    
    # Validate SOCKS5 proxies  
    if socks_count > 0:
        print(f"\n\n🔄 Validating SOCKS5 proxies...")
        
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(proxies["socks5"]), BATCH_SIZE):
                batch = proxies["socks5"][i:i+BATCH_SIZE]
                results = await asyncio.gather(*[
                    test_socks5_proxy(p, session) for p in batch
                ], return_exceptions=True)
                
                for j, result in enumerate(results):
                    proxy = batch[j]
                    
                    if isinstance(result, Exception):
                        blacklisted.append((proxy, str(result)))
                        continue
                    
                    is_valid, score, reason = result
                    if is_valid:
                        valid_socks.append(f"{proxy}|{score}|{datetime.now().strftime('%Y-%m-%d')}")
                    else:
                        blacklisted.append((proxy, reason))
                
                progress = min(i + len(batch), socks_count)
                current_valid = len([v for v in valid_socks])
                print(f"\rSOCKS5 [{progress}/{socks_count}] ✓ {current_valid}", end="")
    
    # Save results
    with open(VALIDATED_HTTP, 'w') as f:
        f.write('\n'.join(valid_http))
    
    with open(VALIDATED_SOCKS, 'w') as f:
        f.write('\n'.join(valid_socks))
    
    with open(BLACKLIST_FILE, 'w') as f:
        for proxy, reason in blacklisted:
            f.write(f"{proxy}|{reason}\n")
    
    print("\n\n" + "=" * 50)
    print("✅ VALIDATION COMPLETE!")
    print(f"   HTTP Valid: {len(valid_http)}")
    print(f"   SOCKS5 Valid: {len(valid_socks)}")
    print(f"   Rejected: {len(blacklisted)}")
    
    if valid_http:
        avg_http = sum(int(v.split('|')[1]) for v in valid_http) / len(valid_http)
        print(f"   HTTP Avg Score: {avg_http:.1f}")
    
    if valid_socks:
        avg_socks = sum(int(v.split('|')[1]) for v in valid_socks) / len(valid_socks)
        print(f"   SOCKS5 Avg Score: {avg_socks:.1f}")
    
    print(f"\n💾 Saved:")
    print(f"   ✓ HTTP: {VALIDATED_HTTP}")
    print(f"   ✓ SOCKS5: {VALIDATED_SOCKS}")
    print(f"   ✗ Blacklist: {BLACKLIST_FILE}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
