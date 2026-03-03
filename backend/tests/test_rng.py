from app.simulation.rng import TickRNG, derive_seed


def test_derive_seed_deterministic():
    """Same inputs always produce the same seed."""
    seed_a = derive_seed(42, 1)
    seed_b = derive_seed(42, 1)
    assert seed_a == seed_b


def test_derive_seed_varies_with_tick():
    """Different tick numbers produce different seeds."""
    seed_1 = derive_seed(42, 1)
    seed_2 = derive_seed(42, 2)
    assert seed_1 != seed_2


def test_derive_seed_varies_with_previous():
    """Different previous seeds produce different seeds."""
    seed_a = derive_seed(42, 1)
    seed_b = derive_seed(99, 1)
    assert seed_a != seed_b


def test_derive_seed_within_range():
    """Derived seed fits in a 64-bit signed integer."""
    for prev in [0, 1, 2**62, 999999999]:
        for tick in [1, 100, 999999]:
            seed = derive_seed(prev, tick)
            assert 0 <= seed < 2**63


def test_tick_rng_same_seed_same_sequence():
    """Two RNGs with the same seed produce identical sequences."""
    rng_a = TickRNG(12345)
    rng_b = TickRNG(12345)
    seq_a = [rng_a.random() for _ in range(100)]
    seq_b = [rng_b.random() for _ in range(100)]
    assert seq_a == seq_b


def test_tick_rng_different_seed_different_sequence():
    """Two RNGs with different seeds produce different sequences."""
    rng_a = TickRNG(12345)
    rng_b = TickRNG(54321)
    seq_a = [rng_a.random() for _ in range(20)]
    seq_b = [rng_b.random() for _ in range(20)]
    assert seq_a != seq_b


def test_tick_rng_all_methods():
    """All RNG methods return expected types without error."""
    rng = TickRNG(42)
    assert isinstance(rng.random(), float)
    assert isinstance(rng.uniform(1.0, 10.0), float)
    assert isinstance(rng.gauss(0.0, 1.0), float)
    assert isinstance(rng.randint(1, 100), int)
    assert 1 <= rng.randint(1, 100) <= 100
    assert rng.choice([10, 20, 30]) in [10, 20, 30]
    result = rng.choices([10, 20, 30], k=5)
    assert len(result) == 5
    assert all(v in [10, 20, 30] for v in result)


def test_tick_rng_seed_property():
    """Seed property returns the construction seed."""
    rng = TickRNG(42)
    assert rng.seed == 42
    # Calling methods doesn't change the stored seed
    rng.random()
    rng.gauss(0, 1)
    assert rng.seed == 42