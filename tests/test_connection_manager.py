"""Tests for ConnectionManager class - Phase 1."""

import pytest
from query_viz.connection_manager import ConnectionManager


@pytest.mark.unit
def test_connection_manager_instantiation():
    """Test that ConnectionManager can be instantiated."""
    manager = ConnectionManager()
    assert manager is not None
    assert isinstance(manager, ConnectionManager)


@pytest.mark.unit
def test_connection_manager_import():
    """Test that ConnectionManager can be imported from main package."""
    from query_viz import ConnectionManager as ImportedConnectionManager
    
    manager = ImportedConnectionManager()
    assert manager is not None
    assert isinstance(manager, ImportedConnectionManager)
