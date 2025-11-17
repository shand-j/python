# Brand Management Quick Reference

## Quick Start

```bash
# 1. Create brands.txt file
cp brands.txt.example brands.txt

# 2. Load brands
python brand_manager.py load brands.txt

# 3. Show processing queue
python brand_manager.py queue
```

## Common Commands

### Load & Validate
```bash
# Load brands from file
python brand_manager.py load brands.txt

# Load and validate immediately
python brand_manager.py load brands.txt --validate
```

### View Brands
```bash
# List all brands
python brand_manager.py list

# Filter by priority
python brand_manager.py list --priority high

# Filter by status
python brand_manager.py list --status validated

# Show processing queue
python brand_manager.py queue
```

### Manage Brands
```bash
# Add new brand
python brand_manager.py add "Brand" "website.com" --priority high

# Update brand
python brand_manager.py update "Brand" --priority low

# Remove brand
python brand_manager.py remove "Brand"

# View history
python brand_manager.py history
```

### Validate
```bash
# Validate all brands
python brand_manager.py validate

# Validate specific brand
python brand_manager.py validate --brand "SMOK"
```

## Brands File Format

```
# Format: BrandName|website.com|priority
# Priority: high, medium, low (default: medium)

SMOK|smoktech.com|high
Vaporesso|vaporesso.com|high
VOOPOO|voopoo.com|medium
GeekVape|geekvape.com|medium
Lost Vape|lostvape.com|low
```

## Priority Levels

- **high**: Processed first
- **medium**: Processed second (default)
- **low**: Processed last

## Status Values

- **pending**: Not yet validated
- **validated**: Successfully validated
- **failed**: Validation failed
- **inactive**: Marked as inactive

## Options

```bash
# Use custom registry file
--registry custom_registry.json

# Use custom config file
--config custom.env

# Enable verbose logging
--verbose
```

## Examples

```bash
# Complete workflow
python brand_manager.py load brands.txt --validate
python brand_manager.py queue
python brand_manager.py list --status validated

# Add and validate new brand
python brand_manager.py add "NewBrand" "newbrand.com" --priority high --validate

# Update priorities
python brand_manager.py update "SMOK" --priority medium
python brand_manager.py update "OldBrand" --status inactive

# Review changes
python brand_manager.py history
```

## Files

- `brands.txt` - Brand configuration input
- `brands_registry.json` - Brand registry (auto-created)
- `brands.txt.example` - Example template

## Validation Checks

- Domain accessibility
- DNS resolution
- SSL certificate validity
- Response time metrics
- Error handling

## See Also

- [Brand Management Guide](BRAND_MANAGEMENT.md) - Complete documentation
- [README.md](README.md) - Project overview
