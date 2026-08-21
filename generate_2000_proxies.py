#!/usr/bin/env python3
"""
Generate & Validate 2000+ Fresh Proxies dari Multiple Sources
Support: HTTP, HTTPS, SOCKS4, SOCKS5
Target: Import ke 9Router Proxy Pools
"""

import asyncio
import aiohttp
from datetime import datetime
import random

# Sources dengan volume proxy besar
SOURCES = [
    ("proxifly", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.txt"),
    ("thespeedx-http", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ("thespeedx-socks5", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt"),
    ("proxylists-net", "https://api.proxyscrape.com/v2/?method=get&country=ALL&request=&version=v4beta1&ssl=all"),
    ("sslproxies-org", "https://www.sslproxies.org/"),
    ("hidemyass", "https://www.hidemyass.com/proxy-list/new/:0/"),
]

OUTPUT_FILE = "./proxies/fresh_2000_plus.txt"
MAX_PROXY_COUNT = 2000
BATCH_SIZE = 50  # Validasi per batch
TIMEOUT_VALIDATION = 8  # detik timeout per proxy

def extract_proxy_from_html(html_text):
    """Extract proxies dari HTML page"""
    import re
    
    proxies = []
    
    # Pattern untuk http/https
    pattern_http = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+'
    
    # Pattern untuk socks4/5
    pattern_socks = r'(socks[45])://([^\s]+)'
    
    for match in re.finditer(pattern_socks, html_text):
        protocol, addr = match.groups()
        if ':' in addr:
            ip_port = addr.split(':')
            if len(ip_port) == 2:
                proxies.append(f"{protocol}://{addr}")
    
    for match in re.finditer(pattern_http, html_text):
        ip_port = match.group(0)
        proxies.append(f"http://{ip_port}")
    
    return proxies

async def validate_proxy_single(proxy_url: str, session: aiohttp.ClientSession) -> bool:
    """Validate single proxy dengan cepat"""
    
    try:
        async with session.get(
            "https://cloudflare.com",
            proxy=proxy_url,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_VALIDATION),
            allow_redirects=False,
            ssl=True  # Force HTTPS test
        ) as resp:
            status = resp.status
            has_redirect = len(resp.history) > 0
            
            # Accept codes 200, 301, 302 (redirect is okay for validation)
            return status in (200, 301, 302) and not has_redirect
            
    except Exception:
        return False

async def main():
    print("=" * 60)
    print("🔄 GENERATING 2000+ FRESH PROXIES FROM MULTIPLE SOURCES")
    print("=" * 60)
    
    all_proxies = set()
    
    # Download dari multiple sources
    print("\n📥 Downloading from sources...")
    
    for name, url in SOURCES:
        print(f"   → {name}: ", end="", flush=True)
        try:
            if name.endswith("-http"):
                # Direct download text file
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        content = await resp.text()
                        lines = [l.strip() for l in content.split('\n') if l.strip() and ':' in l]
                
                # Filter only valid IP:PORT format
                valid_lines = []
                for line in lines[:500]:  # Limit 500 per source
                    parts = line.split(':')
                    if len(parts) >= 2:
                        ip = parts[0]
                        port = parts[-1]
                        # Check basic IP format
                        if ip.count('.') == 3:
                            valid_lines.append(line)
                
                all_proxies.update(valid_lines)
                
                # Save raw output
                with open(f"./proxies/raw_{name}.txt", 'w') as f:
                    f.write('\n'.join(valid_lines))
                
                print(f"✓ ({len(valid_lines)} extracted)")
            
            elif name.endswith("-socks5"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        content = await resp.text()
                        lines = [l.strip() for l in content.split('\n') if l.strip()]
                
                valid_lines = []
                for line in lines[:300]:
                    if line.startswith('socks5://'):
                        valid_lines.append(line)
                
                all_proxies.update(valid_lines)
                
                with open(f"./proxies/raw_{name}.txt", 'w') as f:
                    f.write('\n'.join(valid_lines))
                
                print(f"✓ ({len(valid_lines)} SOCKS5)")
            
            else:
                # Generic text extraction
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        content = await resp.text()
                
                if "proxis" in content.lower() or "socks5" in content.lower():
                    lines = extract_proxy_from_html(content)
                else:
                    lines = []
                    for l in content.splitlines()[:200]:
                        l = l.strip()
                        if ':' in l and len(l.split(':')) == 2:
                            parts = l.split(':')
                            if '.' in parts[0]:  # Looks like IP
                                lines.append(l)
                
                all_proxies.update(lines)
                
                with open(f"./proxies/raw_{name}.txt", 'w') as f:
                    f.write('\n'.join(lines))
                
                print(f"✓ ({len(lines)} extracted)")
        
        except Exception as e:
            print(f"✗ Failed: {str(e)[:50]}")
    
    # Limit to target count
    all_proxies = list(all_proxies)[:MAX_PROXY_COUNT + 100]  # Extra for validation
    
    print(f"\n📦 Total raw proxies: {len(all_proxies)}")
    
    # Validation phase
    print(f"\n🔍 Validating proxies (this takes time)...")
    print(f"   Timeout per proxy: {TIMEOUT_VALIDATION}s")
    print(f"   Batch size: {BATCH_SIZE}")
    
    validated_proxies = []
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(all_proxies), BATCH_SIZE):
            batch = all_proxies[i:i+BATCH_SIZE]
            
            results = await asyncio.gather(*[
                validate_proxy_single(p, session) for p in batch
            ], return_exceptions=True)
            
            for j, result in enumerate(results):
                proxy = batch[j]
                
                if isinstance(result, Exception):
                    continue
                
                if result:
                    validated_proxies.append(proxy)
                    print(f"   ✅ {proxy}", flush=True)
            
            progress = min(i + BATCH_SIZE, len(all_proxies))
            print(f"\rValidated: {progress}/{len(all_proxies)} | Active: {len(validated_proxies)}", end="")
    
    # Remove duplicates and sort by score
    validated_proxies = list(set(validated_proxies))
    
    # Write to 9router ready file
    print(f"\n\n💾 Writing {len(validated_proxies)} validated proxies to: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w') as f:
        for p in validated_proxies:
            f.write(f"{p}\n")
    
    # Also write scores.json for tracking
    import json
    scores_file = OUTPUT_FILE.replace('.txt', '_scores.json')
    
    data = {}
    for p in validated_proxies:
        data[p] = {
            "status": "active",
            "validated_at": datetime.now().isoformat(),
            "source": "multi_source_aggregate"
        }
    
    with open(scores_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ DONE!")
    print(f"{'='*60}")
    print(f"\nSummary:")
    print(f"   Raw downloaded: {sum(len(x) for x in [list(s) for _ in [1]])}")  # Approximate
    print(f"   After validation: {len(validated_proxies)}")
    print(f"   Target reached: {'Yes' if len(validated_proxies) >= 2000 else 'No, but good enough'}")
    
    print(f"\nFiles created:")
    print(f"   • {OUTPUT_FILE}")
    print(f"   • {scores_file}")
    print(f"   • ./proxies/raw_*.{ext}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")

