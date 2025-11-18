#!/usr/bin/env python3
"""
Test Script - Competitor Site Configuration
Tests competitor site management functionality
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import (
    CompetitorSite, CompetitorSiteManager,
    ScrapingParameters, SitePriority, SiteStatus,
    RobotsTxtParser, SiteHealthMonitor, UserAgentRotator,
    setup_logger
)


def test_scraping_parameters():
    """Test 1: Scraping Parameters Validation"""
    print("\n" + "="*60)
    print("Test 1: Scraping Parameters Validation")
    print("="*60)
    
    # Valid parameters
    params = ScrapingParameters(
        request_delay=2.0,
        max_pages_per_session=100,
        concurrent_requests=1,
        timeout_seconds=30
    )
    
    tests = [
        ("Parameters created", params is not None),
        ("Default delay", params.request_delay == 2.0),
        ("Default max pages", params.max_pages_per_session == 100),
        ("Default concurrent", params.concurrent_requests == 1),
        ("Default timeout", params.timeout_seconds == 30),
    ]
    
    # Valid parameters should pass
    errors = params.validate()
    tests.append(("Valid parameters pass", len(errors) == 0))
    
    # Invalid parameters
    invalid_params = ScrapingParameters(
        request_delay=0.1,  # Too low
        max_pages_per_session=20000,  # Too high
        concurrent_requests=10,  # Too high
        timeout_seconds=500  # Too high
    )
    
    errors = invalid_params.validate()
    tests.append(("Invalid parameters detected", len(errors) > 0))
    tests.append(("Multiple errors", len(errors) == 4))
    
    return run_tests(tests)


def test_competitor_site_model():
    """Test 2: Competitor Site Data Model"""
    print("\n" + "="*60)
    print("Test 2: Competitor Site Data Model")
    print("="*60)
    
    site = CompetitorSite(
        name="Vape UK",
        base_url="https://vapeuk.co.uk",
        priority=SitePriority.HIGH.value
    )
    
    tests = [
        ("Site created", site is not None),
        ("Name set", site.name == "Vape UK"),
        ("URL set", site.base_url == "https://vapeuk.co.uk"),
        ("Priority set", site.priority == "high"),
        ("Default status", site.status == SiteStatus.PENDING.value),
        ("Has scraping params", site.scraping_params is not None),
        ("Has site structure", site.site_structure is not None),
        ("Has robots info", site.robots_txt_info is not None),
        ("Has health info", site.site_health is not None),
    ]
    
    # Test serialization
    site_dict = site.to_dict()
    tests.append(("to_dict works", isinstance(site_dict, dict)))
    tests.append(("Dict has name", site_dict.get('name') == site.name))
    
    # Test deserialization
    site_copy = CompetitorSite.from_dict(site_dict)
    tests.append(("from_dict works", site_copy.name == site.name))
    tests.append(("URL preserved", site_copy.base_url == site.base_url))
    
    return run_tests(tests)


def test_site_manager():
    """Test 3: Competitor Site Manager"""
    print("\n" + "="*60)
    print("Test 3: Competitor Site Manager")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        registry_file = Path(temp_dir) / "sites_registry.json"
        logger = setup_logger('test', None, 'ERROR')
        manager = CompetitorSiteManager(registry_file, logger)
        
        tests = [
            ("Manager created", manager is not None),
            ("Empty initially", len(manager.get_all_sites()) == 0),
        ]
        
        # Add site
        site = CompetitorSite(
            name="Vape UK",
            base_url="https://vapeuk.co.uk",
            priority=SitePriority.HIGH.value
        )
        
        added = manager.add_site(site)
        tests.append(("Site added", added == True))
        tests.append(("Has 1 site", len(manager.get_all_sites()) == 1))
        
        # Get site
        retrieved = manager.get_site("Vape UK")
        tests.append(("Site retrieved", retrieved is not None))
        tests.append(("Correct site", retrieved.name == "Vape UK"))
        
        # Update site
        updated = manager.update_site("Vape UK", status=SiteStatus.ACTIVE.value)
        tests.append(("Site updated", updated == True))
        
        site_after = manager.get_site("Vape UK")
        tests.append(("Status updated", site_after.status == SiteStatus.ACTIVE.value))
        
        # Remove site
        removed = manager.remove_site("Vape UK")
        tests.append(("Site removed", removed == True))
        tests.append(("Empty after remove", len(manager.get_all_sites()) == 0))
        
        return run_tests(tests)


def test_site_manager_persistence():
    """Test 4: Site Manager Persistence"""
    print("\n" + "="*60)
    print("Test 4: Site Manager Persistence")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        registry_file = Path(temp_dir) / "sites_registry.json"
        logger = setup_logger('test', None, 'ERROR')
        
        # Create and save
        manager1 = CompetitorSiteManager(registry_file, logger)
        site = CompetitorSite(
            name="Vape UK",
            base_url="https://vapeuk.co.uk"
        )
        manager1.add_site(site)
        
        tests = [
            ("Registry file created", registry_file.exists()),
        ]
        
        # Load in new manager
        manager2 = CompetitorSiteManager(registry_file, logger)
        tests.append(("Sites loaded", len(manager2.get_all_sites()) == 1))
        
        loaded_site = manager2.get_site("Vape UK")
        tests.append(("Site loaded correctly", loaded_site.name == "Vape UK"))
        tests.append(("URL preserved", loaded_site.base_url == "https://vapeuk.co.uk"))
        
        return run_tests(tests)


def test_site_manager_file_loading():
    """Test 5: Load Sites from File"""
    print("\n" + "="*60)
    print("Test 5: Load Sites from File")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = Path(temp_dir) / "sites.txt"
        test_file.write_text("""
# Test sites
Vape UK|https://vapeuk.co.uk|high
Vape Superstore|https://vapesuperstore.co.uk|medium

# Comment line
E-Cigarette Direct|https://ecigarettedirect.co.uk|low
""")
        
        registry_file = Path(temp_dir) / "sites_registry.json"
        logger = setup_logger('test', None, 'ERROR')
        manager = CompetitorSiteManager(registry_file, logger)
        
        # Load file
        count = manager.load_sites_from_file(test_file)
        
        tests = [
            ("Sites loaded", count == 3),
            ("Has 3 sites", len(manager.get_all_sites()) == 3),
        ]
        
        # Check sites
        uk_site = manager.get_site("Vape UK")
        tests.append(("Vape UK loaded", uk_site is not None))
        tests.append(("Correct priority", uk_site.priority == "high"))
        
        super_site = manager.get_site("Vape Superstore")
        tests.append(("Vape Superstore loaded", super_site is not None))
        
        return run_tests(tests)


def test_robots_txt_parser():
    """Test 6: Robots.txt Parser"""
    print("\n" + "="*60)
    print("Test 6: Robots.txt Parser")
    print("="*60)
    
    logger = setup_logger('test', None, 'ERROR')
    parser = RobotsTxtParser(logger)
    
    tests = [
        ("Parser created", parser is not None),
        ("No parsers initially", len(parser.parsers) == 0),
    ]
    
    # Test with mock
    with patch('modules.robots_txt_parser.requests.get') as mock_get:
        # Mock 404 response (no robots.txt)
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        success, robots_info = parser.fetch_and_parse("https://example.com")
        tests.append(("404 handled", success == True))
        tests.append(("Assumes allowed", robots_info['compliant'] == True))
        
        # Mock successful response
        mock_response.status_code = 200
        mock_response.text = """
User-agent: *
Disallow: /admin/
Allow: /public/
Crawl-delay: 1
"""
        mock_get.return_value = mock_response
        
        success, robots_info = parser.fetch_and_parse("https://example.com")
        tests.append(("Parse successful", success == True))
        tests.append(("Has disallowed paths", len(robots_info['disallowed_paths']) > 0))
        tests.append(("Has crawl delay", robots_info['crawl_delay'] == 1.0))
    
    return run_tests(tests)


def test_site_health_monitor():
    """Test 7: Site Health Monitor"""
    print("\n" + "="*60)
    print("Test 7: Site Health Monitor")
    print("="*60)
    
    logger = setup_logger('test', None, 'ERROR')
    monitor = SiteHealthMonitor(logger)
    
    tests = [
        ("Monitor created", monitor is not None),
        ("No metrics initially", len(monitor.site_metrics) == 0),
    ]
    
    # Test with mock
    with patch('modules.site_health_monitor.requests.head') as mock_head:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        health = monitor.check_site_health("Test Site", "https://example.com", timeout=10)
        
        tests.append(("Health check successful", health['is_healthy'] == True))
        tests.append(("Has response time", health['response_time_ms'] is not None))
        tests.append(("Status code set", health['status_code'] == 200))
        tests.append(("Not blocked", health['is_blocked'] == False))
        
        # Check site can be accessed
        tests.append(("Site accessible", monitor.can_access_site("Test Site") == True))
        
        # Test blocking
        mock_response.status_code = 403
        health = monitor.check_site_health("Test Site", "https://example.com")
        tests.append(("Blocking detected", health['is_blocked'] == True))
    
    return run_tests(tests)


def test_user_agent_rotator():
    """Test 8: User Agent Rotator"""
    print("\n" + "="*60)
    print("Test 8: User Agent Rotator")
    print("="*60)
    
    logger = setup_logger('test', None, 'ERROR')
    rotator = UserAgentRotator(logger)
    
    tests = [
        ("Rotator created", rotator is not None),
        ("Has user agents", len(rotator.USER_AGENTS) > 0),
    ]
    
    # Get user agent
    ua1 = rotator.get_user_agent()
    tests.append(("User agent returned", ua1 is not None))
    tests.append(("UA is string", isinstance(ua1, str)))
    tests.append(("UA not empty", len(ua1) > 0))
    
    # Get random
    ua2 = rotator.get_random_user_agent()
    tests.append(("Random UA returned", ua2 is not None))
    tests.append(("UA in pool", ua2 in rotator.USER_AGENTS))
    
    # Test modes
    rotator.set_rotation_mode(False)  # Sequential
    ua3 = rotator.get_user_agent()
    tests.append(("Sequential mode works", ua3 is not None))
    
    return run_tests(tests)


def test_priority_filtering():
    """Test 9: Site Filtering by Priority"""
    print("\n" + "="*60)
    print("Test 9: Site Filtering by Priority")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        registry_file = Path(temp_dir) / "sites_registry.json"
        logger = setup_logger('test', None, 'ERROR')
        manager = CompetitorSiteManager(registry_file, logger)
        
        # Add sites with different priorities
        for i, priority in enumerate(['high', 'medium', 'low'], 1):
            site = CompetitorSite(
                name=f"Site {i}",
                base_url=f"https://site{i}.com",
                priority=priority
            )
            manager.add_site(site)
        
        tests = [
            ("Has 3 sites", len(manager.get_all_sites()) == 3),
        ]
        
        # Filter by priority
        high_sites = manager.get_sites_by_priority('high')
        tests.append(("1 high priority", len(high_sites) == 1))
        tests.append(("High priority correct", high_sites[0].priority == 'high'))
        
        medium_sites = manager.get_sites_by_priority('medium')
        tests.append(("1 medium priority", len(medium_sites) == 1))
        
        low_sites = manager.get_sites_by_priority('low')
        tests.append(("1 low priority", len(low_sites) == 1))
        
        return run_tests(tests)


def test_status_filtering():
    """Test 10: Site Filtering by Status"""
    print("\n" + "="*60)
    print("Test 10: Site Filtering by Status")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        registry_file = Path(temp_dir) / "sites_registry.json"
        logger = setup_logger('test', None, 'ERROR')
        manager = CompetitorSiteManager(registry_file, logger)
        
        # Add sites
        site1 = CompetitorSite(name="Site 1", base_url="https://site1.com", status=SiteStatus.ACTIVE.value)
        site2 = CompetitorSite(name="Site 2", base_url="https://site2.com", status=SiteStatus.PENDING.value)
        manager.add_site(site1)
        manager.add_site(site2)
        
        tests = []
        
        # Filter by status
        active_sites = manager.get_active_sites()
        tests.append(("1 active site", len(active_sites) == 1))
        tests.append(("Active correct", active_sites[0].status == SiteStatus.ACTIVE.value))
        
        pending_sites = manager.get_sites_by_status(SiteStatus.PENDING.value)
        tests.append(("1 pending site", len(pending_sites) == 1))
        
        return run_tests(tests)


def run_tests(tests):
    """Run a list of tests and report results"""
    passed = 0
    failed = 0
    
    for test_name, result in tests:
        if result:
            print(f"  ✓ {test_name}")
            passed += 1
        else:
            print(f"  ✗ {test_name}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests"""
    print("="*60)
    print("Competitor Site Configuration Test Suite")
    print("="*60)
    
    all_passed = True
    
    try:
        all_passed &= test_scraping_parameters()
        all_passed &= test_competitor_site_model()
        all_passed &= test_site_manager()
        all_passed &= test_site_manager_persistence()
        all_passed &= test_site_manager_file_loading()
        all_passed &= test_robots_txt_parser()
        all_passed &= test_site_health_monitor()
        all_passed &= test_user_agent_rotator()
        all_passed &= test_priority_filtering()
        all_passed &= test_status_filtering()
        
        print("\n" + "="*60)
        if all_passed:
            print("✓ All tests passed!")
        else:
            print("✗ Some tests failed")
        print("="*60)
        
        return 0 if all_passed else 1
    
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
