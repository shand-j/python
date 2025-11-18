# Competitor Website Configuration Guide

## Overview

The Competitor Website Configuration feature provides ethical and respectful scraping capabilities for acquiring product data from competitor retail websites. It includes robots.txt compliance, site health monitoring, intelligent backoff strategies, and user agent rotation.

## Quick Start

### 1. Configure Competitor Sites

```bash
# Create sites file
cat > competitor_sites.txt << EOF
Vape UK|https://vapeuk.co.uk|high
Vape Superstore|https://www.vapesuperstore.co.uk|high
Vapourism|https://www.vapourism.co.uk|high
E-Cigarette Direct|https://www.ecigarettedirect.co.uk|medium
EOF

# Load sites
python competitor_manager.py load competitor_sites.txt
```

### 2. Check Site Health

```bash
# Check all sites
python competitor_manager.py health

# Check specific site
python competitor_manager.py health --site "Vape UK"
```

### 3. Verify Robots.txt Compliance

```bash
# Check robots.txt for site
python competitor_manager.py robots --site "Vape UK"
```

## Ethical Scraping Principles

This system is built on ethical web scraping principles:

1. **Respect robots.txt** - Always honor robots.txt directives
2. **Rate Limiting** - Configurable delays between requests
3. **Realistic User Agents** - Browser-like requests
4. **Health Monitoring** - Detect and back off when sites are stressed
5. **Legal Compliance** - Scrape only public data
6. **Transparency** - Clear identification via user agents

## Features

### Competitor Site Registry

Manage configurations for multiple competitor websites:

```bash
# List all configured sites
python competitor_manager.py list

# Filter by priority
python competitor_manager.py list --priority high

# Filter by status
python competitor_manager.py list --status active
```

### Scraping Parameters

Each site has configurable parameters with validation:

| Parameter           | Default | Min   | Max   | Purpose                    |
|---------------------|---------|-------|-------|----------------------------|
| request_delay       | 2.0s    | 0.5s  | 60s   | Delay between requests     |
| max_pages_per_session | 100   | 1     | 10000 | Limit scope per session    |
| concurrent_requests | 1       | 1     | 5     | Avoid overwhelming servers |
| timeout_seconds     | 30      | 5     | 300   | Request timeout limit      |

**Validation Rules:**
- Delays must be at least 0.5 seconds (respectful)
- Maximum 5 concurrent requests (prevent server overload)
- All parameters have reasonable min/max bounds

### Robots.txt Compliance

Automatic robots.txt parsing and enforcement:

```bash
# Check robots.txt for a site
python competitor_manager.py robots --site "Vape UK"
```

**Features:**
- Automatic fetch and parse of robots.txt
- Identifies allowed and disallowed paths
- Respects crawl-delay directives
- Handles missing robots.txt gracefully (assumes allowed)
- Logs compliance status

**Robots.txt Directives Supported:**
- `User-agent`: Matches specific agents
- `Allow`: Explicitly allowed paths
- `Disallow`: Blocked paths
- `Crawl-delay`: Minimum delay between requests

### Site Health Monitoring

Continuous monitoring with intelligent backoff:

```bash
# Monitor all sites
python competitor_manager.py health
```

**Metrics Tracked:**
- Response time (milliseconds)
- HTTP status codes
- Consecutive failures
- Success rate
- Block detection (403, 429, 503)

**Exponential Backoff:**

When a site fails or blocks requests, the system applies exponential backoff:

```
Failure 1: Wait 1 minute
Failure 2: Wait 2 minutes  
Failure 3: Wait 4 minutes
Failure 4: Wait 8 minutes
Failure 5: Wait 16 minutes
Failure 6: Wait 32 minutes
Maximum: 1 hour (60 minutes)
```

After the backoff period, requests can resume. If the site continues failing, backoff increases again.

### User Agent Rotation

Realistic browser user agents to avoid detection:

**Included User Agents:**
- Chrome on Windows (2 versions)
- Chrome on Mac (2 versions)
- Firefox on Windows (2 versions)
- Firefox on Mac (2 versions)
- Safari on Mac (2 versions)
- Edge on Windows (2 versions)

**Total:** 12 realistic browser user agents

**Rotation Modes:**
- **Random**: Selects random user agent for each request
- **Sequential**: Rotates through agents in order

### Request Frequency Adjustment

Dynamic adjustment based on site health:

**Factors Considered:**
1. **Response Time**
   - Slow sites (>3s): 2x delay multiplier
   - Medium sites (>1s): 1.5x delay multiplier
   - Fast sites (<1s): 1x multiplier

2. **Success Rate**
   - <50% success: 2x delay multiplier
   - <80% success: 1.5x delay multiplier
   - ≥80% success: 1x multiplier

**Example:**
```
Base delay: 2 seconds
Site slow (>3s) + low success (<50%):
Adjusted delay: 2s × 2.0 × 2.0 = 8 seconds
```

### Site Structure Analysis

Analyze competitor site structure:

```bash
python competitor_manager.py analyze --site "Vape UK"
```

**Analysis Includes:**
- Main category pages
- Pagination patterns  
- Product page URL structures
- Navigation hierarchy

*Note: Structure analysis requires manual configuration.*

## Commands

### load

Load competitor sites from file.

```bash
python competitor_manager.py load sites.txt
```

**File Format** (pipe-delimited):
```
Name|Base URL|Priority
Vape UK|https://vapeuk.co.uk|high
Vape Superstore|https://www.vapesuperstore.co.uk|medium
```

**Priority Levels:**
- `high` - Process first
- `medium` - Standard priority
- `low` - Process last

### list

List competitor sites with optional filters.

```bash
# List all sites
python competitor_manager.py list

# Filter by priority
python competitor_manager.py list --priority high

# Filter by status
python competitor_manager.py list --status active
```

**Status Values:**
- `pending` - Not yet validated
- `active` - Currently usable
- `blocked` - Site is blocking requests
- `inactive` - Disabled

### add

Add a new competitor site.

```bash
python competitor_manager.py add "Site Name" "https://site.com" --priority high --delay 2.0
```

**Options:**
- `--priority, -p`: Priority level (high, medium, low)
- `--delay, -d`: Request delay in seconds (default: 2.0)

### update

Update an existing site.

```bash
python competitor_manager.py update "Vape UK" --priority high --status active --delay 3.0
```

**Options:**
- `--priority, -p`: New priority
- `--status, -s`: New status
- `--delay, -d`: New request delay

### remove

Remove a competitor site.

```bash
python competitor_manager.py remove "Site Name"
```

### health

Check site health and update status.

```bash
# Check all sites
python competitor_manager.py health

# Check specific site
python competitor_manager.py health --site "Vape UK"
```

**Health Check Results:**
- Response time
- HTTP status code
- Block detection
- Consecutive failures

### robots

Check robots.txt compliance for a site.

```bash
python competitor_manager.py robots --site "Vape UK"
```

**Output:**
- Allowed paths
- Disallowed paths
- Crawl-delay directive
- Compliance status

### analyze

Analyze site structure (manual configuration required).

```bash
python competitor_manager.py analyze --site "Vape UK"
```

### history

Show registry change history.

```bash
python competitor_manager.py history
```

Shows last 20 registry changes with timestamps.

## Use Cases

### Initial Setup

```bash
# 1. Create sites configuration
cat > competitor_sites.txt << EOF
Vape UK|https://vapeuk.co.uk|high
Vape Superstore|https://www.vapesuperstore.co.uk|high
Vapourism|https://www.vapourism.co.uk|high
E-Cigarette Direct|https://www.ecigarettedirect.co.uk|medium
EOF

# 2. Load sites
python competitor_manager.py load competitor_sites.txt

# 3. Verify sites loaded
python competitor_manager.py list

# 4. Check health
python competitor_manager.py health

# 5. Check robots.txt compliance
python competitor_manager.py robots --site "Vape UK"
```

### Regular Monitoring

```bash
# Check health of all sites
python competitor_manager.py health

# Review high-priority sites
python competitor_manager.py list --priority high

# Check for blocked sites
python competitor_manager.py list --status blocked
```

### Handling Blocked Sites

```bash
# Identify blocked site
python competitor_manager.py health --site "Vape UK"

# If blocked, system applies exponential backoff automatically
# Wait for backoff period, then retry

# Manually mark as inactive if needed
python competitor_manager.py update "Vape UK" --status inactive
```

### Adjusting Parameters

```bash
# Increase delay for slow site
python competitor_manager.py update "Vape UK" --delay 5.0

# Change priority
python competitor_manager.py update "E-Cigarette Direct" --priority low
```

## Configuration

Competitor site configurations are stored in `competitor_sites_registry.json`:

```json
{
  "sites": [
    {
      "name": "Vape UK",
      "base_url": "https://vapeuk.co.uk",
      "priority": "high",
      "status": "active",
      "scraping_params": {
        "request_delay": 2.0,
        "max_pages_per_session": 100,
        "concurrent_requests": 1,
        "timeout_seconds": 30
      },
      "robots_txt_info": {
        "allowed_paths": [],
        "disallowed_paths": ["/admin/"],
        "crawl_delay": 1.0,
        "compliant": true
      },
      "site_health": {
        "last_check": "2025-11-18T12:00:00",
        "response_time_ms": 245.5,
        "status_code": 200,
        "is_blocked": false,
        "consecutive_failures": 0
      }
    }
  ]
}
```

## Best Practices

1. **Always Check Robots.txt First**
   - Verify compliance before scraping
   - Honor all directives

2. **Start with High Delays**
   - Begin with 2-3 second delays
   - Adjust based on site health

3. **Monitor Site Health Regularly**
   - Check health before scraping sessions
   - Respect backoff periods

4. **Use Realistic User Agents**
   - Built-in rotation provides good coverage
   - Avoid custom suspicious agents

5. **Limit Concurrent Requests**
   - Default of 1 is safest
   - Never exceed 5

6. **Respect Site Limits**
   - Keep max_pages_per_session reasonable
   - Take breaks between sessions

7. **Handle Blocks Gracefully**
   - Don't force through blocks
   - Wait for exponential backoff
   - Consider alternative sources

## Troubleshooting

### Site Shows as Blocked

**Symptoms:**
- HTTP 403, 429, or 503 status
- Consecutive failures ≥ 5
- In backoff state

**Solutions:**
- Wait for backoff period to expire
- Increase request delay
- Reduce concurrent requests
- Check if robots.txt changed
- Verify user agent is acceptable

### Robots.txt Parse Fails

**Symptoms:**
- Cannot fetch robots.txt
- Parse errors in logs

**Solutions:**
- Check if robots.txt exists manually
- Verify URL is correct
- Check network connectivity
- Site may be blocking requests

### Slow Response Times

**Symptoms:**
- High response times (>3 seconds)
- Timeouts

**Solutions:**
- System automatically adjusts delays
- Manually increase delay if needed
- Check site during off-peak hours
- Verify network connection

### Can't Add Site

**Symptoms:**
- Site addition fails
- Validation errors

**Solutions:**
- Check parameter values are in valid ranges
- Verify URL format is correct
- Ensure site name is unique

## API Usage

You can use the modules programmatically:

```python
from pathlib import Path
from modules import (
    CompetitorSiteManager, CompetitorSite,
    ScrapingParameters, RobotsTxtParser,
    SiteHealthMonitor, UserAgentRotator,
    setup_logger
)

# Initialize
logger = setup_logger('Scraper', None, 'INFO')
manager = CompetitorSiteManager(Path('sites.json'), logger)
health_monitor = SiteHealthMonitor(logger)
robots_parser = RobotsTxtParser(logger)
ua_rotator = UserAgentRotator(logger)

# Add site
site = CompetitorSite(
    name="Vape UK",
    base_url="https://vapeuk.co.uk",
    priority="high"
)
manager.add_site(site)

# Check health
health = health_monitor.check_site_health("Vape UK", "https://vapeuk.co.uk")
if health['is_healthy']:
    print("Site is healthy!")

# Check robots.txt
success, robots_info = robots_parser.fetch_and_parse("https://vapeuk.co.uk")
if robots_parser.can_fetch("https://vapeuk.co.uk", "/products"):
    print("Can scrape /products")

# Get user agent
user_agent = ua_rotator.get_user_agent()
```

## Legal and Ethical Considerations

**Important:**
- Only scrape publicly available data
- Respect intellectual property rights
- Honor Terms of Service
- Comply with data protection laws (GDPR, etc.)
- Don't overwhelm servers
- Be transparent about scraping activity

**This system provides tools for ethical scraping but does not guarantee legal compliance. Users are responsible for ensuring their scraping activities comply with all applicable laws and website terms.**

## Major UK Vape Retailers

Pre-configured support for major UK vape retailers:

| Retailer             | Website                          | Priority |
|----------------------|----------------------------------|----------|
| Vape UK              | https://vapeuk.co.uk             | High     |
| Vape Superstore      | https://vapesuperstore.co.uk     | High     |
| Vapourism            | https://vapourism.co.uk          | High     |
| E-Cigarette Direct   | https://ecigarettedirect.co.uk   | Medium   |

These can be loaded from the provided `competitor_sites.txt.example` file.

## Integration

Works alongside other features:

```bash
# Complete workflow
python competitor_manager.py load competitor_sites.txt
python competitor_manager.py health
python competitor_manager.py robots --site "Vape UK"

# After scraping, process product data
python main.py process_products.csv
```

## Future Enhancements

Potential future features:
- JavaScript rendering support (Selenium/Playwright)
- Automatic category detection
- Product URL pattern learning
- CAPTCHA handling
- Proxy rotation
- Session management
- Rate limit auto-detection

The competitor website configuration system provides a complete, ethical foundation for scraping retail websites while respecting their resources and complying with industry standards!
