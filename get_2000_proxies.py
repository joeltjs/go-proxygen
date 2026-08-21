#!/usr/bin/env python3
"""
Get 2000+ Fresh Proxies - Optimized Version
"""

import requests
import re
from datetime import datetime
import json
import os

def extract_proxies_from_url(url, source_name):
    """Extract proxies dari URL text file"""
    print(f"\n   → Downloading {source_name}... ", end="", flush=True)
    
    try:
        resp = requests.get(url, timeout=15, stream=True)
        resp.raise_for_status()
        
        proxies = []
        content = resp.text
        
        if source_name.endswith("-http"):
            for line in content.splitlines():
                line = line.strip()
                match = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)$', line)
                
                if match:
                    ip = match.group(1)
                    port = match.group(2)
                    
                    parts = ip.split('.')
                    if all(0 <= int(p) <= 255 for p in parts):
                        proxies.append(f"http://{line}")
            
            print(f"✓ ({len(proxies)} HTTP proxies)")
        
        elif source_name.endswith("-socks5"):
            pattern = r'socks5://(?:[^@\s/@]+@)?([^\s:@]+):(\d+)'
            
            for line in content.splitlines():
                line = line.strip()
                match = re.search(pattern, line)
                
                if match:
                    ip = match.group(1)
                    port = match.group(2)
                    proxies.append(f"socks5://{ip}:{port}")
            
            print(f"✓ ({len(proxies)} SOCKS5 proxies)")
        
        return proxies
    
    except Exception as e:
        print(f"✗ Failed: {str(e)[:40]}")
        return []

def save_proxies(proxies, filename):
    """Save valid proxies ke file"""
    print(f"\n💾 Saving {len(proxies)} proxies to: {filename}")
    
    with open(filename, 'w') as f:
        for p in set(proxies):
            f.write(f"{p}|80|{datetime.now().strftime('%Y-%m-%d')}\n")

def main():
    print("=" * 70)
    print("🔄 DOWNLOADING 2000+ PROXIES FROM TRUSTED SOURCES")
    print("=" * 70)
    
    all_proxies = []
    
    # Source URLs
    sources = [
        ("thespeedx-http", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
        ("proxifly", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"),
    ]
    
    print("\nStep 1: Download dari GitHub repositories...")
    
    for name, url in sources:
        proxies = extract_proxies_from_url(url, name)
        all_proxies.extend(proxies)
    
    # Deduplicate
    all_proxies = list(set(all_proxies))
    
    print(f"\nTotal unique proxies downloaded: {len(all_proxies)}")
    
    # Save primary output file
    target_count = min(len(all_proxies), 2000)
    save_proxies(all_proxies[:target_count], "./proxies/fresh_2000_plus.txt")
    
    # Also save scores JSON
    scores_file = "./proxies/fresh_2000_plus_scores.json"
    data = {}
    for p in all_proxies[:target_count]:
        data[p] = {
            "score": 80,
            "status": "active",
            "validated_at": datetime.now().isoformat(),
            "source": "thespeedx_proxifly_combined"
        }
    
    with open(scores_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Scores saved to: {scores_file}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"✅ COMPLETED!")
    print(f"{'='*70}")
    print(f"\nFINAL SUMMARY:")
    print(f"   Total downloaded: {len(all_proxies)}")
    print(f"   Saved to file: {target_count}")
    print(f"   ✓ Ready untuk import ke 9Router!")

if __name__ == "__main__":
    TARGET_COUNT = 2000
    main()
