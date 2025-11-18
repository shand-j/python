# Feature 2: Official Media Pack Discovery
# Iteration 2 - Official brand media pack detection and analysis

Feature: Official Media Pack Discovery
  As a vape product data analyst
  I want to discover official media packs from brand websites
  So that I can acquire authoritative product assets

  Background:
    Given the system has a validated brand registry
    And the system has web scraping capabilities
    And the system implements respectful crawling practices

  Scenario: Media Pack URL Pattern Discovery
    Given I am processing brand "Vaporesso" with website "vaporesso.com"
    When the system searches for media pack locations
    Then it should check standard media pack paths:
      | Path Pattern       | Expected Content    |
      | /media-pack       | Direct downloads    |
      | /press            | Press kits          |
      | /resources        | Marketing materials |
      | /downloads        | Product assets      |
    And it should identify downloadable file links
    And it should log discovered URLs

  Scenario: File Type Recognition
    Given I have discovered potential media pack URLs
    When the system analyzes the file types
    Then it should recognize media file extensions:
      | Extension | Content Type        |
      | .zip     | Compressed archive  |
      | .rar     | Compressed archive  |
      | .pdf     | Documentation       |
      | .jpg     | High-res images     |
      | .png     | High-res images     |
      | .svg     | Vector graphics     |
    And it should prioritize comprehensive archives (.zip, .rar)
    And it should validate file accessibility

  Scenario: Dynamic Content Detection
    Given I am scanning a brand website for media packs
    When the system encounters JavaScript-generated content
    Then it should wait for dynamic content loading
    And it should execute JavaScript to reveal hidden downloads
    And it should extract URLs from dynamically loaded elements
    And it should handle AJAX-based file listings

  Scenario: Media Pack Content Preview
    Given I have discovered a media pack URL "https://vaporesso.com/media/press-kit-2024.zip"
    When the system analyzes the media pack before download
    Then it should check file size using HEAD request
    And it should estimate download time
    And it should verify URL accessibility
    And it should check for access restrictions
    And it should log content metadata

  Scenario: Alternative Domain Discovery
    Given I have a primary brand domain "smoktech.com"
    When the system searches for alternative domains
    Then it should identify related domains like "smokstore.com"
    And it should verify domain authenticity
    And it should check for additional media sources
    And it should maintain domain relationships

  Scenario: Access Restriction Handling
    Given I encounter a media pack with access restrictions
    When the system attempts to access the content
    Then it should detect authentication requirements
    And it should log access restriction type
    And it should mark content as "restricted" in registry
    And it should continue with other available sources