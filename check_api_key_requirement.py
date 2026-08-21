#!/usr/bin/env python3
"""Test apakah OpenCode benar-benar perlu API key atau bisa access gratis tanpa auth"""

import aiohttp
import asyncio
import os

async def test_without_api_key():
    """Test request KE OPENCODE TANPA API KEY sama sekali"""
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Try to get models WITHOUT authentication
        print("🧪 Testing without API key...")
        
        try:
            async with session.get(
                "https://api.opencode.ai/v1/models",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                
                if resp.status == 200:
                    models = await resp.json()
                    print(f"✅ WORKS! Models available: {len(models.get('data', []))}")
                    return True
                    
                elif resp.status == 401 or resp.status == 403:
                    print(f"❌ REQUIRES AUTH (Status {resp.status})")
                    text = await resp.text()[:200]
                    print(f"   Error: {text}")
                    
                    # Now try WITH a sample fake key to confirm
                    print("\n→ Trying WITH fake key to compare...")
                    async with session.get(
                        "https://api.opencode.ai/v1/models",
                        headers={"Authorization": "Bearer fake_key_123"},
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp2:
                        print(f"   Status with fake key: {resp2.status}")
                        
                    return False
                    
                else:
                    print(f"? Other status: {resp.status}")
                    return False
                    
        except Exception as e:
            print(f"Error: {str(e)[:100]}")
            return False

async def main():
    result = await test_without_api_key()
    
    print("\n" + "="*70)
    print("CONCLUSION:")
    print("="*70)
    
    if result:
        print("✅ OPENCODE FREE TIER DOESN'T NEED API KEY!")
        print("You can make requests without any authentication.")
    else:
        print("❌ OPENCODE REQUIRES API KEY for free tier")
        print("But maybe the key is auto-generated when you visit their site?")
        print("Need to check documentation...")

if __name__ == "__main__":
    asyncio.run(main())
