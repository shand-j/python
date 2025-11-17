"""
Vape Product Taxonomy Module
Defines comprehensive hierarchical taxonomy for vaping products
"""

class VapeTaxonomy:
    """Comprehensive vaping product taxonomy definitions"""
    
    # Device Type Taxonomy
    DEVICE_TYPES = {
        "Disposable": {
            "tags": ["Disposable", "Single Use", "Disposable Vape"],
            "keywords": ["disposable", "single use", "throw away", "one time"]
        },
        "Rechargeable": {
            "tags": ["Rechargeable", "Reusable", "Rechargeable Device"],
            "keywords": ["rechargeable", "reusable", "refillable"]
        },
        "Pod": {
            "tags": ["Pod System", "Pod", "Pod Device"],
            "keywords": ["pod", "pod system", "pod mod"]
        },
        "Mod": {
            "tags": ["Mod", "Vape Mod", "Advanced Device"],
            "keywords": ["mod", "vape mod", "box mod"]
        },
        "AIO": {
            "tags": ["AIO", "All-in-One", "All in One"],
            "keywords": ["aio", "all-in-one", "all in one"]
        }
    }
    
    # Device Form Taxonomy
    DEVICE_FORMS = {
        "Pen": {
            "tags": ["Pen Style", "Pen", "Stick Style"],
            "keywords": ["pen", "stick", "pen style"]
        },
        "Box Mod": {
            "tags": ["Box Mod", "Box", "Square Mod"],
            "keywords": ["box mod", "box", "square"]
        },
        "Stick": {
            "tags": ["Stick", "Stick Style", "Tube"],
            "keywords": ["stick", "tube", "cylindrical"]
        },
        "Compact": {
            "tags": ["Compact", "Small", "Portable", "Mini"],
            "keywords": ["compact", "small", "mini", "portable", "pocket"]
        }
    }
    
    # Flavor Taxonomy with Detailed Sub-Categories
    FLAVOR_TAXONOMY = {
        "Fruit": {
            "tags": ["Fruit", "Fruit Flavor", "Fruity"],
            "keywords": ["fruit", "fruity"],
            "sub_categories": {
                "Citrus": {
                    "tags": ["Citrus", "Citrus Fruit"],
                    "keywords": ["lemon", "lime", "orange", "grapefruit", "citrus", "tangerine"]
                },
                "Berry": {
                    "tags": ["Berry", "Berry Flavor"],
                    "keywords": ["strawberry", "raspberry", "blueberry", "blackberry", "berry", "cranberry"]
                },
                "Tropical": {
                    "tags": ["Tropical", "Tropical Fruit"],
                    "keywords": ["mango", "pineapple", "coconut", "papaya", "guava", "passion fruit", "tropical"]
                },
                "Stone Fruit": {
                    "tags": ["Stone Fruit", "Peach", "Plum"],
                    "keywords": ["peach", "plum", "apricot", "nectarine", "cherry"]
                }
            }
        },
        "Dessert": {
            "tags": ["Dessert", "Dessert Flavor", "Sweet"],
            "keywords": ["dessert", "sweet"],
            "sub_categories": {
                "Custard": {
                    "tags": ["Custard", "Creamy Custard"],
                    "keywords": ["custard", "vanilla custard", "egg custard"]
                },
                "Bakery": {
                    "tags": ["Bakery", "Baked Goods"],
                    "keywords": ["cookie", "cake", "pastry", "donut", "waffle", "bakery"]
                },
                "Cream": {
                    "tags": ["Cream", "Creamy"],
                    "keywords": ["cream", "creamy", "whipped cream", "ice cream"]
                },
                "Pudding": {
                    "tags": ["Pudding", "Pudding Flavor"],
                    "keywords": ["pudding", "flan", "creme brulee"]
                }
            }
        },
        "Menthol": {
            "tags": ["Menthol", "Cooling", "Cool"],
            "keywords": ["menthol", "cool", "cooling", "ice", "icy"],
            "sub_categories": {
                "Cool": {
                    "tags": ["Cool", "Cooling Effect", "Ice"],
                    "keywords": ["ice", "icy", "cool", "cold"]
                },
                "Mint": {
                    "tags": ["Mint", "Peppermint", "Spearmint"],
                    "keywords": ["mint", "peppermint", "spearmint"]
                },
                "Arctic": {
                    "tags": ["Arctic", "Extreme Cool", "Freeze"],
                    "keywords": ["arctic", "freeze", "frozen", "extreme cool"]
                },
                "Herbal Mint": {
                    "tags": ["Herbal Mint", "Natural Mint"],
                    "keywords": ["herbal mint", "natural mint", "eucalyptus"]
                }
            }
        },
        "Tobacco": {
            "tags": ["Tobacco", "Tobacco Flavor"],
            "keywords": ["tobacco"],
            "sub_categories": {
                "Classic": {
                    "tags": ["Classic Tobacco", "Traditional Tobacco"],
                    "keywords": ["classic tobacco", "traditional", "pure tobacco"]
                },
                "Sweet": {
                    "tags": ["Sweet Tobacco", "Honey Tobacco"],
                    "keywords": ["sweet tobacco", "honey tobacco", "caramel tobacco"]
                },
                "Blend": {
                    "tags": ["Tobacco Blend", "Mixed Tobacco"],
                    "keywords": ["blend", "mixed tobacco", "tobacco blend"]
                },
                "Dark": {
                    "tags": ["Dark Tobacco", "Bold Tobacco"],
                    "keywords": ["dark tobacco", "bold", "robust tobacco"]
                }
            }
        },
        "Beverage": {
            "tags": ["Beverage", "Drink Flavor"],
            "keywords": ["beverage", "drink"],
            "sub_categories": {
                "Coffee": {
                    "tags": ["Coffee", "Espresso", "Caffeine"],
                    "keywords": ["coffee", "espresso", "cappuccino", "latte", "mocha"]
                },
                "Soda": {
                    "tags": ["Soda", "Cola", "Fizzy Drink"],
                    "keywords": ["cola", "soda", "fizzy", "pop"]
                },
                "Cocktail": {
                    "tags": ["Cocktail", "Mixed Drink"],
                    "keywords": ["cocktail", "mojito", "margarita", "pina colada"]
                },
                "Tea": {
                    "tags": ["Tea", "Tea Flavor"],
                    "keywords": ["tea", "green tea", "black tea", "chai"]
                }
            }
        }
    }
    
    # Nicotine Strength Taxonomy
    NICOTINE_STRENGTH = {
        "Zero": {
            "range": [0, 0],
            "tags": ["0mg", "Zero Nicotine", "No Nicotine", "Nicotine Free"],
            "keywords": ["0mg", "zero", "no nicotine", "nicotine free"]
        },
        "Low": {
            "range": [1, 6],
            "tags": ["Low Strength", "Mild Strength", "Light"],
            "keywords": ["3mg", "6mg", "low", "mild", "light"]
        },
        "Medium": {
            "range": [7, 12],
            "tags": ["Medium Strength", "Moderate Strength", "Regular"],
            "keywords": ["9mg", "12mg", "medium", "moderate", "regular"]
        },
        "High": {
            "range": [13, 99],
            "tags": ["High Strength", "Strong", "Extra Strong"],
            "keywords": ["18mg", "20mg", "high", "strong", "extra strong"]
        }
    }
    
    # Nicotine Type Taxonomy
    NICOTINE_TYPES = {
        "Freebase": {
            "tags": ["Freebase Nicotine", "Traditional Nicotine", "Standard Nicotine"],
            "keywords": ["freebase", "traditional", "standard nicotine"]
        },
        "Salt": {
            "tags": ["Nicotine Salt", "Salt Nicotine", "Nic Salt", "Smooth", "Quick Absorption"],
            "keywords": ["salt", "nic salt", "nicotine salt", "smooth", "quick absorption"]
        }
    }
    
    # Compliance and Age Verification Tags
    COMPLIANCE_TAGS = {
        "age_restriction": ["18+", "Age Restricted", "Adult Only", "Age Verification Required"],
        "regional_compliance": ["US Compliant", "EU Compliant", "TPD Compliant"],
        "shipping_restriction": ["Shipping Restrictions Apply", "Limited Shipping"],
        "nicotine_warnings": ["Contains Nicotine", "Nicotine Warning", "Addictive Substance"]
    }
    
    # Device Compatibility Tags
    COMPATIBILITY_TAGS = {
        "coil_types": ["Sub-Ohm", "Plus-Ohm", "Mesh Coil", "Ceramic Coil"],
        "battery_types": ["Built-in Battery", "Removable Battery", "18650", "21700"],
        "tank_systems": ["Top Fill", "Bottom Fill", "Side Fill"],
        "usage_profiles": ["MTL", "DL", "RDL", "Mouth to Lung", "Direct Lung"]
    }
    
    @classmethod
    def get_all_flavor_families(cls):
        """Get all main flavor families"""
        return list(cls.FLAVOR_TAXONOMY.keys())
    
    @classmethod
    def get_flavor_subcategories(cls, flavor_family):
        """Get sub-categories for a specific flavor family"""
        if flavor_family in cls.FLAVOR_TAXONOMY:
            return cls.FLAVOR_TAXONOMY[flavor_family].get("sub_categories", {})
        return {}
    
    @classmethod
    def get_nicotine_strength_level(cls, mg_value):
        """Determine nicotine strength level from mg value"""
        try:
            mg = float(mg_value)
            for level, data in cls.NICOTINE_STRENGTH.items():
                if data["range"][0] <= mg <= data["range"][1]:
                    return level, data["tags"]
        except (ValueError, TypeError):
            pass
        return None, []
    
    @classmethod
    def get_all_device_types(cls):
        """Get all device type categories"""
        return list(cls.DEVICE_TYPES.keys())
    
    @classmethod
    def get_all_device_forms(cls):
        """Get all device form categories"""
        return list(cls.DEVICE_FORMS.keys())
