#!/usr/bin/env python3
"""
Controlled AI Product Tagger
===========================
AI-powered product tagging with strict vocabulary control.
Only approved tags from approved_tags.json can be applied.
"""

import json
import ollama
import sqlite3
import csv
import re
import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
import os

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Controlled AI Product Tagger - Strict vocabulary tagging for vaping products',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Tag products from default input directory
  python controlled_tagger.py
  
  # Tag specific file
  python controlled_tagger.py --input products.csv
  
  # Tag with custom output and limit
  python controlled_tagger.py --input products.csv --output tagged.csv --limit 10
  
  # Disable AI (rule-based only)
  python controlled_tagger.py --no-ai
  
  # Verbose logging
  python controlled_tagger.py --verbose
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Input CSV file path (default: auto-detect from input/)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output CSV file path (default: output/controlled_tagged_products.csv)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (config.env)'
    )
    
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI-powered tagging (use only rule-based tagging)'
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit processing to first N products (useful for testing)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

# Simple logger setup
def setup_simple_logger():
    logger = logging.getLogger('controlled-tagger')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class ControlledTagger:
    def __init__(self, config_file=None, no_ai=False, verbose=False):
        # Load config
        if config_file:
            load_dotenv(config_file)
        else:
            # Try default config.env
            config_path = Path('config.env')
            if config_path.exists():
                load_dotenv(config_path)
        
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.1')
        self.no_ai = no_ai
        
        # Setup logging
        self.logger = self._setup_logger(verbose)
        
        self.approved_tags = self._load_approved_tags()
        self.all_approved_tags = self._flatten_approved_tags()
        self.tag_to_category = self._build_tag_to_category()
        
        # Category priority for more specific categorization
        self.category_priority = {
            'pod': 12,
            'e-liquid': 13,
            'cbd': 13,
            'disposable': 10,
            'pod_system': 8,
            'device': 7,
            'coil': 5,
            'box_mod': 4,
            'tank': 3,
            'accessory': 2,
        }
        self.category_tags = set(self.approved_tags.get('category', []))
        
    def _setup_logger(self, verbose):
        """Setup logger with appropriate level"""
        logger = logging.getLogger('controlled-tagger')
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
        
    def _load_approved_tags(self):
        """Load approved tags structure"""
        tags_file = Path('approved_tags.json')
        if not tags_file.exists():
            raise FileNotFoundError("approved_tags.json not found. Run cleanup first.")
        
        with open(tags_file) as f:
            data = json.load(f)
            self.rules = data.pop('rules', {})
            return data
    
    def _flatten_approved_tags(self):
        """Create flat list of all approved tags"""
        tags = []
        for cat_data in self.approved_tags.values():
            if isinstance(cat_data, dict):
                tags.extend(cat_data.get('tags', []))
            else:
                tags.extend(cat_data)
        return tags
    
    def _build_tag_to_category(self):
        """Build mapping from tag to category"""
        tag_to_cat = {}
        for cat, cat_data in self.approved_tags.items():
            if isinstance(cat_data, dict):
                for tag in cat_data.get('tags', []):
                    tag_to_cat[tag] = cat
            else:
                for tag in cat_data:
                    tag_to_cat[tag] = cat
        return tag_to_cat
    
    def _create_ai_prompt(self, handle, title, description="", option1_name="", option1_value="", option2_name="", option2_value="", option3_name="", option3_value=""):
        """Create focused AI prompt for tag suggestion"""
        
        rules_text = "\n".join(f"- {rule}" for rule in self.rules.values())
        
        prompt = f"""You are a vaping product expert. Analyze this product and suggest ONLY tags from the approved list.

PRODUCT HANDLE: {handle}
PRODUCT TITLE: {title}
DESCRIPTION: {description or 'Not provided'}
OPTION1: {option1_name} - {option1_value}
OPTION2: {option2_name} - {option2_value}
OPTION3: {option3_name} - {option3_value}

APPROVED TAGS (choose only from these):
{json.dumps(self.approved_tags, indent=2)}

RULES:
{rules_text}

Respond with ONLY a JSON array of suggested tags:
["tag1", "tag2", "tag3"]"""

        return prompt
    
    def get_ai_tags(self, product_or_handle, title=None, description=""):
        """Get AI tag suggestions using controlled vocabulary"""
        
        if isinstance(product_or_handle, dict):
            product = product_or_handle
            handle = product['handle']
            title = product['title']
            description = product['description']
            option1_name = product.get('option1_name', '')
            option1_value = product.get('option1_value', '')
            option2_name = product.get('option2_name', '')
            option2_value = product.get('option2_value', '')
            option3_name = product.get('option3_name', '')
            option3_value = product.get('option3_value', '')
        else:
            handle = product_or_handle
            option1_name = option1_value = option2_name = option2_value = option3_name = option3_value = ""
        
        if self.no_ai:
            return []
        
        try:
            prompt = self._create_ai_prompt(handle, title, description, option1_name, option1_value, option2_name, option2_value, option3_name, option3_value)
            
            response = ollama.chat(
                model=self.ollama_model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            # Parse AI response
            response_text = response['message']['content'].strip()
            
            # Extract JSON array from response
            import re
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if json_match:
                suggested_tags = json.loads(json_match.group())
            else:
                return []
            
            # Validate all suggested tags are approved
            valid_tags = [tag for tag in suggested_tags if tag in self.all_approved_tags]
            
            self.logger.info(f"AI suggested {len(suggested_tags)} tags, {len(valid_tags)} valid: {valid_tags}")
            return valid_tags
            
        except Exception as e:
            self.logger.error(f"AI tagging error: {e}")
            return []
    
    def get_rule_based_tags(self, handle, title, description=""):
        """Extract obvious tags using rules"""
        
        text = f"{handle} {title} {description}".lower()
        handle_title = f"{handle} {title}".lower()
        rule_tags = []
        
        # Prioritize handle/title for category determination
        if 'charger' in handle_title:
            rule_tags.append('charger')
            forced_category = 'accessory'
        elif 'battery' in handle_title:
            rule_tags.append('battery')
            forced_category = 'accessory'
        elif 'coil' in handle_title:
            rule_tags.append('coil')
            forced_category = 'coil'
        elif 'e-liquid' in handle_title or 'liquid' in handle_title or ('nic' in handle_title and 'salt' in handle_title) or 'salt' in handle_title or 'mg' in handle_title:
            rule_tags.append('e-liquid')
            forced_category = 'e-liquid'
        elif 'pod' in handle_title:
            rule_tags.append('pod')
            forced_category = 'pod'
        elif 'disposable' in handle_title:
            rule_tags.append('disposable')
            forced_category = 'disposable'
        elif 'pouch' in handle_title:
            rule_tags.append('pouch')
            forced_category = 'accessory'
        elif 'case' in handle_title:
            rule_tags.append('case')
            forced_category = 'accessory'
        elif 'mouthpiece' in handle_title:
            rule_tags.append('mouthpiece')
            forced_category = 'accessory'
        else:
            forced_category = None
        
        # If no category from handle/title, fall back to full text
        if not any(tag in self.category_tags for tag in rule_tags):
            if 'charger' in text and 'charger' not in rule_tags:
                rule_tags.append('charger')
            elif 'battery' in text and 'battery' not in rule_tags:
                rule_tags.append('battery')
            elif 'glass' in text and 'replacement' in text:
                rule_tags.append('replacement_glass')
            # Add more as needed
        
        # Nicotine strength detection
        mg_matches = re.findall(r'(\d+)mg', text)
        if mg_matches:
            # Skip if CBD/CBG
            if 'cbd' in text or 'cbg' in text:
                pass
            else:
                strengths = [f"{m}mg" for m in mg_matches if f"{m}mg" in self.approved_tags.get('nicotine_strength', {}).get('tags', [])]
                if strengths:
                    rule_tags.append(strengths[0])  # Take first valid strength
        
        # Nicotine type detection
        if 'nic' in text and 'salt' in text:
            rule_tags.append('nic_salt')
        
        # CBD strength detection
        if 'cbd' in text or 'cbg' in text:
            mg_matches = re.findall(r'(\d+)mg', text)
            if mg_matches:
                for mg in mg_matches:
                    cbd_tag = f"{mg}mg"
                    if cbd_tag in self.approved_tags.get('cbd_strength', {}).get('tags', []):
                        rule_tags.append(cbd_tag)
                        break
            # Check for unlimited
            if 'unlimited' in text.lower():
                if 'unlimited mg' in self.approved_tags.get('cbd_strength', {}).get('tags', []):
                    rule_tags.append('unlimited mg')
        
        # Bottle size detection
        for size in ['2ml', '5ml', '10ml', '20ml', '30ml', '50ml', '100ml']:
            if size in text:
                rule_tags.append(size)
                break
        
        # VG/PG ratio detection
        ratio_matches = re.findall(r'(\d+)\s*vg\s*[/-]\s*(\d+)\s*pg', text)
        if not ratio_matches:
            # Try alternative format like "50/50 VG/PG"
            ratio_matches = re.findall(r'(\d+)[/-](\d+)\s*vg[/-]pg', text)
        if ratio_matches:
            for vg, pg in ratio_matches:
                ratio = f"{vg}/{pg}"
                if ratio in self.approved_tags.get('vg_ratio', {}).get('tags', []):
                    rule_tags.append(ratio)
                    break  # Take first valid ratio
        
        # Pure VG detection
        if not ratio_matches and 'vg' in text and 'pg' not in text:
            rule_tags.append('100/0')
        
        # Shortfill detection
        if 'shortfill' in text:
            rule_tags.append('shortfill')
        
        # Basic product type
        if any(word in text for word in ['disposable', 'puff']):
            rule_tags.append('disposable')
        elif any(word in text for word in ['e-liquid', 'liquid', 'juice']) or ('nic' in text and 'salt' in text):
            rule_tags.append('e-liquid')
        elif any(word in text for word in ['kit', 'device', 'mod']):
            rule_tags.append('device')
        
        # Specific types
        if 'coil' in text:
            rule_tags.append('coil')
        if 'tank' in text or ('replacement' in text and 'glass' in text):
            rule_tags.append('tank')
        if 'pod' in text:
            if 'replacement' in text:
                rule_tags.append('replacement_pod')
            else:
                rule_tags.append('pod')
        if 'box' in text and 'mod' in text:
            rule_tags.append('box_mod')
        
        # Battery detection
        if any(word in text for word in ['battery', 'batteries']):
            rule_tags.append('accessory')
            rule_tags.append('battery')
        
        # Charger detection
        if 'charger' in text:
            rule_tags.append('accessory')
            rule_tags.append('charger')
        
        # Pod detection
        if 'pod' in text:
            if 'refillable' in text or 'replacement' in text:
                rule_tags.append('refillable_pod')
            elif 'prefilled' in text or 'pre-filled' in text or 'pre_filled' in text:
                rule_tags.append('prefilled_pod')
            else:
                rule_tags.append('pod')
            # Also set category
            rule_tags.append('pod')
        
        # Device style detection
        if 'pen' in text and 'style' in text:
            rule_tags.append('pen_style')
        elif 'pod' in text and 'style' in text:
            rule_tags.append('pod_style')
        elif 'box' in text and 'style' in text:
            rule_tags.append('box_style')
        elif 'stick' in text:
            rule_tags.append('stick_style')
        elif 'compact' in text:
            rule_tags.append('compact')
        elif 'mini' in text:
            rule_tags.append('mini')
        
        # Coil ohm detection
        ohm_matches = re.findall(r'(\d+)[-\.]?(\d*)\s*[ωo]h?m?', text)
        if ohm_matches:
            for match in ohm_matches:
                ohm = f"{match[0]}.{match[1]}" if match[1] else match[0]
                ohm_tag = f"{ohm}ohm"
                if ohm_tag in self.approved_tags.get('coil_ohm', {}).get('tags', []):
                    rule_tags.append(ohm_tag)
                    break
        
        # Flavour type detection
        if any(word in text for word in ['e-liquid', 'liquid', 'juice', 'pod', 'disposable']):
            if any(word in text for word in ['fruit', 'berry', 'citrus', 'apple', 'orange']):
                rule_tags.append('fruity')
            elif 'ice' in text or 'cool' in text:
                rule_tags.append('ice')
            elif 'tobacco' in text:
                rule_tags.append('tobacco')
            elif any(word in text for word in ['dessert', 'bakery', 'cake', 'cookie']):
                rule_tags.append('desserts/bakery')
            elif any(word in text for word in ['beverage', 'drink', 'cola', 'coffee']):
                rule_tags.append('beverages')
            elif 'nut' in text:
                rule_tags.append('nuts')
            elif any(word in text for word in ['spice', 'herb', 'mint', 'cinnamon']):
                rule_tags.append('spices_&_herbs')
            elif 'cereal' in text:
                rule_tags.append('cereal')
            elif 'unflavoured' in text or 'plain' in text:
                rule_tags.append('unflavoured')
        
        # Validate rule tags
        valid_tags = []
        for tag in rule_tags:
            if tag in self.all_approved_tags or (forced_category == 'CBD' and re.match(r'\d+mg', tag)):
                valid_tags.append(tag)
        return valid_tags, forced_category
    
    def tag_products(self, input_file, output_file=None, limit=None):
        """Tag products from input CSV"""
        
        self.logger.info(f"Starting controlled tagging from {input_file}")
        
        if not Path(input_file).exists():
            self.logger.error(f"Input file not found: {input_file}")
            return
        
        # Read input products
        products = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            products = list(reader)
        
        if limit:
            products = products[:limit]
            self.logger.info(f"Limited to first {limit} products")
        
        self.logger.info(f"Processing {len(products)} products")
        
        # Process each product
        tagged_products = []
        untagged_products = []
        untagged_originals = []
        
        for i, product in enumerate(products, 1):
            product_dict = {
                'handle': product.get('Handle', ''),
                'title': product.get('Title', ''),
                'description': product.get('Body (HTML)', ''),
                'option1_name': product.get('Option1 Name', ''),
                'option1_value': product.get('Option1 Value', ''),
                'option2_name': product.get('Option2 Name', ''),
                'option2_value': product.get('Option2 Value', ''),
                'option3_name': product.get('Option3 Name', ''),
                'option3_value': product.get('Option3 Value', ''),
            }
            
            # Get AI suggestions
            ai_tags = self.get_ai_tags(product_dict)
            
            # Get rule-based tags
            rule_tags, forced_category = self.get_rule_based_tags(product_dict['handle'], product_dict['title'], product_dict['description'])
            
            # Combine and deduplicate
            all_tags = list(set(ai_tags + rule_tags))
            
            # Determine product category with priority
            product_category = None
            max_priority = -1
            for tag in all_tags:
                if tag in self.category_tags:
                    priority = self.category_priority.get(tag, 0)
                    if priority > max_priority:
                        max_priority = priority
                        product_category = tag
            
            # Override with forced category from handle
            if forced_category:
                product_category = forced_category
            
            # Infer vaping style from VG/PG ratio for e-liquids
            inferred_tags = []
            if product_category == 'e-liquid':
                for tag in all_tags:
                    if '/' in tag and tag in self.approved_tags.get('vg_ratio', {}).get('tags', []):
                        try:
                            vg, pg = map(int, tag.split('/'))
                            if pg >= 50:
                                inferred_tags.append('mouth-to-lung')
                            elif 60 <= vg <= 70:
                                inferred_tags.append('restricted_direct_to_lung')
                            elif vg >= 70:
                                inferred_tags.append('direct-to-lung')
                        except ValueError:
                            pass
            all_tags.extend(inferred_tags)
            all_tags = list(set(all_tags))
            
            # Filter tags based on applies_to and enforce category limits
            tag_by_cat = defaultdict(list)
            for tag in all_tags:
                cat = self.tag_to_category.get(tag)
                if cat == 'category':
                    continue
                cat_data = self.approved_tags.get(cat, {})
                applies_to = cat_data.get('applies_to', ['all']) if isinstance(cat_data, dict) else ['all']
                if 'all' in applies_to or product_category in applies_to:
                    tag_by_cat[cat].append(tag)
            
            # Sort tags within each category by specificity (longer tags first)
            for cat in tag_by_cat:
                if cat == 'accessory_type':
                    # Prioritize charger over battery
                    tag_by_cat[cat].sort(key=lambda t: (0 if t == 'charger' else 1 if t == 'battery' else 2, -len(t)))
                else:
                    tag_by_cat[cat].sort(key=len, reverse=True)
            
            final_tags = []
            for cat, tags in tag_by_cat.items():
                final_tags.extend(tags[:1])  # Keep at most one per category
            
            self.logger.info(f"Product: {product_dict['handle']} | All tags: {all_tags} | Product category: {product_category} | Tag by cat: {dict(tag_by_cat)} | Final tags: {final_tags}")
            
            # Flagging for ambiguous products
            flagged = False
            nic_strengths = tag_by_cat.get('nicotine_strength', [])
            if len(nic_strengths) > 1:
                flagged = True
            if 'device' in final_tags and 'e-liquid' in final_tags:
                flagged = True
            
            self.logger.info(f"Product: {product_dict['handle']} | Product category: {product_category} | Final tags: {final_tags}")
            
            # Create output product with only required fields
            product_output = {
                'Handle': product.get('Handle', ''),
                'Variant SKU': product.get('Variant SKU', ''),
                'Tags': ', '.join(final_tags)
            }
            tagged_products.append(product_output)
            
            # If no tags, add to untagged
            if not final_tags:
                untagged_products.append(product_output)
                untagged_originals.append(product)
            
            if i % 50 == 0:
                self.logger.info(f"Processed {i}/{len(products)} products")
        
        # Save tagged products
        if not output_file:
            output_file = Path('output/controlled_tagged_products.csv')
        else:
            output_file = Path(output_file)
        
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if tagged_products:
                fieldnames = tagged_products[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(tagged_products)
        
        self.logger.info(f"Tagged products saved to {output_file}")
        
        # Save untagged products
        untagged_file = output_file.parent / 'controlled_untagged_products.csv'
        with open(untagged_file, 'w', newline='', encoding='utf-8') as f:
            if untagged_products:
                fieldnames = untagged_products[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(untagged_products)
                self.logger.info(f"Untagged products saved to {untagged_file} ({len(untagged_products)} products)")
            else:
                # Write header even if empty
                writer = csv.DictWriter(f, fieldnames=['Handle', 'Variant SKU', 'Tags'])
                writer.writeheader()
                self.logger.info("No untagged products found")
        
        # Secondary AI pass for untagged products
        if untagged_originals and not self.no_ai:
            self.logger.info(f"Attempting secondary AI tagging for {len(untagged_originals)} untagged products using gpt-oss:latest")
            original_model = self.ollama_model
            self.ollama_model = 'gpt-oss:latest'
            newly_tagged = []
            still_untagged = []
            for orig_product in untagged_originals:
                handle = orig_product.get('Handle', '')
                title = orig_product.get('Title', '')
                description = orig_product.get('Body (HTML)', '')
                
                # Get rule-based tags again (in case)
                rule_tags_secondary, forced_category_secondary = self.get_rule_based_tags(handle, title, description)
                
                # Get secondary AI tags
                ai_tags_secondary = self.get_ai_tags(handle, title, description)
                
                # Combine
                all_tags = list(set(ai_tags + rule_tags))
                
                # Determine product category with priority (using only rule_tags for secondary)
                rule_tags_secondary, forced_category_secondary = self.get_rule_based_tags(handle, title, description)
                product_category = None
                max_priority = -1
                for tag in rule_tags_secondary:
                    if tag in self.category_tags:
                        priority = self.category_priority.get(tag, 0)
                        if priority > max_priority:
                            max_priority = priority
                            product_category = tag
                
                # Override with forced category
                if forced_category_secondary:
                    product_category = forced_category_secondary
                
                # Infer vaping style from VG/PG ratio for e-liquids
                inferred_tags = []
                if product_category == 'e-liquid':
                    for tag in all_tags:
                        if '/' in tag and tag in self.approved_tags.get('vg_ratio', {}).get('tags', []):
                            try:
                                vg, pg = map(int, tag.split('/'))
                                if pg >= 50:
                                    inferred_tags.append('mouth-to-lung')
                                elif 60 <= vg <= 70:
                                    inferred_tags.append('restricted_direct_to_lung')
                                elif vg >= 70:
                                    inferred_tags.append('direct-to-lung')
                            except ValueError:
                                pass
                all_tags.extend(inferred_tags)
                all_tags = list(set(all_tags))
                
                # Filter tags based on applies_to and enforce category limits
                tag_by_cat = defaultdict(list)
                for tag in all_tags:
                    cat = self.tag_to_category.get(tag)
                    if cat == 'category':
                        continue
                    cat_data = self.approved_tags.get(cat, {})
                    applies_to = cat_data.get('applies_to', ['all']) if isinstance(cat_data, dict) else ['all']
                    if 'all' in applies_to or product_category in applies_to:
                        tag_by_cat[cat].append(tag)
                
                # Sort tags within each category by specificity (longer tags first)
                for cat in tag_by_cat:
                    if cat == 'accessory_type':
                        # Prioritize charger over battery
                        tag_by_cat[cat].sort(key=lambda t: (0 if t == 'charger' else 1 if t == 'battery' else 2, -len(t)))
                    else:
                        tag_by_cat[cat].sort(key=len, reverse=True)
                
                final_tags = []
                for cat, tags in tag_by_cat.items():
                    final_tags.extend(tags[:1])  # Keep at most one per category
                
                self.logger.info(f"Secondary AI for {handle} | Final tags: {final_tags}")
                
                product_output = {
                    'Handle': handle,
                    'Variant SKU': orig_product.get('Variant SKU', ''),
                    'Tags': ', '.join(final_tags)
                }
                
                if final_tags:
                    newly_tagged.append(product_output)
                else:
                    still_untagged.append(product_output)
            
            # Update the lists
            tagged_products.extend(newly_tagged)
            untagged_products[:] = still_untagged
            
            # Re-save files
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if tagged_products:
                    fieldnames = tagged_products[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(tagged_products)
            
            with open(untagged_file, 'w', newline='', encoding='utf-8') as f:
                if untagged_products:
                    fieldnames = untagged_products[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(untagged_products)
                    self.logger.info(f"After secondary AI: {len(newly_tagged)} newly tagged, {len(still_untagged)} still untagged")
                else:
                    writer = csv.DictWriter(f, fieldnames=['Handle', 'Variant SKU', 'Tags'])
                    writer.writeheader()
                    self.logger.info("All products now tagged after secondary AI")
            
            # Restore model
            self.ollama_model = original_model
        
        return output_file

if __name__ == "__main__":
    args = parse_arguments()
    
    # Initialize tagger
    tagger = ControlledTagger(
        config_file=args.config,
        no_ai=args.no_ai,
        verbose=args.verbose
    )
    
    # Determine input file
    if args.input:
        input_file = args.input
    else:
        # Auto-detect from input/
        input_files = list(Path('input').glob('*.csv'))
        if not input_files:
            print("❌ No input CSV found in input/ directory")
            sys.exit(1)
        input_file = input_files[0]
    
    # Tag products
    result = tagger.tag_products(input_file, args.output, args.limit)
    if result:
        print(f"✅ Tagging complete: {result}")
    else:
        print("❌ Tagging failed")
        sys.exit(1)
