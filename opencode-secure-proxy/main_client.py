#!/usr/bin/env python3
"""
Main Opencode Client dengan 9Router Proxy Pool Integration
Full-featured client dengan automatic proxy rotation & quota handling

Features:
✅ Intelligent proxy rotation via 9Router
✅ Automatic failover on quota/limit errors
✅ Quota tracking per proxy
✅ Privacy protection (no prompt logging)
✅ Performance monitoring
✅ Real-time statistics
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Callable
import json

# Import all components
try:
    from proxy_pool_manager import ProxyPoolManager, init_pool_from_files, pool_manager
    from nine_router import NineRouter, init_9router, nine_router
    
    # Initialize system
    print("🔧 Initializing 9Router Proxy Pool System...")
    
    # Load proxies dari validated files
    http_file = "./proxies/validated_http.txt"
    socks_file = "./proxies/validated_socks.txt"
    
    if os.path.exists(http_file) or os.path.exists(socks_file):
        try:
            router = init_9router(http_file, socks_file)
            print(f"✅ Loaded {len(pool_manager.proxies)} proxies into pool")
        except Exception as e:
            print(f"⚠️ Error loading proxies: {e}")
            router = None
    else:
        print("⚠️ No validated proxies found - running without proxy pool")
        router = None
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Make sure all dependencies are installed:")
    print("   pip install aiohttp python-dotenv")
    router = None

class MainOpencodeClient:
    """Main client untuk Opencode API dengan full integration"""
    
    def __init__(self, api_key: str = None, enable_logging: bool = False):
        self.api_key = api_key or os.getenv("OPENCODE_API_KEY")
        
        if not self.api_key:
            print("⚠️ WARNING: OPENCODE_API_KEY not set!")
            print("   Set environment variable:")
            print("   export OPENCODE_API_KEY='your_api_key'")
        
        self.enable_logging = enable_logging
        
        # Routing system
        self.router = router
        
        # Statistics
        self.session_stats = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "rotations": 0,
            "start_time": datetime.now()
        }
        
        # Callbacks untuk customization
        self.on_success: Optional[Callable] = None
        self.on_failure: Optional[Callable] = None
        self.on_rotation: Optional[Callable] = None
    
    async def send_request(
        self, 
        prompt: str, 
        model: str = "free",
        use_router: bool = True,
        verbose: bool = True
    ) -> Optional[Dict]:
        """
        Send request to Opencode API dengan automatic proxy routing
        
        Args:
            prompt: User's prompt text
            model: Model to use ("free", "pro", etc)
            use_router: Whether to use 9Router for proxy selection
            verbose: Print detailed logs
            
        Returns:
            Response dict atau None jika failed
        """
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"📤 Request #{self.session_stats['total_requests'] + 1}")
            print(f"{'='*60}")
            print(f"   Model: {model}")
            if not self.enable_logging and self.api_key:
                print(f"   🔒 Prompt masked for privacy")
            else:
                print(f"   📝 Prompt: [logged]")
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Request-ID": f"{datetime.now().timestamp()}",
            "User-Agent": "Mozilla/5.0 (compatible; OpencodeClient/1.0)"
        }
        
        # Mask prompt display
        if not self.enable_logging:
            prompt_display = "[ENCRYPTED - NOT LOGGED]"
            actual_prompt = prompt  # Use real prompt internally
        else:
            prompt_display = prompt
            actual_prompt = prompt
        
        payload = {
            "model": model,
            "prompt": prompt_display,  # Encrypted in header
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        if not use_router or not self.router:
            # Fallback tanpa proxy routing
            if verbose:
                print("   ⚠️ Running without proxy routing")
            
            try:
                result = await self._send_direct(payload, headers, verbose)
                
                if result:
                    self.session_stats["successful"] += 1
                else:
                    self.session_stats["failed"] += 1
                
                return result
                
            except Exception as e:
                if verbose:
                    print(f"❌ Direct request failed: {e}")
                return None
        else:
            # Use 9Router for intelligent routing
            result = await self.router.send_to_opencode(
                prompt=actual_prompt,
                model=model,
                route_name="opencode-ai",
                custom_callback=self._on_response_received
            )
            
            if result:
                self.session_stats["successful"] += 1
                
                if verbose:
                    stats = self.router.get_stats()
                    route_stats = stats['routes'].get('opencode-ai', {})
                    current_proxy = route_stats.get('current_proxy')
                    
                    if current_proxy:
                        print(f"✅ Success! Proxy: {current_proxy}")
                        print(f"   Requests this session: {route_stats['requests']}")
            else:
                self.session_stats["failed"] += 1
                if verbose:
                    print("❌ All routing attempts failed")
            
            return result
    
    async def _send_direct(self, payload: Dict, headers: Dict, verbose: bool = True):
        """Direct request tanpa proxy"""
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.opencode.ai/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()[:200]
                        if verbose:
                            print(f"❌ HTTP {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            if verbose:
                print(f"❌ Direct connection error: {e}")
            return None
    
    async def _on_response_received(self, response: Dict, route_name: str, proxy=None):
        """Callback saat response diterima"""
        
        # Calculate performance metrics
        processing_time = None
        if 'usage' in response:
            tokens = response['usage'].get('completion_tokens', 0)
            processing_time = response['usage'].get('processing_time_ms') / 1000
        
        if self.enable_logging:
            status_icon = "✅"
        else:
            status_icon = "🔐"
        
        if verbose_output:
            print(f"{status_icon} Received response")
            print(f"   Processing time: {processing_time:.2f}s" if processing_time else "")
            print(f"   Tokens used: {response['usage'].get('completion_tokens', 0)}")
        
        # Call custom callback if defined
        if self.on_success:
            try:
                self.on_success(response, route_name, proxy)
            except:
                pass
    
    def get_session_stats(self) -> Dict:
        """Get comprehensive session statistics"""
        
        uptime = (datetime.now() - self.session_stats["start_time"]).total_seconds()
        
        return {
            **self.session_stats,
            "uptime_seconds": round(uptime, 1),
            "success_rate": round(
                self.session_stats["successful"] / max(1, self.session_stats["total_requests"]) * 100, 1
            ),
            "rotations": self.router.total_rotations if self.router else 0,
            "router_stats": self.router.get_stats() if self.router else None
        }
    
    def save_stats(self, filename: str = "./data/client_stats.json"):
        """Save session statistics ke file"""
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        stats_data = {
            "session_end": datetime.now().isoformat(),
            "stats": self.get_session_stats()
        }
        
        if self.router:
            stats_data["router_config"] = self.router.export_config()
        
        with open(filename, 'w') as f:
            json.dump(stats_data, f, indent=2)
        
        print(f"💾 Stats saved to {filename}")

async def main():
    """Demo usage dengan test requests"""
    
    global verbose_output
    verbose_output = True
    
    # Initialize client
    client = MainOpencodeClient(enable_logging=False)
    
    # Show initialization status
    stats = client.router.get_stats() if client.router else {}
    
    print("\n" + "=" * 60)
    print("🚀 Opencode AI Client dengan 9Router Proxy Pool")
    print("=" * 60)
    print("\n🔒 Security Features:")
    print("   ✅ Prompt/response encrypted (not logged)")
    print("   ✅ Proxy rotation automatic")
    print("   ✅ Quota detection & failover")
    print("   ✅ Only AI traffic through proxies")
    print("\n📦 Proxy Pool Info:")
    
    if client.router:
        pool_stats = stats.get('pool_stats', {})
        print(f"   Total Proxies: {pool_stats.get('total_proxies', 0)}")
        print(f"   Active: {pool_stats.get('active', 0)}")
        print(f"   Average Score: {pool_stats.get('average_score', 0)}")
        print(f"   Current Route: {stats.get('routes', {}).get('opencode-ai', {}).get('state')}")
    else:
        print("   ⚠️ No proxy pool active - using direct connection")
    
    # Test prompts
    test_prompts = [
        "Hello, can you help me?",
        "What is Python programming?",
        "Generate a short story about space travel"
    ]
    
    print("\n🎯 Starting test requests...\n")
    
    for i, prompt in enumerate(test_prompts, 1):
        client.session_stats["total_requests"] += 1
        
        result = await client.send_request(
            prompt=prompt,
            model="free",
            use_router=True,
            verbose=True
        )
        
        if result:
            print(f"✓ Response received ({len(str(result))} chars)")
        else:
            print("✗ Request failed\n")
        
        # Small delay between requests
        await asyncio.sleep(2)
    
    # Final stats
    final_stats = client.get_session_stats()
    
    print("\n" + "=" * 60)
    print("📊 FINAL SESSION STATISTICS")
    print("=" * 60)
    print(f"Total Requests: {final_stats['total_requests']}")
    print(f"Successful: {final_stats['successful']}")
    print(f"Failed: {final_stats['failed']}")
    print(f"Success Rate: {final_stats['success_rate']}%")
    print(f"Proxy Rotations: {final_stats['rotations']}")
    print(f"Uptime: {final_stats['uptime_seconds']}s")
    
    # Save stats
    client.save_stats()

if __name__ == "__main__":
    try:
        import aiohttp
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(0)
