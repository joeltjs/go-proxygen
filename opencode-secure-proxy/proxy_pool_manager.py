#!/usr/bin/env python3
"""
Unified Proxy Pool Manager
Manages proxy pool untuk 9Router + Opencode routing system
Features:
- Central proxy storage & management
- Health monitoring & auto-revalidation
- Geographic & performance tracking
- Integration with 9Router dan Opencode client
- Automatic failover & quota management
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import random

# File paths
POOL_DB_FILE = "./config/proxy_pool.db.json"
CONFIG_FILE = "./config/settings.json"

@dataclass
class ProxyEntry:
    """Single proxy entry dengan metadata lengkap"""
    ip: str
    port: int
    protocol: str  # http atau socks5
    score: int  # Health score (0-100)
    country: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    
    # Usage statistics
    requests_made: int = 0
    failures: int = 0
    last_used: Optional[datetime] = None
    last_validated: Optional[datetime] = None
    
    # Service tagging
    service_tags: List[str] = field(default_factory=lambda: ["opencode-ai"])
    
    # Status
    is_active: bool = True
    is_blacklisted: bool = False
    blocked_by_quota: bool = False
    
    def to_dict(self):
        return {
            "ip": self.ip,
            "port": self.port,
            "protocol": self.protocol,
            "score": self.score,
            "country": self.country,
            "city": self.city,
            "isp": self.isp,
            "requests_made": self.requests_made,
            "failures": self.failures,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "service_tags": self.service_tags,
            "is_active": self.is_active,
            "is_blacklisted": self.is_blacklisted,
            "blocked_by_quota": self.blocked_by_quota
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        obj = cls(
            ip=data["ip"],
            port=data["port"],
            protocol=data.get("protocol", "http"),
            score=data.get("score", 80),
            country=data.get("country"),
            city=data.get("city"),
            isp=data.get("isp"),
            requests_made=data.get("requests_made", 0),
            failures=data.get("failures", 0),
            is_active=data.get("is_active", True),
            is_blacklisted=data.get("is_blacklisted", False),
            blocked_by_quota=data.get("blocked_by_quota", False)
        )
        
        if isinstance(data.get("last_used"), str):
            try:
                obj.last_used = datetime.fromisoformat(data["last_used"])
            except:
                pass
        
        if isinstance(data.get("last_validated"), str):
            try:
                obj.last_validated = datetime.fromisoformat(data["last_validated"])
            except:
                pass
        
        return obj

class ProxyPoolManager:
    """Central manager untuk proxy pool integration dengan 9Router"""
    
    def __init__(self):
        self.proxies: Dict[str, ProxyEntry] = {}  # Key: IP:PORT
        self.pool_size = 0
        self.health_check_interval = 3600  # 1 jam
        self.quota_limit = 1000  # Max requests per proxy per hour
        
        # Statistics
        self.total_requests = 0
        self.rotation_count = 0
        self.quota_failures = 0
        
        # Load existing pool
        self._load_pool()
    
    def _load_pool(self):
        """Load proxy pool dari database file"""
        if not os.path.exists(POOL_DB_FILE):
            print(f"ℹ️ No existing pool found at {POOL_DB_FILE}")
            return
        
        try:
            with open(POOL_DB_FILE, 'r') as f:
                data = json.load(f)
                
                for key, proxy_data in data.items():
                    proxy_entry = ProxyEntry.from_dict(proxy_data)
                    self.proxies[key] = proxy_entry
            
            print(f"✅ Loaded {len(self.proxies)} proxies from pool database")
            
        except Exception as e:
            print(f"❌ Failed to load pool: {e}")
    
    def _save_pool(self):
        """Save pool ke database file"""
        try:
            os.makedirs(os.path.dirname(POOL_DB_FILE), exist_ok=True)
            
            data = {key: proxy.to_dict() for key, proxy in self.proxies.items()}
            
            with open(POOL_DB_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
        except Exception as e:
            print(f"⚠️ Failed to save pool: {e}")
    
    def add_proxy(self, ip: str, port: int, protocol: str = "http", 
                  source: str = "manual", **metadata) -> bool:
        """Add single proxy ke pool"""
        
        key = f"{ip}:{port}"
        
        if key in self.proxies:
            # Update existing
            existing = self.proxies[key]
            existing.score = max(existing.score, metadata.get("score", 80))
            existing.service_tags = list(set(existing.service_tags + metadata.get("tags", ["opencode-ai"])))
            existing.is_blacklisted = False
            existing.is_active = True
        else:
            # New proxy
            self.proxies[key] = ProxyEntry(
                ip=ip,
                port=port,
                protocol=protocol,
                score=metadata.get("score", 80),
                country=metadata.get("country"),
                city=metadata.get("city"),
                isp=metadata.get("isp"),
                service_tags=[source],
                is_active=True,
                is_blacklisted=False
            )
            
            self.pool_size += 1
            print(f"✓ Added proxy: {key} ({protocol}) - Score: {metadata.get('score', 80)}")
        
        self._save_pool()
        return True
    
    def add_proxies_from_file(self, file_path: str, protocol: str = "http",
                               scores_file: Optional[str] = None):
        """Bulk add proxies dari file validated.txt"""
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
        
        scores = {}
        if scores_file and os.path.exists(scores_file):
            with open(scores_file, 'r') as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) >= 2:
                        scores[parts[0]] = int(parts[1])
        
        count = 0
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                
                try:
                    # Format: IP:PORT atau IP:PORT|SCORE|DATE
                    parts = line.split("|")
                    ip_port = parts[0]
                    
                    ip, port = ip_port.split(":")
                    port = int(port)
                    
                    score = scores.get(ip_port, 80)
                    if len(parts) >= 2:
                        try:
                            score = int(parts[1])
                        except:
                            pass
                    
                    self.add_proxy(
                        ip=ip,
                        port=port,
                        protocol=protocol,
                        source="validated",
                        score=score
                    )
                    count += 1
                    
                except Exception as e:
                    continue
        
        print(f"✅ Added {count} proxies from file")
        self._save_pool()
    
    def get_available_proxy(self, service: str = "opencode-ai", 
                           exclude_ips: Optional[Set[str]] = None) -> Optional[ProxyEntry]:
        """
        Get optimal proxy dari pool untuk service tertentu
        Implements smart selection logic:
        - Prioritize high-score proxies
        - Avoid recently used ones (rotation)
        - Check quota limits
        """
        
        if not self.proxies:
            return None
        
        # Filter available proxies
        candidates = [
            p for p in self.proxies.values()
            if p.is_active 
            and not p.is_blacklisted 
            and not p.blocked_by_quota
            and service in p.service_tags
        ]
        
        if exclude_ips:
            candidates = [p for p in candidates if f"{p.ip}:{p.port}" not in exclude_ips]
        
        if not candidates:
            return None
        
        # Weighted selection based on score & freshness
        scored_candidates = []
        
        for proxy in candidates:
            # Calculate freshness bonus
            hours_since_last_use = 0
            if proxy.last_used:
                delta = datetime.now() - proxy.last_used
                hours_since_last_use = delta.total_seconds() / 3600
            
            freshness_bonus = min(hours_since_last_use * 5, 20)  # Max 20 points
            final_score = proxy.score + freshness_bonus
            
            scored_candidates.append((proxy, final_score))
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Select top candidate (with some randomness for variety)
        if len(scored_candidates) > 1:
            # Pick from top 3 with weighted probability
            top_candidates = scored_candidates[:min(3, len(scored_candidates))]
            weights = [c[1] for c in top_candidates]
            total_weight = sum(weights)
            
            rand_val = random.random() * total_weight
            cumulative = 0
            
            selected = top_candidates[0][0]
            for candidate, weight in zip(top_candidates, weights):
                cumulative += weight
                if rand_val <= cumulative:
                    selected = candidate[0]
                    break
        else:
            selected = scored_candidates[0][0]
        
        # Update stats
        selected.last_used = datetime.now()
        selected.requests_made += 1
        self.total_requests += 1
        
        return selected
    
    def record_success(self, proxy_ip: str, proxy_port: int):
        """Record successful request"""
        key = f"{proxy_ip}:{proxy_port}"
        if key in self.proxies:
            self.proxies[key].score = min(100, self.proxies[key].score + 2)
            self.proxies[key].failures = max(0, self.proxies[key].failures - 1)
    
    def record_failure(self, proxy_ip: str, proxy_port: int, reason: str = "unknown"):
        """Record failed request dan trigger appropriate action"""
        key = f"{proxy_ip}:{proxy_port}"
        
        if key in self.proxies:
            proxy = self.proxies[key]
            proxy.failures += 1
            
            # Auto-blacklist jika repeated failures
            if proxy.failures >= 3:
                proxy.is_blacklisted = True
                print(f"🚫 Blacklisted {key} due to repeated failures")
            
            # Track quota-based blocking
            elif reason.lower().find("quota") >= 0 or reason.lower().find("limit") >= 0:
                proxy.blocked_by_quota = True
                self.quota_failures += 1
                print(f"⚠️ Quota reached for {key} - will rotate")
                # Auto-unblock after 1 hour
                self._schedule_unblock_after_hour(key)
            
            # Update score
            proxy.score = max(0, proxy.score - 10)
    
    def _schedule_unblock_after_hour(self, key: str):
        """Schedule proxy unblock setelah 1 jam"""
        async def unblock():
            await asyncio.sleep(3600)  # 1 hour
            if key in self.proxies:
                self.proxies[key].blocked_by_quota = False
                self.proxies[key].score = max(60, self.proxies[key].score + 5)
                print(f"✅ Unblocked {key} after quota timeout")
                self._save_pool()
        
        asyncio.create_task(unblock())
    
    def rotate_for_quota_hit(self, current_proxy_key: str) -> Optional[ProxyEntry]:
        """
        Trigger automatic rotation ketika quota hit
        Mark current proxy sebagai temporarily blocked
        Return new proxy
        """
        # Temporarily block current proxy
        if current_proxy_key in self.proxies:
            self.proxies[current_proxy_key].blocked_by_quota = True
        
        # Find new proxy yang belum dipakai
        return self.get_available_proxy(exclude_ips={current_proxy_key})
    
    def mark_as_9router_proxy(self, ip: str, port: int, route_name: str = "default"):
        """Mark proxy untuk 9Router usage"""
        key = f"{ip}:{port}"
        if key in self.proxies:
            if "9router" not in self.proxies[key].service_tags:
                self.proxies[key].service_tags.append("9router")
    
    def get_pool_stats(self) -> Dict:
        """Get comprehensive pool statistics"""
        active = sum(1 for p in self.proxies.values() if p.is_active and not p.is_blacklisted)
        blacklisted = sum(1 for p in self.proxies.values() if p.is_blacklisted)
        blocked_quota = sum(1 for p in self.proxies.values() if p.blocked_by_quota)
        
        avg_score = sum(p.score for p in self.proxies.values()) / max(1, len(self.proxies))
        total_reqs = sum(p.requests_made for p in self.proxies.values())
        
        return {
            "total_proxies": len(self.proxies),
            "active": active,
            "blacklisted": blacklisted,
            "quota_blocked": blocked_quota,
            "average_score": round(avg_score, 1),
            "total_requests": total_reqs,
            "my_total_requests": self.total_requests,
            "quota_failures": self.quota_failures,
            "rotation_count": self.rotation_count
        }

# Global instance
pool_manager = ProxyPoolManager()

def init_pool_from_files(http_file: str = "./proxies/validated_http.txt",
                         socks_file: str = "./proxies/validated_socks.txt"):
    """Initialize pool dari validated proxy files"""
    
    global pool_manager
    
    # Add HTTP proxies
    if os.path.exists(http_file):
        pool_manager.add_proxies_from_file(http_file, protocol="http")
    
    # Add SOCKS5 proxies
    if os.path.exists(socks_file):
        pool_manager.add_proxies_from_file(socks_file, protocol="socks5")
    
    return pool_manager

if __name__ == "__main__":
    # Test initialization
    print("=" * 50)
    print("🔧 Testing Proxy Pool Manager")
    print("=" * 50)
    
    manager = init_pool_from_files()
    
    # Show stats
    stats = manager.get_pool_stats()
    print("\n📊 Pool Stats:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test proxy selection
    print("\n🎲 Testing proxy selection...")
    for i in range(5):
        proxy = manager.get_available_proxy(service="opencode-ai")
        if proxy:
            print(f"   #{i+1}: {proxy.ip}:{proxy.port} | Score: {proxy.score}")
            manager.record_success(proxy.ip, proxy.port)
