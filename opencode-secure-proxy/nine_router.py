#!/usr/bin/env python3
"""
9Router - Intelligent Proxy Router untuk Multi-Proxy Rotation
Connects Proxy Pool Manager dengan Opencode API melalui different proxies

Features:
✅ Smart proxy selection & rotation
✅ Automatic failover on quota/block errors  
✅ Quota tracking per proxy
✅ Rate limit detection
✅ Health monitoring
✅ Integration dengan AI services (Opencode, dll)
"""

import os
import sys
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass
from enum import Enum

# Import dari proxy pool manager
try:
    from proxy_pool_manager import ProxyPoolManager, init_pool_from_files, pool_manager
except ImportError:
    # Fallback jika file belum ada
    print("⚠️ Import failed, running standalone...")
    pool_manager = None

class RouteState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    BLOCKED = "blocked"
    QUOTA_EXCEEDED = "quota_exceeded"
    ROTATING = "rotating"

@dataclass
class RouteSession:
    """Single routing session"""
    route_name: str
    current_proxy_key: Optional[str] = None
    current_proxy_entry = None
    state: RouteState = RouteState.IDLE
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_request_time: Optional[datetime] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class NineRouter:
    """
    Main 9Router class untuk intelligent proxy routing
    Manages multiple routes/proxy combinations
    """
    
    def __init__(self, pool_manager: ProxyPoolManager = None):
        self.pool_manager = pool_manager or pool_manager
        
        if not self.pool_manager:
            # Create new pool manager
            self.pool_manager = ProxyPoolManager()
        
        self.routes: Dict[str, RouteSession] = {}
        self.default_route = "opencode-ai"
        
        # Callbacks untuk events
        self.on_quota_hit: Optional[Callable] = None
        self.on_rotation: Optional[Callable] = Callable[[str], None]
        self.on_failure: Optional[Callable] = Callable[[str, str], None]
        
        # Statistics
        self.total_routed_requests = 0
        self.total_rotations = 0
        self.total_failures = 0
        
        # Initialize default route
        self._create_default_route()
    
    def _create_default_route(self):
        """Create default route untuk opencode-ai"""
        self.routes[self.default_route] = RouteSession(
            route_name=self.default_route,
            current_proxy_entry=None,
            state=RouteState.IDLE
        )
    
    async def select_proxy(self, route_name: str = None) -> Optional[Any]:
        """
        Select optimal proxy untuk route tertentu
        Returns ProxyEntry atau None jika tidak available
        """
        
        if not route_name:
            route_name = self.default_route
        
        # Get proxy dari pool
        proxy = self.pool_manager.get_available_proxy(service="opencode-ai")
        
        if proxy:
            # Update route state
            if route_name in self.routes:
                session = self.routes[route_name]
                
                old_key = session.current_proxy_key
                session.current_proxy_key = f"{proxy.ip}:{proxy.port}"
                session.current_proxy_entry = proxy
                session.state = RouteState.ACTIVE
                
                # Track rotation
                if old_key != session.current_proxy_key:
                    self.total_rotations += 1
            
            return proxy
        
        return None
    
    async def mark_success(self, route_name: str = None):
        """Mark request berhasil"""
        
        if not route_name:
            route_name = self.default_route
        
        if route_name in self.routes:
            session = self.routes[route_name]
            
            if session.current_proxy_entry:
                self.pool_manager.record_success(
                    session.current_proxy_entry.ip,
                    session.current_proxy_entry.port
                )
            
            session.success_count += 1
            session.request_count += 1
            self.total_routed_requests += 1
    
    async def mark_failure(self, route_name: str = None, reason: str = "unknown"):
        """Mark request gagal dengan reason"""
        
        if not route_name:
            route_name = self.default_route
        
        if route_name in self.routes:
            session = self.routes[route_name]
            
            if session.current_proxy_entry:
                self.pool_manager.record_failure(
                    session.current_proxy_entry.ip,
                    session.current_proxy_entry.port,
                    reason
                )
            
            session.failure_count += 1
            session.request_count += 1
            self.total_failures += 1
            
            # Trigger callback
            if self.on_failure:
                try:
                    self.on_failure(route_name, reason)
                except:
                    pass
    
    async def handle_quota_hit(self, route_name: str = None):
        """Handle ketika quota/limit exceeded"""
        
        if not route_name:
            route_name = self.default_route
        
        if route_name in self.routes:
            session = self.routes[route_name]
            
            if session.current_proxy_key:
                # Mark proxy sebagai temporarily blocked
                new_proxy = self.pool_manager.rotate_for_quota_hit(session.current_proxy_key)
                
                if new_proxy:
                    # Rotate ke proxy baru
                    session.current_proxy_key = f"{new_proxy.ip}:{new_proxy.port}"
                    session.current_proxy_entry = new_proxy
                    session.state = RouteState.ROTATING
                    
                    # Reset stats untuk fresh start
                    session.request_count = 0
                    session.failure_count = 0
                    
                    print(f"🔄 Quota hit - Rotated to {session.current_proxy_key}")
                    
                    self.total_rotations += 1
                    
                    # Trigger callback
                    if self.on_rotation:
                        try:
                            self.on_rotation(route_name)
                        except:
                            pass
                    
                    return new_proxy
            
            session.state = RouteState.QUOTA_EXCEEDED
    
    async def send_to_opencode(self, prompt: str, model: str = "free", 
                               route_name: str = None,
                               custom_callback: Optional[Callable] = None) -> Optional[Dict]:
        """
        Send request ke Opencode via selected proxy
        
        Args:
            prompt: User prompt (will be masked dalam logging)
            model: Model to use
            route_name: Route identifier
            custom_callback: Function to call on each response for analysis
        
        Returns:
            Response dict atau None jika failed
        """
        
        if not route_name:
            route_name = self.default_route
        
        # Loop hingga successful atau run out of proxies
        max_attempts = len(self.pool_manager.proxies)
        attempts = 0
        
        while attempts < max_attempts:
            # Select proxy
            proxy = await self.select_proxy(route_name)
            
            if not proxy:
                print("❌ No available proxies!")
                return None
            
            proxy_key = f"{proxy.ip}:{proxy.port}"
            
            try:
                # Prepare request
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('OPENCODE_API_KEY', '')}",
                    "X-Request-ID": f"{datetime.now().timestamp()}",
                    "X-Routing": f"9router-{route_name}"
                }
                
                # Mask prompt for privacy
                prompt_display = "[ENCRYPTED - NOT LOGGED]"
                
                payload = {
                    "model": model,
                    "prompt": prompt_display,
                    "temperature": 0.7
                }
                
                # Setup proxy
                proxies = {
                    "http": f"http://{proxy.ip}:{proxy.port}",
                    "https": f"https://{proxy.ip}:{proxy.port}"
                }
                
                # Make request
                timeout = aiohttp.ClientTimeout(total=30)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.opencode.ai/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        proxies=proxies,
                        timeout=timeout
                    ) as response:
                        
                        status_code = response.status
                        
                        if status_code == 200:
                            result = await response.json()
                            
                            # Success
                            await self.mark_success(route_name)
                            
                            # Call custom callback
                            if custom_callback:
                                try:
                                    await custom_callback(result, route_name, proxy)
                                except Exception as e:
                                    print(f"⚠️ Callback error: {e}")
                            
                            return result
                        
                        else:
                            # Analyze error
                            error_text = await response.text()[:200]
                            
                            # Check untuk quota/rate limit
                            is_quota_error = any([
                                "quota" in error_text.lower(),
                                "limit" in error_text.lower(),
                                "too many" in error_text.lower(),
                                "rate_limit" in error_text.lower(),
                                status_code >= 429
                            ])
                            
                            if is_quota_error:
                                # Handle quota hit
                                await self.handle_quota_hit(route_name)
                                continue  # Retry dengan proxy baru
                            else:
                                # Regular failure
                                await self.mark_failure(route_name, error_text)
                                return None
            
            except asyncio.TimeoutError:
                print(f"⏱️ Timeout for {proxy_key}")
                await self.mark_failure(route_name, "timeout")
                attempts += 1
                
            except Exception as e:
                error_str = str(e)[:100]
                print(f"❌ Error via {proxy_key}: {error_str}")
                await self.mark_failure(route_name, error_str)
                attempts += 1
        
        # Ran out of proxies
        print(f"⚠️ Max attempts ({max_attempts}) reached for {route_name}")
        return None
    
    def get_stats(self) -> Dict:
        """Get comprehensive routing statistics"""
        stats = {
            "total_routes": len(self.routes),
            "total_requests_routed": self.total_routed_requests,
            "total_rotations": self.total_rotations,
            "total_failures": self.total_failures,
            "success_rate": round(
                (self.total_routed_requests - self.total_failures) / max(1, self.total_routed_requests) * 100, 1
            ),
            "pool_stats": self.pool_manager.get_pool_stats() if self.pool_manager else {},
            "routes": {}
        }
        
        for route_name, session in self.routes.items():
            stats["routes"][route_name] = {
                "state": session.state.value,
                "current_proxy": session.current_proxy_key,
                "requests": session.request_count,
                "successes": session.success_count,
                "failures": session.failure_count,
                "last_request": session.last_request_time.isoformat() if session.last_request_time else None
            }
        
        return stats
    
    def export_config(self) -> Dict:
        """Export router configuration untuk backup/recovery"""
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "pool_size": self.pool_manager.pool_size,
            "routes": {
                name: {
                    "current_proxy": session.current_proxy_key,
                    "state": session.state.value,
                    "stats": {
                        "requests": session.request_count,
                        "successes": session.success_count,
                        "failures": session.failure_count
                    }
                }
                for name, session in self.routes.items()
            },
            "statistics": {
                "total_routed": self.total_routed_requests,
                "total_rotations": self.total_rotations,
                "total_failures": self.total_failures
            }
        }

# Singleton instance
nine_router = NineRouter(pool_manager)

def init_9router(http_file: str = "./proxies/validated_http.txt",
                 socks_file: str = "./proxies/validated_socks.txt") -> NineRouter:
    """Initialize 9Router dengan proxy pool files"""
    
    global nine_router
    
    # Initialize pool first
    pool_manager = init_pool_from_files(http_file, socks_file)
    
    # Create 9Router instance
    nine_router = NineRouter(pool_manager)
    
    return nine_router

if __name__ == "__main__":
    # Test initialization
    print("=" * 60)
    print("🔄 Testing 9Router Initialization")
    print("=" * 60)
    
    try:
        router = init_9router()
        
        # Show stats
        stats = router.get_stats()
        print("\n📊 Router Stats:")
        print(f"   Total Routes: {stats['total_routes']}")
        print(f"   Total Requests: {stats['total_requests_routed']}")
        print(f"   Total Rotations: {stats['total_rotations']}")
        print(f"   Success Rate: {stats['success_rate']}%")
        
        print(f"\n🔮 Pool Stats:")
        pool_stats = stats['pool_stats']
        print(f"   Total Proxies: {pool_stats['total_proxies']}")
        print(f"   Active: {pool_stats['active']}")
        
        # Test proxy selection
        print("\n🎲 Testing proxy selection...")
        for i in range(3):
            proxy = asyncio.run(router.select_proxy())
            if proxy:
                print(f"   ✓ Selected: {proxy.ip}:{proxy.port} | Score: {proxy.score}")
                asyncio.run(router.mark_success())
            else:
                print(f"   ❌ No proxy available")
    
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
