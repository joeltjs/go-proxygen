#!/usr/bin/env python3
"""
9Router Proxy Pool Fetcher & Exporter
Mengambil proxy gratis dari GitHub (TheSpeedX, proxifly, dll),
memvalidasi, dan meng-export format yang siap di-Copy-Paste
ke menu 'Batch Import Proxies' di 9Router UI!
"""

import asyncio
import aiohttp
import sys
from datetime import datetime

OUTPUT_FILE = "./9router_import_list.txt"
TIMEOUT = aiohttp.ClientTimeout(total=6)
TEST_URL = "https://cloudflare.com"

SOURCES = [
    ("TheSpeedX HTTP", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ("TheSpeedX SOCKS5", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt"),
    ("Proxifly SOCKS5", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt")
]

async def check_proxy(proxy_url: str, session: aiohttp.ClientSession):
    try:
        async with session.get(TEST_URL, proxy=proxy_url, timeout=TIMEOUT, allow_redirects=False) as resp:
            if resp.status == 200:
                return proxy_url
    except Exception:
        pass
    return None

async def main():
    print("=" * 60)
    print("🚀 9Router Proxy Collector & Validator")
    print("=" * 60)
    
    raw_list = []
    
    async with aiohttp.ClientSession() as session:
        # 1. Download
        print("\n📥 Mengambil proxy dari GitHub sources...")
        for name, url in SOURCES:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status == 200:
                        text = await r.text()
                        lines = [l.strip() for l in text.splitlines() if l.strip()]
                        print(f"   ✓ {name}: {len(lines)} proxies")
                        
                        for line in lines[:100]: # Sample 100 per source for fast check
                            if line.startswith("socks5://") or line.startswith("http://"):
                                raw_list.append(line)
                            else:
                                raw_list.append(f"http://{line}")
            except Exception as e:
                print(f"   ✗ {name} failed: {e}")
                
        # Remove duplicates
        raw_list = list(set(raw_list))
        print(f"\n🔍 Total raw sample untuk ditest: {len(raw_list)}")
        print("⚡ Memvalidasi proxy yang aktif dan responsif...\n")
        
        valid_proxies = []
        batch_size = 30
        
        for i in range(0, len(raw_list), batch_size):
            batch = raw_list[i:i+batch_size]
            tasks = [check_proxy(p, session) for p in batch]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res:
                    valid_proxies.append(res)
                    print(f"   ✅ WORK: {res}")
            
            print(f"\r   Progress: {min(i+batch_size, len(raw_list))}/{len(raw_list)} (Ditemukan: {len(valid_proxies)})", end="")
            sys.stdout.flush()

    print("\n\n" + "=" * 60)
    print(f"🎉 Selesai! Ditemukan {len(valid_proxies)} proxy aktif.")
    
    # Save to 9router ready file
    with open(OUTPUT_FILE, "w") as f:
        for p in valid_proxies:
            f.write(f"{p}\n")
            
    print(f"📁 List proxy siap copy disimpan di: {OUTPUT_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
