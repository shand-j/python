# Brand Management Guide

## Overview

The Brand Management feature provides a comprehensive system for configuring, validating, and managing brand information for vape product data acquisition. This system allows you to organize brands with priorities, validate their websites, and maintain a historical registry of changes.

## Quick Start

### 1. Create a Brands File

Create a `brands.txt` file with your brands:

```
# Brand Configuration File
# Format: BrandName|website.com|priority
# Priority: high, medium, low (default: medium)

SMOK|smoktech.com|high
Vaporesso|vaporesso.com|high
VOOPOO|voopoo.com|medium
GeekVape|geekvape.com|medium
Lost Vape|lostvape.com|low
Uwell|uwellvape.com|medium
```

### 2. Load Brands

```bash
python brand_manager.py load brands.txt
```

This will:
- Parse the brands file
- Validate format
- Add brands to the registry
- Save to `brands_registry.json`

### 3. Validate Brands

```bash
python brand_manager.py validate
```

This checks each brand's website for:
- Domain accessibility
- SSL certificate validity
- Response time metrics

### 4. View Processing Queue

```bash
python brand_manager.py queue
```

Shows brands ordered by priority (high → medium → low) ready for processing.

## Features

### Brand Data Model

Each brand includes:
- **Name**: Brand identifier
- **Website**: Brand website URL
- **Priority**: Processing priority (high, medium, low)
- **Status**: Validation status (pending, validated, failed, inactive)
- **Response Time**: Website response time in seconds
- **SSL Valid**: Whether SSL certificate is valid
- **Error Message**: Any validation errors
- **Timestamps**: Created and updated timestamps

### Priority-Based Queuing

Brands are processed in priority order:
1. **High Priority** - Processed first
2. **Medium Priority** - Processed second
3. **Low Priority** - Processed last

Within each priority level, brands are sorted alphabetically for consistent ordering.

### Brand Registry

The registry maintains:
- Current brand configurations
- Validation results
- Complete history of changes
- Persistent JSON storage

### Website Validation

Validation checks include:
- **Accessibility**: DNS resolution and domain reachability
- **SSL Certificate**: HTTPS availability and certificate validity
- **Response Time**: Website performance metrics
- **Error Handling**: Detailed error messages for failures

## Commands

### Load Brands from File

```bash
# Load brands
python brand_manager.py load brands.txt

# Load and validate immediately
python brand_manager.py load brands.txt --validate
```

### Validate Brands

```bash
# Validate all brands
python brand_manager.py validate

# Validate specific brand
python brand_manager.py validate --brand "SMOK"
```

### List Brands

```bash
# List all brands
python brand_manager.py list

# Filter by priority
python brand_manager.py list --priority high

# Filter by status
python brand_manager.py list --status validated
```

### Show Processing Queue

```bash
python brand_manager.py queue
```

### Add New Brand

```bash
# Add brand with default priority
python brand_manager.py add "Brand Name" "website.com"

# Add brand with specific priority
python brand_manager.py add "SMOK" "smoktech.com" --priority high

# Add and validate immediately
python brand_manager.py add "SMOK" "smoktech.com" --validate
```

### Update Brand

```bash
# Update website
python brand_manager.py update "SMOK" --website "newsite.com"

# Update priority
python brand_manager.py update "SMOK" --priority low

# Update status
python brand_manager.py update "SMOK" --status inactive
```

### Remove Brand

```bash
python brand_manager.py remove "Brand Name"
```

### View History

```bash
python brand_manager.py history
```

Shows the last 20 registry modifications with timestamps and details.

## Configuration

### Command-Line Options

```bash
# Use custom configuration file
python brand_manager.py --config config.env load brands.txt

# Use custom registry file
python brand_manager.py --registry custom_registry.json list

# Enable verbose logging
python brand_manager.py --verbose validate
```

### Configuration File

The brand manager uses the same `config.env` as the product scraper:

```env
# Request Configuration
REQUEST_TIMEOUT=30
REQUEST_DELAY=2
MAX_RETRIES=3

# Logging
LOG_LEVEL=INFO
LOGS_DIR=./logs
```

## Brand File Format

### Basic Format

```
BrandName|website.com|priority
```

### Examples

```
# High priority brands
SMOK|smoktech.com|high
Vaporesso|vaporesso.com|high

# Medium priority (default)
VOOPOO|voopoo.com|medium
GeekVape|geekvape.com

# Low priority
Lost Vape|lostvape.com|low

# Comments start with #
# Empty lines are ignored
```

### Format Rules

1. Three fields separated by `|`
2. Brand name (required)
3. Website URL (required)
4. Priority: high, medium, or low (optional, defaults to medium)
5. Lines starting with `#` are comments
6. Empty lines are ignored

## Error Handling

### Common Errors

**Invalid URL Format**
```
Error: Invalid URL format - missing domain
```

**Domain Not Found**
```
Error: Domain not found (DNS resolution failed)
```

**Request Timeout**
```
Error: Request timeout after 30s
```

**SSL Certificate Issues**
```
Error: SSL error - certificate verification failed
```

### Error Summary Report

When loading brands from a file, any errors are summarized:

```
Error Summary (2 errors):
============================================================
1. Line 5: Missing website for Brand
2. Line 8: Invalid URL format
============================================================
```

Valid brands are still processed even when errors occur.

## Registry File Structure

The `brands_registry.json` file contains:

```json
{
  "brands": {
    "SMOK": {
      "name": "SMOK",
      "website": "smoktech.com",
      "priority": "high",
      "status": "validated",
      "response_time": 0.523,
      "ssl_valid": true,
      "last_validated": "2025-11-17T10:30:00",
      "error_message": null,
      "created_at": "2025-11-17T10:00:00",
      "updated_at": "2025-11-17T10:30:00"
    }
  },
  "history": [
    {
      "action": "add",
      "brand": "SMOK",
      "data": {...},
      "timestamp": "2025-11-17T10:00:00"
    }
  ],
  "last_updated": "2025-11-17T10:30:00"
}
```

## Use Cases

### Initial Setup

1. Create brands.txt with your brands
2. Load brands: `python brand_manager.py load brands.txt --validate`
3. Review results: `python brand_manager.py list`
4. Check queue: `python brand_manager.py queue`

### Daily Validation

```bash
# Re-validate all brands
python brand_manager.py validate

# Check for failures
python brand_manager.py list --status failed
```

### Adding New Brands

```bash
# Add and validate
python brand_manager.py add "NewBrand" "newbrand.com" --priority high --validate

# Verify addition
python brand_manager.py queue
```

### Updating Priorities

```bash
# Promote brand to high priority
python brand_manager.py update "Brand" --priority high

# View updated queue
python brand_manager.py queue
```

### Maintenance

```bash
# Mark inactive brands
python brand_manager.py update "OldBrand" --status inactive

# Remove completely
python brand_manager.py remove "OldBrand"

# View change history
python brand_manager.py history
```

## Integration with Product Scraper

The brand management system is designed to complement the product scraper:

1. **Configure Brands**: Use brand manager to set up and validate brands
2. **Process Queue**: Get priority-ordered list of brands to scrape
3. **Product Scraping**: Use product scraper with brand URLs
4. **Continuous Updates**: Re-validate brands periodically

## Best Practices

1. **Start with High Priority**: Focus on important brands first
2. **Regular Validation**: Run validation weekly to catch website changes
3. **Monitor Errors**: Review failed validations promptly
4. **Maintain History**: Keep registry file in version control (without sensitive data)
5. **Use Priorities**: Organize brands by business importance
6. **Document Changes**: Add comments in brands.txt for clarity

## Troubleshooting

### Network Issues

If validation fails due to network restrictions:
- Check firewall settings
- Verify DNS resolution
- Test with `curl` or `wget`
- Consider proxy configuration

### SSL Errors

For SSL certificate issues:
- Verify certificate is not expired
- Check for self-signed certificates
- Ensure proper HTTPS configuration

### Performance

For slow validations:
- Adjust `REQUEST_TIMEOUT` in config
- Use `--validate` flag selectively
- Validate specific brands instead of all

### Registry Corruption

If registry file is corrupted:
1. Backup current registry
2. Delete `brands_registry.json`
3. Reload from `brands.txt`
4. Re-validate brands

## Examples

### Complete Workflow

```bash
# 1. Setup
cp brands.txt.example brands.txt
# Edit brands.txt with your brands

# 2. Load and validate
python brand_manager.py load brands.txt --validate

# 3. Review results
python brand_manager.py list

# 4. Check queue
python brand_manager.py queue

# 5. Add new brand
python brand_manager.py add "NewBrand" "newbrand.com" --priority high

# 6. Update existing brand
python brand_manager.py update "SMOK" --priority medium

# 7. View history
python brand_manager.py history

# 8. Remove inactive brand
python brand_manager.py remove "OldBrand"
```

### Filtering and Reporting

```bash
# High priority brands only
python brand_manager.py list --priority high

# Failed validations
python brand_manager.py list --status failed

# Validated brands
python brand_manager.py list --status validated

# Queue for processing
python brand_manager.py queue > processing_order.txt
```

## API Usage

You can also use the brand management modules programmatically:

```python
from modules import BrandManager, BrandValidator, Brand, Config, setup_logger

# Initialize
config = Config()
logger = setup_logger('MyApp', config.logs_dir, config.log_level)
manager = BrandManager(logger=logger)
validator = BrandValidator(timeout=10, logger=logger)

# Load brands
brands, errors = manager.load_brands_from_file('brands.txt')

# Add to registry
for brand in brands:
    manager.add_brand(brand)

# Validate
for brand in brands:
    results = validator.validate_brand(brand.name, brand.website)
    brand.response_time = results['response_time']
    brand.ssl_valid = results['ssl_valid']
    brand.status = 'validated' if results['accessible'] else 'failed'
    manager.update_brand(brand)

# Get processing queue
queue = manager.get_processing_queue()

# Save
manager.save_registry()
```

## Support

For issues or questions:
1. Check this guide for common solutions
2. Review error messages in logs
3. Verify configuration settings
4. Test with example brands file

## Future Enhancements

Potential future features:
- Automated periodic validation
- Email notifications for failures
- Brand metrics and statistics
- Integration with media acquisition pipeline
- Bulk import/export capabilities
- Advanced filtering and search
