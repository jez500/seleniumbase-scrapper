# SeleniumBase API Tests

This directory contains comprehensive test coverage for the SeleniumBase API server.

## Test Structure

- **test_helpers.py** - Unit tests for helper functions (cache operations, parameter parsing, HTML extraction)
- **test_endpoints.py** - Integration/feature tests for API endpoints (/health, /, /api/article)

## Running Tests

Tests are designed to run inside the Docker container where all dependencies are available.

### Running All Tests

```bash
# Inside the Docker container
cd /SeleniumBase/api
python3 -m unittest discover tests -v
```

### Running Specific Test Files

```bash
# Run only helper function tests
python3 -m unittest tests.test_helpers -v

# Run only endpoint tests
python3 -m unittest tests.test_endpoints -v
```

### Running Specific Test Classes

```bash
# Run only cache function tests
python3 -m unittest tests.test_helpers.TestCacheFunctions -v

# Run only /health endpoint tests
python3 -m unittest tests.test_endpoints.TestHealthEndpoint -v
```

### Running Specific Test Methods

```bash
# Run a single test
python3 -m unittest tests.test_helpers.TestCacheFunctions.test_get_cache_key_generates_consistent_hash -v
```

## Test Coverage

### Unit Tests (test_helpers.py)

#### Cache Functions
- Cache key generation (consistency, uniqueness, parameter order independence)
- Cache save/load operations
- Cache expiration (TTL handling)
- Handling of corrupted/old cache formats

#### Parameter Parsing Functions
- Boolean parameter parsing (various formats: true/false, 1/0, yes/no)
- Integer parameter parsing (valid/invalid strings, defaults)
- List parameter parsing (comma-separated values)

#### HTML Extraction Functions
- Meta tag extraction (Open Graph, Twitter cards)
- Article content extraction (article, main, common class names)
- Text content extraction (script/style removal, cleanup)
- Published time extraction (various meta tags and time elements)

### Integration Tests (test_endpoints.py)

#### /health Endpoint
- Returns 200 status code
- Returns JSON content
- Contains status and service fields

#### / (Root) Endpoint
- Returns 200 status code
- Returns JSON documentation
- Contains service info and endpoint documentation

#### /api/article Endpoint

**Basic Functionality:**
- Requires URL parameter (returns 400 without it)
- Returns all required fields (id, url, domain, title, etc.)
- Error handling (proper error format, exception handling)
- Driver lifecycle management (initialization, cleanup)

**Parameter Handling:**
- full-content: Include/exclude full HTML
- screenshot: Take screenshots when enabled
- viewport-width/height: Set browser viewport size
- timeout: Configure page load timeout
- sleep: Wait time after page load
- scroll-down: Scroll page by pixels
- user-scripts: Execute custom JavaScript
- incognito: Browser incognito mode

**Caching:**
- Results are saved to cache
- Cache is used when cache=true
- Cache is ignored by default

**Screenshots:**
- Screenshot not taken by default
- Screenshot taken and URI returned when screenshot=true

## Test Dependencies

The tests use Python's built-in `unittest` framework and `unittest.mock` for mocking.
Additional dependencies installed in the Docker container:
- flask
- beautifulsoup4
- seleniumbase
- pytest (optional, for alternative test runner)
- pytest-mock (optional)

## Notes

- Tests use mocking to avoid actual browser operations in endpoint tests
- Tests use temporary directories for cache/screenshots to avoid side effects
- All tests are isolated and can run independently
- Tests clean up their resources in tearDown methods
