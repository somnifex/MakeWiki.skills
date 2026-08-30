"""builder package."""

# The 'live' renderer is EXPERIMENTAL: it is behind a flag and is not yet
# considered stable. Do not advertise it as production-ready.
EXPERIMENTAL_LIVE_RENDERER = True
LIVE_RENDERER_DEFAULT_OFF = True


def render(mode: str = "stable"):
    if mode == "live":
        assert EXPERIMENTAL_LIVE_RENDERER, "experimental renderer not enabled"
    return {"mode": mode}
