# Feature 3: Media Pack Download and Extraction
# Iteration 3 - Downloading and extracting official brand media packs

Feature: Media Pack Download and Extraction
  As a vape product data analyst
  I want to download and extract media packs reliably
  So that I can access individual media assets

  Background:
    Given the system has discovered valid media pack URLs
    And the system has sufficient storage space
    And the system has download capabilities

  Scenario: Successful Media Pack Download
    Given I have a validated media pack URL "https://smoktech.com/downloads/smok-media-2024.zip"
    And the file size is 45MB
    When the system downloads the media pack
    Then it should create brand-specific directory:
      ```
      downloads/SMOK/media-packs/smok-media-2024.zip
      ```
    And it should show download progress
    And it should verify file integrity with checksums
    And it should log download completion time

  Scenario: Resumable Download Support
    Given I am downloading a large media pack "geekvape-assets-2024.zip"
    And the download is interrupted at 60% completion
    When the system resumes the download
    Then it should continue from the last successful byte
    And it should verify partial file integrity
    And it should complete the remaining download
    And it should validate final file integrity

  Scenario: Media Pack Extraction
    Given I have successfully downloaded "smok-media-2024.zip"
    When the system extracts the media pack
    Then it should create organized extraction directory:
      ```
      extracted/smok-media-2024/
      ├── product-images/
      ├── logos/
      ├── marketing-materials/
      └── documentation/
      ```
    And it should categorize files by type automatically
    And it should preserve original file structure
    And it should generate extraction manifest

  Scenario: File Organization and Naming
    Given I have extracted media pack contents
    When the system organizes the files
    Then it should apply standardized naming conventions:
      | Original Name           | Standardized Name        |
      | IMG_001.jpg            | smok-product-001.jpg     |
      | logo_variation_2.png   | smok-logo-variation-2.png|
      | spec_sheet.pdf         | smok-specifications.pdf  |
    And it should maintain file type categorization
    And it should preserve high-priority assets

  Scenario: Duplicate Detection During Extraction
    Given I am extracting a media pack with duplicate files
    When the system encounters duplicate content
    Then it should compare file signatures (checksums)
    And it should keep the highest quality version
    And it should log duplicate file information
    And it should avoid storage waste

  Scenario: Corrupted Archive Handling
    Given I have downloaded a corrupted media pack
    When the system attempts extraction
    Then it should detect archive corruption
    And it should attempt repair if possible
    And it should log corruption details
    And it should quarantine corrupted files
    And it should retry download if necessary

  Scenario: Metadata Generation
    Given I have successfully extracted a media pack
    When the system generates metadata
    Then it should create comprehensive metadata.json:
      ```json
      {
        "brand": "SMOK",
        "media_pack": "smok-media-2024.zip",
        "download_date": "2024-11-17T10:30:00Z",
        "extraction_date": "2024-11-17T10:32:00Z",
        "total_files": 156,
        "categories": {
          "product-images": 89,
          "logos": 12,
          "marketing-materials": 34,
          "documentation": 21
        }
      }
      ```
    And it should include file inventory
    And it should track processing timestamps