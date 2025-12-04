# Feature 8: Cross-Source Integration and Deduplication
# Iteration 8 - Integrating media from all sources and removing duplicates

Feature: Cross-Source Integration and Deduplication
  As a vape product data analyst
  I want to integrate media from all sources and eliminate duplicates
  So that I can create a unified, high-quality media catalog

  Background:
    Given the system has media from official brand sources
    And the system has media from competitor sources  
    And the system has content quality assessments
    And the system can perform cross-source analysis

  Scenario: Cross-Source Product Matching
    Given I have the same product from multiple sources
    When the system matches products across sources
    Then it should use multiple matching criteria:
      | Matching Method        | Weight | Threshold |
      | Exact product name     | 100%   | 95%       |
      | Brand + model number   | 90%    | 85%       |
      | Similar image hashes   | 80%    | 75%       |
      | Feature specifications | 70%    | 70%       |
    And it should create unified product profiles
    And it should maintain source attribution for each match

  Scenario: Source Priority-Based Deduplication
    Given I have identical content from multiple sources
    When the system performs deduplication
    Then it should apply source priority hierarchy:
      | Priority | Source Type           | Selection Rule        |
      | 1        | Official brand media  | Always preferred      |
      | 2        | Authorized distributors| High quality preferred|
      | 3        | Major competitors     | Best quality selected |
      | 4        | Other sources         | Last resort only      |
    And it should preserve highest quality version per priority level
    And it should maintain source metadata for all versions

  Scenario: Image Similarity Detection
    Given I have product images from different sources
    When the system analyzes image similarity
    Then it should use perceptual image hashing (pHash)
    And it should detect near-duplicate images with variations:
      | Variation Type     | Detection Method       |
      | Different crops    | Feature point matching |
      | Color adjustments  | Histogram comparison   |
      | Watermark overlay  | Template matching      |
      | Resolution changes | Scale-invariant hashing|
    And it should group similar images together
    And it should select best version from each group

  Scenario: Unified Product Catalog Creation
    Given I have processed and deduplicated all sources
    When the system creates unified product catalog
    Then it should generate master product records:
      ```json
      {
        "product_id": "vaporesso-xros-3",
        "brand": "Vaporesso",
        "name": "XROS 3 Pod Kit",
        "primary_source": "official",
        "media_assets": {
          "primary_images": [
            {"source": "official", "quality": 9.2, "path": "..."}
          ],
          "alternative_images": [
            {"source": "vapeuk.co.uk", "quality": 8.5, "path": "..."}
          ],
          "documentation": [
            {"source": "official", "type": "manual", "path": "..."}
          ]
        }
      }
      ```
    And it should maintain complete source lineage
    And it should support source preference overrides

  Scenario: Quality-Based Asset Selection
    Given I have multiple versions of the same asset
    When the system selects the best version
    Then it should consider multiple quality factors:
      | Quality Factor      | Weight | Assessment Method    |
      | Technical quality   | 40%    | Resolution, clarity  |
      | Source reliability  | 30%    | Official > competitor|
      | Content completeness| 20%    | Full product view    |
      | Usage suitability   | 10%    | Background, framing  |
    And it should document selection reasoning
    And it should maintain access to alternative versions

  Scenario: Content Gap Identification
    Given I have created unified product catalog
    When the system identifies content gaps
    Then it should detect missing content types:
      | Gap Type                | Impact Level |
      | No high-res images     | Critical     |
      | Missing lifestyle shots| Medium       |
      | No technical specs     | Medium       |
      | Incomplete variants    | Low          |
    And it should recommend acquisition priorities
    And it should suggest alternative sources for gaps

  Scenario: Master Asset Inventory Generation
    Given I have completed cross-source integration
    When the system generates final inventory
    Then it should provide comprehensive statistics:
      | Inventory Metric         | Example Value |
      | Total unique products    | 247          |
      | Products with official media| 198       |
      | Products with competitor media| 156     |
      | Average quality score    | 8.3/10       |
      | Coverage completeness    | 87%          |
    And it should identify high-priority improvement areas
    And it should generate export-ready asset mappings