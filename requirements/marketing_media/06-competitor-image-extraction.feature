# Feature 6: Competitor Image Extraction
# Iteration 6 - Extracting and downloading images from competitor product pages

Feature: Competitor Image Extraction
  As a vape product data analyst
  I want to extract product images from competitor websites
  So that I can acquire visual assets for product catalogs

  Background:
    Given the system has discovered target brand products on competitor sites
    And the system has image processing capabilities
    And the system implements respectful download practices

  Scenario: Product Page Image Discovery
    Given I am processing product page "https://vapeuk.co.uk/products/smok-novo-5-vape-kit"
    When the system extracts product images
    Then it should identify multiple image sources:
      | Image Type          | CSS Selectors              | Priority |
      | Main gallery        | .product-gallery img       | high     |
      | Thumbnails          | .product-thumbnails img    | medium   |
      | Zoom images         | [data-zoom-image]          | high     |
      | Alternative views   | .carousel img              | high     |
    And it should extract original high-resolution URLs
    And it should handle lazy-loaded images
    And it should skip placeholder images

  Scenario: Image Quality Analysis
    Given I have discovered product images on a competitor site
    When the system analyzes image quality
    Then it should check image dimensions and resolution
    And it should verify minimum quality thresholds:
      | Quality Metric      | Minimum Requirement |
      | Resolution         | 400x400 pixels      |
      | File size          | > 10KB              |
      | Aspect ratio       | Square preferred     |
    And it should detect and skip low-quality images
    And it should prioritize high-resolution variants

  Scenario: Lazy Loading and Dynamic Image Handling
    Given I encounter lazy-loaded images on competitor product pages
    When the system processes dynamic images
    Then it should simulate page scrolling to trigger image loading
    And it should wait for images to load completely
    And it should extract actual image URLs after loading
    And it should handle loading timeouts appropriately

  Scenario: Image Download with Attribution
    Given I have identified quality product images for "Vaporesso XROS 3"
    When the system downloads competitor images
    Then it should create organized storage:
      ```
      competitor-media/
      └── vapeuk.co.uk/
          └── vaporesso/
              └── xros-3-pod-kit/
                  ├── images/
                  │   ├── main-001.jpg
                  │   ├── main-002.jpg
                  │   └── thumbnail-001.jpg
                  └── metadata.json
      ```
    And it should implement download delays (minimum 2 seconds)
    And it should verify download integrity
    And it should generate comprehensive metadata

  Scenario: Image Metadata Generation
    Given I have downloaded competitor product images
    When the system generates image metadata
    Then it should create detailed metadata.json:
      ```json
      {
        "source_url": "https://vapeuk.co.uk/products/vaporesso-xros-3",
        "brand": "Vaporesso", 
        "product_name": "XROS 3 Pod Kit",
        "competitor": "vapeuk.co.uk",
        "discovery_date": "2024-11-17T14:30:00Z",
        "images": [
          {
            "filename": "main-001.jpg",
            "original_url": "https://cdn.vapeuk.co.uk/vaporesso-xros-3-1.jpg",
            "dimensions": "800x800",
            "file_size": "142KB"
          }
        ]
      }
      ```
    And it should include source attribution
    And it should track image processing details

  Scenario: Watermark and Logo Detection
    Given I am downloading competitor product images
    When the system analyzes images for watermarks
    Then it should detect competitor logos or watermarks
    And it should flag images with visible branding
    And it should assess watermark prominence
    And it should log watermark detection results
    And it should prioritize clean images when available

  Scenario: Image Format Optimization
    Given I have downloaded various image formats from competitors
    When the system processes downloaded images
    Then it should handle multiple formats:
      | Original Format | Processing Action        |
      | WebP           | Convert to JPEG if needed |
      | PNG            | Preserve transparency     |
      | JPEG           | Maintain quality          |
      | SVG            | Preserve for scalability  |
    And it should maintain original images
    And it should create web-optimized versions
    And it should generate thumbnails automatically