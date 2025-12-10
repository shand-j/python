#!/usr/bin/env python3
"""
Test Autonomous Pipeline
=========================
Simple integration test for the autonomous tagging pipeline
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.autonomous_pipeline import AutonomousPipeline


def create_test_csv():
    """Create a small test CSV with sample products"""
    csv_content = """Handle,Title,Body (HTML),Vendor,Type,Tags,Published,Option1 Name,Option1 Value,Option2 Name,Option2 Value,Option3 Name,Option3 Value,Variant SKU,Variant Grams,Variant Inventory Tracker,Variant Inventory Policy,Variant Fulfillment Service,Variant Price,Variant Compare At Price,Variant Requires Shipping,Variant Taxable,Variant Barcode,Image Src,Image Position,Image Alt Text,Gift Card,SEO Title,SEO Description,Google Shopping / Google Product Category,Google Shopping / Gender,Google Shopping / Age Group,Google Shopping / MPN,Google Shopping / AdWords Grouping,Google Shopping / AdWords Labels,Google Shopping / Condition,Google Shopping / Custom Product,Google Shopping / Custom Label 0,Google Shopping / Custom Label 1,Google Shopping / Custom Label 2,Google Shopping / Custom Label 3,Google Shopping / Custom Label 4,Variant Image,Variant Weight Unit,Variant Tax Code,Cost per item,Status
test-cbd-1000mg,"CBD Gummies 1000mg Full Spectrum","Premium CBD gummies with 1000mg full spectrum CBD extract",TestVendor,CBD products,,TRUE,Title,Default Title,,,,,SKU001,100,,,manual,29.99,,TRUE,TRUE,,https://example.com/image.jpg,1,,FALSE,,,,,,,,,,,,,,,,,kg,,5.00,active
test-eliquid-50ml,"Strawberry Ice 50ml Shortfill 70/30","Delicious strawberry ice cream flavor in 50ml shortfill bottle, 70VG/30PG ratio, 0mg nicotine",TestVendor,E-Liquid,,TRUE,Title,Default Title,,,,,SKU002,100,,,manual,12.99,,TRUE,TRUE,,https://example.com/image2.jpg,1,,FALSE,,,,,,,,,,,,,,,,,kg,,3.00,active
test-disposable-20mg,"Blue Razz 600 Puff Disposable 20mg","Disposable vape device with blue raspberry flavor, 20mg nicotine salt, 600 puffs",TestVendor,Vaping/Smoking Products,,TRUE,Title,Default Title,,,,,SKU003,50,,,manual,6.99,,TRUE,TRUE,,https://example.com/image3.jpg,1,,FALSE,,,,,,,,,,,,,,,,,kg,,2.00,active
test-pod-system,"Compact Pod System Kit","Rechargeable pod system device with mouth-to-lung vaping style, includes USB-C charging",TestVendor,Vaping/Smoking Products,,TRUE,Title,Default Title,,,,,SKU004,150,,,manual,24.99,,TRUE,TRUE,,https://example.com/image4.jpg,1,,FALSE,,,,,,,,,,,,,,,,,kg,,8.00,active
test-cbd-oil-500mg,"CBD Oil Tincture 500mg Broad Spectrum","High-quality CBD oil tincture, 500mg broad spectrum CBD in MCT oil carrier",TestVendor,CBD products,,TRUE,Title,Default Title,,,,,SKU005,80,,,manual,19.99,,TRUE,TRUE,,https://example.com/image5.jpg,1,,FALSE,,,,,,,,,,,,,,,,,kg,,4.00,active
"""
    return csv_content


def test_autonomous_pipeline():
    """Test the autonomous pipeline with sample data"""
    print("="*80)
    print("Testing Autonomous Pipeline")
    print("="*80)
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create test CSV
        test_csv = temp_dir / "test_products.csv"
        test_csv.write_text(create_test_csv())
        print(f"✓ Created test CSV: {test_csv}")
        
        # Create output directory
        output_dir = temp_dir / "output"
        output_dir.mkdir(exist_ok=True)
        print(f"✓ Created output directory: {output_dir}")
        
        # Initialize pipeline
        print("\n" + "="*80)
        print("Initializing Pipeline")
        print("="*80)
        
        pipeline = AutonomousPipeline(verbose=True)
        pipeline.accuracy_target = 0.60  # Lower target for test
        pipeline.max_iterations = 2  # Fewer iterations for test
        
        # Initialize components (disable AI for speed)
        use_ai = False  # Set to True to test with AI
        pipeline.initialize(use_ai=use_ai)
        
        print("\n" + "="*80)
        print("Running Autonomous Pipeline")
        print("="*80)
        
        # Run pipeline
        exit_code = pipeline.run_autonomous(
            input_csv=test_csv,
            output_dir=output_dir,
            use_ai=use_ai,
            limit=None
        )
        
        # Check results
        print("\n" + "="*80)
        print("Verifying Results")
        print("="*80)
        
        # Check for output files
        csv_files = list(output_dir.glob("*.csv"))
        db_files = list(output_dir.glob("*.db"))
        
        assert len(csv_files) >= 2, f"Expected at least 2 CSV files, found {len(csv_files)}"
        print(f"✓ Found {len(csv_files)} output CSV files")
        
        assert len(db_files) >= 1, f"Expected at least 1 audit DB, found {len(db_files)}"
        print(f"✓ Found {len(db_files)} audit database(s)")
        
        # Check CSV content
        for csv_file in csv_files:
            lines = csv_file.read_text().strip().split('\n')
            assert len(lines) >= 2, f"CSV file {csv_file.name} has no data rows"
            print(f"✓ {csv_file.name}: {len(lines)-1} products")
        
        # Check exit code
        if exit_code == 0:
            print(f"\n✅ Pipeline succeeded with exit code {exit_code}")
        else:
            print(f"\n⚠️  Pipeline completed with exit code {exit_code} (target not met, but results available)")
        
        print("\n" + "="*80)
        print("Test Output Files:")
        print("="*80)
        for f in sorted(output_dir.iterdir()):
            size = f.stat().st_size
            print(f"  {f.name}: {size} bytes")
        
        print("\n✅ Autonomous Pipeline Test PASSED")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"\n✓ Cleaned up temporary directory")


if __name__ == '__main__':
    sys.exit(test_autonomous_pipeline())
