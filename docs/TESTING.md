# Testing Documentation

## Overview

This project includes a comprehensive testing suite to ensure code quality, reliability, and maintainability. The tests are written using pytest and cover unit tests, integration tests, and performance tests.

## Test Structure

```
tests/
├── __init__.py           # Makes tests a Python package
├── conftest.py          # Pytest configuration and shared fixtures
├── test_ai.py           # Unit tests for AI module
├── test_db.py           # Unit tests for database module
├── test_maps.py         # Unit tests for maps module
└── test_integration.py  # Integration and end-to-end tests
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Tests with Coverage
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Run Specific Test Files
```bash
# Test only AI module
pytest tests/test_ai.py -v

# Test only database module
pytest tests/test_db.py -v

# Test only maps module
pytest tests/test_maps.py -v

# Run integration tests
pytest tests/test_integration.py -v
```

### Run Tests by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Test Coverage

The project aims for >80% code coverage. View coverage reports:

1. **Terminal Report**: Shows coverage summary after running tests
2. **HTML Report**: Detailed line-by-line coverage at `htmlcov/index.html`
3. **XML Report**: For CI/CD integration at `coverage.xml`

### View HTML Coverage Report
```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
python -m http.server 8000 --directory htmlcov
```

## Test Categories

### 1. Unit Tests

**AI Module (`test_ai.py`)**
- `TestGenerateIntel`: Tests LLM-powered intelligence generation
- `TestRunChatResponse`: Tests chat functionality
- `TestRunGenResponse`: Tests generation responses
- `TestGeneratePlaceSummary`: Tests place summary generation

**Database Module (`test_db.py`)**
- `TestGetConnection`: Tests database connection management
- `TestSaveItinerary`: Tests saving travel itineraries
- `TestUpdateItinerary`: Tests updating saved data
- `TestDeleteItinerary`: Tests deletion operations
- `TestGetHistory`: Tests retrieving saved itineraries
- `TestSaveChatMessage`: Tests chat message persistence
- `TestLoadChatHistory`: Tests chat history retrieval

**Maps Module (`test_maps.py`)**
- `TestExtractMapData`: Tests coordinate extraction from text
- `TestDisplayLabeledMap`: Tests map visualization
- `TestGetLocationSummaries`: Tests location description extraction
- `TestCleanTextForPdf`: Tests text sanitization
- `TestCreatePdf`: Tests PDF generation
- `TestWikipediaSearchUrl`: Tests URL generation for Wikipedia
- `TestPlaceReferenceUrl`: Tests URL generation for Google Maps

### 2. Integration Tests (`test_integration.py`)

- `TestAppIntegration`: End-to-end application workflows
- `TestCrossModuleIntegration`: Module interaction tests
- `TestErrorHandling`: Error handling and resilience tests
- `TestDataValidation`: Input validation and sanitization
- `TestPerformance`: Performance and scalability tests

## Test Fixtures

Shared fixtures are defined in `conftest.py`:

- `mock_environment`: Mock environment variables
- `mock_streamlit`: Mock Streamlit components
- `mock_database_connection`: Mock database connections
- `sample_intel_response`: Sample AI-generated content
- `sample_coordinates_text`: Sample coordinate data
- `sample_itinerary_data`: Sample saved itineraries
- `sample_chat_history`: Sample chat conversations

## Writing New Tests

### Test Structure Template

```python
import pytest
from unittest.mock import Mock, patch

class TestYourFeature:
    """Test suite for your feature"""
    
    def test_feature_success(self):
        """Test successful execution"""
        # Arrange
        input_data = "test"
        
        # Act
        result = your_function(input_data)
        
        # Assert
        assert result == expected_output
    
    def test_feature_error_handling(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            your_function(invalid_input)
    
    @patch('module.external_dependency')
    def test_feature_with_mock(self, mock_dep):
        """Test with mocked dependencies"""
        mock_dep.return_value = "mocked"
        result = your_function()
        assert result is not None
```

### Best Practices

1. **Use descriptive test names**: `test_feature_with_valid_input_returns_expected_output`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Mock external dependencies**: APIs, databases, file systems
4. **Test edge cases**: Empty inputs, None values, invalid data
5. **Test error handling**: Exceptions, failures, timeouts
6. **Use fixtures**: Share common setup across tests
7. **Keep tests independent**: Each test should run in isolation
8. **Document test purpose**: Add docstrings explaining what's tested

## Continuous Integration

Tests run automatically on every push and pull request via GitHub Actions.

### CI Pipeline Stages

1. **Test**: Runs full test suite on Python 3.9, 3.10, 3.11
2. **Lint**: Code quality checks (flake8, black, isort)
3. **Security**: Security scanning (safety, bandit)
4. **Build**: Docker image build and validation
5. **Coverage**: Upload coverage reports to Codecov

### CI Configuration

See `.github/workflows/ci-cd.yml` for full pipeline configuration.

## Test Markers

Custom markers for organizing tests:

```python
@pytest.mark.unit
def test_unit_feature():
    pass

@pytest.mark.integration
def test_integration_feature():
    pass

@pytest.mark.slow
def test_slow_feature():
    pass

@pytest.mark.api
def test_api_feature():
    pass
```

## Mocking Strategy

### Mock External APIs

```python
@patch('ai.ChatGroq')
@patch('ai.TavilySearchResults')
def test_with_mocked_apis(mock_tavily, mock_groq):
    mock_groq.return_value = Mock()
    mock_tavily.return_value = Mock()
    # Test code
```

### Mock Database

```python
@patch('db.get_connection')
def test_with_mocked_db(mock_conn):
    mock_conn.return_value = Mock()
    # Test code
```

### Mock Streamlit

```python
@patch('streamlit.toast')
@patch('streamlit.warning')
def test_with_mocked_streamlit(mock_warn, mock_toast):
    # Test code
```

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Database Connection Errors**
```bash
# Tests use mocked connections by default
# Set DATABASE_URL to test database if needed
export DATABASE_URL="postgresql://test:test@localhost/testdb"
```

**API Key Errors**
```bash
# Tests use mock API keys
# Override in conftest.py if needed
```

### Debug Tests

```bash
# Run with verbose output
pytest -v -s

# Run specific test with print statements
pytest tests/test_ai.py::TestGenerateIntel::test_generate_intel_success -v -s

# Drop into debugger on failure
pytest --pdb
```

## Performance Testing

```bash
# Run performance tests only
pytest -m slow

# Profile test execution
pytest --durations=10
```

## Test Coverage Goals

| Module | Target Coverage | Current |
|--------|----------------|---------|
| ai.py | 85% | - |
| db.py | 90% | - |
| maps.py | 85% | - |
| ui.py | 70% | - |
| Overall | 80% | - |

## Contributing

When adding new features:

1. Write tests first (TDD approach recommended)
2. Ensure tests pass locally
3. Maintain or improve code coverage
4. Follow existing test patterns
5. Update this documentation if adding new test categories

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
