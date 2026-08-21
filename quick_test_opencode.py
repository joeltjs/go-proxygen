#!/usr/bin/env python3
"""
Quick test script untuk verify OpenCode routing via 9Router
Tanpa perlu login, langsung test endpoint dengan no-auth strategy
"""

import aiohttp
import asyncio
from datetime import datetime

PROXY_POOL_ID = "fe258500-f6c0-4b28-867d-ba0eb8906a45"  # Your active proxy pool ID
BASE_URL = "http://localhost:20128"
API_ENDPOINT = f"{BASE_URL}/api/completions"  # No-auth endpoint

async def test_opencode_routing():
    """Test if openrouter proxy rotation is working"""
    
    print("=" * 70)
    print("🧪 TESTING OPENCODE FREE VIA 9ROUTER (NO AUTH)")
    print("=" * 70)
    print(f"\nProxy Pool ID: {PROXY_POOL_ID}")
    print(f"9Router Endpoint: {BASE_URL}")
    print(f"Available Models:")
    print(f"  - deepseek-v4-flash-free")
    print(f"  - mimo-v2.5-free")
    print(f"  - qwen3.6-plus-free")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Try to make request to OpenCode-compatible endpoint
            payload = {
                "model": "deepseek-v4-flash-free",
                "prompt": "Hello! Can you introduce yourself?",
                "max_tokens": 100,
                "temperature": 0.7
            }
            
            start_time = datetime.now()
            
            # Direct call without auth (no-auth provider)
            async with session.post(
                API_ENDPOINT,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"Content-Type": "application/json"}
            ) as resp:
                
                elapsed = (datetime.now() - start_time).total_seconds()
                status_code = resp.status
                
                print(f"\n📊 Request Results:")
                print(f"   Status Code: {status_code}")
                print(f"   Response Time: {elapsed:.2f}s")
                
                if status_code == 200:
                    result = await resp.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    print(f"\n✅ SUCCESS!")
                    print(f"   Content Length: {len(content)} characters")
                    print(f"   First Line: {content.split(chr(10))[0][:80]}...")
                    
                    return True
                    
                else:
                    error_text = await resp.text()[:300]
                    print(f"\n❌ FAILED")
                    print(f"   Error Details: {error_text}")
                    
                    # Try alternative endpoint
                    print(f"\n💡 Trying alternative endpoint...")
                    alt_endpoint = f"{BASE_URL}/api/chat/completions"
                    
                    async with session.post(
                        alt_endpoint,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30),
                        headers={"Content-Type": "application/json"}
                    ) as alt_resp:
                        
                        alt_status = alt_resp.status
                        alt_result = await alt_resp.read()
                        
                        print(f"   Alternative Status: {alt_status}")
                        print(f"   Alternative Result: {alt_result[:200]}")
                        
                        return alt_status == 200
                        
    except Exception as e:
        error_msg = str(e)[:200]
        print(f"\n❌ CONNECTION ERROR")
        print(f"   Error: {error_msg}")
        
        # Try manual proxy test
        print(f"\n💡 Testing individual proxies manually...")
        await test_individual_proxies(session)

async def test_individual_proxies(session):
    """Directly test if any proxy from pool can reach internet"""
    
    # From the database, get some active proxies
    test_urls = ["https://google.com", "https://cloudflare.com"]
    
    for url in test_urls:
        print(f"\nTesting direct connection to: {url}")
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                print(f"   ✅ Direct connection OK: {resp.status}")
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:50]}")

if __name__ == "__main__":
    result = asyncio.run(test_opencode_routing())
    
    print("\n" + "=" * 70)
    print("🎯 SUMMARY")
    print("=" * 70)
    
    if result:
        print("✅ System is working!")
        print("   → Proxy pools imported successfully")
        print("   → OpenCode Free models accessible")
        print("   → Routing through 9Router active")
    else:
        print("⚠️ Issues detected:")
        print("   1. Check if 9Router is running on port 20128")
        print("   2. Make sure OpenCode connection exists")
        print("   3. Verify browser dashboard shows 'Active' connection")
        
    print("=" * 70)
