#!/usr/bin/env python3
"""
ULTRA-FAST Proxy Validator - Fokus pada kecepatan + security minimal
Batasan ketat untuk menghindari hang
"""

import asyncio
import aiohttp
from datetime import datetime
import random

# Simpler setup
VALIDATED_HTTP = "./proxies/validated_http.txt"
BLACKLIST = "./blacklist/dangerous.txt"

TIMEOUT = aiohttp.ClientTimeout(total=5)  # Sangat cepat!
BATCH_SIZE = 10  # Batch sangat kecil
MAX_PROXY_COUNT = 200  # Max total proxies

async def quick_test(proxy_str: str, session: aiohttp.ClientSession) -> bool:
    """Ultra-fast test - hanya check basic connectivity"""
    try:
        async with session.get(
            "https://cloudflare.com",
            proxy=f"http://{proxy_str}",
            timeout=TIMEOUT,
            allow_redirects=False
        ) as resp:
            return resp.status == 200 and len(resp.history) == 0
    except:
        return False

def load_proxies():
    """Load max 200 HTTP proxies dari TheSpeedX"""
    all_proxies = []
    
    thespeedx_path = "./proxies/thespeedx_raw.txt"
    if os.path.exists(thespeedx_path):
        with open(thespeedx_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Only valid IP:PORT format
                if ":" in line and not line.startswith(("http://", "https://")):
                    parts = line.split(":")
                    if len(parts) == 2:
                        all_proxies.append(line)
                    
                    # Stop after MAX count
                    if len(all_proxies) >= MAX_PROXY_COUNT:
                        break
    
    return all_proxies

async def main():
    global os
    import os
    
    print("⚡ ULTRA-FAST Proxy Validator")
    print("=" * 40)
    
    # Load limited proxies
    proxies = load_proxies()
    print(f"\n📦 Loaded {len(proxies)} proxies (max {MAX_PROXY_COUNT})\n")
    
    if len(proxies) < 5:
        print("❌ Not enough proxies!")
        return
    
    valid = []
    failed = 0
    
    start_time = datetime.now()
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(proxies), BATCH_SIZE):
            batch = proxies[i:i+BATCH_SIZE]
            
            results = await asyncio.gather(*[
                quick_test(p, session) for p in batch
            ])
            
            for p, ok in zip(batch, results):
                if ok:
                    score = 95
                    valid.append(f"{p}|{score}|{datetime.now().strftime('%Y-%m-%d')}")
                else:
                    failed += 1
            
            progress = min(i + len(batch), len(proxies))
            current_valid = len(valid)
            print(f"\r[{progress}/{len(proxies)}] ✓ {current_valid} | ✗ {failed}", end="")
    
    # Save results
    with open(VALIDATED_HTTP, 'w') as f:
        f.write('\n'.join(valid))
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print("\n\n✅ DONE!")
    print(f"   Time: {elapsed:.1f}s")
    print(f"   Valid: {len(valid)}")
    print(f"   Failed: {failed}")
    print(f"   Rate: {len(proxies)/elapsed:.1f} proxies/sec")
    
    if valid:
        avg_score = sum(int(v.split('|')[1]) for v in valid) / len(valid)
        print(f"   Avg Score: {avg_score:.1f}")

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted")
