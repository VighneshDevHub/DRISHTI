from app.config import Settings
from app.services import build_services


def make_services(**flags):
    """Full pipeline by default. Pass enable_baseline=False, enable_drift=False
    to isolate the Phase 1-3 lenses (their exact numbers are asserted in those tests)."""
    return build_services(Settings(db_path=":memory:", **flags))


def make_isolated():
    """Role + provenance + decoy lenses only (the Phase 3 configuration)."""
    return make_services(enable_baseline=False, enable_drift=False)


class FakeClock:
    """Move time on demand: token expiry and approval timeouts become deterministic tests."""
    def __init__(self, start: float = 1_000_000.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def make_enforcing(clock=None, **flags):
    """Enforce mode. Returns (services, clock)."""
    clock = clock or FakeClock()
    return build_services(Settings(db_path=":memory:", mode="enforce", **flags), clock=clock), clock
