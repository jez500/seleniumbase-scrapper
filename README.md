# SeleniumBase API

This project exposes an HTTP API for SeleniumBase, allowing you to fetch web page content and metadata via HTTP requests.

Its API is based on [scrapper](https://github.com/amerkurev/scrapper) (which uses playwrite) and uses the same parameters 
and response format so it should be interchangeable with it.

## Building the Docker Image

The `Dockerfile` downloads the SeleniumBase repository from GitHub during the build process, so you only need the `api` 
directory and `Dockerfile` locally.

### Basic Build

To build the Docker image with API support using the default SeleniumBase version (v4.44.10):

```bash
docker build -f Dockerfile -t seleniumbase-api .
```

### Build with Custom SeleniumBase Version

You can specify a different SeleniumBase version using the `SELENIUMBASE_VERSION` build argument:

```bash
docker build -f Dockerfile --build-arg SELENIUMBASE_VERSION=v4.44.10 -t seleniumbase-api .
```

Replace `v4.44.10` with any valid SeleniumBase git tag from the [SeleniumBase repository](https://github.com/seleniumbase/SeleniumBase).

## Running the Container

Start the container with the API server:

```bash
docker run -d -p 3000:3000 --name seleniumbase-api seleniumbase-api
```

The API will be automatically started and available on port 3000.

## Configuration

### Environment Variables

You can set default values for all API parameters using environment variables. This is useful for configuring the behavior 
of the API without changing query parameters for each request.

Example with environment variables:

```bash
docker run -d -p 3000:3000 \
  -e DEFAULT_CACHE=true \
  -e DEFAULT_FULL_CONTENT=false \
  -e DEFAULT_SCREENSHOT=false \
  -e DEFAULT_INCOGNITO=true \
  -e DEFAULT_TIMEOUT=60000 \
  -e DEFAULT_SLEEP=1000 \
  --name seleniumbase-api seleniumbase-api
```

Example with custom host and port:

```bash
docker run -d -p 9000:9000 \
  -e API_HOST=0.0.0.0 \
  -e API_PORT=9000 \
  --name seleniumbase-api seleniumbase-api
```

All available environment variables:

#### Server Configuration
- `API_HOST` (default: `0.0.0.0`) - The host/IP address the server binds to
- `API_PORT` (default: `3000`) - The port the server listens on

#### Scraper and Browser Defaults
- `DEFAULT_CACHE` (default: `false`)
- `DEFAULT_CACHE_TTL` (default: `3600` - cache time-to-live in seconds, 60 minutes)
- `DEFAULT_FULL_CONTENT` (default: `false`)
- `DEFAULT_SCREENSHOT` (default: `false`)
- `DEFAULT_USER_SCRIPTS` (default: empty)
- `DEFAULT_USER_SCRIPTS_TIMEOUT` (default: `0`)
- `DEFAULT_INCOGNITO` (default: `true`)
- `DEFAULT_TIMEOUT` (default: `60000`)
- `DEFAULT_WAIT_UNTIL` (default: `domcontentloaded`)
- `DEFAULT_SLEEP` (default: `0`)
- `DEFAULT_RESOURCE` (default: empty, all resources allowed)
- `DEFAULT_VIEWPORT_WIDTH` (default: empty)
- `DEFAULT_VIEWPORT_HEIGHT` (default: empty)
- `DEFAULT_SCREEN_WIDTH` (default: empty)
- `DEFAULT_SCREEN_HEIGHT` (default: empty)
- `DEFAULT_DEVICE` (default: `Desktop Chrome`)
- `DEFAULT_SCROLL_DOWN` (default: `0`)
- `DEFAULT_IGNORE_HTTPS_ERRORS` (default: `true`)
- `DEFAULT_USER_AGENT` (default: empty)
- `DEFAULT_LOCALE` (default: empty)
- `DEFAULT_TIMEZONE` (default: empty)
- `DEFAULT_HTTP_CREDENTIALS` (default: empty)
- `DEFAULT_EXTRA_HTTP_HEADERS` (default: empty)

### User Scripts

User scripts allow you to execute custom JavaScript code on the page after it loads but before article extraction begins. This is useful for:
- Removing advertisements
- Clicking cookie consent buttons
- Handling modal popups
- Customizing page content

**To use user scripts:**

1. Create your JavaScript files and place them in the `api/user_scripts` directory
2. Reference them in the API call using the `user-scripts` parameter

**Example user script** (`api/user_scripts/example-remove-ads.js`):

```javascript
// Remove common ad elements
(function() {
    const adSelectors = ['.advertisement', '.ad-container', '.ads', '#ad'];
    adSelectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => el.remove());
    });
})();
```

**Usage:**

```bash
curl -X GET "http://localhost:3000/api/article?url=https://example.com&user-scripts=example-remove-ads.js"
```

Multiple scripts can be specified separated by commas:

```bash
curl -X GET "http://localhost:3000/api/article?url=https://example.com&user-scripts=remove-ads.js,accept-cookies.js"
```

## API Endpoints

### GET /api/article

Fetches article content and metadata from a specified URL using SeleniumBase.

**Parameters:**

All parameters except `url` have default values that can be set via environment variables (with `DEFAULT_` prefix).

#### Scraper Settings

| Parameter | Description | Default | Env Variable |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------- | :-------- |
| `url` | Page URL. The page should contain the text of the article that needs to be extracted. | (required) | - |
| `cache` | All scraping results are always saved to disk. This parameter determines whether to retrieve results from cache or execute a new request. When set to true, existing cached results will be returned if available. By default, cache reading is disabled, so each request is processed anew. | `false` | `DEFAULT_CACHE` |
| `full-content` | If this option is set to true, the result will have the full HTML contents of the page (`fullContent` field in the response). | `false` | `DEFAULT_FULL_CONTENT` |
| `screenshot` | If this option is set to true, the result will have the link to the screenshot of the page (`screenshotUri` field in the response). Scrapper initially attempts to take a screenshot of the entire scrollable page. If it fails because the image is too large, it will only capture the currently visible viewport. | `false` | `DEFAULT_SCREENSHOT` |
| `user-scripts` | To use your JavaScript scripts on a webpage, put your script files into the `user_scripts` directory. Then, list the scripts you need in the `user-scripts` parameter, separating them with commas. These scripts will run after the page loads but before the article parser starts. This means you can use these scripts to do things like remove ad blocks or automatically click the cookie acceptance button. Keep in mind, script names cannot include commas, as they are used for separation.<br>For example, you might pass `example-remove-ads.js`. | | `DEFAULT_USER_SCRIPTS` |
| `user-scripts-timeout` | Waits for the given timeout in milliseconds after users scripts injection. For example if you want to navigate through page to specific content, set a longer period (higher value). The default value is 0, which means no sleep. | `0` | `DEFAULT_USER_SCRIPTS_TIMEOUT` |

#### Browser Settings

| Parameter | Description | Default | Env Variable |
| :---------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------- | :-------- |
| `incognito` | Allows creating `incognito` browser contexts. Incognito browser contexts don't write any browsing data to disk. | `true` | `DEFAULT_INCOGNITO` |
| `timeout` | Maximum operation time to navigate to the page in milliseconds; defaults to 60000 (60 seconds). Pass 0 to disable the timeout. | `60000` | `DEFAULT_TIMEOUT` |
| `wait-until` | When to consider navigation succeeded, defaults to `domcontentloaded`. Events can be either:<br/>`load` - consider operation to be finished when the `load` event is fired.<br/>`domcontentloaded` - consider operation to be finished when the DOMContentLoaded event is fired.<br/>`networkidle` - consider operation to be finished when there are no network connections for at least 500 ms.<br/>`commit` - consider operation to be finished when network response is received and the document started loading. | `domcontentloaded` | `DEFAULT_WAIT_UNTIL` |
| `sleep` | Waits for the given timeout in milliseconds before parsing the article, and after the page has loaded. In many cases, a sleep timeout is not necessary. However, for some websites, it can be quite useful. Other waiting mechanisms, such as waiting for selector visibility, are not currently supported. The default value is 0, which means no sleep. | `0` | `DEFAULT_SLEEP` |
| `resource` | List of resource types allowed to be loaded on the page. All other resources will not be allowed, and their network requests will be aborted. **By default, all resource types are allowed.** The following resource types are supported: `document`, `stylesheet`, `image`, `media`, `font`, `script`, `texttrack`, `xhr`, `fetch`, `eventsource`, `websocket`, `manifest`, `other`. Example: `document,stylesheet,fetch`. | | `DEFAULT_RESOURCE` |
| `viewport-width` | The viewport width in pixels. It's better to use the `device` parameter instead of specifying it explicitly. | | `DEFAULT_VIEWPORT_WIDTH` |
| `viewport-height` | The viewport height in pixels. It's better to use the `device` parameter instead of specifying it explicitly. | | `DEFAULT_VIEWPORT_HEIGHT` |
| `screen-width` | The page width in pixels. Emulates consistent window screen size available inside web page via window.screen. Is only used when the viewport is set. | | `DEFAULT_SCREEN_WIDTH` |
| `screen-height` | The page height in pixels. | | `DEFAULT_SCREEN_HEIGHT` |
| `device` | Simulates browser behavior for a specific device, such as user agent, screen size, viewport, and whether it has touch enabled.<br/>Individual parameters like `user-agent`, `viewport-width`, and `viewport-height` can also be used; in such cases, they will override the `device` settings. | `Desktop Chrome` | `DEFAULT_DEVICE` |
| `scroll-down` | Scroll down the page by a specified number of pixels. This is particularly useful when dealing with lazy-loading pages (pages that are loaded only as you scroll down). This parameter is used in conjunction with the `sleep` parameter. Make sure to set a positive value for the `sleep` parameter, otherwise, the scroll function won't work. | `0` | `DEFAULT_SCROLL_DOWN` |
| `ignore-https-errors` | Whether to ignore HTTPS errors when sending network requests. The default setting is to ignore HTTPS errors. | `true` | `DEFAULT_IGNORE_HTTPS_ERRORS` |
| `user-agent` | Specific user agent. It's better to use the `device` parameter instead of specifying it explicitly. | | `DEFAULT_USER_AGENT` |
| `locale` | Specify user locale, for example en-GB, de-DE, etc. Locale will affect navigator.language value, Accept-Language request header value as well as number and date formatting rules. | | `DEFAULT_LOCALE` |
| `timezone` | Changes the timezone of the context. See ICU's metaZones.txt for a list of supported timezone IDs. | | `DEFAULT_TIMEZONE` |
| `http-credentials` | Credentials for HTTP authentication (string containing username and password separated by a colon, e.g. `username:password`). | | `DEFAULT_HTTP_CREDENTIALS` |
| `extra-http-headers` | Contains additional HTTP headers to be sent with every request. Example: `X-API-Key:123456;X-Auth-Token:abcdef`. | | `DEFAULT_EXTRA_HTTP_HEADERS` |

**Examples:**

Basic usage:
```bash
curl -X GET "http://localhost:3000/api/article?url=https://en.wikipedia.org/wiki/web_scraping"
```

With caching enabled:
```bash
curl -X GET "http://localhost:3000/api/article?url=https://example.com&cache=true"
```

With full content and screenshot:
```bash
curl -X GET "http://localhost:3000/api/article?url=https://example.com&full-content=true&screenshot=true"
```

With custom viewport and sleep:
```bash
curl -X GET "http://localhost:3000/api/article?url=https://example.com&viewport-width=1024&viewport-height=768&sleep=2000"
```

With user scripts:
```bash
curl -X GET "http://localhost:3000/api/article?url=https://example.com&user-scripts=example-remove-ads.js&user-scripts-timeout=1000"
```

With scroll for lazy-loading content:
```bash
curl -X GET "http://localhost:3000/api/article?url=https://example.com&scroll-down=1000&sleep=2000"
```

**Response Fields:**

The response to the `/api/article` request returns a JSON object containing the following fields:

| Parameter | Description | Type |
| :---------------- | :-------------------------------------------------------------------- | :------------ |
| `byline` | author metadata | null or str |
| `content` | HTML string of processed article content | null or str |
| `dir` | content direction | null or str |
| `excerpt` | article description, or short excerpt from the content | null or str |
| `fullContent` | full HTML contents of the page | null or str |
| `id` | unique result ID | str |
| `url` | page URL after redirects, may not match the query URL | str |
| `domain` | page's registered domain | str |
| `lang` | content language | null or str |
| `length` | length of extracted article, in characters | null or int |
| `date` | date of extracted article in ISO 8601 format | str |
| `query` | request parameters | object |
| `meta` | social meta tags (open graph, twitter) | object |
| `resultUri` | URL of the current result, the data here is always taken from cache | str |
| `screenshotUri` | URL of the screenshot of the page | null or str |
| `siteName` | name of the site | null or str |
| `textContent` | text content of the article, with all the HTML tags removed | null or str |
| `title` | article title | null or str |
| `publishedTime` | article publication time | null or str |

**Example Response:**

```json
{
  "id": "13cfc98ddfe0fd340fbccd298ada8c17",
  "url": "https://en.wikipedia.org/wiki/Web_scraping",
  "domain": "en.wikipedia.org",
  "title": "Web scraping - Wikipedia",
  "byline": null,
  "excerpt": null,
  "siteName": null,
  "content": "<article>...</article>",
  "textContent": "Web scraping - Wikipedia\nJump to content...",
  "length": 27104,
  "lang": "en",
  "dir": "ltr",
  "publishedTime": null,
  "fullContent": "<html>...</html>",
  "date": "2025-11-11T22:37:42.235424Z",
  "query": {
    "url": "https://en.wikipedia.org/wiki/Web_scraping"
  },
  "meta": {
    "og_title": "Web scraping - Wikipedia",
    "og_type": "website"
  },
  "resultUri": "api://article/13cfc98ddfe0fd340fbccd298ada8c17",
  "screenshotUri": null
}
```

**Error Handling:**

Error responses follow this structure:

```json
{
  "detail": [
    {
      "type": "error_type",
      "msg": "some message"
    }
  ]
}
```

For detailed error information, consult the Docker container logs.

**Response Codes:**
- Success (200): Returns JSON with article data and metadata
- Error (400): Missing URL parameter
- Error (500): Failed to fetch URL

### GET /health

Health check endpoint to verify the API is running.

**Example:**

```bash
curl -X GET "http://localhost:3000/health"
```

**Response:**
```json
{
  "status": "healthy",
  "service": "seleniumbase-api"
}
```

### GET /

Root endpoint that provides API documentation.

**Example:**

```bash
curl -X GET "http://localhost:3000/"
```

**Response:**
```json
{
  "service": "SeleniumBase API",
  "version": "1.0.0",
  "endpoints": {
    "/api/article": {
      "method": "GET",
      "description": "Fetch HTML content from a URL",
      "parameters": {
        "url": "The URL to fetch (required)"
      },
      "example": "/api/article?url=https://en.wikipedia.org/wiki/web_scraping"
    },
    "/health": {
      "method": "GET",
      "description": "Health check endpoint"
    }
  }
}
```

## Usage Examples

### Fetch Wikipedia Page

```bash
curl -X GET "http://localhost:3000/api/article?url=https://en.wikipedia.org/wiki/Python_(programming_language)"
```

### Fetch Any Website

```bash
curl -X GET "http://localhost:3000/api/article?url=https://www.example.com"
```

### Save HTML to File

```bash
curl -X GET "http://localhost:3000/api/article?url=https://www.example.com" -o output.html
```

## Features

- **Headless Browser**: Uses Chrome in headless mode for efficient scraping
- **JavaScript Rendering**: Fully renders JavaScript-heavy pages
- **Undetected Mode**: Uses SeleniumBase's undetected mode to bypass bot detection
- **Error Handling**: Proper error responses with meaningful messages
- **Auto Cleanup**: Automatically closes browser drivers after each request

## Technical Details

- **Framework**: Flask
- **Browser**: Chrome (headless)
- **Port**: 3000
- **SeleniumBase Driver**: UC mode enabled for better compatibility

## Container Management

### View Logs

```bash
docker logs seleniumbase-api
```

### Stop Container

```bash
docker stop seleniumbase-api
```

### Start Existing Container

```bash
docker start seleniumbase-api
```

### Remove Container

```bash
docker rm -f seleniumbase-api
```

## Interactive Mode

You can also run the container interactively while still having the API available:

```bash
docker run -it -p 3000:3000 --name seleniumbase-api seleniumbase-api
```

The API server will start automatically in the background, and you'll have access to a bash shell.

## Troubleshooting

### Check if API is running

```bash
curl http://localhost:3000/health
```

### View API logs inside container

```bash
docker exec -it seleniumbase-api bash
# Then check for the API process
ps aux | grep python
```

### Port already in use

If port 3000 is already in use, map to a different port:

```bash
docker run -d -p 9000:3000 --name seleniumbase-api seleniumbase-api
curl -X GET "http://localhost:9000/api/article?url=https://example.com"
```

## Testing

The project includes comprehensive test coverage for the API server, covering both unit tests for helper functions and integration tests for endpoints.

### Test Structure

- **api/tests/test_helpers.py** - Unit tests for helper functions (cache operations, parameter parsing, HTML extraction)
- **api/tests/test_endpoints.py** - Integration tests for API endpoints (/health, /, /api/article)

### Running Tests

Tests are designed to run inside the Docker container where all dependencies are available.

#### Run All Tests

```bash
# Start a container with bash access
docker run -it -p 3000:3000 --name seleniumbase-api-test seleniumbase-api bash

# Inside the container, navigate to the API directory
cd /SeleniumBase/api

# Run all tests
python3 -m unittest discover tests -v
```

#### Run Specific Test Files

```bash
# Inside the container
cd /SeleniumBase/api

# Run only helper function tests
python3 -m unittest tests.test_helpers -v

# Run only endpoint tests
python3 -m unittest tests.test_endpoints -v
```

#### Run Specific Test Classes

```bash
# Run only cache function tests
python3 -m unittest tests.test_helpers.TestCacheFunctions -v

# Run only /health endpoint tests
python3 -m unittest tests.test_endpoints.TestHealthEndpoint -v
```

### Test Coverage Summary

**Unit Tests (test_helpers.py):**
- Cache operations: key generation, save/load, expiration, corruption handling
- Parameter parsing: boolean, integer, and list parameters
- HTML extraction: meta tags, article content, text content, published time

**Integration Tests (test_endpoints.py):**
- `/health` endpoint: status checks, JSON response format
- `/` (root) endpoint: API documentation, service information
- `/api/article` endpoint:
  - URL parameter validation
  - All response fields (id, url, domain, title, byline, excerpt, etc.)
  - Parameter handling (full-content, screenshot, viewport, timeout, sleep, scroll, user-scripts, incognito)
  - Caching functionality (save, retrieve, TTL)
  - Screenshot generation
  - Error handling and format

For detailed testing documentation, see [api/tests/README.md](api/tests/README.md).
