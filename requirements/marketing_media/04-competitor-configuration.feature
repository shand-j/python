# Feature 4: Competitor Website Configuration
# Iteration 4 - Setting up competitor website scraping foundation

Feature: Competitor Website Configuration
  As a vape product data analyst
  I want to configure competitor websites for product discovery
  So that I can acquire additional product media from retail sources

  Background:
    Given the system has ethical scraping capabilities
    And the system respects robots.txt and rate limiting
    And the system maintains legal compliance

  Scenario: Competitor Website Registry
    Given I want to configure competitor websites
    When I set up the competitor registry
    Then the system should support major vape retailers:
      | Website Name         | Base URL                        | Priority |
      | Vape UK             | https://vapeuk.co.uk            | high     |
      | Vape Superstore     | https://www.vapesuperstore.co.uk| high     |
      | Vapourism           | https://www.vapourism.co.uk     | high     |
      | E-Cigarette Direct  | https://www.ecigarettedirect.co.uk| medium |
    And each site should have configurable parameters
    And the system should validate site accessibility

  Scenario: Scraping Parameter Configuration
    Given I am configuring a competitor website "vapeuk.co.uk"
    When I set scraping parameters
    Then the system should allow configuration of:
      | Parameter           | Default Value | Purpose                    |
      | request_delay       | 2 seconds     | Respectful crawling        |
      | max_pages_session   | 100 pages     | Limit scraping scope       |
      | concurrent_requests | 1             | Avoid overwhelming server  |
      | timeout_seconds     | 30            | Request timeout limit      |
    And the system should validate parameter ranges
    And the system should store configuration per site

  Scenario: Site Structure Analysis
    Given I am analyzing competitor website "https://vapeuk.co.uk"
    When the system performs initial site analysis
    Then it should identify main category pages:
      | Category Type       | URL Pattern     |
      | Vape Kits          | /vape-kits      |
      | Disposable Vapes   | /disposable-vapes|
      | E-Liquids          | /e-liquids      |
    And it should detect pagination patterns
    And it should identify product page URL structures
    And it should analyze site navigation hierarchy

  Scenario: Robots.txt Compliance Check
    Given I am configuring competitor website scraping
    When the system checks robots.txt compliance
    Then it should fetch and parse robots.txt for each site
    And it should identify allowed and disallowed paths
    And it should respect crawl-delay directives
    And it should log compliance status per site
    And it should adjust scraping behavior accordingly

  Scenario: User Agent and Session Management
    Given I need to configure respectful scraping practices
    When I set up user agent rotation
    Then the system should use realistic browser user agents
    And it should rotate user agents between requests
    And it should maintain consistent sessions per site
    And it should avoid detection patterns
    And it should log user agent usage

  Scenario: Site Health Monitoring
    Given I have configured multiple competitor sites
    When the system monitors site health
    Then it should check site response times regularly
    And it should detect if sites are blocking requests
    And it should adjust request frequency based on response
    And it should implement exponential backoff for failures
    And it should alert on persistent site issues