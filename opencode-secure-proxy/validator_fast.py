#!/usr/bin/env python3
"""
Fast & Secure Proxy Validator - Optimized untuk privacy protection
Focus pada speed + security dengan batch size yang manageable
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Tuple, List

# Sources terpercaya
PROXY_SOURCES = [
    ("proxifly", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.txt"),
    ("thespeedx", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt")
]

VALIDATED_FILE = "./proxies/validated.txt"
BLACKLIST_FILE = "./blacklist/dangerous.txt"
TIMELIMIT_FILE = "./proxies/timelimit.txt"

TIMEOUT = aiohttp.ClientTimeout(total=8)
BATCH_SIZE = 15  # Lebih kecil untuk safety
MAX_TOTAL_PROXY = 500  # Batas max proxy untuk di-validate

async def test_proxy(proxy_str: str, session: aiohttp.ClientSession) -> Tuple[bool, int, str]:
    """Test single proxy dengan timeout ketat"""
    if not proxy_str or ":" not in proxy_str:
        return False, 0, "invalid"
    
    try:
        ip_port = proxy_str.split(":")
        if len(ip_port) < 2:
            return False, 0, "malformed"
        
        proxy_url = f"http://{proxy_str}"
        
        async with session.get(
            "https://google.com",
            proxy=proxy_url,
            timeout=TIMEOUT,
            allow_redirects=False
        ) as resp:
            
            # Check response
            if resp.status == 200 and len(resp.history) == 0:
                return True, 95, "valid_fast"
            elif resp.status == 200:
                return True, 70, "valid_slow"
            else:
                return False, resp.status, "status_error"
                
    except Exception as e:
        error_msg = str(e)[:50]
        return False, 0, error_msg

async def main():
    print("🔐 Fast Secure Proxy Validator")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   Max proxies: {MAX_TOTAL_PROXY}")
    print()
    
    # Download sources
    print("📥 Downloading proxy lists...")
    all_proxies = []
    
    for name, url in PROXY_SOURCES:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    content = await resp.text()
                    proxies = [p.strip() for p in content.split('\n') if p.strip()]
                    
                    if len(proxies) > (MAX_TOTAL_PROXY // len(PROXY_SOURCES)):
                        proxies = proxies[:MAX_TOTAL_PROXY // len(PROXY_SOURCES)]
                    
                    all_proxies.extend(proxies)
                    print(f"   ✅ {name}: {len(proxies)} proxies")
                    
        except Exception as e:
            print(f"   ⚠️ Failed to download {name}: {e}")
            continue
    
    # Limit total
    if len(all_proxies) > MAX_TOTAL_PROXY:
        all_proxies = all_proxies[:MAX_TOTAL_PROXY]
        print(f"\n⚠️ Limited to {MAX_TOTAL_PROXY} proxies for faster validation")
    
    print(f"\n🔄 Validating {len(all_proxies)} proxies...\n")
    
    valid_proxies = []
    blacklisted = []
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(all_proxies), BATCH_SIZE):
            batch = all_proxies[i:i+BATCH_SIZE]
            results = await asyncio.gather(*[
                test_proxy(p, session) for p in batch
            ], return_exceptions=True)
            
            batch_valid = 0
            batch_black = 0
            
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    blacklisted.append((batch[j], str(result)))
                    batch_black += 1
                    continue
                
                is_valid, score, reason = result
                if is_valid:
                    valid_proxies.append(f"{batch[j]}|{score}|{datetime.now().strftime('%Y-%m-%d')}")
                    batch_valid += 1
                else:
                    blacklisted.append((batch[j], f"{reason}"))
                    batch_black += 1
            
            progress = min(i + len(batch), len(all_proxies))
            print(f"\r[{progress}/{len(all_proxies)}] ✓ {batch_valid} | ✗ {batch_black}", end="")
    
    # Save results
    with open(VALIDATED_FILE, 'w') as f:
        f.write('\n'.join(valid_proxies))
    
    with open(BLACKLIST_FILE, 'w') as f:
        for proxy, reason in blacklisted:
            f.write(f"{proxy}|{reason}\n")
    
    print(f"\n\n✅ DONE!")
    print(f"   Valid: {len(valid_proxies)}")
    print(f"   Rejected: {len(blacklisted)}")
    
    if valid_proxies:
        avg_score = sum(int(v.split('|')[1]) for v in valid_proxies) / len(valid_proxies)
        print(f"   Avg Score: {avg_score:.1f}")
        
        print(f"\n💾 Saved:")
        print(f"   ✓ {VALIDATED_FILE}")
        print(f"   ✗ {BLACKLIST_FILE}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted")
