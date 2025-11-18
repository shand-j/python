# Content Quality and Validation

Complete guide for validating and assessing the quality of acquired media assets.

## Overview

The Content Quality and Validation system provides comprehensive assessment tools for evaluating media assets acquired from both official brand sources and competitor websites. It ensures all content meets business requirements through automated quality scoring, brand consistency validation, and intelligent categorization.

## Table of Contents

1. [Features](#features)
2. [CLI Commands](#cli-commands)
3. [Quality Assessment](#quality-assessment)
4. [Brand Consistency](#brand-consistency)
5. [Content Categorization](#content-categorization)
6. [Quality Reports](#quality-reports)
7. [Best Practices](#best-practices)

## Features

### Image Quality Assessment
- **Resolution Validation**: Check pixel dimensions against minimum and optimal thresholds
- **Sharpness Detection**: Identify blurry images using Laplacian variance analysis
- **Color Profile Validation**: Verify RGB color mode and detect unusual profiles
- **Compression Analysis**: Detect over-compression and potential artifacts
- **Background Assessment**: Evaluate background uniformity and cleanliness

### Brand Consistency Validation
- **Logo Variation Detection**: Identify multiple logo versions across assets
- **Color Palette Extraction**: Extract and compare dominant colors
- **Consistency Scoring**: Rate brand consistency across multiple sources
- **Counterfeit Detection**: Identify potential unauthorized materials

### Content Categorization
- **Intelligent Categorization**: Auto-categorize into 5 main types (product, lifestyle, technical, marketing, branding)
- **Auto-Tagging**: Apply 20+ relevant tags based on content analysis
- **Metadata Enrichment**: Extract dimensions, file size, and content type
- **Batch Processing**: Process entire directories efficiently

## CLI Commands

### Brand Manager - Quality Check

Assess quality of extracted media packs from official brand sources.

```bash
# Basic quality check for all brands
python brand_manager.py quality-check

# Check specific brand
python brand_manager.py quality-check --brand "SMOK"

# Custom directory and minimum score
python brand_manager.py quality-check --directory extracted/ --min-score 7.0

# Generate detailed report
python brand_manager.py quality-check --brand "Vaporesso" --report reports/vaporesso_quality.json
```

**Options:**
- `--brand, -b`: Check quality for specific brand only
- `--directory, -d`: Directory to assess (default: extracted/)
- `--min-score, -m`: Minimum acceptable quality score 1-10 (default: 6.0)
- `--report, -r`: Save report to specified JSON file

### Competitor Manager - Validate Content

Validate content quality from competitor image extractions.

```bash
# Validate all competitor images
python competitor_manager.py validate-content

# Validate specific brand
python competitor_manager.py validate-content --brand "SMOK"

# Validate specific competitor site
python competitor_manager.py validate-content --site "Vape UK"

# Validate with custom threshold and report
python competitor_manager.py validate-content --brand "Vaporesso" --min-score 7.0 --report validation_report.json
```

**Options:**
- `--brand, -b`: Validate content for specific brand only
- `--site, -s`: Validate content from specific competitor site only
- `--min-score, -m`: Minimum acceptable quality score 1-10 (default: 6.0)
- `--report, -r`: Save report to specified JSON file

## Quality Assessment

### Quality Scoring System

Images are scored on a 1-10 scale using weighted metrics:

| Metric | Weight | Description |
|--------|--------|-------------|
| Resolution | 30% | Pixel dimensions evaluation |
| Sharpness | 25% | Blur detection via Laplacian variance |
| Color | 20% | Color profile validation |
| Compression | 15% | Artifact detection |
| Background | 10% | Uniformity and cleanliness |

### Resolution Thresholds

```
Low Resolution:    < 400x400 pixels   (Score: 1.0-5.0)
Acceptable:        400-800 pixels     (Score: 5.0-7.0)
Optimal:           800-1200 pixels    (Score: 7.0-9.0)
High Resolution:   > 1200 pixels      (Score: 9.0-10.0)
```

### Sharpness Detection

Uses Laplacian variance to detect blur:
- **Threshold**: 100.0
- **Sharp**: Variance > 300 (Score: 8.0-10.0)
- **Acceptable**: Variance 100-300 (Score: 6.0-8.0)
- **Blurry**: Variance < 100 (Score: 3.0, flagged)

### Quality Flags

Each image receives boolean flags:
- `is_low_res`: Resolution below minimum threshold
- `is_blur`: Sharpness below acceptable level
- `has_artifacts`: Compression artifacts detected
- `has_clean_background`: Uniform background detected
- `passed_quality`: Overall quality above minimum score

### Example Output

```
SMOK
  Assessing image quality...
  Total images: 45
  Passed quality: 38 (84.4%)
  Failed quality: 7
  Average score: 7.3/10
  Low quality images (< 6.0):
    - product-001.jpg: 5.2/10
    - lifestyle-03.jpg: 4.8/10
    ... and 5 more
```

## Brand Consistency

### Consistency Validation

Evaluates brand consistency across multiple assets:

**Logo Variation Detection**
- Identifies files with "logo" in filename
- Counts unique logo variations
- Flags excessive variations (> 3)

**Color Palette Analysis**
- Extracts dominant colors from each image
- Compares palettes across assets
- Calculates consistency ratio

**Consistency Scoring**

```
Consistency Score = (Color Consistency × 0.6) + (Typography × 0.4)
```

### Counterfeit Detection

Heuristics for identifying unauthorized materials:
- Suspicious keywords: fake, replica, copy, clone, knockoff
- Quality inconsistencies
- Mismatched branding elements

### Example Output

```
  Validating brand consistency...
  Consistency score: 8.2/10
  Logo variations: 2
  Inconsistencies found:
    - Significant color palette variations detected
```

## Content Categorization

### Categories

**Product** (Keywords: product, item, device, kit, mod)
- Product-only shots
- White background images
- Isolated product views

**Lifestyle** (Keywords: lifestyle, user, person, vaping, using)
- People using products
- Real-world scenarios
- Environmental context

**Technical** (Keywords: specs, specification, diagram, schematic, manual)
- Technical diagrams
- Specification sheets
- Assembly instructions

**Marketing** (Keywords: banner, promo, promotion, marketing, campaign)
- Promotional banners
- Campaign materials
- Marketing collateral

**Branding** (Keywords: logo, brand, trademark, identity)
- Logos and variations
- Brand identity elements
- Trademark assets

### Auto-Tags

20+ intelligent tags applied based on content:

**Product Tags**
- product-shot, close-up, hero-image, thumbnail

**Content Tags**
- unboxing, comparison, infographic, lifestyle-photo

**Component Tags**
- e-liquid, coil, battery, pod, tank, drip-tip

**Media Tags**
- banner, social-media, color-variant, kit-contents

**Quality Tags**
- high-resolution, hd, png-format, jpg-format, vector-format

### Example Output

```
  Categorizing content...
  Content categories:
    - product: 28 files
    - branding: 8 files
    - marketing: 6 files
    - lifestyle: 3 files
```

## Quality Reports

### Report Structure

JSON reports contain comprehensive quality data:

```json
{
  "generated_at": "2024-11-18T15:30:00Z",
  "SMOK": {
    "quality": {
      "product-001.jpg": {
        "overall_score": 8.5,
        "resolution_score": 9.0,
        "sharpness_score": 8.0,
        "color_score": 10.0,
        "compression_score": 7.0,
        "background_score": 9.0,
        "width": 1200,
        "height": 1200,
        "file_size": 245678,
        "passed_quality": true,
        "is_low_res": false,
        "is_blur": false,
        "issues": []
      }
    },
    "consistency": {
      "brand_name": "SMOK",
      "total_assets": 45,
      "logo_variations": 2,
      "overall_consistency_score": 8.2,
      "inconsistencies": [
        "Significant color palette variations detected"
      ],
      "counterfeit_indicators": []
    },
    "categories": {
      "product-001.jpg": {
        "category": "product",
        "tags": ["product-shot", "high-resolution"],
        "confidence": 0.85
      }
    }
  }
}
```

### Report Analysis

Use reports to:
1. Identify low-quality assets for re-acquisition
2. Track brand consistency issues
3. Organize assets by category
4. Generate quality metrics for stakeholders

## Best Practices

### Quality Thresholds

**Recommended minimum scores by use case:**
- **E-commerce listings**: 7.0+
- **Marketing materials**: 8.0+
- **Print materials**: 9.0+
- **Social media**: 6.0+

### Workflow Integration

1. **Extract Media** → Use brand_manager.py extract or competitor_manager.py extract-images
2. **Quality Check** → Run quality-check or validate-content
3. **Review Reports** → Analyze JSON reports for issues
4. **Re-acquire** → Download better quality versions of failed images
5. **Validate Again** → Confirm improvements

### Batch Processing

Process multiple brands efficiently:

```bash
# Quality check all extracted media packs
python brand_manager.py quality-check --report all_brands_quality.json

# Validate all competitor images
python competitor_manager.py validate-content --report all_competitor_validation.json
```

### Custom Thresholds

Adjust minimum scores based on requirements:

```bash
# Strict quality requirements (print materials)
python brand_manager.py quality-check --min-score 8.5 --brand "Premium Brand"

# Lenient quality (web thumbnails)
python competitor_manager.py validate-content --min-score 5.0 --brand "Budget Brand"
```

### Iterative Improvement

1. Initial extraction with default settings
2. Quality check to identify issues
3. Adjust extraction parameters (--min-quality in extract-images)
4. Re-extract problematic products
5. Validate improvements

## Python API

### Direct Usage

```python
from modules import (
    ImageQualityAssessor,
    BrandConsistencyValidator,
    ContentCategorizer
)

# Assess single image
assessor = ImageQualityAssessor()
metrics = assessor.assess_image('path/to/image.jpg')
print(f"Quality score: {metrics.overall_score}/10")

# Batch assess directory
results = assessor.batch_assess('path/to/directory')
assessor.generate_report(results, 'quality_report.json')

# Validate brand consistency
validator = BrandConsistencyValidator()
report = validator.validate_brand_assets('SMOK', 'path/to/assets')
validator.generate_report(report, 'consistency_report.json')

# Categorize content
categorizer = ContentCategorizer()
metadata = categorizer.categorize_file('path/to/file.jpg')
print(f"Category: {metadata.category}, Tags: {metadata.tags}")

# Batch categorization
catalog = categorizer.batch_categorize('path/to/directory')
categorizer.generate_catalog(catalog, 'content_catalog.json')
```

## Troubleshooting

### No Images Found

```
Directory not found: extracted/
```

**Solution**: Extract media packs first using the extract command.

### Low Quality Scores

If many images score below 6.0:
1. Check source quality (official media packs may have better quality)
2. Adjust extraction parameters (--min-quality, --images-per-product)
3. Target different competitor sites
4. Re-download from high-resolution sources

### Consistency Issues

If brand consistency scores are low:
1. Check if assets are from mixed sources
2. Verify logo variations are intentional
3. Compare against official brand guidelines
4. Flag inconsistent assets for manual review

## Next Steps

- [Media Pack Discovery](MEDIA_PACK_DISCOVERY.md) - Find official brand assets
- [Image Extraction](IMAGE_EXTRACTION.md) - Extract competitor images
- [Product Discovery](PRODUCT_DISCOVERY.md) - Discover products on competitor sites
