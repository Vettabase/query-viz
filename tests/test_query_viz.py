"""Basic test for QueryViz class."""

import pytest


@pytest.mark.unit
def test_query_viz_instantiation(query_viz):
    """Test that QueryViz can be instantiated."""
    assert query_viz is not None
