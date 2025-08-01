"""Tests for DatabaseConnection abstract base class."""

import pytest
from query_viz.database.base import DatabaseConnection, SUCCESS, FAIL


##  *****
##  Mocks
##  *****


class ConcreteDatabaseConnection(DatabaseConnection):
    """Concrete implementation for testing"""
    
    def connect(self):
        self.status = SUCCESS
        return "connected"
    
    def execute_query(self, query):
        return ["col1", "col2"], [("value1", "value2")]
    
    def close(self):
        return "closed"


class IncompleteConnection(DatabaseConnection):
    """Incomplete implementation missing required methods"""
    
    def connect(self):
        pass
    
    # Missing execute_query and close methods


##  *****
##  Tests
##  *****


@pytest.fixture
def connection_config():
    """Sample connection configuration"""
    return {
        'name': 'test_db',
        'dbms': 'test',
        'host': 'localhost',
        'port': 3306,
        'user': 'testuser',
        'password': 'testpass'
    }


@pytest.mark.unit
def test_cannot_instantiate_abstract_base_class(connection_config):
    """Test that DatabaseConnection cannot be instantiated directly"""
    with pytest.raises(TypeError, match="Can't instantiate abstract class DatabaseConnection"):
        DatabaseConnection(connection_config, 10)


@pytest.mark.unit
def test_cannot_instantiate_incomplete_implementation(connection_config):
    """Test that incomplete implementations cannot be instantiated"""
    with pytest.raises(TypeError, match="Can't instantiate abstract class IncompleteConnection"):
        IncompleteConnection(connection_config, 10)


@pytest.mark.unit
def test_concrete_implementation_can_be_instantiated(connection_config):
    """Test that a complete concrete implementation can be instantiated"""
    conn = ConcreteDatabaseConnection(connection_config, 10)
    assert conn is not None
    assert isinstance(conn, DatabaseConnection)


@pytest.mark.unit
def test_initialization_sets_attributes(connection_config):
    """Test that initialization properly sets all attributes"""
    db_timeout = 15
    conn = ConcreteDatabaseConnection(connection_config, db_timeout)
    
    assert conn.name == 'test_db'
    assert conn.dbms == 'test'
    assert conn.host == 'localhost'
    assert conn.port == 3306
    assert conn.user == 'testuser'
    assert conn.password == 'testpass'
    assert conn.status is None
    assert conn.db_timeout == 15


@pytest.mark.unit
def test_concrete_methods_work(connection_config):
    """Test that concrete implementation methods work correctly"""
    conn = ConcreteDatabaseConnection(connection_config, 10)
    
    # Test connect
    result = conn.connect()
    assert result == "connected"
    assert conn.status == SUCCESS
    
    # Test execute_query
    columns, results = conn.execute_query("SELECT * FROM test")
    assert columns == ["col1", "col2"]
    assert results == [("value1", "value2")]
    
    # Test close
    result = conn.close()
    assert result == "closed"


@pytest.mark.unit
def test_status_constants():
    """Test that status constants are defined"""
    import query_viz.database.base_module
    assert hasattr(base_module, 'SUCCESS')
    assert hasattr(base_module, 'FAIL')


@pytest.mark.unit
def test_isinstance_check(connection_config):
    """Test that concrete implementations are instances of the abstract base"""
    conn = ConcreteDatabaseConnection(connection_config, 10)
    assert isinstance(conn, DatabaseConnection)


@pytest.mark.unit
def test_abstract_methods_are_defined():
    """Test that abstract methods are properly defined in the base class"""
    abstract_methods = DatabaseConnection.__abstractmethods__
    expected_methods = {'connect', 'execute_query', 'close'}
    assert abstract_methods == expected_methods
