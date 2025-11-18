# Media Pack Download and Extraction Guide

## Overview

The Media Pack Download and Extraction feature provides a complete pipeline for acquiring and processing official brand media packs. It handles downloading with resume support, integrity verification, automatic extraction, intelligent file organization, and comprehensive metadata generation.

## Quick Start

### Complete Workflow

```bash
# 1. Discover media packs
python brand_manager.py discover-media --save

# 2. Download discovered packs
python brand_manager.py download

# 3. Extract archives
python brand_manager.py extract

# 4. Access organized files
ls extracted/SMOK/smok-media-2024/
```

## Download Features

### Resumable Downloads

Downloads support automatic resumption if interrupted:

```bash
# Start download
python brand_manager.py download --brand "SMOK"

# If interrupted, resume automatically
python brand_manager.py download --brand "SMOK"
```

**How it works:**
- Uses HTTP Range headers
- Checks existing partial files
- Continues from last successful byte
- Verifies file integrity after completion

### Progress Tracking

Real-time download progress with:
- **Percentage Complete**: Current progress
- **Download Speed**: MB/s or KB/s
- **ETA**: Estimated time remaining
- **Downloaded/Total**: Bytes transferred

### File Integrity Verification

Every downloaded file is verified:
- **SHA256 Checksum**: Calculated after download
- **Logged for Reference**: Checksum saved in logs
- **Corruption Detection**: Failed downloads can be retried

### Brand-Specific Organization

Files are organized in a structured hierarchy:

```
downloads/
├── SMOK/
│   └── media-packs/
│       ├── smok-media-2024.zip
│       └── smok-press-kit.rar
├── Vaporesso/
│   └── media-packs/
│       └── vaporesso-assets.zip
└── VOOPOO/
    └── media-packs/
        └── voopoo-media.tar.gz
```

## Extraction Features

### Supported Archive Formats

- **ZIP** (.zip) - Fully supported
- **TAR.GZ** (.tar.gz, .tgz) - Fully supported
- **RAR** (.rar) - Requires rarfile library (optional)
- **7-Zip** (.7z) - Requires py7zr library (optional)

### Automatic File Categorization

Extracted files are automatically organized into categories:

| Category              | File Types / Keywords                    | Example Files              |
|-----------------------|------------------------------------------|----------------------------|
| product-images        | .jpg, .jpeg, .png, .webp, .gif          | product-001.jpg            |
| logos                 | "logo", "brand", "symbol" in filename    | smok-logo-white.png        |
| marketing-materials   | "banner", "poster", "ad", "promo"        | summer-campaign-banner.jpg |
| documentation         | .pdf, .doc, .docx, .txt, .md             | smok-specifications.pdf    |
| vectors               | .svg, .ai, .eps                          | logo-vector.svg            |
| videos                | .mp4, .mov, .avi, .wmv                   | product-demo.mp4           |
| fonts                 | .ttf, .otf, .woff                        | brand-font.ttf             |
| other                 | Uncategorized files                      | readme.txt                 |

### Standardized File Naming

Files are renamed with brand prefixes:

| Original Name         | Standardized Name          | Category           |
|-----------------------|----------------------------|--------------------|
| IMG_001.jpg          | smok-product-001.jpg       | product-images     |
| logo_variation_2.png | smok-logo-variation-2.png  | logos              |
| spec_sheet.pdf       | smok-spec-sheet.pdf        | documentation      |

### Organized Directory Structure

After extraction, files are organized:

```
extracted/
└── SMOK/
    └── smok-media-2024/
        ├── metadata.json
        ├── product-images/
        │   ├── smok-product-001.jpg
        │   ├── smok-product-002.jpg
        │   └── smok-product-003.jpg
        ├── logos/
        │   ├── smok-logo-primary.png
        │   └── smok-logo-white.svg
        ├── marketing-materials/
        │   └── smok-banner-summer.jpg
        └── documentation/
            └── smok-specifications.pdf
```

### Duplicate Detection

Automatically detects and removes duplicate files:

- **Content-Based**: Uses SHA256 checksums
- **Quality Selection**: Keeps largest version (highest quality)
- **Space Efficient**: Removes redundant files
- **Logged**: Duplicate removal logged for audit

### Corrupted Archive Handling

Protects against corrupted downloads:

1. **Integrity Check**: Verifies archive before extraction
2. **Repair Attempt**: Tries to recover partial data
3. **Quarantine**: Moves corrupted files to quarantine folder
4. **Retry Option**: Logs for potential re-download

### Metadata Generation

Each extraction creates a comprehensive metadata.json:

```json
{
  "brand": "SMOK",
  "media_pack": "smok-media-2024.zip",
  "archive_path": "/path/to/downloads/SMOK/media-packs/smok-media-2024.zip",
  "extraction_dir": "/path/to/extracted/SMOK/smok-media-2024",
  "download_date": "2024-11-17T10:30:00Z",
  "extraction_date": "2024-11-17T10:32:00Z",
  "total_files": 156,
  "categories": {
    "product-images": {
      "count": 89,
      "files": ["smok-product-001.jpg", "..."]
    },
    "logos": {
      "count": 12,
      "files": ["smok-logo-primary.png", "..."]
    },
    "marketing-materials": {
      "count": 34,
      "files": ["smok-banner-001.jpg", "..."]
    },
    "documentation": {
      "count": 21,
      "files": ["smok-specifications.pdf", "..."]
    }
  },
  "duplicates_removed": 3,
  "file_inventory": [
    {
      "name": "smok-product-001.jpg",
      "size": 2456789,
      "path": "product-images/smok-product-001.jpg"
    }
  ]
}
```

## Commands

### download

Download media packs for brands.

```bash
# Download for all brands with discovered media packs
python brand_manager.py download

# Download for specific brand
python brand_manager.py download --brand "SMOK"

# Download specific URL
python brand_manager.py download --brand "SMOK" --url "https://smoktech.com/media.zip"

# Disable resume (start fresh)
python brand_manager.py download --brand "SMOK" --no-resume
```

**Options:**
- `--brand, -b`: Download for specific brand only
- `--url, -u`: Download specific URL (requires --brand)
- `--resume`: Enable resumable downloads (default: true)

**Output Example:**
```
Downloading Media Packs (3 brand(s))
====================================

SMOK
  Downloading: https://smoktech.com/media/press-kit-2024.zip
  45.2% - 20.5MB/45.0MB - 2.3MB/s - ETA: 11s
  ✓ Downloaded: downloads/SMOK/media-packs/press-kit-2024.zip
  Checksum: a1b2c3d4...
```

### extract

Extract downloaded media pack archives.

```bash
# Extract all downloaded archives
python brand_manager.py extract

# Extract for specific brand
python brand_manager.py extract --brand "SMOK"

# Extract specific file
python brand_manager.py extract --brand "SMOK" --file "downloads/SMOK/media-packs/pack.zip"

# Skip automatic organization
python brand_manager.py extract --brand "SMOK" --no-organize
```

**Options:**
- `--brand, -b`: Extract for specific brand only
- `--file, -f`: Extract specific file (requires --brand)
- `--no-organize`: Skip file organization and categorization

**Output Example:**
```
Extracting Media Packs
======================

SMOK
  Extracting: smok-media-2024.zip
  ✓ Extracted 156 files

Extraction Summary: 1 successful, 0 failed
```

## Use Cases

### Initial Media Acquisition

```bash
# 1. Configure brands
python brand_manager.py load brands.txt

# 2. Discover available media packs
python brand_manager.py discover-media --save

# 3. Download all discovered packs
python brand_manager.py download

# 4. Extract and organize
python brand_manager.py extract

# 5. Review organized files
ls extracted/*/*/product-images/
```

### Targeted Brand Download

```bash
# Download and extract for specific brand
python brand_manager.py download --brand "Vaporesso"
python brand_manager.py extract --brand "Vaporesso"

# Review results
ls extracted/Vaporesso/
cat extracted/Vaporesso/*/metadata.json
```

### Resume Interrupted Download

```bash
# Start download (gets interrupted at 60%)
python brand_manager.py download --brand "SMOK"

# Resume automatically
python brand_manager.py download --brand "SMOK"
# Continues from 60%
```

### Manual URL Download

```bash
# Download specific media pack URL
python brand_manager.py download \
  --brand "SMOK" \
  --url "https://smoktech.com/special-release-2024.zip"

# Extract it
python brand_manager.py extract \
  --brand "SMOK" \
  --file "downloads/SMOK/media-packs/special-release-2024.zip"
```

### Batch Processing

```bash
# Process multiple brands
for brand in SMOK Vaporesso VOOPOO; do
  python brand_manager.py download --brand "$brand"
  python brand_manager.py extract --brand "$brand"
done
```

## Directory Structure

### After Download

```
downloads/
├── SMOK/
│   └── media-packs/
│       ├── smok-media-2024.zip (45.2 MB)
│       └── smok-press-kit.rar (22.1 MB)
└── Vaporesso/
    └── media-packs/
        └── vaporesso-assets.tar.gz (89.3 MB)
```

### After Extraction

```
extracted/
├── SMOK/
│   ├── smok-media-2024/
│   │   ├── metadata.json
│   │   ├── product-images/
│   │   │   ├── smok-product-001.jpg
│   │   │   └── ...
│   │   ├── logos/
│   │   │   ├── smok-logo-primary.png
│   │   │   └── ...
│   │   └── documentation/
│   │       └── smok-specifications.pdf
│   └── smok-press-kit/
│       └── ...
└── Vaporesso/
    └── vaporesso-assets/
        └── ...
```

## Technical Details

### Download Process

1. **Metadata Retrieval**: HEAD request to get file size and resume support
2. **Partial File Check**: Check for existing partial downloads
3. **Range Request**: Request from last byte if resuming
4. **Progress Tracking**: Monitor speed, progress, ETA
5. **Integrity Verification**: Calculate SHA256 checksum
6. **Storage**: Save in brand-specific directory

### Extraction Process

1. **Archive Type Detection**: Determine format (.zip, .tar.gz, etc.)
2. **Integrity Verification**: Check archive is not corrupted
3. **Extraction**: Extract to brand/archive-name directory
4. **Duplicate Detection**: Find and remove duplicate files
5. **Categorization**: Organize files by type
6. **Naming Standardization**: Rename with brand prefixes
7. **Metadata Generation**: Create comprehensive manifest

### File Categorization Algorithm

1. **Keyword Matching**: Check filename for category keywords (logo, banner, etc.)
2. **Extension Matching**: Match file extension to category
3. **Fallback**: Assign to "other" if no match

### Duplicate Detection

Uses content-based deduplication:
1. Calculate SHA256 hash for each file
2. Group files by hash
3. For duplicates, sort by file size
4. Keep largest (highest quality)
5. Remove smaller versions

## Configuration

Uses existing configuration from `config.env`:

```env
# Download Configuration
REQUEST_TIMEOUT=30        # Timeout for requests
REQUEST_DELAY=2          # Delay between requests
MAX_RETRIES=3            # Retry attempts

# Logging
LOG_LEVEL=INFO           # Logging level
LOGS_DIR=./logs          # Log directory
```

## Error Handling

### Network Errors

If download fails:
- Partial file is preserved
- Can resume on next attempt
- Error logged with details

### Corrupted Archives

If archive is corrupted:
- Moved to quarantine directory
- Repair attempted if possible
- Error logged for retry

### Extraction Errors

If extraction fails:
- Partial extraction preserved
- Error logged with details
- Can retry with same command

## Best Practices

1. **Discover First**: Always run discover-media before downloading
2. **Check Disk Space**: Ensure sufficient space for downloads and extraction
3. **Resume Support**: Use default resume behavior for large files
4. **Verify Checksums**: Check logs for integrity verification
5. **Review Metadata**: Use metadata.json to understand extraction results
6. **Organize Early**: Don't skip organization - makes files easier to find

## Troubleshooting

### Download Fails

**Issue:** Download keeps failing

**Solutions:**
- Check network connectivity
- Verify URL is still valid
- Check disk space
- Review logs for specific error
- Try downloading specific URL manually

### Resume Not Working

**Issue:** Download starts from beginning

**Solutions:**
- Check if server supports Range headers
- Verify partial file exists
- Check file permissions

### Extraction Fails

**Issue:** Archive won't extract

**Solutions:**
- Check if archive is corrupted
- Look in quarantine directory
- Try downloading again
- Verify archive format is supported

### Files Not Categorized

**Issue:** All files in "other" category

**Solutions:**
- Check if files have extensions
- Use --no-organize to skip categorization
- Files still accessible, just not organized

## API Usage

You can use download and extraction programmatically:

```python
from pathlib import Path
from modules import (
    MediaPackDownloader,
    MediaPackExtractor,
    Config,
    setup_logger
)

# Initialize
config = Config()
logger = setup_logger('MediaDownload', config.logs_dir, config.log_level)

# Download
download_dir = Path("downloads")
downloader = MediaPackDownloader(download_dir, config, logger)

result = downloader.download_media_pack(
    url="https://smoktech.com/media.zip",
    brand_name="SMOK",
    resume=True,
    verify_integrity=True
)

if result['success']:
    print(f"Downloaded: {result['filepath']}")
    print(f"Checksum: {result['checksum']}")
    
    # Extract
    extraction_dir = Path("extracted")
    extractor = MediaPackExtractor(extraction_dir, config, logger)
    
    result = extractor.extract_media_pack(
        Path(result['filepath']),
        brand_name="SMOK",
        organize=True,
        detect_duplicates=True
    )
    
    if result['success']:
        print(f"Extracted: {result['extraction_dir']}")
        print(f"Files: {result['total_files']}")
        print(f"Categories: {result['categories']}")
```

## Integration

Works seamlessly with other features:

```bash
# Complete pipeline
python brand_manager.py load brands.txt
python brand_manager.py validate
python brand_manager.py discover-media --save
python brand_manager.py media-packs --type archive
python brand_manager.py download
python brand_manager.py extract
```

## Future Enhancements

Potential future features:
- Parallel downloads
- Download scheduling
- Automatic retry with exponential backoff
- Cloud storage integration
- Download bandwidth limiting
- More archive format support (RAR, 7z)
- Image optimization during extraction
- Video preview generation

## Support

For issues:
1. Check this guide
2. Review error logs in logs/ directory
3. Verify file permissions
4. Check disk space
5. Test with single brand first

The download and extraction features provide a complete, production-ready solution for acquiring and organizing official brand media packs!
