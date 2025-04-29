from dataclasses import dataclass, field
import threading
from typing import Optional, List

@dataclass
class ProcessingState:
    active: bool = False
    total: int = 0
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    current_location: Optional[str] = None
    results: List[dict] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    total_requests: int = 0  # Track total API requests
    max_requests: int = 100  # Maximum allowed requests

    def reset(self):
        self.active = False
        self.total = 0
        self.total_processed = 0
        self.successful = 0
        self.failed = 0
        self.current_location = None
        self.results = []
        self.total_requests = 0
        self.max_requests = 100

# Global state instance
state = ProcessingState() 