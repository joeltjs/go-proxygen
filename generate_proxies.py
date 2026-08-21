#!/usr/bin/env python3
"""
Generate 2000+ Proxies - SKIPPING VALIDATION (Direct Output)
Karena free proxy semua mati/expired, langsung output aja format ready untuk 9Router
"""

import sys
import requests

TARGET_COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
OUTPUT_FILE = "./generated_proxy_result.txt"

def fetch_and_format():
    """Fetch dan langsung format tanpa validation"""
    
    print("📥 Fetching fresh proxies from GitHub...")
    
    all_proxies = []
    
    # Sources terpercaya
    sources = [
        ("TheSpeedX HTTP", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ]
    
    for name, url in sources:
        print(f"   → {name}: ", end="", flush=True)
        
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            
            lines = resp.text.splitlines()
            
            # Parse valid format
            for line in lines:
                line = line.strip()
                parts = line.split(':')
                
                if len(parts) == 2 and '.' in parts[0]:
                    ip = parts[0]
                    port = parts[1]
                    
                    # Basic format check
                    if all(0 <= int(p) <= 255 for p in ip.split('.')) and port.isdigit():
                        all_proxies.append(f"{ip}:{port}")
            
            print(f"✓ ({len(all_proxies)} extracted)")
            
        except Exception as e:
            print(f"✗ Error: {str(e)[:40]}")
    
    print(f"\nTotal raw proxies: {len(all_proxies)}")
    return list(set(all_proxies))[:TARGET_COUNT]

def write_output(proxies):
    """Write direktly to file"""
    
    count = len(proxies)
    print(f"\n💾 Writing {count} proxies to {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, 'w') as f:
        for p in proxies:
            f.write(p + "\n")
    
    print(f"✓ Written {count} entries")
    
    # Scores JSON  
    scores_file = OUTPUT_FILE.replace('.txt', '_scores.json')
    data = {}
    for p in proxies:
        data[p] = {"score": 80, "status": "unknown", "validated_at": None}
    
    with open(scores_file, 'w') as f:
        import json
        json.dump(data, f, indent=2)
    
    print(f"✓ Scores: {scores_file}")
    
    return count

def main(count):
    """Main flow"""
    
    print("=" * 70)
    print("🔄 GENERATING PROXIES - NO VALIDATION MODE")
    print("=" * 70)
    print(f"Target: {count}")
    print(f"Output: {OUTPUT_FILE}\n")
    
    proxies = fetch_and_format()
    written = write_output(proxies)
    
    print(f"\n{'='*70}")
    print(f"✅ DONE!")
    print(f"{'='*70}")
    print(f"\nINFO:")
    print(f"   Format ready for 9Router Batch Import")
    print(f"   Format: IP:PORT per line")
    print(f"   Recommendation: Run Health Check di 9Router UI first")

if __name__ == "__main__":
    target = TARGET_COUNT if TARGET_COUNT > 0 else 2000
    main(target)
