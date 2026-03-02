import time
import threading
from typing import Dict, Any, List
from utils import logger
from dns_message import TYPE_A, TYPE_AAAA, TYPE_MX, TYPE_NS, TYPE_CNAME

class DnsCache:
    def __init__(self):
        # Format: {(domain, type): (records_list, expiry_timestamp)}
        self.cache: Dict[tuple, tuple] = {}
        self.lock = threading.Lock()
        
        # Start a background thread to periodically clean up expired entries
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def get(self, domain: str, record_type: int) -> List[Any]:
        with self.lock:
            key = (domain, record_type)
            if key in self.cache:
                records, expiry = self.cache[key]
                if time.time() < expiry:
                    logger.debug(f"Cache hit for {domain} (Type: {record_type})")
                    return records
                else:
                    logger.debug(f"Cache expired for {domain} (Type: {record_type})")
                    del self.cache[key]
        return None

    def set(self, domain: str, record_type: int, records: List[Dict[str, Any]], custom_ttl: int = None):
        if not records:
            return
            
        # Extract minimum TTL from the records or use provided custom ttl
        ttl = custom_ttl if custom_ttl is not None else min(r.get('ttl', 300) for r in records)
        
        # Don't cache if TTL is explicitly 0
        if ttl <= 0:
            return
            
        expiry = time.time() + ttl
        
        with self.lock:
            key = (domain, record_type)
            self.cache[key] = (records, expiry)
            logger.debug(f"Cached {len(records)} records for {domain} (Type: {record_type}) with TTL {ttl}s")

    def _cleanup_loop(self):
        while True:
            time.sleep(60) # Check every 60 seconds
            self._purge_expired()

    def _purge_expired(self):
        current_time = time.time()
        expired_keys = []
        with self.lock:
            for key, (records, expiry) in self.cache.items():
                if current_time >= expiry:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
                
        if expired_keys:
            logger.debug(f"Purged {len(expired_keys)} expired entries from cache")

cache = DnsCache()
