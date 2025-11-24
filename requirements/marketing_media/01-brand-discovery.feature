# Feature 1: Brand Discovery and Configuration
# Iteration 1 - Core brand management functionality

Feature: Brand Discovery and Configuration
  As a vape product data analyst
  I want to configure and validate brand information
  So that I can establish a foundation for media acquisition

  Background:
    Given the system has basic configuration capabilities
    And the system can validate web connectivity

  Scenario: Basic Brand List Input
    Given I have a brand list input file "brands.txt"
    And the file contains basic brand information:
      | Brand Name | Website        |
      | SMOK      | smoktech.com   |
      | Vaporesso | vaporesso.com  |
    When I load the brand configuration
    Then the system should validate each brand entry
    And the system should store the brand registry
    And the system should log validation results

  Scenario: Brand Website Validation
    Given I have a brand "SMOK" with website "smoktech.com"
    When the system validates the brand website
    Then it should check domain accessibility
    And it should verify SSL certificate validity
    And it should record response time metrics
    And it should store validation status

  Scenario: Priority-Based Brand Queuing
    Given I have multiple brands configured with different priorities:
      | Brand Name | Priority |
      | SMOK      | high     |
      | VOOPOO    | medium   |
      | Lost Vape | low      |
    When I queue brands for processing
    Then the system should order by priority (high, medium, low)
    And the system should prepare processing queue
    And the system should log queue status

  Scenario: Brand Registry Management
    Given I have processed brand validations
    When I manage the brand registry
    Then the system should support adding new brands
    And the system should support updating existing brands
    And the system should support removing inactive brands
    And the system should maintain registry history

  Scenario: Configuration Error Handling
    Given I have a brand list with invalid entries:
      | Brand Name | Website           | Issue        |
      | BadBrand  | invalid-url       | Invalid URL  |
      | TestBrand | nonexistent.com   | No response  |
    When the system processes the configuration
    Then it should log specific validation errors
    And it should skip invalid entries
    And it should continue processing valid entries
    And it should generate error summary report