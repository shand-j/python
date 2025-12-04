# Feature 9: Shopify Export and Integration
# Iteration 9 - Preparing and exporting media assets for Shopify integration

Feature: Shopify Export and Integration  
  As a vape product data analyst
  I want to export processed media assets for Shopify integration
  So that I can populate product catalogs with high-quality media

  Background:
    Given the system has a unified media catalog
    And the system understands Shopify asset requirements
    And the system can generate Shopify-compatible exports

  Scenario: Shopify Asset Optimization
    Given I have high-quality product images in the unified catalog
    When the system prepares assets for Shopify
    Then it should create multiple optimized versions:
      | Image Type        | Dimensions | Quality | Purpose           |
      | Thumbnail        | 300x300    | 80%     | Product listings  |
      | Standard         | 800x800    | 90%     | Product pages     |
      | High-resolution  | 1200x1200  | 95%     | Zoom functionality|
    And it should maintain aspect ratios
    And it should optimize file sizes for web delivery

  Scenario: Asset URL Generation
    Given I have optimized assets for Shopify export
    When the system generates asset URLs
    Then it should create CDN-compatible URLs:
      ```
      Structure Examples:
      - /assets/vaporesso/xros-3/thumb/vaporesso-xros-3-main.jpg
      - /assets/smok/novo-5/standard/smok-novo-5-angle-1.jpg
      - /assets/geekvape/aegis/high-res/geekvape-aegis-front.jpg
      ```
    And it should ensure URL uniqueness and consistency
    And it should support version management for updated assets

  Scenario: Product-Asset Mapping Generation
    Given I have products and their associated media assets
    When the system creates Shopify mappings
    Then it should generate product-asset relationship data:
      ```json
      {
        "sku": "VAPO-XROS3-BLK",
        "brand": "Vaporesso", 
        "product_name": "XROS 3 Pod Kit - Black",
        "primary_image": "/assets/vaporesso/xros-3/standard/main.jpg",
        "gallery_images": [
          "/assets/vaporesso/xros-3/standard/angle-1.jpg",
          "/assets/vaporesso/xros-3/standard/angle-2.jpg"
        ],
        "technical_docs": [
          "/assets/vaporesso/xros-3/docs/specifications.pdf"
        ],
        "source_quality": 9.2
      }
      ```
    And it should handle product variants appropriately
    And it should maintain source attribution metadata

  Scenario: Batch Export for Shopify Import
    Given I have completed product-asset mappings
    When the system generates Shopify import files
    Then it should create Shopify-compatible CSV format:
      | Column Name        | Example Value                    |
      | Handle            | vaporesso-xros-3-pod-kit         |
      | Title             | Vaporesso XROS 3 Pod Kit         |
      | Image Src         | https://cdn.../main.jpg          |
      | Image Alt Text    | Vaporesso XROS 3 Main View       |
      | Variant Image     | https://cdn.../variant-black.jpg |
    And it should support incremental updates
    And it should validate CSV format compliance

  Scenario: Asset Version Management
    Given I have existing Shopify assets that need updates
    When the system manages asset versions
    Then it should detect when assets have been updated
    And it should create new versions without breaking existing links
    And it should maintain rollback capabilities
    And it should notify when manual review is needed for changes

  Scenario: Quality Assurance for Export
    Given I am preparing assets for Shopify export
    When the system performs final quality checks
    Then it should validate all required assets are present:
      | Requirement Type    | Validation Rule              |
      | Primary image       | Must exist for each product  |
      | Image dimensions    | Must meet minimum thresholds |
      | File accessibility  | URLs must be reachable       |
      | Format compliance   | Must be web-compatible       |
    And it should generate export readiness report
    And it should flag any issues requiring resolution

  Scenario: Integration API Preparation
    Given I have export-ready assets and mappings
    When the system prepares for API integration
    Then it should provide REST API endpoints for:
      | Endpoint Purpose      | Example URL                     |
      | Asset retrieval       | /api/assets/{sku}              |
      | Product media lookup  | /api/products/{id}/media       |
      | Batch asset export    | /api/export/shopify            |
      | Quality reports       | /api/reports/quality           |
    And it should implement proper authentication
    And it should support pagination and filtering
    And it should provide comprehensive API documentation