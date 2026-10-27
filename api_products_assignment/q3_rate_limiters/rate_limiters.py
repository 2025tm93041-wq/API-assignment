"""Token Bucket and Leaky Bucket rate limiters (thread-safe, testable clock)."""
import threading
import time
from collections import deque


class TokenBucket:
    """Allows bursts up to `capacity`; tokens refill at `refill_rate` per second."""

    def __init__(self, capacity, refill_rate, clock=time.monotonic):
        self.capacity, self.refill_rate, self._clock = capacity, refill_rate, clock
        self.tokens = float(capacity)
        self._last = clock()
        self._lock = threading.Lock()

    def _refill(self):
        now = self._clock()
        self.tokens = min(self.capacity, self.tokens + (now - self._last) * self.refill_rate)
        self._last = now

    def allow(self, n=1):
        with self._lock:
            self._refill()
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False


class LeakyBucket:
    """Meter variant: water level rises per request, leaks at `leak_rate`/sec.
    Request rejected if adding it would overflow `capacity`. Output rate is smoothed."""

    def __init__(self, capacity, leak_rate, clock=time.monotonic):
        self.capacity, self.leak_rate, self._clock = capacity, leak_rate, clock
        self.level = 0.0
        self._last = clock()
        self._lock = threading.Lock()

    def _leak(self):
        now = self._clock()
        self.level = max(0.0, self.level - (now - self._last) * self.leak_rate)
        self._last = now

    def allow(self, n=1):
        with self._lock:
            self._leak()
            if self.level + n <= self.capacity:
                self.level += n
                return True
            return False


class LeakyBucketQueue:
    """Queue variant: requests wait in a FIFO queue (size `capacity`) and are
    processed at a constant rate. enqueue() returns False when the queue is full."""

    def __init__(self, capacity, leak_rate, clock=time.monotonic):
        self.capacity, self.interval, self._clock = capacity, 1.0 / leak_rate, clock
        self.queue = deque()
        self._next_leak = clock()
        self._lock = threading.Lock()

    def enqueue(self, request):
        with self._lock:
            if len(self.queue) >= self.capacity:
                return False
            self.queue.append(request)
            return True

    def process(self):
        """Call periodically; returns list of requests released since last call."""
        released = []
        with self._lock:
            now = self._clock()
            if not self.queue:
                self._next_leak = now          # idle: don't bank credit
            while self.queue and self._next_leak <= now:
                released.append(self.queue.popleft())
                self._next_leak += self.interval
        return released


if __name__ == "__main__":
    class FakeClock:
        def __init__(self): self.t = 0.0
        def __call__(self): return self.t
        def advance(self, s): self.t += s

    print("=== Demo: burst of 10 requests at t=0, then 1 request/sec ===")
    c1, c2 = FakeClock(), FakeClock()
    tb = TokenBucket(capacity=5, refill_rate=1, clock=c1)
    lb = LeakyBucket(capacity=5, leak_rate=1, clock=c2)
    print("Burst (t=0):")
    for i in range(1, 11):
        print(f"  req {i:2}: TokenBucket={'ALLOW' if tb.allow() else 'DENY ':5} "
              f"LeakyBucket={'ALLOW' if lb.allow() else 'DENY'}")
    for sec in range(1, 4):
        c1.advance(1); c2.advance(1)
        print(f"t={sec}s: TokenBucket={'ALLOW' if tb.allow() else 'DENY'} "
              f"LeakyBucket={'ALLOW' if lb.allow() else 'DENY'}")

    print("\n=== Real-time demo (TokenBucket cap=3, 1 token/s) ===")
    real = TokenBucket(3, 1)
    for i in range(1, 7):
        print(f"  req {i}: {'ALLOW' if real.allow() else 'DENY'}")
    time.sleep(2)
    print("  after 2s sleep:", "ALLOW" if real.allow() else "DENY")
