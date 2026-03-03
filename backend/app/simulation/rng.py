import hashlib
import random


def derive_seed(previous_seed: int, tick_number: int) -> int:
    """Derive a deterministic seed from the previous seed and tick number.

    Uses SHA-256 truncated to 64-bit signed integer range.
    Given the same inputs, always returns the same output.
    """
    data = f"{previous_seed}:{tick_number}".encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    # Truncate to 64-bit signed int range
    return int(digest[:16], 16) % (2**63)


class TickRNG:
    """Deterministic RNG for a single simulation tick.

    Wraps stdlib random.Random so all calls are isolated
    from the global random state. Every method call advances
    the internal state deterministically.
    """

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    @property
    def seed(self) -> int:
        return self._seed

    def random(self) -> float:
        """Uniform float in [0.0, 1.0)."""
        return self._rng.random()

    def uniform(self, a: float, b: float) -> float:
        """Uniform float in [a, b]."""
        return self._rng.uniform(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        """Gaussian distribution."""
        return self._rng.gauss(mu, sigma)

    def randint(self, a: int, b: int) -> int:
        """Random integer in [a, b] inclusive."""
        return self._rng.randint(a, b)

    def choice(self, seq: list):
        """Random element from non-empty sequence."""
        return self._rng.choice(seq)

    def choices(self, population: list, weights: list[float] | None = None, k: int = 1) -> list:
        """Weighted random selection with replacement."""
        return self._rng.choices(population, weights=weights, k=k)