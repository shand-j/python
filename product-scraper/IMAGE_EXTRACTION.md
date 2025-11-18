# Competitor Image Extraction Guide

Complete guide to extracting and downloading product images from competitor websites with quality analysis and smart organization.

## Table of Contents
- [Overview](#overview)
- [Image Extraction](#image-extraction)
- [Quality Analysis](#quality-analysis)
- [Downloading Images](#downloading-images)
- [CLI Usage](#cli-usage)
- [Configuration](#configuration)
- [Examples](#examples)

## Overview

The Competitor Image Extraction system discovers, analyzes, and downloads product images from competitor websites with:

- **Multi-selector image discovery** across 5 image types
- **Quality analysis** with scoring system (0-100)
- **Lazy loading support** for dynamic images
- **Placeholder filtering** to skip logos/placeholders
- **Smart downloading** with duplicate detection
- **Brand-organized** directory structure

## Image Extraction

### Image Types Discovered

The system searches for images using multiple CSS selectors:

| Image Type | Priority | Selectors | Use Case |
|------------|----------|-----------|----------|
| Gallery | High | `.product-gallery img`, `.product-image-gallery img` | Main product photos |
| Zoom | High | `[data-zoom-image]`, `[data-large-image]` | High-resolution images |
| Carousel | High | `.carousel img`, `.slider img` | Product views carousel |
| Thumbnails | Medium | `.product-thumbnails img`, `.thumbs img` | Thumbnail images |
| Alternative | Medium | `.product-image img`, `picture img` | Other product images |

### Lazy Loading Support

Handles various lazy loading techniques:

```python
Supported Attributes:
- src (standard)
- data-src
- data-lazy
- data-lazy-src
- data-original
- data-zoom-image
- data-large-image
- srcset (multiple resolutions)
- data-srcset
```

### Placeholder Filtering

Automatically filters out non-product images:

**Placeholder Patterns:**
- `placeholder`, `no-image`, `default`
- `loading`, `spinner`, `1x1`
- `blank`, `dummy`

**Logo Patterns:**
- `logo`, `brand-icon`, `watermark`

## Quality Analysis

### Quality Metrics

Each image is analyzed and scored (0-100) based on:

| Metric | Weight | Scoring |
|--------|--------|---------|
| Resolution | 40 points | Min 400x400, optimal 800x800+ |
| File Size | 20 points | Min 10KB, optimal 100KB+ |
| Aspect Ratio | 20 points | Square images (1:1) preferred |
| Image Type Priority | 20 points | High priority types get more points |

### Quality Thresholds

```python
Minimum Quality Requirements:
- Width: 400px
- Height: 400px
- File Size: 10KB

High Resolution:
- Width: 800px+
- Height: 800px+
```

### Quality Score Examples

**High Quality (80-100):**
- 1200x1200px image
- 150KB file size
- 1:1 aspect ratio
- Gallery type

**Medium Quality (50-79):**
- 600x600px image
- 50KB file size
- Close to square ratio
- Thumbnail type

**Low Quality (0-49):**
- 300x300px image
- 8KB file size
- Non-square ratio
- Low priority type

## Downloading Images

### Directory Structure

```
competitor_images/
└── BRAND/
    └── COMPETITOR_SITE/
        ├── product-name-01.jpg
        ├── product-name-02.jpg
        ├── product-name-03.jpg
        └── product-name-metadata.json
```

### File Naming Convention

Images are renamed with standardized format:

```
Format: {sanitized-product-name}-{number}.{extension}

Examples:
- smok-novo-5-kit-01.jpg
- vaporesso-xros-3-pod-02.png
- lost-mary-disposable-03.webp
```

### Duplicate Detection

Uses MD5 checksums to detect and skip duplicate images:
- Calculates MD5 hash of image content
- Skips images with identical content
- Saves storage and download time

### Metadata Generation

Each product gets a metadata JSON file:

```json
{
  "brand": "SMOK",
  "product_name": "Novo 5 Kit",
  "competitor_site": "Vape UK",
  "downloaded_at": "2024-11-18 15:30:00",
  "total_images": 5,
  "downloaded": 3,
  "skipped": 1,
  "failed": 1,
  "images": [
    {
      "filename": "novo-5-kit-01.jpg",
      "url": "https://example.com/image1.jpg",
      "type": "gallery",
      "quality_score": 85,
      "size": 124853,
      "width": 1200,
      "height": 1200
    }
  ]
}
```

## CLI Usage

### Extract Images Command

Extract and optionally download images from discovered products:

```bash
# Basic extraction (analysis only, no download)
python competitor_manager.py extract-images

# Extract and download for specific brand
python competitor_manager.py extract-images --brand "SMOK" --save

# Extract from specific competitor site
python competitor_manager.py extract-images --site "Vape UK" --save

# Limit products and images
python competitor_manager.py extract-images --max-products 20 --images-per-product 3 --save

# Set quality threshold
python competitor_manager.py extract-images --min-quality 70 --save

# Complete example
python competitor_manager.py extract-images \
  --brand "SMOK" \
  --site "Vape UK" \
  --max-products 10 \
  --images-per-product 5 \
  --min-quality 60 \
  --save
```

**Options:**
- `--brand, -b`: Extract for specific brand only
- `--site, -s`: Extract from specific competitor site
- `--max-products, -p`: Maximum products to process (default: 10)
- `--images-per-product, -i`: Max images per product (default: 5)
- `--min-quality, -q`: Minimum quality score 0-100 (default: 50)
- `--save, -o`: Download and save images (analysis only without this flag)

### View Images Command

View summary of downloaded images:

```bash
# View all downloaded images
python competitor_manager.py images

# View images for specific brand
python competitor_manager.py images --brand "SMOK"
```

**Output Example:**
```
============================================================
Downloaded Images Summary
============================================================
Total Brands: 3
Total Images: 156
Total Size: 45.3 MB

SMOK
  Total Images: 89
  Total Size: 23.7 MB
    vape-uk: 45 images (12.3 MB)
    vape-superstore: 44 images (11.4 MB)

VAPORESSO
  Total Images: 42
  Total Size: 13.1 MB
    vape-uk: 42 images (13.1 MB)
```

## Configuration

### Quality Settings

Adjust quality thresholds in code:

```python
from modules import ImageExtractor

extractor = ImageExtractor()

# Customize thresholds
extractor.MIN_WIDTH = 500  # Default: 400
extractor.MIN_HEIGHT = 500  # Default: 400
extractor.MIN_FILE_SIZE = 15360  # Default: 10KB (10240)
extractor.HIGH_RES_WIDTH = 1000  # Default: 800
extractor.HIGH_RES_HEIGHT = 1000  # Default: 800
```

### Download Settings

Customize downloader behavior:

```python
from modules import CompetitorImageDownloader

downloader = CompetitorImageDownloader(
    base_dir="custom_images",  # Default: "competitor_images"
    user_agent="Custom User Agent"
)
```

## Examples

### Example 1: Extract High-Quality Images

Extract only high-quality images (70+ score) for premium brands:

```bash
python competitor_manager.py extract-images \
  --brand "SMOK" \
  --min-quality 70 \
  --images-per-product 3 \
  --save
```

### Example 2: Bulk Extraction

Extract images for multiple brands from all configured sites:

```bash
# First, ensure brands are discovered
python competitor_manager.py discover --brands brands_registry.json --save

# Then extract images
python competitor_manager.py extract-images \
  --max-products 50 \
  --images-per-product 5 \
  --min-quality 60 \
  --save
```

### Example 3: Site-Specific Extraction

Extract images from a specific competitor site only:

```bash
python competitor_manager.py extract-images \
  --site "Vape UK" \
  --max-products 20 \
  --save
```

### Example 4: Analysis Without Download

Analyze image quality without downloading:

```bash
python competitor_manager.py extract-images --max-products 5
```

Output shows quality analysis for each image without downloading.

## Workflow Integration

### Complete Product Media Acquisition

1. **Configure Competitor Sites:**
```bash
python competitor_manager.py load competitor_sites.txt
python competitor_manager.py health
```

2. **Discover Products:**
```bash
python competitor_manager.py discover --brands brands_registry.json --save
```

3. **Extract Images:**
```bash
python competitor_manager.py extract-images \
  --brand "SMOK" \
  --min-quality 60 \
  --images-per-product 5 \
  --save
```

4. **Review Downloads:**
```bash
python competitor_manager.py images --brand "SMOK"
```

### Programmatic Usage

Use modules directly in Python code:

```python
from modules import ImageExtractor, CompetitorImageDownloader

# Extract images
extractor = ImageExtractor()
images = extractor.extract_images('https://example.com/product')

# Filter by quality
quality_images = extractor.filter_quality_images(
    images,
    min_quality=60,
    analyze=True
)

# Get best images
best_images = extractor.get_best_images(
    quality_images,
    max_images=5,
    prefer_high_res=True
)

# Download images
downloader = CompetitorImageDownloader()
metadata = downloader.download_product_images(
    brand='SMOK',
    product_name='Novo 5 Kit',
    images=best_images,
    competitor_site='Vape UK',
    max_images=5
)

print(f"Downloaded {metadata['downloaded']} images")
```

## Best Practices

### Quality Filtering

- Use minimum quality 60+ for production catalogs
- Use 70+ for premium/featured products
- Use 50+ for comprehensive catalogs

### Download Limits

- Start with --max-products 10 to test
- Increase gradually to avoid overwhelming servers
- Use delays between products (built-in 1s delay)

### Storage Management

- Review downloads periodically
- Remove low-quality images manually if needed
- Monitor disk space usage

### Respectful Scraping

- Process products in batches
- Use appropriate delays
- Respect robots.txt and rate limits
- Monitor site health before bulk extraction

## Troubleshooting

### No Images Found

**Problem:** `Extracted 0 images`

**Solutions:**
- Check if product page has images
- Verify page loaded correctly
- Check if images are behind JavaScript (use browser dev tools)
- Try different URL or product

### Low Quality Scores

**Problem:** All images scored below threshold

**Solutions:**
- Lower --min-quality threshold
- Check image dimensions on website
- Verify images aren't thumbnails
- Try different products

### Download Failures

**Problem:** `Error downloading image`

**Solutions:**
- Check network connectivity
- Verify image URLs are accessible
- Check if site is blocking requests
- Review error messages in logs

### Duplicate Detection Issues

**Problem:** Too many images skipped as duplicates

**Solutions:**
- This is normal for products with repeated images
- Duplicate detection saves bandwidth
- Use skip_duplicates=False if needed in code

## Summary

The Competitor Image Extraction system provides:

✅ **Smart Discovery** - Multi-selector search across 5 image types
✅ **Quality Analysis** - Comprehensive scoring system (0-100)
✅ **Lazy Loading** - Handles modern dynamic image loading
✅ **Filtering** - Automatic placeholder/logo detection
✅ **Organization** - Brand/site directory structure
✅ **Deduplication** - MD5-based duplicate detection
✅ **Metadata** - Complete JSON manifests
✅ **Production Ready** - Tested with 15 test cases

Perfect for building comprehensive product catalogs with high-quality imagery from competitor sources!
