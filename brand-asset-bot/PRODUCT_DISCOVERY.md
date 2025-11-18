# Competitor Product Discovery Guide

Complete guide to discovering and cataloging products on competitor vape retailer websites.

## Overview

The Competitor Product Discovery system systematically scans configured competitor websites to:
- Identify product category pages
- Extract product URLs with pagination support
- Filter products by target brand names
- Build comprehensive product inventories organized by brand and category
- Save discovered products for further processing

## Quick Start

### 1. Prerequisites

Ensure you have:
- Configured competitor sites (see COMPETITOR_CONFIGURATION.md)
- Target brand list (brands_registry.json or custom file)

### 2. Discover Products

```bash
# Discover products from all active competitor sites
python competitor_manager.py discover --brands brands_registry.json --save

# Discover from specific site
python competitor_manager.py discover --site "Vape UK" --brands brands.txt --max-pages 20 --save

# Discover without saving (preview mode)
python competitor_manager.py discover --site "Vape Superstore" --brands brands.txt
```

### 3. View Discovered Products

```bash
# View all discovered products
python competitor_manager.py products

# Filter by brand
python competitor_manager.py products --brand "SMOK"

# Filter by category
python competitor_manager.py products --category "vape-kits"

# Filter by site and brand
python competitor_manager.py products --site "Vape UK" --brand "Vaporesso"
```

## Discovery Process

### Step 1: Category Discovery

The system automatically identifies main category pages using common patterns:

**Supported Category Types:**
- `/vape-kits` - Complete vape kits
- `/disposable-vapes` - Disposable vapes
- `/vape-mods` - Box mods and devices
- `/e-liquids` - E-liquid products
- `/tanks` - Vape tanks
- `/coils` - Replacement coils
- `/batteries` - Vape batteries
- `/accessories` - Vape accessories

### Step 2: Product URL Extraction

For each category, the system:
1. Processes pagination (configurable max pages)
2. Extracts product URLs using 4 regex patterns:
   - `/products?/[product-slug]` - Most common
   - `/[category]/[product].html` - Traditional e-commerce
   - `/p/[product-id]` - Short format
   - `/product/[product-slug]` - Alternative format

**Pagination Handling:**
- Detects common pagination patterns (`?page=N`, `&page=N`)
- Respects configured request delays
- Stops when no new products found

### Step 3: Brand Filtering

Products are filtered using multiple matching methods:

**URL-Based Matching** (fastest):
```
/products/smok-novo-5-kit → Matches "SMOK"
/products/vaporesso-xros-3 → Matches "Vaporesso"
```

**Content-Based Matching** (comprehensive):
- **Title tag**: `<title>SMOK Novo 5 Pod Kit | Vape UK</title>`
- **H1 heading**: `<h1>SMOK Novo 5 Pod Kit</h1>`
- **Meta description**: `<meta name="description" content="SMOK Novo 5...">`
- **Breadcrumbs**: `Home > Vape Kits > SMOK > Novo 5`

### Step 4: Product Data Extraction

For each matched product, the system extracts:

| Field | Source | Example |
|-------|--------|---------|
| Title | `<title>` or `<h1>` | "SMOK Novo 5 Pod Kit" |
| Price | Elements with class containing "price" | "£24.99" |
| Image | Product images | `https://example.com/images/smok-novo-5.jpg` |
| Stock Status | Elements with "stock" or "availability" | In Stock / Out of Stock |
| Category | From category URL | "vape-kits" |

### Step 5: Inventory Building

Products are organized into a structured inventory:

```json
{
  "competitor_site": "Vape UK",
  "total_products": 156,
  "brand_products": {
    "SMOK": [
      {
        "url": "https://vapeuk.co.uk/products/smok-novo-5",
        "title": "SMOK Novo 5 Pod Kit",
        "brand": "SMOK",
        "category": "vape-kits",
        "price": "£24.99",
        "in_stock": true,
        "discovered_at": "2024-11-18T10:30:00Z"
      }
    ],
    "Vaporesso": [...],
    "GeekVape": [...]
  },
  "category_summary": {
    "vape-kits": 89,
    "disposable-vapes": 34,
    "vape-mods": 33
  },
  "last_scan": "2024-11-18T10:30:00Z"
}
```

## Configuration Options

### Discovery Command Options

```bash
python competitor_manager.py discover [OPTIONS]
```

**Options:**
- `--site, -s` - Discover from specific site only (default: all active sites)
- `--brands, -b` - Brand list file (JSON registry or plain text)
- `--max-pages, -m` - Max pages per category (default: 10)
- `--save, -o` - Save discovered products to inventory

### Target Brands File

**JSON Format** (brands_registry.json):
```json
{
  "brands": [
    {"name": "SMOK", "website": "smoktech.com", "priority": "high"},
    {"name": "Vaporesso", "website": "vaporesso.com", "priority": "high"}
  ]
}
```

**Plain Text Format** (brands.txt):
```
SMOK
Vaporesso
GeekVape
Lost Mary
VOOPOO
```

## Output Files

Inventories are saved to `data/product_inventory/`:

```
data/product_inventory/
├── vape_uk_inventory.json
├── vape_superstore_inventory.json
└── vapourism_inventory.json
```

## Usage Examples

### Example 1: Quick Discovery

Discover products from all active sites with default settings:

```bash
python competitor_manager.py discover --brands brands_registry.json --save
```

**Output:**
```
Processing: Vape UK
Found 8 categories
Processing category: vape-kits
Page 1: Found 24 products
Page 2: Found 18 products
...
Matched product: SMOK - SMOK Novo 5 Pod Kit
Matched product: Vaporesso - Vaporesso XROS 3
...
Discovery Summary: Vape UK
Total products found: 156
By Brand:
  SMOK: 45 products
  Vaporesso: 38 products
  GeekVape: 29 products
...
✓ Inventory saved: data/product_inventory/vape_uk_inventory.json
```

### Example 2: Targeted Discovery

Discover only from specific site with more pages:

```bash
python competitor_manager.py discover \
  --site "Vape UK" \
  --brands brands.txt \
  --max-pages 20 \
  --save
```

### Example 3: View Discovered Products

```bash
# View all products
python competitor_manager.py products

# View SMOK products from Vape UK
python competitor_manager.py products --site "Vape UK" --brand "SMOK"

# View all vape kits
python competitor_manager.py products --category "vape-kits"
```

**Output:**
```
Vape UK - SMOK (45 products)

  ✓ SMOK Novo 5 Pod Kit
    https://vapeuk.co.uk/products/smok-novo-5
    Price: £24.99
  
  ✓ SMOK Nord 4 80W Pod Kit
    https://vapeuk.co.uk/products/smok-nord-4
    Price: £29.99
  
  ✓ SMOK RPM 5 Pro Kit
    https://vapeuk.co.uk/products/smok-rpm-5-pro
    Price: £34.99
  
  ... and 42 more
```

## Best Practices

### 1. Respectful Scraping

- Use configured request delays (minimum 2 seconds recommended)
- Limit max pages per category (10-20 pages is usually sufficient)
- Process one site at a time for first-time discovery
- Monitor site health during discovery

### 2. Target Brand Management

- Maintain accurate brand list
- Use normalized brand names (as they appear on competitor sites)
- Include brand variations if needed (e.g., "Lost Mary" vs "LostMary")

### 3. Periodic Updates

```bash
# Weekly discovery
python competitor_manager.py discover --brands brands_registry.json --save

# Update specific site
python competitor_manager.py discover --site "Vape UK" --brands brands_registry.json --save
```

### 4. Error Handling

The system automatically handles:
- Network errors and timeouts
- Missing pages or broken links
- Rate limiting and blocking detection
- Invalid HTML structure

Errors are logged without stopping the entire discovery process.

## Troubleshooting

### Issue: No products discovered

**Possible causes:**
1. Site structure changed - Update category patterns
2. Brand names don't match - Check brand name variations
3. Network issues - Check site health
4. Rate limiting - Increase request delay

**Solution:**
```bash
# Check site health first
python competitor_manager.py health --site "Vape UK"

# Try with higher delay
python competitor_manager.py discover --site "Vape UK" --brands brands.txt --save
```

### Issue: Too many false positives

**Possible causes:**
- Overly broad brand name matching
- Category pages being matched as products

**Solution:**
- Use more specific brand names in filter
- Review product URL patterns

### Issue: Discovery very slow

**Possible causes:**
- Too many pages configured
- Long request delays
- Large number of brands

**Solution:**
```bash
# Reduce max pages
python competitor_manager.py discover --max-pages 5 --save

# Process specific brands only
echo "SMOK
Vaporesso" > priority_brands.txt
python competitor_manager.py discover --brands priority_brands.txt --save
```

## Integration with Other Features

### Use with Brand Registry

```bash
# 1. Load brands
python brand_manager.py load brands.txt

# 2. Discover products
python competitor_manager.py discover --brands brands_registry.json --save

# 3. View by brand
python competitor_manager.py products --brand "SMOK"
```

### Process Discovered Products

After discovery, product URLs can be used for:
1. Detailed product scraping
2. Image acquisition
3. Price monitoring
4. Stock tracking
5. Competitive analysis

## Advanced Usage

### Custom Brand Filtering

For more complex filtering needs, the ProductDiscovery class can be used programmatically:

```python
from modules import ProductDiscovery

discovery = ProductDiscovery()

# Discover with custom logic
target_brands = ["SMOK", "Vaporesso", "GeekVape"]
inventory = discovery.discover_products_for_site(
    competitor_site="Vape UK",
    base_url="https://vapeuk.co.uk",
    target_brands=target_brands,
    max_pages_per_category=15,
    delay=2.5,
    timeout=30
)

# Access discovered products
for brand, products in inventory.brand_products.items():
    print(f"{brand}: {len(products)} products")
    for product in products:
        print(f"  - {product['title']}: {product['price']}")
```

### Batch Processing

Process multiple sites with custom settings:

```python
from pathlib import Path
import json
from modules import CompetitorSiteManager, ProductDiscovery

# Load site manager
manager = CompetitorSiteManager(Path("competitor_sites_registry.json"))
sites = manager.get_sites_by_priority("high")

# Load brands
with open("brands_registry.json") as f:
    brands_data = json.load(f)
    target_brands = [b["name"] for b in brands_data["brands"]]

# Discover from each site
discovery = ProductDiscovery()
for site in sites:
    print(f"Processing {site.name}...")
    inventory = discovery.discover_products_for_site(
        competitor_site=site.name,
        base_url=site.base_url,
        target_brands=target_brands,
        max_pages_per_category=10,
        delay=site.scraping_params.request_delay
    )
    
    # Save inventory
    output_file = f"data/product_inventory/{site.name.lower().replace(' ', '_')}_inventory.json"
    with open(output_file, 'w') as f:
        json.dump(inventory.to_dict(), f, indent=2)
```

## Summary

The Competitor Product Discovery system provides:
- ✅ Automated product discovery from competitor websites
- ✅ Smart brand-based filtering with multiple matching methods
- ✅ Comprehensive product data extraction
- ✅ Organized inventory management
- ✅ Respectful scraping with rate limiting
- ✅ Easy CLI interface for common workflows

Use this system to build comprehensive product catalogs from competitor sites, enabling competitive analysis, price monitoring, and targeted media acquisition.
