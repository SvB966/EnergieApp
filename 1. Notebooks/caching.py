import threading
import time
from typing import Any, Optional, Hashable, Tuple

class TTLCache:
    """
    Een eenvoudige, thread-safe time-to-live cache.
    
    Attributes:
        ttl (int): Levensduur van een cache-entry in seconden.
    """
    def __init__(self, ttl: int = 300) -> None:
        self._cache: dict[Hashable, Tuple[Any, float]] = {}
        self.ttl: int = ttl
        self._lock = threading.Lock()

    def get(self, key: Hashable) -> Optional[Any]:
        """
        Haal de waarde voor 'key' op als deze nog niet verlopen is.
        Returns None als de key niet bestaat of verlopen is.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                # Verwijder verlopen entry
                del self._cache[key]
                return None
            return value

    def set(self, key: Hashable, value: Any) -> None:
        """
        Voeg of update een entry met huidige tijd + TTL als vervaldatum.
        """
        expires_at = time.time() + self.ttl
        with self._lock:
            self._cache[key] = (value, expires_at)
