# Media Pack Discovery Guide

## Overview

The Media Pack Discovery feature automatically discovers, analyzes, and catalogs official media packs from brand websites. This enables efficient acquisition of authoritative product assets including press kits, marketing materials, and high-resolution media files.

## Quick Start

### 1. Ensure Brands are Configured

```bash
# Load brands if not already done
python brand_manager.py load brands.txt
```

### 2. Discover Media Packs

```bash
# Discover for all brands and save to registry
python brand_manager.py discover-media --save

# Or discover for specific brand
python brand_manager.py discover-media --brand "Vaporesso" --save
```

### 3. View Discovered Media

```bash
# Show all discovered media packs
python brand_manager.py media-packs

# Filter by type
python brand_manager.py media-packs --type archive
```

## Features

### Media Pack URL Pattern Discovery

The system automatically checks standard media pack locations:

| Path Pattern    | Expected Content        |
|----------------|-------------------------|
| /media-pack    | Direct downloads        |
| /press         | Press kits              |
| /press-kit     | Press kits              |
| /resources     | Marketing materials     |
| /downloads     | Product assets          |
| /assets        | Brand assets            |
| /marketing     | Marketing materials     |
| /brand-assets  | Brand resources         |

### File Type Recognition

Automatically recognizes and categorizes media files:

| Extension  | Content Type        | Priority | Category  |
|-----------|---------------------|----------|-----------|
| .zip      | Compressed archive  | 1        | archive   |
| .rar      | Compressed archive  | 1        | archive   |
| .7z       | Compressed archive  | 1        | archive   |
| .tar.gz   | Compressed archive  | 1        | archive   |
| .pdf      | Documentation       | 2        | document  |
| .jpg      | High-res images     | 3        | image     |
| .png      | High-res images     | 3        | image     |
| .svg      | Vector graphics     | 3        | vector    |
| .ai       | Vector graphics     | 3        | vector    |
| .eps      | Vector graphics     | 3        | vector    |

**Priority System:**
- Priority 1 (Highest): Compressed archives (most comprehensive)
- Priority 2: Documentation
- Priority 3: Individual media files

### Media Pack Content Preview

Before downloading, the system analyzes each media pack:

- **File Size**: Retrieved via HEAD request
- **Content Type**: Determined from headers and extension
- **Accessibility**: Checks if file is accessible
- **Restrictions**: Detects authentication or access requirements
- **Download Time Estimate**: Based on file size

### Alternative Domain Discovery

Automatically discovers related domains:

Starting from `smoktech.com`, discovers:
- `smoktechstore.com`
- `smoktech-store.com`
- `shopsmoketech.com`
- `storesmoketech.com`

Each alternative domain is validated for authenticity and scanned for additional media sources.

### Access Restriction Handling

Detects and categorizes access restrictions:

| HTTP Status | Restriction Type           | Action                    |
|------------|---------------------------|---------------------------|
| 401        | Authentication required   | Marked as restricted      |
| 403        | Access forbidden          | Marked as restricted      |
| WWW-Authenticate header | Auth required  | Marked as restricted      |

Restricted content is logged but processing continues with other available sources.

## Commands

### discover-media

Discover media packs for brands.

```bash
# Discover for all brands
python brand_manager.py discover-media --save

# Discover for specific brand
python brand_manager.py discover-media --brand "SMOK" --save

# Discover without saving (preview only)
python brand_manager.py discover-media --brand "Vaporesso"
```

**Options:**
- `--brand, -b`: Discover for specific brand only
- `--save`: Save discovered media packs to brand registry

**Output Example:**
```
SMOK (smoktech.com)
  Found 3 media pack(s):
    1. ✓ Compressed archive (.zip)
       https://smoktech.com/media/press-kit-2024.zip
       Size: 45.2 MB
    2. ✓ Documentation (.pdf)
       https://smoktech.com/press/brand-guide.pdf
       Size: 2.1 MB
    3. ✓ High-res images (.jpg)
       https://smoktech.com/assets/product-photo.jpg
       Size: 856.0 KB
  ✓ Saved 3 media pack(s) to registry
```

### media-packs

Show discovered media packs from registry.

```bash
# Show all media packs
python brand_manager.py media-packs

# Show for specific brand
python brand_manager.py media-packs --brand "SMOK"

# Filter by file type category
python brand_manager.py media-packs --type archive
python brand_manager.py media-packs --type document
python brand_manager.py media-packs --type image
```

**Options:**
- `--brand, -b`: Show media packs for specific brand
- `--type, -t`: Filter by category (archive, document, image, vector)

**Output Example:**
```
Vaporesso
  Website: vaporesso.com
  Last scan: 2025-11-17T20:30:00
  Media packs: 5

  1. ✓ Compressed archive (.zip)
     https://vaporesso.com/media-pack/2024-q4.zip
     Size: 125.5 MB

  2. ✓ Compressed archive (.rar)
     https://vaporesso.com/press/brand-assets.rar
     Size: 89.3 MB

  3. ✓ Documentation (.pdf)
     https://vaporesso.com/resources/product-catalog.pdf
     Size: 15.2 MB
```

## Brand Model Integration

Media pack information is stored in the Brand model:

```python
@dataclass
class Brand:
    name: str
    website: str
    priority: str
    status: str
    # ... other fields ...
    
    # Media pack fields
    media_packs: Optional[List[Dict]] = None
    media_pack_count: int = 0
    last_media_scan: Optional[str] = None
```

Each media pack entry contains:

```python
{
    "url": "https://brand.com/media.zip",
    "file_type": ".zip",
    "file_size": 45678901,
    "content_type": "Compressed archive",
    "accessible": True,
    "restricted": False,
    "restriction_type": None,
    "estimated_download_time": 43.5,
    "discovered_from": "https://brand.com/press"
}
```

## Use Cases

### Initial Media Discovery

```bash
# 1. Configure brands
python brand_manager.py load brands.txt

# 2. Discover media packs
python brand_manager.py discover-media --save

# 3. Review findings
python brand_manager.py media-packs

# 4. Filter for comprehensive archives
python brand_manager.py media-packs --type archive
```

### Targeted Brand Scanning

```bash
# Scan specific high-priority brand
python brand_manager.py discover-media --brand "Vaporesso" --save

# View results
python brand_manager.py media-packs --brand "Vaporesso"
```

### Regular Updates

```bash
# Re-scan all brands to find new media
python brand_manager.py discover-media --save

# Compare with previous scan using timestamps
python brand_manager.py media-packs
```

### Access Restriction Analysis

```bash
# Discover and identify restricted content
python brand_manager.py discover-media --save

# Review all packs (including restricted)
python brand_manager.py media-packs

# Look for restriction indicators in output
```

## Technical Details

### Discovery Algorithm

1. **Standard Path Scanning**
   - Checks each standard media pack path pattern
   - Parses HTML for downloadable links
   - Identifies media file extensions

2. **Homepage Analysis**
   - Scans homepage for media-related keywords
   - Follows links to potential media pages
   - Extracts downloadable resources

3. **Alternative Domain Discovery**
   - Generates domain variations
   - Validates domain existence
   - Scans valid alternatives

4. **Content Analysis**
   - Executes HEAD requests for metadata
   - Checks accessibility and restrictions
   - Estimates download requirements

### File Size Formatting

File sizes are displayed in human-readable format:

- B (Bytes): < 1 KB
- KB (Kilobytes): < 1 MB
- MB (Megabytes): < 1 GB
- GB (Gigabytes): ≥ 1 GB

### Priority Ordering

Media packs are automatically prioritized:

1. **Comprehensive archives** (.zip, .rar, .7z)
   - Likely contain complete media kits
   - Preferred for bulk acquisition

2. **Documentation** (.pdf)
   - Brand guidelines and catalogs
   - Useful for context

3. **Individual media files** (.jpg, .png, .svg)
   - Specific assets
   - May require multiple downloads

## Best Practices

1. **Initial Scan**
   - Run discovery after adding new brands
   - Always use `--save` to persist findings
   - Review output for access restrictions

2. **Regular Updates**
   - Re-scan periodically for new media
   - Brands update media packs seasonally
   - Check `last_media_scan` timestamps

3. **Priority Focus**
   - Target archive files (.zip, .rar) first
   - These contain comprehensive media kits
   - Save time vs. downloading individual files

4. **Access Management**
   - Note restricted content
   - Contact brands directly for access
   - Document authentication requirements

5. **Validation**
   - Verify file accessibility before download
   - Check file sizes for reasonableness
   - Confirm URLs are still valid

## Troubleshooting

### No Media Packs Found

**Possible causes:**
- Brand doesn't have public media packs
- Media located at non-standard paths
- Website blocks automated scanning

**Solutions:**
- Check brand website manually
- Contact brand directly
- Try alternative domains

### Access Restrictions

**Issue:** Media packs marked as restricted

**Solutions:**
- Contact brand for access credentials
- Check if registration is required
- Look for alternative sources

### Network Timeouts

**Issue:** Discovery times out

**Solutions:**
- Increase timeout in config
- Check network connectivity
- Try discovering one brand at a time

### Outdated Information

**Issue:** URLs no longer work

**Solutions:**
- Re-run discovery to update
- Check brand website for changes
- Remove outdated entries

## API Usage

You can also use media pack discovery programmatically:

```python
from modules import MediaPackDiscovery, Config, setup_logger

# Initialize
config = Config()
logger = setup_logger('MediaDiscovery', config.logs_dir, config.log_level)
discovery = MediaPackDiscovery(config, logger)

# Discover media packs
media_packs = discovery.discover_media_packs("Vaporesso", "vaporesso.com")

# Prioritize results
prioritized = discovery.get_prioritized_packs(media_packs)

# Display results
for pack in prioritized:
    size = discovery.format_file_size(pack.file_size)
    print(f"{pack.content_type}: {pack.url} ({size})")
```

## Integration with Brand Management

Media pack discovery is fully integrated with brand management:

```bash
# Complete workflow
python brand_manager.py load brands.txt
python brand_manager.py validate
python brand_manager.py discover-media --save
python brand_manager.py media-packs --type archive

# Brand registry now contains:
# - Brand information
# - Validation status
# - Media pack inventory
# - Last scan timestamps
```

## Configuration

Media pack discovery uses existing configuration:

```env
# config.env
REQUEST_TIMEOUT=30        # Timeout for requests
REQUEST_DELAY=2          # Delay between requests
MAX_RETRIES=3            # Retry attempts
LOG_LEVEL=INFO           # Logging level
```

## Future Enhancements

Potential future features:
- JavaScript rendering for dynamic content
- AJAX-based file listing support
- Download automation
- Media pack extraction and analysis
- Content verification
- Duplicate detection
- Version tracking

## Support

For issues or questions:
1. Check this guide for common solutions
2. Review logged error messages
3. Verify network connectivity
4. Test with single brand first

## Examples

### Complete Discovery Workflow

```bash
# 1. Setup brands
cat > brands.txt << EOF
SMOK|smoktech.com|high
Vaporesso|vaporesso.com|high
VOOPOO|voopoo.com|medium
EOF

# 2. Load brands
python brand_manager.py load brands.txt

# 3. Discover media packs
python brand_manager.py discover-media --save

# 4. Review comprehensive archives
python brand_manager.py media-packs --type archive

# 5. Check specific brand
python brand_manager.py media-packs --brand "SMOK"
```

### Filtering and Analysis

```bash
# View all archives across brands
python brand_manager.py media-packs --type archive

# View all documents
python brand_manager.py media-packs --type document

# View images
python brand_manager.py media-packs --type image
```

The media pack discovery feature provides a comprehensive, automated approach to identifying and cataloging official brand media resources, streamlining the media acquisition process for vape product data analysis.
