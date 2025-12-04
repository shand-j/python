# Feature 5: Competitor Product Discovery
# Iteration 5 - Discovering and cataloging products on competitor websites

Feature: Competitor Product Discovery
  As a vape product data analyst
  I want to discover products on competitor websites
  So that I can identify target brand products for media acquisition

  Background:
    Given the system has configured competitor websites
    And the system has target brand lists
    And the system implements respectful crawling

  Scenario: Category Page Navigation
    Given I am processing competitor "https://vapeuk.co.uk"
    When the system navigates category pages
    Then it should process main categories systematically:
      | Category           | Expected Products |
      | /vape-kits        | 200-500 products  |
      | /disposable-vapes | 100-300 products  |
      | /vape-mods        | 150-400 products  |
    And it should handle pagination correctly
    And it should extract product URLs from each page
    And it should respect rate limiting between pages

  Scenario: Product URL Pattern Recognition
    Given I am scanning competitor product listings
    When the system identifies product URLs
    Then it should recognize common URL patterns:
      ```
      Examples:
      - /products/smok-novo-5-vape-kit
      - /products/vaporesso-xros-3-pod-kit  
      - /products/20mg-lost-mary-4in1-pod-vape-kit-2400-puffs
      ```
    And it should extract product identifiers from URLs
    And it should build comprehensive product URL inventory
    And it should detect URL parameters for variants

  Scenario: Brand-Specific Filtering
    Given I have target brands ["SMOK", "Vaporesso", "Lost Mary", "GeekVape"]
    And I am processing competitor product listings
    When the system filters for target brand products
    Then it should identify products using multiple methods:
      | Method              | Implementation                    |
      | Title matching      | Case-insensitive brand search     |
      | URL analysis        | Brand name in product slug        |
      | Breadcrumb check    | Brand in navigation breadcrumbs   |
    And it should prioritize exact matches over partial matches
    And it should log brand coverage statistics

  Scenario: Product Variant Detection
    Given I am processing a product URL with parameters like "?Flavour=Menthol"
    When the system analyzes product variants
    Then it should identify variant parameters:
      | Parameter Type | Example Values                |
      | Flavour       | Menthol, Strawberry, Grape    |
      | Nicotine      | 0mg, 10mg, 20mg             |
      | Color         | Black, Blue, Red             |
    And it should map variants to master product records
    And it should track unique variant combinations
    And it should preserve variant-specific URLs

  Scenario: Dynamic Content Handling
    Given I encounter dynamically loaded product listings
    When the system processes dynamic content
    Then it should detect infinite scroll patterns
    And it should simulate scrolling to load more products
    And it should wait for AJAX requests to complete
    And it should extract products from dynamically loaded content
    And it should handle loading timeouts gracefully

  Scenario: Product Discovery Progress Tracking
    Given I am processing multiple competitor sites
    When the system tracks discovery progress
    Then it should maintain discovery statistics:
      | Metric                    | Example Value |
      | Total products found      | 1,247        |
      | Target brand products     | 156          |
      | Sites processed           | 3/5          |
      | Processing time elapsed   | 15 minutes   |
    And it should provide real-time progress updates
    And it should estimate remaining processing time