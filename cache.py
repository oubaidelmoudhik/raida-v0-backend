"""
Simple in-memory cache for AI responses.
Reduces OpenAI API costs and improves response times for repeated lessons.
"""
import hashlib
import json
import time
from typing import Optional, Dict, Any

class LessonCache:
    def __init__(self, ttl_seconds: int = 86400):  # 24 hours default
        """
        Initialize the cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 24 hours)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0
        }
    
    def _generate_key(self, content: str, language: str, subject: str, session: str) -> str:
        """
        Generate a unique cache key based on lesson content and parameters.
        
        Args:
            content: Lesson content text
            language: Language (fr/ar)
            subject: Subject name
            session: Session number
            
        Returns:
            SHA256 hash as cache key
        """
        key_data = f"{content}|{language}|{subject}|{session}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, content: str, language: str, subject: str, session: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached lesson data if available and not expired.
        
        Returns:
            Cached lesson data or None if not found/expired
        """
        self.stats["total_requests"] += 1
        key = self._generate_key(content, language, subject, session)
        
        if key in self.cache:
            entry = self.cache[key]
            # Check if entry has expired
            if time.time() - entry["timestamp"] < self.ttl_seconds:
                self.stats["hits"] += 1
                print(f"✅ Cache HIT for key: {key[:16]}...")
                return entry["data"]
            else:
                # Remove expired entry
                del self.cache[key]
                print(f"⏰ Cache EXPIRED for key: {key[:16]}...")
        
        self.stats["misses"] += 1
        print(f"❌ Cache MISS for key: {key[:16]}...")
        return None
    
    def set(self, content: str, language: str, subject: str, session: str, data: Dict[str, Any]) -> None:
        """
        Store lesson data in cache.
        
        Args:
            content: Lesson content text
            language: Language (fr/ar)
            subject: Subject name
            session: Session number
            data: Lesson data to cache
        """
        key = self._generate_key(content, language, subject, session)
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
        print(f"💾 Cached lesson data for key: {key[:16]}...")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        print("🗑️  Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hit rate and counts
        """
        hit_rate = (self.stats["hits"] / self.stats["total_requests"] * 100) if self.stats["total_requests"] > 0 else 0
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "total_requests": self.stats["total_requests"],
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self.cache)
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry["timestamp"] >= self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)

# Global cache instance
lesson_cache = LessonCache(ttl_seconds=86400)  # 24 hours
