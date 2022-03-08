"""pytest fixtures."""
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def bypass_setup_fixture():
    """Prevent setup."""
    with patch("custom_components.volkswagencarnet.async_setup", return_value=True,), patch(
        "custom_components.volkswagencarnet.async_setup_entry",
        return_value=True,
    ):
        yield


@pytest.fixture
def m_connection():
    """Real connection for integration tests."""
    return MockConnection()


class MockConnection:
    """Mock connection for testing."""

    def __init__(self, **kwargs):
        """Init."""
        pass

    async def doLogin(self):
        """No-op login."""
        return True

    async def update(self):
        """No-op update."""
        return True
