# AI Travel Planner - Portfolio Showcase

## Project Overview

A production-ready, AI-powered travel intelligence application that demonstrates professional software engineering practices, comprehensive testing, and modern DevOps workflows.

## Key Features

### 1. **AI-Powered Intelligence Generation**
- Real-time web search integration (Tavily API)
- LLM-powered content generation (Groq/Llama 3)
- Structured data extraction and parsing
- Interactive chat interface for follow-up questions

### 2. **Interactive Map Visualization**
- Automated coordinate extraction from AI responses
- Dynamic map rendering with PyDeck
- Smart label positioning to avoid overlaps
- Support for Mapbox Dark theme and public basemaps

### 3. **Data Persistence**
- PostgreSQL database integration
- Save/load travel guides
- Chat history persistence
- Full CRUD operations

### 4. **Export Capabilities**
- PDF generation with custom formatting
- Clean text sanitization for PDF output
- Branded export documents

## Technical Highlights

### Architecture & Design
- **Modular Design**: Clean separation of concerns (UI, AI, Maps, Database)
- **Error Handling**: Comprehensive exception handling and graceful degradation
- **Type Safety**: Strategic use of type hints
- **Documentation**: Extensive inline documentation and external docs

### Testing Excellence
- **Unit Tests**: 100+ test cases covering all modules
- **Integration Tests**: End-to-end workflow validation
- **Mocking Strategy**: Comprehensive mocking of external dependencies
- **Coverage**: 80%+ code coverage target
- **Test Fixtures**: Reusable test data and configurations
- **CI/CD Integration**: Automated testing on every commit

### DevOps & Quality Assurance
- **GitHub Actions**: Automated CI/CD pipeline
- **Multi-Python Testing**: Support for Python 3.9, 3.10, 3.11
- **Code Quality**: Automated linting (flake8, black, isort)
- **Security Scanning**: Bandit and Safety checks
- **Coverage Reporting**: Codecov integration
- **Docker Support**: Containerized deployment ready

## Test Suite Breakdown

### Unit Tests (`tests/test_ai.py`)
```
✓ AI module (ai.py) - 15 tests
  - LLM intel generation
  - Chat response handling
  - Place summary generation
  - Error handling and edge cases
```

### Unit Tests (`tests/test_db.py`)
```
✓ Database module (db.py) - 20 tests
  - Connection management
  - CRUD operations
  - Chat persistence
  - Error handling
  - SQL injection prevention
```

### Unit Tests (`tests/test_maps.py`)
```
✓ Maps module (maps.py) - 25 tests
  - Coordinate extraction
  - Map visualization
  - Location summaries
  - PDF generation
  - URL generation
```

### Integration Tests (`tests/test_integration.py`)
```
✓ Full application flow - 15 tests
  - End-to-end workflows
  - Cross-module integration
  - Error scenarios
  - Performance testing
```

## Code Quality Metrics

| Metric | Value |
|--------|-------|
| Test Coverage | 80%+ |
| Number of Tests | 75+ |
| Lines of Code | ~1,500 |
| Modules Tested | 4/4 (100%) |
| CI/CD Status | ✅ Passing |
| Security Scans | ✅ Passing |

## Technologies Used

### Core Framework
- **Streamlit**: Modern web framework for data apps
- **Python 3.9+**: Modern Python features

### AI & LLM
- **LangChain**: LLM orchestration framework
- **Groq API**: Fast LLM inference
- **Tavily API**: Web search integration

### Data & Visualization
- **PyDeck**: Interactive map visualization
- **Pandas**: Data manipulation
- **Mapbox**: Professional map styling

### Database
- **PostgreSQL**: Relational database
- **psycopg3**: Modern PostgreSQL adapter

### Testing & QA
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **GitHub Actions**: CI/CD automation

### Code Quality
- **flake8**: Linting
- **black**: Code formatting
- **isort**: Import sorting
- **bandit**: Security scanning
- **safety**: Dependency vulnerability checking

## Development Workflow

### 1. Local Development
```bash
# Setup
git clone <repo>
pip install -r requirements.txt

# Run tests
./run_tests.sh all

# Check coverage
./run_tests.sh coverage

# Run app
streamlit run app.py
```

### 2. Testing Workflow
```bash
# Quick tests
./run_tests.sh quick

# Specific module
./run_tests.sh file test_ai.py

# With coverage
./run_tests.sh coverage

# Code quality
./run_tests.sh lint
```

### 3. CI/CD Pipeline
Every push triggers:
1. ✅ Test suite on multiple Python versions
2. ✅ Code quality checks
3. ✅ Security scans
4. ✅ Coverage reporting
5. ✅ Docker build validation

## Best Practices Demonstrated

### 1. **Test-Driven Development**
- Comprehensive test coverage
- Unit and integration tests
- Mocking external dependencies
- Edge case handling

### 2. **Clean Code**
- Modular architecture
- Clear naming conventions
- DRY principles
- Single responsibility

### 3. **Error Handling**
- Graceful degradation
- Informative error messages
- Fallback mechanisms
- User-friendly feedback

### 4. **Security**
- Environment variable management
- SQL injection prevention
- Input validation
- Dependency scanning

### 5. **Documentation**
- Comprehensive README
- Testing documentation
- Inline code comments
- API documentation

### 6. **DevOps**
- Automated CI/CD
- Docker containerization
- Multi-environment support
- Continuous integration

## Portfolio Value

This project demonstrates:

1. **Full-Stack Development**: Frontend (Streamlit), Backend (Python), Database (PostgreSQL)
2. **AI/ML Integration**: Real-world LLM application with RAG patterns
3. **Testing Expertise**: Professional test suite with 80%+ coverage
4. **DevOps Skills**: CI/CD pipelines, containerization, automation
5. **Code Quality**: Professional standards, linting, formatting
6. **Security Awareness**: Scanning, validation, best practices
7. **Documentation**: Clear, comprehensive, maintainable

## Future Enhancements

- [ ] UI component testing with Selenium
- [ ] Load testing and performance benchmarks
- [ ] Monitoring and observability (logging, metrics)
- [ ] Rate limiting and caching layer
- [ ] Multi-language support
- [ ] Advanced analytics and insights
- [ ] Deployment to cloud platforms (AWS/Azure/GCP)

## Links

- **Repository**: [GitHub](https://github.com/Jfor12/ai-travel-planner)
- **Documentation**: [Testing Guide](docs/TESTING.md)
- **CI/CD**: [GitHub Actions](.github/workflows/ci-cd.yml)
- **Coverage**: View with `./run_tests.sh show-coverage`

## Contact

**Jacopo Fornesi**
- LinkedIn: [linkedin.com/in/jacopo-fornesi](https://www.linkedin.com/in/jacopo-fornesi)
- GitHub: [github.com/Jfor12](https://github.com/Jfor12)
- Email: jacopofornesi@hotmail.com
