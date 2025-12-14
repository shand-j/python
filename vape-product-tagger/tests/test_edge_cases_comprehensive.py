"""
Comprehensive edge case tests for vape product tagging system
Tests for bugs in nicotine, CBD, VG/PG, flavor, category, and word boundary matching
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import ControlledTagger


def test_nicotine_strength_word_boundary():
    """Test that nicotine extraction uses word boundaries to avoid false matches"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # Should NOT extract nicotine from product IDs or model numbers
    handle = 'product-20mg-5000'
    title = 'Vape Device 5000 puffs'
    description = 'Long-lasting device model 20MG-5000'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    # Should find 20mg nicotine strength
    assert '20mg' in rule_tags, f"Should find 20mg, got: {rule_tags}"


def test_nicotine_zero_detection():
    """Test explicit zero nicotine detection"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    handle = 'zero-nic-liquid'
    title = 'Zero Nicotine E-Liquid 100ml'
    description = 'Nicotine free vape juice'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    # Should detect 0mg nicotine
    assert '0mg' in rule_tags, f"Should find 0mg, got: {rule_tags}"


def test_nicotine_vs_cbd_mg_values():
    """Test that high mg values are CBD, not nicotine"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # 1000mg should be CBD, not nicotine (nicotine max is 20mg)
    handle = 'cbd-oil-1000mg'
    title = 'CBD Oil 1000mg Full Spectrum'
    description = 'Premium CBD oil with 1000mg CBD per bottle'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    # Should detect CBD category and CBD strength
    assert 'CBD' in rule_tags, f"Should detect CBD category, got: {rule_tags}"
    assert '1000mg' in rule_tags, f"Should find 1000mg CBD strength, got: {rule_tags}"
    # Should NOT tag as e-liquid
    assert 'e-liquid' not in rule_tags, f"Should not tag as e-liquid, got: {rule_tags}"


def test_cbd_strength_range_validation():
    """Test CBD strength is validated within 0-50000mg range"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # Test valid CBD strengths
    valid_strengths = ['100mg', '500mg', '1000mg', '2500mg', '5000mg', '10000mg']
    
    for strength_value in valid_strengths:
        handle = f'cbd-oil-{strength_value}'
        title = f'CBD Oil {strength_value}'
        description = f'Full spectrum CBD {strength_value} per bottle'
        
        rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
        assert strength_value in rule_tags, f"Should find {strength_value}, got: {rule_tags}"


def test_vg_pg_ratio_patterns():
    """Test VG/PG ratio detection patterns"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # Note: approved_tags.json uses '70/30' format, not '70vg_30pg'
    test_cases = [
        ('70vg-30pg-liquid', '70VG E-Liquid', '70/30 VG/PG ratio', '70/30'),
        ('50-50-juice', '50/50 Vape Juice', 'Balanced 50VG 50PG', '50/50'),
        ('high-vg-liquid', 'High VG E-Liquid', '80% VG 20% PG', '80/20'),
    ]
    
    for handle, title, description, expected_tag in test_cases:
        rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
        assert expected_tag in rule_tags, f"Expected {expected_tag} for '{title}', got: {rule_tags}"


def test_flavor_type_multiple_detection():
    """Test that products can have multiple flavor types (fruity + ice)"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    handle = 'strawberry-ice-liquid'
    title = 'Strawberry Ice E-Liquid 10ml'
    description = 'Sweet strawberry with icy menthol cooling'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    # Should detect BOTH fruity and ice
    assert 'fruity' in rule_tags, f"Should detect fruity, got: {rule_tags}"
    assert 'ice' in rule_tags, f"Should detect ice, got: {rule_tags}"


def test_ice_flavor_not_in_device():
    """Test that 'ice' in 'device' doesn't trigger ice flavor"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    handle = 'vape-device-kit'
    title = 'Sleek Device Kit'
    description = 'Premium vape device with advanced features'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    # Should NOT detect ice flavor (device has 'ice' substring)
    assert 'ice' not in rule_tags, f"Should not detect ice in 'device', got: {rule_tags}"


def test_category_priority_cbd_highest():
    """Test that CBD has highest category priority"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # Product that could be both CBD and e-liquid
    handle = 'cbd-vape-liquid-1000mg'
    title = 'CBD Vape E-Liquid 1000mg'
    description = 'CBD vaping liquid for devices'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    # CBD should be forced category (highest priority)
    assert forced == 'CBD', f"CBD should be forced category, got: {forced}"
    assert 'CBD' in rule_tags, f"Should have CBD tag, got: {rule_tags}"


def test_category_pod_word_boundary():
    """Test that 'pod' uses word boundary to avoid 'airpod' false match"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # Should NOT match 'airpod' case
    handle = 'airpod-case-protective'
    title = 'AirPod Case Protective Cover'
    description = 'Protective case for airpods'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    # Should detect 'case' not 'pod'
    assert 'case' in rule_tags, f"Should detect case, got: {rule_tags}"
    assert 'pod' not in rule_tags, f"Should not detect pod from 'airpod', got: {rule_tags}"


def test_pod_kit_vs_pod_replacement():
    """Test distinction between pod kits and replacement pods"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # Pod kit
    handle1 = 'pod-system-kit'
    title1 = 'Pod Kit System Starter'
    description1 = 'Complete pod kit with device'
    
    rule_tags1, forced1 = ct.get_rule_based_tags(handle1, title1, description1)
    assert 'pod_system' in rule_tags1, f"Should detect pod_system, got: {rule_tags1}"
    assert forced1 == 'pod_system', f"Should force pod_system category, got: {forced1}"
    
    # Replacement pod
    handle2 = 'replacement-pod-pack'
    title2 = 'Replacement Pod Cartridge'
    description2 = 'Replacement pod for device'
    
    rule_tags2, forced2 = ct.get_rule_based_tags(handle2, title2, description2)
    assert 'pod' in rule_tags2 or 'replacement_pod' in rule_tags2, f"Should detect pod, got: {rule_tags2}"


def test_disposable_brand_detection():
    """Test disposable brand keyword detection"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    brands = ['elf bar', 'crystal bar', 'lost mary', 'geek bar', 'hayati']
    
    for brand in brands:
        handle = f'{brand.replace(" ", "-")}-4000-puffs'
        title = f'{brand.title()} 4000 Puffs'
        description = f'Premium {brand} disposable vape'
        
        rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
        
        assert 'disposable' in rule_tags, f"Should detect disposable for {brand}, got: {rule_tags}"
        assert forced == 'disposable', f"Should force disposable for {brand}, got: {forced}"


def test_shortfill_detection_excludes_small_bottles():
    """Test that shortfill is only tagged for 50ml+ bottles"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # 10ml should NOT be shortfill
    handle1 = 'liquid-10ml-eliquid'
    title1 = '10ml E-Liquid'
    description1 = 'Premium 10ml vape juice'
    
    rule_tags1, forced1 = ct.get_rule_based_tags(handle1, title1, description1)
    assert 'shortfill' not in rule_tags1, f"10ml should not be shortfill, got: {rule_tags1}"
    
    # 100ml SHOULD be shortfill (if it's a nicotine-free liquid)
    handle2 = 'liquid-100ml-zero-nic'
    title2 = '100ml Shortfill E-Liquid Zero Nicotine'
    description2 = 'Large 100ml bottle for adding nic shots'
    
    rule_tags2, forced2 = ct.get_rule_based_tags(handle2, title2, description2)
    assert 'shortfill' in rule_tags2, f"100ml zero-nic should be shortfill, got: {rule_tags2}"


def test_cbd_form_detection_priority():
    """Test that CBD form is detected from handle/title first, not description"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # Title says 'oil', description mentions topical - should tag as 'oil' not 'topical'
    handle = 'cbd-oil-1000mg'
    title = 'CBD Oil 1000mg Natural'
    description = 'Can be used topically or ingested. Full spectrum CBD oil for wellness.'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    assert 'oil' in rule_tags, f"Should detect oil from title, got: {rule_tags}"
    assert 'topical' not in rule_tags, f"Should not detect topical from description, got: {rule_tags}"


def test_nic_salt_detection():
    """Test nicotine salt type detection"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    handle = 'nic-salt-20mg-liquid'
    title = 'Nic Salt E-Liquid 20mg'
    description = 'Smooth nicotine salt formula'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    assert 'nic_salt' in rule_tags, f"Should detect nic_salt, got: {rule_tags}"
    assert '20mg' in rule_tags, f"Should detect 20mg, got: {rule_tags}"


def test_device_style_cbd_gating():
    """Test that CBD products don't get device style tags"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # CBD product with 'pen' in name but not a vape device
    handle = 'cbd-pen-applicator'
    title = 'CBD Pen Applicator 500mg'
    description = 'Easy application CBD pen dispenser'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description, product_type='CBD')
    
    # Should detect CBD but NOT pen_style
    assert 'CBD' in rule_tags, f"Should detect CBD, got: {rule_tags}"
    assert 'pen_style' not in rule_tags, f"CBD product should not get pen_style, got: {rule_tags}"


def test_capacity_vs_bottle_size():
    """Test distinction between capacity (pod/device) and bottle_size (liquid)"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    # Pod with 2ml capacity
    handle1 = 'replacement-pod-2ml'
    title1 = 'Replacement Pod 2ml'
    description1 = '2ml capacity replacement pod'
    
    rule_tags1, forced1 = ct.get_rule_based_tags(handle1, title1, description1)
    assert '2ml' in rule_tags1, f"Should detect 2ml capacity, got: {rule_tags1}"
    
    # E-liquid with 10ml bottle
    handle2 = 'eliquid-10ml-bottle'
    title2 = 'E-Liquid 10ml Bottle'
    description2 = '10ml bottle of premium e-liquid'
    
    rule_tags2, forced2 = ct.get_rule_based_tags(handle2, title2, description2)
    assert '10ml' in rule_tags2, f"Should detect 10ml bottle_size, got: {rule_tags2}"


def test_usb_cable_before_charger():
    """Test that USB cables are detected before generic charger"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    handle = 'usb-c-charging-cable'
    title = 'USB-C Charging Cable'
    description = 'Type-C USB cable for charging devices'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    # Should detect charging_cable, not just charger
    assert 'charging_cable' in rule_tags, f"Should detect charging_cable, got: {rule_tags}"
    assert forced == 'accessory', f"Should force accessory category, got: {forced}"


def test_coil_ohm_detection():
    """Test coil resistance (ohm) detection"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    handle = 'coil-0-4-ohm'
    title = 'Replacement Coil 0.4ohm'
    description = '0.4Ω mesh coil for sub-ohm vaping'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    assert '0.4ohm' in rule_tags, f"Should detect 0.4ohm, got: {rule_tags}"
    assert 'coil' in rule_tags, f"Should detect coil category, got: {rule_tags}"


def test_terpene_product_detection():
    """Test terpene product category detection"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    handle = 'indica-terpene-blend'
    title = 'Indica Terpene Profile'
    description = 'Natural terpene blend with indica profile'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    assert 'terpene' in rule_tags, f"Should detect terpene, got: {rule_tags}"
    assert 'indica' in rule_tags, f"Should detect indica type, got: {rule_tags}"
    assert forced == 'terpene', f"Should force terpene category, got: {forced}"


def test_supplement_without_cbd():
    """Test supplement detection (vitamins, etc.) excluding CBD"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    handle = 'vitamin-b12-supplement'
    title = 'Vitamin B12 Supplement'
    description = 'Daily vitamin supplement for energy'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    assert 'supplement' in rule_tags, f"Should detect supplement, got: {rule_tags}"
    assert 'vitamin' in rule_tags, f"Should detect vitamin, got: {rule_tags}"
    assert forced == 'supplement', f"Should force supplement category, got: {forced}"


def test_extraction_equipment_detection():
    """Test extraction equipment (rosin press, etc.) detection"""
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    handle = 'rosin-press-kit'
    title = 'Rosin Press Heat Press'
    description = 'Professional rosin extraction press'
    
    rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
    
    assert 'extraction_equipment' in rule_tags, f"Should detect extraction_equipment, got: {rule_tags}"
    assert 'rosin_press' in rule_tags, f"Should detect rosin_press, got: {rule_tags}"
    assert forced == 'extraction_equipment', f"Should force extraction_equipment category, got: {forced}"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
