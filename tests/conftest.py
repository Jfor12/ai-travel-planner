"""
Pytest configuration and shared fixtures for the test suite.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope='session')
def mock_environment():
    """Fixture to provide mock environment variables for tests"""
    return {
        'GROQ_API_KEY': 'test-groq-key',
        'TAVILY_API_KEY': 'test-tavily-key',
        'DATABASE_URL': 'postgresql://test:test@localhost/testdb',
        'MAPBOX_API_KEY': 'test-mapbox-key',
        'GROQ_MODEL_INTEL': 'llama-3.3-70b-versatile',
        'GROQ_MODEL_CHAT': 'llama-3.1-8b-instant',
        'GROQ_TEMP_INTEL': '0.3',
        'GROQ_TEMP_CHAT': '0.5'
    }


@pytest.fixture
def mock_streamlit():
    """Fixture to mock Streamlit components"""
    with patch('streamlit.toast'), \
         patch('streamlit.warning'), \
         patch('streamlit.error'), \
         patch('streamlit.info'), \
         patch('streamlit.pydeck_chart'):
        yield


@pytest.fixture
def mock_database_connection():
    """Fixture to provide a mock database connection"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None
    return mock_conn, mock_cursor


@pytest.fixture
def sample_destination():
    """Fixture providing a sample destination"""
    return "Paris, France"


@pytest.fixture
def sample_month():
    """Fixture providing a sample travel month"""
    return "June"


@pytest.fixture
def sample_intel_response():
    """Fixture providing a sample intelligence response"""
    return """
## 🍝 Gastronomy (What to order)
* **Croissant:** Flaky, buttery pastry - breakfast staple.
* **Baguette:** Traditional French bread - fresh daily.
* **Escargot:** Snails in garlic butter - classic delicacy.

## 🏘️ Neighborhoods
* **Le Marais:** Historic Jewish quarter, now trendy with boutiques and cafes.
* **Montmartre:** Artistic hilltop area with Sacré-Cœur basilica.
* **Latin Quarter:** Student district with bookshops and bistros.

## ⚠️ Logistics
* **Tips:** Service charge (15%) usually included - round up for good service.
* **Transport:** Metro is efficient. Buy Navigo pass for week-long stays.
* **Safety:** Watch for pickpockets near tourist sites and metro.

## 🎒 Seasonal (June)
* **Weather:** Warm 18-25°C, occasional rain.
* **Crowds:** High season - book in advance.

(---PAGE BREAK---)

### COORDINATES
Le Marais | 48.8566 | 2.3522
Montmartre | 48.8867 | 2.3431
Latin Quarter | 48.8526 | 2.3441
"""


@pytest.fixture
def sample_coordinates_text():
    """Fixture providing sample coordinate text"""
    return """
    Eiffel Tower | 48.8584 | 2.2945
    Louvre Museum | 48.8606 | 2.3376
    Arc de Triomphe | 48.8738 | 2.2950
    Notre-Dame | 48.8530 | 2.3499
    """


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as requiring API access"
    )


# Auto-use fixture to prevent actual API calls during testing
@pytest.fixture(autouse=True)
def prevent_actual_api_calls(monkeypatch):
    """Automatically prevent actual API calls in all tests"""
    def mock_api_call(*args, **kwargs):
        raise RuntimeError("Attempted to make actual API call during testing")
    
    # Only patch if the modules are imported
    try:
        monkeypatch.setenv('GROQ_API_KEY', 'test-key')
        monkeypatch.setenv('TAVILY_API_KEY', 'test-key')
    except Exception:
        pass


# Fixture to capture and suppress streamlit warnings
@pytest.fixture
def suppress_streamlit_warnings():
    """Suppress Streamlit warnings during tests"""
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        yield


# Helper fixture for temporary test data
@pytest.fixture
def temp_test_data(tmp_path):
    """Provide a temporary directory for test data"""
    test_data_dir = tmp_path / "test_data"
    test_data_dir.mkdir()
    return test_data_dir


# Mock for LLM responses
@pytest.fixture
def mock_llm_response():
    """Fixture to mock LLM streaming responses"""
    def _create_mock_stream(chunks):
        return iter(chunks)
    return _create_mock_stream


# Database fixtures
@pytest.fixture
def sample_itinerary_data():
    """Fixture providing sample itinerary data"""
    from datetime import datetime
    return [
        (1, 'Paris, France [June]', datetime(2025, 1, 15)),
        (2, 'London, UK [December]', datetime(2025, 2, 20)),
        (3, 'Rome, Italy [April]', datetime(2025, 3, 10))
    ]


@pytest.fixture
def sample_chat_history():
    """Fixture providing sample chat history"""
    return [
        {'role': 'user', 'content': 'What should I visit in Paris?'},
        {'role': 'assistant', 'content': 'You should visit the Eiffel Tower, Louvre Museum, and Notre-Dame.'},
        {'role': 'user', 'content': 'What about food?'},
        {'role': 'assistant', 'content': 'Try croissants, baguettes, and escargot.'}
    ]


# Performance testing fixtures
@pytest.fixture
def large_coordinate_dataset():
    """Fixture providing a large dataset for performance testing"""
    return "\n".join([
        f"Place {i} | {40 + (i % 50) * 0.01} | {-70 + (i % 50) * 0.01}"
        for i in range(200)
    ])


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatically cleanup after each test"""
    yield
    # Any cleanup code here
    pass
