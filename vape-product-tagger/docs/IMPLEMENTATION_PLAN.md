# Vape Product Tagger - Refactor Implementation Plan

## Status: IN PROGRESS
**Date**: 7 December 2025

---

## ✅ COMPLETED

### 1. Taxonomy Refactor (`taxonomy.py`)
- ✅ Removed sub-category flavor tags (Berry, Citrus, etc.)
- ✅ Aligned with `approved_tags.json` as single source of truth
- ✅ Added secondary flavor keyword mappings for opportunistic tagging
- ✅ Added VG/PG ratio keywords
- ✅ Added CBD form/type keywords
- ✅ Removed deprecated COMPLIANCE_TAGS
- ✅ Updated class methods to return strength tags directly (e.g., "3mg", "1000mg")

### 2. Product Tagger - Core Helpers (`product_tagger.py`)
- ✅ Updated `_extract_nicotine_value()` to validate max 20mg and handle CBD category
- ✅ Added `_extract_cbd_value()` for CBD strength extraction (0-50000mg)
- ✅ Added `_extract_vg_ratio()` to parse VG/PG ratios (70/30, 70VG/30PG, etc.)
- ✅ Added `_extract_secondary_flavors()` for opportunistic flavor keyword capture
- ✅ Added `tag_category()` for primary category detection

---

## 🚧 IN PROGRESS

### 3. Product Tagger - Refactor Tagging Methods

#### Actions Required:
```python
# REMOVE these old methods:
- tag_device_type()  # Uses old DEVICE_TYPES taxonomy
- tag_device_form()  # Uses old DEVICE_FORMS taxonomy  
- tag_flavors()      # Uses old FLAVOR_TAXONOMY with sub-categories
- tag_nicotine()     # Uses old NICOTINE_STRENGTH taxonomy
- tag_compliance()   # DEPRECATED - remove entirely

# REPLACE with NEW methods:

def tag_category(product_data: Dict) -> str:
    """Returns primary category: e-liquid, CBD, disposable, etc."""
    # ✅ DONE

def tag_device_style(product_data: Dict, category: str) -> List[str]:
    """Returns device_style tags (pen_style, compact, etc.)
    Only applies to: device, pod_system"""
    # Uses DEVICE_STYLE_KEYWORDS
    # Validates applies_to rule
    
def tag_capacity(product_data: Dict, category: str) -> str:
    """Returns capacity tag (2ml, 5ml, etc.)
    Only applies to: tank, pod"""
    # Uses CAPACITY_KEYWORDS
    # Validates applies_to rule
    
def tag_bottle_size(product_data: Dict, category: str) -> str:
    """Returns bottle_size tag (50ml, shortfill, etc.)
    Only applies to: e-liquid"""
    # Uses BOTTLE_SIZE_KEYWORDS
    # Validates applies_to rule

def tag_flavors(product_data: Dict, category: str) -> Dict:
    """Returns {
        'primary': ['fruity', 'ice'],  # approved flavour_type tags
        'secondary': ['strawberry', 'banana', 'menthol']  # opportunistic keywords
    }
    Only applies to: e-liquid, disposable, nicotine_pouches, pod"""
    # Uses FLAVOR_KEYWORDS
    # Validates applies_to rule
    # Calls _extract_secondary_flavors()

def tag_nicotine_strength(product_data: Dict, category: str) -> str:
    """Returns nicotine strength tag (0mg, 3mg, 12mg, etc.)
    Max 20mg. Returns empty string for CBD products.
    Only applies to: e-liquid, disposable, device, pod_system, nicotine_pouches"""
    # Calls _extract_nicotine_value()
    # Calls taxonomy.get_nicotine_strength_tag()
    # Validates applies_to rule

def tag_nicotine_type(product_data: Dict, category: str) -> List[str]:
    """Returns nicotine type tags (nic_salt, freebase_nicotine, etc.)
    Only applies to: e-liquid, disposable, device, pod_system, nicotine_pouches"""
    # Uses NICOTINE_TYPE_KEYWORDS
    # Validates applies_to rule

def tag_vg_ratio(product_data: Dict, category: str) -> str:
    """Returns VG/PG ratio tag (70/30, 50/50, etc.)
    Only applies to: e-liquid"""
    # Calls _extract_vg_ratio()
    # Validates applies_to rule

def tag_cbd_strength(product_data: Dict, category: str) -> str:
    """Returns CBD strength tag (1000mg, 5000mg, etc.)
    Max 50000mg. Only applies to: CBD"""
    # Calls _extract_cbd_value()
    # Calls taxonomy.get_cbd_strength_tag()
    # Validates applies_to rule

def tag_cbd_form(product_data: Dict, category: str) -> str:
    """Returns CBD form tag (gummy, oil, tincture, etc.)
    Only applies to: CBD"""
    # Uses CBD_FORM_KEYWORDS
    # Validates applies_to rule

def tag_cbd_type(product_data: Dict, category: str) -> str:
    """Returns CBD type tag (full_spectrum, broad_spectrum, etc.)
    Only applies to: CBD"""
    # Uses CBD_TYPE_KEYWORDS
    # Validates applies_to rule

def tag_power_supply(product_data: Dict, category: str) -> List[str]:
    """Returns power supply tags (rechargeable, removable_battery)
    Only applies to: device, pod_system"""
    # Uses POWER_SUPPLY_KEYWORDS
    # Validates applies_to rule

def tag_pod_type(product_data: Dict, category: str) -> str:
    """Returns pod type tag (prefilled_pod, replacement_pod)
    Only applies to: pod"""
    # Uses POD_TYPE_KEYWORDS
    # Validates applies_to rule

def tag_vaping_style(product_data: Dict, category: str) -> List[str]:
    """Returns vaping style tags (mouth-to-lung, direct-to-lung, etc.)
    Only applies to: device, pod_system, e-liquid"""
    # Uses VAPING_STYLE_KEYWORDS
    # Validates applies_to rule
```

#### Main Tag Orchestration Method:
```python
def tag_product(product_data: Dict, use_ai: bool = True) -> Dict:
    """
    UPDATED FLOW:
    1. Detect category FIRST (required for applies_to validation)
    2. Run ALL applicable rule-based tagging methods
    3. If use_ai=True:
       a) Primary AI (mistral:latest) → tags + confidence
       b) If confidence < threshold → Secondary AI (gpt-oss:latest)
       c) If both < threshold → Third Opinion AI (llama3.1:latest)
       d) If third opinion returns tags → USE THEM + flag for manual review
    4. Validate all tags against approved_tags.json
    5. CBD Validation: Ensure all 3 dimensions present (strength, form, type)
    6. Return enhanced product with:
       - final_tags (deduplicated)
       - needs_manual_review (bool)
       - confidence_scores (dict)
       - tag_breakdown (rule vs AI)
       - failure_reasons (list) if untagged
    """
```

---

## ⏳ TODO

### 4. Multi-Model Cascade System (`ollama_processor.py`)

Create NEW file: `/modules/ai_cascade.py`

```python
class AICascade:
    """Multi-model AI tagging with fallback chain"""
    
    def __init__(self, config, logger):
        self.primary_model = "mistral:latest"
        self.secondary_model = "gpt-oss:latest"
        self.tertiary_model = "llama3.1:latest"
        self.confidence_threshold = config.ai_confidence_threshold
    
    def generate_tags_with_cascade(self, product_data, category, rule_tags):
        """
        Returns: {
            'tags': List[str],
            'confidence': float,
            'model_used': str,
            'needs_manual_review': bool,
            'reasoning': str
        }
        """
        # Try primary
        # If fails → try secondary
        # If fails → try tertiary
        # Track which model succeeded
```

### 5. Audit Database Schema Updates

Add columns to `products` table:
```sql
ALTER TABLE products ADD COLUMN needs_manual_review BOOLEAN DEFAULT FALSE;
ALTER TABLE products ADD COLUMN primary_model_confidence REAL;
ALTER TABLE products ADD COLUMN secondary_model_confidence REAL;
ALTER TABLE products ADD COLUMN tertiary_model_confidence REAL;
ALTER TABLE products ADD COLUMN model_used TEXT;
ALTER TABLE products ADD COLUMN failure_reasons TEXT;  -- JSON array
ALTER TABLE products ADD COLUMN rule_based_tags TEXT;  -- JSON array
ALTER TABLE products ADD COLUMN ai_suggested_tags TEXT;  -- JSON array
ALTER TABLE products ADD COLUMN secondary_flavor_tags TEXT;  -- JSON array
```

### 6. Third Opinion Prompt

Create NEW file: `/modules/third_opinion.py`

```python
def generate_third_opinion_prompt(product_data, suggested_ai_tags, suggested_rule_tags, approved_tags_schema):
    """
    Prompt: You are a vaping product expert. Previous AI models suggested these tags
    but they failed validation. Review the product data and suggested tags.
    
    Product: {title} {description}
    Category: {detected_category}
    
    Suggested AI Tags (failed): {suggested_ai_tags}
    Suggested Rule Tags (failed): {suggested_rule_tags}
    
    Validation Failure Reasons:
    - {reason_1}
    - {reason_2}
    
    Approved Tags Schema: {approved_tags_schema}
    
    Return ONLY tags from the approved schema that accurately describe this product.
    Be conservative - only return tags you are highly confident about.
    
    Response Format: JSON array of tags with confidence score.
    """
```

### 7. Shopify Exporter Updates

Add columns to CSV export:
- `needs_manual_review` (TRUE/FALSE)
- `ai_confidence` (0.0-1.0)
- `model_used` (mistral/gpt-oss/llama3.1)
- `failure_reasons` (comma-separated if untagged)

Update file naming:
- `controlled_tagged_products.csv` → include `needs_manual_review=FALSE` only
- `controlled_tagged_needs_review.csv` → NEW file for `needs_manual_review=TRUE`
- `controlled_untagged_products.csv` → products with NO final tags

### 8. Config Updates (`config.env.example`)

```env
# Multi-Model Cascade Configuration
PRIMARY_AI_MODEL=mistral:latest
SECONDARY_AI_MODEL=gpt-oss:latest
TERTIARY_AI_MODEL=llama3.1:latest

AI_CONFIDENCE_THRESHOLD=0.7

# Enable third opinion for failed validations
ENABLE_THIRD_OPINION=true

# Compliance tagging (DEPRECATED - set to false)
ENABLE_COMPLIANCE_TAGS=false
```

### 9. Validation Engine

Create NEW file: `/modules/tag_validator.py`

```python
class TagValidator:
    """Validates tags against approved_tags.json rules"""
    
    def __init__(self, approved_tags_path):
        self.approved_tags = self._load_approved_tags()
        self.rules = self.approved_tags['rules']
    
    def validate_tag(self, tag, category):
        """Returns (is_valid: bool, reason: str)"""
        # Check if tag exists in approved list
        # Check applies_to rules
        # Check range validations
    
    def validate_cbd_product(self, tags, category):
        """Ensures CBD products have all 3 dimensions"""
        if category != "CBD":
            return True, ""
        
        has_strength = any(tag.endswith('mg') for tag in tags)
        has_form = any(tag in self.approved_tags['cbd_form']['tags'] for tag in tags)
        has_type = any(tag in self.approved_tags['cbd_type']['tags'] for tag in tags)
        
        if not (has_strength and has_form and has_type):
            return False, "CBD product missing required dimensions (strength/form/type)"
        
        return True, ""
```

### 10. Integration Testing

Create test file: `/tests/test_refactored_tagger.py`

Test cases:
1. ✅ E-liquid with secondary flavors: "Strawberry Banana Ice 50ml 0mg 70/30"
2. ✅ CBD gummy with all 3 dimensions: "1000mg Full Spectrum CBD Gummies"
3. ✅ Disposable with illegal nicotine (25mg) → should reject
4. ✅ Product with no clear category → untagged with reason
5. ✅ Low confidence tagging → triggers secondary/tertiary models
6. ✅ Third opinion success → flagged for manual review
7. ✅ VG/PG ratio detection: "70VG/30PG" vs "70/30"

---

## 📊 Summary of Changes

| Component | Status | Files Modified |
|-----------|--------|----------------|
| Taxonomy | ✅ Complete | `modules/taxonomy.py` |
| Helper Methods | ✅ Complete | `modules/product_tagger.py` (partial) |
| Tagging Methods | 🚧 In Progress | `modules/product_tagger.py` |
| AI Cascade | ⏳ TODO | `modules/ai_cascade.py` (new) |
| Third Opinion | ⏳ TODO | `modules/third_opinion.py` (new) |
| Validator | ⏳ TODO | `modules/tag_validator.py` (new) |
| Audit DB | ⏳ TODO | Schema updates |
| Shopify Export | ⏳ TODO | `modules/shopify_handler.py` |
| Config | ⏳ TODO | `config.env.example` |
| Tests | ⏳ TODO | `tests/test_refactored_tagger.py` (new) |

---

## 🎯 Next Immediate Actions

1. **Complete product_tagger.py refactor** (replace old methods with new)
2. **Create ai_cascade.py** for multi-model system
3. **Create tag_validator.py** for validation logic
4. **Update audit DB schema** with new columns
5. **Create third_opinion.py** for failed validation recovery
6. **Update config.env.example** with new settings
7. **Test end-to-end** with sample products

---

## 🔧 Development Commands

```bash
# After refactor is complete, test with:
cd vape-product-tagger
source venv/bin/activate

# Test rule-based only
python main.py --input sample_data/test_products.csv --no-ai --limit 10

# Test with AI cascade
python main.py --input sample_data/test_products.csv --audit-db output/test_audit.db --limit 10

# Review audit results
python tag_auditor.py --audit-db output/test_audit.db --summary

# Export training data
python tag_auditor.py --audit-db output/test_audit.db --output training_data.csv
```

---

**End of Implementation Plan**
