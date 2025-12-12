"""
Vape Product Taxonomy Module
Defines comprehensive hierarchical taxonomy for vaping products
Uses approved_tags.json as single source of truth for allowed tags
"""

class VapeTaxonomy:
    """Comprehensive vaping product taxonomy definitions"""
    
    # Category Keywords (for detection only, approved_tags.json has allowed category tags)
    # ORDER MATTERS: More specific categories should come before broader ones
    CATEGORY_KEYWORDS = {
        "CBD": ["cbd", "cannabidiol", "hemp", "cbg", "cbn"],  # CBD first to prioritize
        "nicotine_pouches": [
            "nicotine pouch", "nic pouch", "snus", "nicotine candy", "nicotine lozenge",
            "energy pouches", "spearmint pouches", "mint pouches", "zero pouches"
        ],  # Before "pouch" alone
        "e-liquid": [
            "e-liquid", "eliquid", "e liquid", "vape juice", "vape liquid", "ejuice",
            "nic salt", "nicotine salt", "shortfill", "longfill", "freebase",
            "50vg", "70vg", "80vg", "vg/pg", "pg/vg"
        ],
        "disposable": ["disposable", "single use", "throw away", "one time", "disposable vape", "disposable pod"],
        "pod_system": ["pod system", "pod mod", "pod device", "pod kit", "starter kit"],  # Before generic device
        "box_mod": ["box mod", "square mod"],
        "device": ["device", "vape device", "vaping device", "mod", "vape mod", "kit"],
        "tank": ["tank", "vape tank", "clearomizer", "atomizer tank", "sub ohm tank", "sub-ohm tank"],
        "coil": ["coil", "replacement coil", "coil head", "atomizer head", "mesh coil"],
        "pod": ["pod", "replacement pod", "prefilled pod", "cartridge", "refillable pod"],
        "accessory": ["accessory", "accessories", "vape accessory", "drip tip", "battery", "charger"]
    }
    
    # Device Style Keywords (maps to device_style tags in approved_tags.json)
    DEVICE_STYLE_KEYWORDS = {
        "pen_style": ["pen", "pen style", "vape pen"],
        "pod_style": ["pod style", "pod-style"],
        "box_style": ["box", "box style", "boxy", "square"],
        "stick_style": ["stick", "stick style", "tube", "cylindrical"],
        "compact": ["compact", "small", "mini", "portable", "pocket"],
        "mini": ["mini", "micro", "tiny"]
    }
    
    # Flavor Type Keywords (approved_tags.json: fruity, ice, tobacco, desserts/bakery, beverages, nuts, spices_&_herbs, cereal, unflavoured, candy/sweets)
    # Secondary flavor keywords captured opportunistically for richer data
    FLAVOR_KEYWORDS = {
        "fruity": {
            "primary_keywords": ["fruit", "fruity"],
            "secondary_keywords": [
                # Citrus
                "lemon", "lime", "orange", "grapefruit", "citrus", "tangerine", "mandarin",
                # Berry (real fruits only - not candy versions)
                "strawberry", "raspberry", "blueberry", "blackberry", "berry", "cranberry",
                # Tropical
                "mango", "pineapple", "coconut", "papaya", "guava", "passion fruit", "tropical", "lychee",
                # Stone Fruit
                "peach", "plum", "apricot", "nectarine", "cherry",
                # Other Fruits
                "apple", "pear", "grape", "watermelon", "melon", "kiwi", "banana"
            ]
        },
        "ice": {
            "primary_keywords": ["ice", "iced", "icy", "cool", "cooling", "menthol", "mint", "freeze", "frozen", "arctic"],
            "secondary_keywords": ["peppermint", "spearmint", "wintergreen", "eucalyptus", "cold"]
        },
        "tobacco": {
            "primary_keywords": ["tobacco"],
            "secondary_keywords": ["virginia", "havana", "cuban", "burley", "cigar", "cigarette", "classic tobacco", "sweet tobacco", "honey tobacco", "caramel tobacco", "dark tobacco", "bold tobacco"]
        },
        "desserts/bakery": {
            "primary_keywords": ["dessert", "bakery", "pastry"],
            "secondary_keywords": ["custard", "cookie", "cake", "donut", "waffle", "cream", "creamy", "pudding", "flan", "ice cream"]
        },
        "candy/sweets": {
            "primary_keywords": ["candy", "sweets", "gummy", "gummies", "sour"],
            "secondary_keywords": [
                # Gummy/Chewy
                "gummy bear", "gummy worm", "jelly", "jelly bean", "haribo", "chewy",
                # Sour Candy
                "sour rainbow", "sour apple", "sour cherry", "sour patch", "tangy", "fizzy",
                # Specific Candy Types
                "blue razz", "razz", "bubblegum", "bubble gum", "cotton candy", "lollipop",
                "skittles", "starburst", "jawbreaker", "sherbet", "rainbow",
                # Sweet/Sugary
                "sugar", "sugary", "toffee", "caramel", "butterscotch", "fudge", "chocolate"
            ]
        },
        "beverages": {
            "primary_keywords": ["beverage", "drink"],
            "secondary_keywords": [
                # Soft Drinks
                "soda", "cola", "lemonade", "energy drink", "fizz",
                # Hot Drinks  
                "coffee", "espresso", "cappuccino", "latte", "mocha", "tea", "green tea", "chai",
                # Cocktails/Alcoholic Inspired
                "cocktail", "mojito", "margarita", "pina colada", "daiquiri", "sangria", "rum"
            ]
        },
        "nuts": {
            "primary_keywords": ["nut", "nuts", "nutty"],
            "secondary_keywords": ["almond", "hazelnut", "peanut", "walnut", "pecan", "pistachio"]
        },
        "spices_&_herbs": {
            "primary_keywords": ["spice", "spices", "herb", "herbs", "spicy"],
            "secondary_keywords": ["cinnamon", "vanilla", "anise", "licorice", "ginger", "clove", "cardamom"]
        },
        "cereal": {
            "primary_keywords": ["cereal", "grain"],
            "secondary_keywords": ["oat", "wheat", "corn", "rice", "granola", "muesli"]
        },
        "unflavoured": {
            "primary_keywords": ["unflavoured", "unflavored", "plain", "natural", "no flavor", "no flavour"],
            "secondary_keywords": []
        }
    }
    
    # Nicotine Type Keywords (approved_tags.json: nic_salt, freebase_nicotine, traditional_nicotine, pouch)
    NICOTINE_TYPE_KEYWORDS = {
        "nic_salt": ["nic salt", "nicotine salt", "salt nicotine", "salt nic", "smooth"],
        "freebase_nicotine": ["freebase", "free base", "freebase nicotine"],
        "traditional_nicotine": ["traditional", "traditional nicotine", "standard nicotine"],
        "pouch": ["pouch", "nicotine pouch"]
    }
    
    # Capacity Keywords (approved_tags.json: 2ml, 2.5ml, 3ml, etc.)
    CAPACITY_KEYWORDS = ["2ml", "2.5ml", "3ml", "4ml", "5ml", "6ml", "7ml", "8ml", "9ml", "10ml"]
    
    # Bottle Size Keywords (approved_tags.json: 5ml, 10ml, 20ml, 30ml, 50ml, 100ml, shortfill)
    BOTTLE_SIZE_KEYWORDS = {
        "5ml": ["5ml", "5 ml"],
        "10ml": ["10ml", "10 ml"],
        "20ml": ["20ml", "20 ml"],
        "30ml": ["30ml", "30 ml"],
        "50ml": ["50ml", "50 ml"],
        "100ml": ["100ml", "100 ml"],
        "shortfill": ["shortfill", "short fill"]
    }
    
    # CBD Form Keywords (approved_tags.json)
    CBD_FORM_KEYWORDS = {
        "tincture": ["tincture", "drops", "liquid drops"],
        "oil": ["oil", "cbd oil"],
        "gummy": ["gummy", "gummies", "gummie"],
        "capsule": ["capsule", "capsules", "pill", "pills"],
        "topical": ["topical", "cream", "lotion", "balm", "salve"],
        "patch": ["patch", "patches", "transdermal"],
        "paste": ["paste"],
        "shot": ["shot", "shots"],
        "isolate": ["isolate", "crystal", "shatter", "wax", "crumble", "dab"],
        "edible": ["edible", "edibles", "food"],
        "beverage": ["beverage", "drink", "tea", "coffee"]
    }
    
    # CBD Type Keywords (approved_tags.json)
    CBD_TYPE_KEYWORDS = {
        "full_spectrum": ["full spectrum", "full-spectrum"],
        "broad_spectrum": ["broad spectrum", "broad-spectrum"],
        "isolate": ["isolate", "pure cbd", "cbd isolate", "shatter", "wax", "crumble", "dab"],
        "cbg": ["cbg", "cannabigerol"],
        "cbda": ["cbda", "cannabidiolic acid"]
    }
    
    # Power Supply Keywords (approved_tags.json)
    POWER_SUPPLY_KEYWORDS = {
        "rechargeable": ["rechargeable", "usb", "usb-c", "charging", "charge"],
        "removable_battery": ["removable battery", "18650", "21700", "replaceable battery"]
    }
    
    # Pod Type Keywords (approved_tags.json)
    POD_TYPE_KEYWORDS = {
        "prefilled_pod": ["prefilled", "pre-filled", "pre filled"],
        "replacement_pod": ["replacement", "refillable", "empty pod"]
    }
    
    # Vaping Style Keywords (approved_tags.json)
    VAPING_STYLE_KEYWORDS = {
        "mouth-to-lung": ["mtl", "mouth to lung", "mouth-to-lung"],
        "direct-to-lung": ["dtl", "direct to lung", "direct-to-lung", "sub ohm", "subohm"],
        "restricted-direct-to-lung": ["rdtl", "restricted dtl", "restricted direct to lung", "restricted-direct-to-lung"]
    }
    
    @classmethod
    def get_all_flavor_types(cls):
        """Get all approved flavor types from FLAVOR_KEYWORDS"""
        return list(cls.FLAVOR_KEYWORDS.keys())
    
    @classmethod
    def get_flavor_secondary_keywords(cls, flavor_type):
        """Get secondary keywords for a specific flavor type for opportunistic tagging"""
        if flavor_type in cls.FLAVOR_KEYWORDS:
            return cls.FLAVOR_KEYWORDS[flavor_type].get("secondary_keywords", [])
        return []
    
    @classmethod
    def detect_flavor_types(cls, text: str) -> list:
        """
        Detect flavor types from a text string (e.g., variant option value).
        
        Args:
            text: Text to analyze (e.g., "Strawberry Ice", "Mango Peach")
            
        Returns:
            List of detected flavor type tags (e.g., ["fruity", "ice"])
        """
        if not text:
            return []
        
        text_lower = text.lower()
        detected = set()
        
        for flavor_type, config in cls.FLAVOR_KEYWORDS.items():
            # Check primary keywords
            for keyword in config.get("primary_keywords", []):
                if keyword.lower() in text_lower:
                    detected.add(flavor_type)
                    break
            
            # Check secondary keywords (more specific)
            if flavor_type not in detected:
                for keyword in config.get("secondary_keywords", []):
                    if keyword.lower() in text_lower:
                        detected.add(flavor_type)
                        break
        
        return list(detected)
    
    @classmethod
    def get_nicotine_strength_tag(cls, mg_value):
        """
        Get nicotine strength tag from mg value
        Returns the value as a tag (e.g., 3mg, 12mg, 0mg)
        Max allowed: 20mg
        """
        try:
            mg = float(mg_value)
            if mg < 0:
                return None
            if mg > 20:
                return None  # Illegal - max 20mg
            # Return as formatted tag
            if mg == int(mg):
                return f"{int(mg)}mg"
            else:
                return f"{mg}mg"
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def get_cbd_strength_tag(cls, mg_value):
        """
        Get CBD strength tag from mg value
        Returns the value as a tag (e.g., 1000mg, 5000mg)
        Max allowed: 50000mg
        """
        try:
            mg = float(mg_value)
            if mg < 0:
                return None
            if mg > 50000:
                return None  # Max 50000mg
            # Return as formatted tag
            if mg == int(mg):
                return f"{int(mg)}mg"
            else:
                return f"{mg}mg"
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def get_all_categories(cls):
        """Get all approved category keywords"""
        return list(cls.CATEGORY_KEYWORDS.keys())
    
    @classmethod
    def get_all_device_styles(cls):
        """Get all approved device style keywords"""
        return list(cls.DEVICE_STYLE_KEYWORDS.keys())
