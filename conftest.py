"""pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def query_viz():
    """Create a QueryViz instance for testing."""
    from query_viz import QueryViz
    return QueryViz()
