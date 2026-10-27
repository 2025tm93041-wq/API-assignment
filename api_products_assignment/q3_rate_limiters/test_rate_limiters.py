import unittest
from rate_limiters import TokenBucket, LeakyBucket, LeakyBucketQueue


class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t


class Tests(unittest.TestCase):
    def test_token_burst_then_refill(self):
        c = Clock(); b = TokenBucket(3, 1, c)
        self.assertEqual([b.allow() for _ in range(4)], [True, True, True, False])
        c.t = 2
        self.assertEqual([b.allow() for _ in range(3)], [True, True, False])

    def test_token_cap(self):
        c = Clock(); b = TokenBucket(3, 1, c); c.t = 100
        self.assertEqual(sum(b.allow() for _ in range(10)), 3)

    def test_leaky_overflow_and_leak(self):
        c = Clock(); b = LeakyBucket(2, 1, c)
        self.assertEqual([b.allow() for _ in range(3)], [True, True, False])
        c.t = 1
        self.assertTrue(b.allow()); self.assertFalse(b.allow())

    def test_leaky_queue(self):
        c = Clock(); q = LeakyBucketQueue(2, 1, c)
        self.assertEqual([q.enqueue(i) for i in range(3)], [True, True, False])
        self.assertEqual(q.process(), [0])
        c.t = 1; self.assertEqual(q.process(), [1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
