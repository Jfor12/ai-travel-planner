#!/bin/bash

# Test Runner Script for AI Travel Planner
# This script provides convenient commands for running different test suites

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to check if pytest is installed
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        print_error "pytest is not installed!"
        echo "Install it with: pip install -r requirements.txt"
        exit 1
    fi
}

# Function to run all tests
run_all_tests() {
    print_header "Running All Tests"
    pytest tests/ -v
    print_success "All tests completed"
}

# Function to run tests with coverage
run_with_coverage() {
    print_header "Running Tests with Coverage"
    pytest tests/ -v \
        --cov=. \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-report=xml \
        --cov-branch
    print_success "Coverage report generated"
    echo "View HTML report: open htmlcov/index.html"
}

# Function to run unit tests only
run_unit_tests() {
    print_header "Running Unit Tests"
    pytest tests/test_ai.py tests/test_db.py tests/test_maps.py -v
    print_success "Unit tests completed"
}

# Function to run integration tests only
run_integration_tests() {
    print_header "Running Integration Tests"
    pytest tests/test_integration.py -v
    print_success "Integration tests completed"
}

# Function to run specific test file
run_specific_file() {
    if [ -z "$1" ]; then
        print_error "Please specify a test file"
        echo "Usage: ./run_tests.sh file test_ai.py"
        exit 1
    fi
    print_header "Running tests from $1"
    pytest "tests/$1" -v
}

# Function to run quick tests (skip slow ones)
run_quick_tests() {
    print_header "Running Quick Tests (Skipping Slow Tests)"
    pytest tests/ -v -m "not slow"
    print_success "Quick tests completed"
}

# Function to run linting
run_lint() {
    print_header "Running Code Quality Checks"
    
    # Check if linting tools are installed
    if command -v flake8 &> /dev/null; then
        echo "Running flake8..."
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics || true
    else
        print_warning "flake8 not installed, skipping"
    fi
    
    if command -v black &> /dev/null; then
        echo "Checking code formatting with black..."
        black --check --diff . || true
    else
        print_warning "black not installed, skipping"
    fi
    
    if command -v isort &> /dev/null; then
        echo "Checking import sorting..."
        isort --check-only --diff . || true
    else
        print_warning "isort not installed, skipping"
    fi
    
    print_success "Linting completed"
}

# Function to run security checks
run_security() {
    print_header "Running Security Checks"
    
    if command -v bandit &> /dev/null; then
        echo "Running bandit security scan..."
        bandit -r . -x ./tests,./venv,./.venv || true
    else
        print_warning "bandit not installed, skipping"
        echo "Install with: pip install bandit"
    fi
    
    if command -v safety &> /dev/null; then
        echo "Running safety check..."
        safety check || true
    else
        print_warning "safety not installed, skipping"
        echo "Install with: pip install safety"
    fi
    
    print_success "Security checks completed"
}

# Function to show coverage report
show_coverage() {
    if [ -d "htmlcov" ]; then
        print_header "Opening Coverage Report"
        if command -v open &> /dev/null; then
            open htmlcov/index.html
        elif command -v xdg-open &> /dev/null; then
            xdg-open htmlcov/index.html
        else
            print_warning "Cannot open browser automatically"
            echo "Open htmlcov/index.html manually"
        fi
    else
        print_error "Coverage report not found"
        echo "Run: ./run_tests.sh coverage"
    fi
}

# Function to clean test artifacts
clean_artifacts() {
    print_header "Cleaning Test Artifacts"
    rm -rf .pytest_cache
    rm -rf htmlcov
    rm -rf .coverage
    rm -rf coverage.xml
    rm -rf .tox
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    print_success "Test artifacts cleaned"
}

# Function to install test dependencies
install_deps() {
    print_header "Installing Test Dependencies"
    pip install -r requirements.txt
    pip install pytest pytest-cov pytest-mock coverage
    pip install flake8 black isort pylint bandit safety
    print_success "Dependencies installed"
}

# Function to show help
show_help() {
    echo "AI Travel Planner - Test Runner"
    echo ""
    echo "Usage: ./run_tests.sh [command]"
    echo ""
    echo "Commands:"
    echo "  all              Run all tests"
    echo "  coverage         Run tests with coverage report"
    echo "  unit             Run unit tests only"
    echo "  integration      Run integration tests only"
    echo "  quick            Run quick tests (skip slow ones)"
    echo "  file <filename>  Run specific test file"
    echo "  lint             Run code quality checks"
    echo "  security         Run security scans"
    echo "  show-coverage    Open coverage report in browser"
    echo "  clean            Clean test artifacts"
    echo "  install          Install test dependencies"
    echo "  help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh all"
    echo "  ./run_tests.sh coverage"
    echo "  ./run_tests.sh file test_ai.py"
    echo "  ./run_tests.sh quick"
}

# Main script logic
main() {
    check_pytest
    
    case "${1:-all}" in
        all)
            run_all_tests
            ;;
        coverage)
            run_with_coverage
            ;;
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        quick)
            run_quick_tests
            ;;
        file)
            run_specific_file "$2"
            ;;
        lint)
            run_lint
            ;;
        security)
            run_security
            ;;
        show-coverage)
            show_coverage
            ;;
        clean)
            clean_artifacts
            ;;
        install)
            install_deps
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
