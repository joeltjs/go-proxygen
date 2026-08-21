#!/usr/bin/env python3
"""Proxy validator dan verifier untuk 9Router system - dengan proof mode"""

import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Tuple
import json
import subprocess

TIMEOUT = aiohttp.ClientTimeout(total=10)
BATCH_SIZE = 50

async def test_proxy(proxy_str: str, session: aiohttp.ClientSession) -> Tuple[bool, int, float]:
    """Test single proxy dengan timing dan status code check"""
    try:
        start = datetime.now()
        
        async with session.get(
            "https://cloudflare.com",
            proxy=f"http://{proxy_str}",
            timeout=TIMEOUT,
            allow_redirects=False
        ) as resp:
            
            elapsed = (datetime.now() - start).total_seconds()
            status = resp.status
            
            if status == 200 or status == 301:
                return True, status, elapsed
            else:
                return False, status, elapsed
                
    except Exception as e:
        error_msg = str(e)[:80]
        print(f"   ❌ Failed {proxy_str}: {error_msg}")
        return False, 0, 0

async def main():
    print("=" * 70)
    print("🔍 PROXY VALIDATOR + VERIFIER FOR 9ROUTER")
    print("=" * 70)
    
    # Load proxies dari file
    proxy_file = "./generated_proxy_result.txt"
    
    try:
        with open(proxy_file, 'r') as f:
            all_proxies = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ File not found: {proxy_file}")
        return
    
    total = len(all_proxies)
    print(f"\n📦 Total proxies to test: {total}")
    
    valid_proxies = []
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, total, BATCH_SIZE):
            batch = all_proxies[i:i+BATCH_SIZE]
            
            print(f"\n🔄 Testing batch {i//BATCH_SIZE + 1}/{(total-1)//BATCH_SIZE + 1}...")
            
            results = await asyncio.gather(*[test_proxy(p, session) for p in batch])
            
            for j, result in enumerate(results):
                proxy = batch[j]
                is_valid, status, time = result
                
                if is_valid:
                    valid_proxies.append({
                        "proxy": proxy,
                        "status": status,
                        "time_ms": round(time * 1000, 1),
                        "tested_at": datetime.now().isoformat()
                    })
                    
                    if len(valid_proxies) % 50 == 0:
                        print(f"\rProgress: {min(i+j+1, total)}/{total} | Valid so far: {len(valid_proxies)}", end="")
    
    print(f"\n\n✅ VALIDATION COMPLETE!")
    print(f"Total tested: {total}")
    print(f"Valid proxies: {len(valid_proxies)} ({len(valid_proxies)/max(1,total)*100:.1f}%)")
    
    # Save validated list
    output_file = "./proxies/validated_" + datetime.now().strftime("%Y%m%d") + ".txt"
    with open(output_file, 'w') as f:
        for item in valid_proxies[:500]:  # Limit to 500 for quick import
            f.write(f"{item['proxy']}|{item['status']}|{item['time_ms']}ms|{item['tested_at']}\n")
    
    print(f"Saved to: {output_file}")
    
    # Show sample
    print(f"\n🎲 Sample of valid proxies:")
    for item in valid_proxies[:5]:
        print(f"   • {item['proxy']} ({item['time_ms']}ms)")

if __name__ == "__main__":
    asyncio.run(main())
