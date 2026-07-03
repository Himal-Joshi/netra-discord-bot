import pytest
from netra.core.i18n import i18n

def test_i18n_load():
    # Verify that the bundle for 'en' is loaded
    assert "en" in i18n.bundles

def test_i18n_get():
    # Verify a simple translation
    result = i18n.get("en", "ping-response", latency=100)
    assert "100" in result
    assert "Pong" in result
