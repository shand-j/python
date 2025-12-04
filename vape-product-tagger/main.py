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
import threading
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import os
from tag_audit_db import TagAuditDB

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
    
    parser.add_argument(
        '--type', '-t',
        type=str,
        help='Optional override for product Type (e.g. "Vaping/Smoking Products" or "CBD products")'
    )

    parser.add_argument(
        '--audit-db',
        type=str,
        help='Path to sqlite audit DB file (enables audit logging). If omitted, auditing is disabled.'
    )

    parser.add_argument(
        '--run-id',
        type=str,
        help='Resume a specific run by ID. If omitted, starts a new run.'
    )
    
    parser.add_argument(
        '--workers', '-w',
        type=int,
        help='Number of parallel workers (overrides MAX_WORKERS env var)'
    )
    
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing (sequential mode)'
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
    def __init__(self, config_file=None, no_ai=False, verbose=False, default_product_type=None, audit_db_path=None, run_id=None, max_workers=None, no_parallel=False):
        # Load config
        if config_file:
            load_dotenv(config_file)
        else:
            # Try default config.env
            config_path = Path('config.env')
            if config_path.exists():
                load_dotenv(config_path)
        
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.1')
        self.model_backend = os.getenv('MODEL_BACKEND', 'ollama')  # 'ollama' or 'huggingface'
        self.hf_repo_id = os.getenv('HF_REPO_ID')
        self.hf_token = os.getenv('HF_TOKEN')
        self.base_model = os.getenv('BASE_MODEL', 'meta-llama/Meta-Llama-3.1-8B-Instruct')
        
        self.no_ai = no_ai
        # Allow CLI override or env var to force a product type for the run
        self.default_product_type = default_product_type or os.getenv('DEFAULT_PRODUCT_TYPE')
        
        # Setup logging
        self.logger = self._setup_logger(verbose)
        
        # HF model (lazy loaded)
        self._hf_model = None
        self._hf_tokenizer = None
        
        # Optional audit DB for persisting decisions
        self.audit_db = TagAuditDB(audit_db_path) if audit_db_path else None
        # Handle run_id: if provided, resume; else start new
        self.run_id = run_id
        if self.audit_db:
            if run_id:
                status = self.audit_db.get_run_status(run_id)
                if not status:
                    raise ValueError(f"Run ID {run_id} not found in audit DB")
                if status == 'completed':
                    raise ValueError(f"Run ID {run_id} is already completed")
                self.logger.info(f"Resuming run {run_id}")
            else:
                config_dict = {
                    'no_ai': no_ai,
                    'verbose': verbose,
                    'default_product_type': default_product_type,
                    'audit_db_path': audit_db_path
                }
                self.run_id = self.audit_db.start_run(config=config_dict)
                self.logger.info(f"Started new run {self.run_id}")
        
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
        
        # Parallel processing config (CLI args override env vars)
        if no_parallel:
            self.parallel_processing = False
        else:
            self.parallel_processing = os.getenv('PARALLEL_PROCESSING', 'true').lower() == 'true'
        
        if max_workers:
            self.max_workers = max_workers
        else:
            self.max_workers = int(os.getenv('MAX_WORKERS', 4))
        
        self.batch_size = int(os.getenv('BATCH_SIZE', 10))
        
        # Performance tracking
        self._processed_count = 0
        self._ai_skipped_count = 0
        self._start_time = None
        self._lock = None  # Will be set when parallel processing starts
        
    def _setup_logger(self, verbose):
        """Setup logger with appropriate level"""
        logger = logging.getLogger('controlled-tagger')
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def _load_hf_model(self):
        """Lazy load HuggingFace model with LoRA adapters from HF Hub"""
        if self._hf_model is not None:
            return self._hf_model, self._hf_tokenizer
        
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import PeftModel
        except ImportError:
            self.logger.error("HuggingFace backend requires: pip install torch transformers peft bitsandbytes")
            raise
        
        self.logger.info(f"Loading HF model: {self.base_model} + LoRA from {self.hf_repo_id}")
        
        # 4-bit quantization for inference
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        
        # Load base model
        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            token=self.hf_token,
        )
        
        # Load LoRA adapters from HF Hub
        if self.hf_repo_id:
            self._hf_model = PeftModel.from_pretrained(base_model, self.hf_repo_id, token=self.hf_token)
        else:
            self._hf_model = base_model
        
        self._hf_tokenizer = AutoTokenizer.from_pretrained(self.base_model, token=self.hf_token)
        self._hf_model.eval()
        
        self.logger.info("HF model loaded successfully")
        return self._hf_model, self._hf_tokenizer
    
    def _get_ai_tags_hf(self, prompt: str) -> tuple:
        """Get AI tags using HuggingFace model"""
        import torch
        
        model, tokenizer = self._load_hf_model()
        
        # Format for chat model
        input_text = f"<|user|>\n{prompt}\n<|assistant|>\n"
        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        response_text = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        return response_text.strip()
        
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
    
    def _create_ai_prompt(self, handle, title, description="", option1_name="", option1_value="", option2_name="", option2_value="", option3_name="", option3_value="", category=None):
        """Create category-aware AI prompt for tag suggestion with confidence scoring"""
        
        rules_text = "\n".join(f"- {rule}" for rule in self.rules.values())
        
        # Truncate description to save tokens
        desc_truncated = (description or 'Not provided')[:300]
        if len(description or '') > 300:
            desc_truncated += "..."
        
        # Compact approved tags - only include relevant categories
        relevant_tags = {}
        if category:
            # Only include category-relevant tags + always-needed ones
            always_include = ['category', 'brand']
            category_map = {
                'CBD': ['cbd_form', 'cbd_spectrum', 'cbd_strength'],
                'e-liquid': ['nicotine_type', 'nicotine_strength', 'vg_ratio', 'flavour_profile', 'bottle_size'],
                'pod': ['pod_type', 'capacity', 'resistance'],
                'coil': ['resistance', 'coil_type'],
                'disposable': ['nicotine_strength', 'puff_count', 'flavour_profile'],
                'device': ['device_type', 'battery_capacity'],
                'accessory': ['accessory_type'],
            }
            for key in always_include + category_map.get(category, []):
                if key in self.approved_tags:
                    relevant_tags[key] = self.approved_tags[key]
        else:
            relevant_tags = self.approved_tags
        
        # Base prompt - shortened
        base_prompt = f"""Analyze this vaping/CBD product and suggest tags from the approved list.

PRODUCT: {handle}
TITLE: {title}
DESC: {desc_truncated}
OPTIONS: {option1_name}:{option1_value} | {option2_name}:{option2_value} | {option3_name}:{option3_value}

APPROVED TAGS:
{json.dumps(relevant_tags, indent=1)}

RULES:
{rules_text}

Return JSON only:
{{"tags": ["tag1", "tag2"], "confidence": 0.0-1.0, "reasoning": "brief"}}

Confidence: 0.95+=explicit in title, 0.80-0.94=strong evidence, 0.60-0.79=inference, <0.60=uncertain"""

        # Shorter category-specific hints
        if category == 'CBD':
            base_prompt += """

CBD HINTS: tincture=drops/oil/sublingual, capsule=pills/softgels, gummy=bears/candies, topical=cream/balm, patch=transdermal, paste=concentrate/wax"""
            
        elif category == 'e-liquid':
            base_prompt += """

E-LIQUID HINTS: Look for VG/PG ratio (50/50, 70/30), nic type (salt vs freebase), bottle size (10ml, 100ml shortfill)"""
            
        elif category == 'pod':
            base_prompt += """

POD HINTS: prefilled_pod=comes with juice, replacement_pod=empty pods for refilling"""

        return base_prompt
    
    def get_ai_tags(self, product_or_handle, title=None, description="", category=None):
        """Get AI tag suggestions using controlled vocabulary with category-aware prompting and confidence scoring.
        Returns tuple: (valid_tags, ai_metadata) where ai_metadata contains prompt, response, confidence, reasoning."""
        
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
        
        ai_metadata = {
            'prompt': None,
            'model_output': None,
            'confidence': None,
            'reasoning': None
        }
        
        if self.no_ai:
            return [], ai_metadata
        
        try:
            prompt = self._create_ai_prompt(handle, title, description, option1_name, option1_value, option2_name, option2_value, option3_name, option3_value, category)
            ai_metadata['prompt'] = prompt
            
            # Route to appropriate backend
            if self.model_backend == 'huggingface':
                response_text = self._get_ai_tags_hf(prompt)
            else:
                # Default: Ollama
                response = ollama.chat(
                    model=self.ollama_model,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                response_text = response['message']['content'].strip()
            
            ai_metadata['model_output'] = response_text
            
            # Extract JSON object from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    ai_response = json.loads(json_match.group())
                    suggested_tags = ai_response.get('tags', [])
                    confidence = ai_response.get('confidence', 0.5)
                    reasoning = ai_response.get('reasoning', '')
                    
                    ai_metadata['confidence'] = confidence
                    ai_metadata['reasoning'] = reasoning
                    
                    # Only use high-confidence suggestions (threshold: 0.7)
                    if confidence >= 0.7:
                        valid_tags = [tag for tag in suggested_tags if tag in self.all_approved_tags]
                        self.logger.info(f"AI suggested {len(suggested_tags)} tags (confidence: {confidence:.2f}), {len(valid_tags)} valid: {valid_tags}")
                        if reasoning:
                            self.logger.debug(f"AI reasoning: {reasoning}")
                        return valid_tags, ai_metadata
                    else:
                        self.logger.info(f"AI confidence too low ({confidence:.2f}), skipping suggestions")
                        return [], ai_metadata
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse AI JSON response: {response_text[:200]}...")
                    return [], ai_metadata
            else:
                self.logger.warning(f"No JSON found in AI response: {response_text[:200]}...")
                return [], ai_metadata
            
        except Exception as e:
            self.logger.error(f"AI tagging error: {e}")
            return [], ai_metadata
    
    def get_rule_based_tags(self, handle, title, description=""):
        """Extract obvious tags using rules"""
        
        text = f"{handle} {title} {description}".lower()
        handle_title = f"{handle} {title}".lower()
        rule_tags = []
        
        # Prioritize handle/title for category determination
        # USB/Charging cable detection - check first (before generic 'charger')
        if any(pattern in handle_title for pattern in ['usb cable', 'charging cable', 'data cable', 'usb-c cable', 'micro usb', 'type-c cable']):
            rule_tags.append('charging_cable')
            forced_category = 'accessory'
        elif 'cable' in handle_title and any(word in handle_title for word in ['usb', 'charge', 'charging', 'data', 'phone', 'iphone', 'android', 'type-c', 'micro']):
            rule_tags.append('charging_cable')
            forced_category = 'accessory'
        elif 'charger' in handle_title:
            rule_tags.append('charger')
            forced_category = 'accessory'
        elif 'battery' in handle_title:
            rule_tags.append('battery')
            forced_category = 'accessory'
        # Atomizer detection
        elif 'atomizer' in handle_title or 'atomiser' in handle_title:
            if '510' in handle_title:
                rule_tags.append('510_atomizer')
            else:
                rule_tags.append('atomizer')
            forced_category = 'accessory'
        elif 'coil' in handle_title:
            rule_tags.append('coil')
            forced_category = 'coil'
        elif 'cbd' in handle_title or 'cbg' in handle_title:
            rule_tags.append('CBD')
            forced_category = 'CBD'
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
        
        # Nicotine strength detection (range-based)
        mg_matches = re.findall(r'(\d+(?:\.\d+)?)mg', text)
        if mg_matches:
            # Skip if CBD/CBG
            if 'cbd' in text or 'cbg' in text:
                pass
            else:
                nicotine_config = self.approved_tags.get('nicotine_strength', {})
                range_config = nicotine_config.get('range')
                if range_config:
                    min_val = range_config.get('min', 0)
                    max_val = range_config.get('max', 20)
                    unit = range_config.get('unit', 'mg')
                    for mg in mg_matches:
                        try:
                            mg_value = float(mg)
                            if min_val <= mg_value <= max_val:
                                rule_tags.append(f"{mg}{unit}")
                                break
                        except ValueError:
                            continue
                else:
                    # Fallback to tag-based validation (legacy)
                    strengths = [f"{m}mg" for m in mg_matches if f"{m}mg" in self.approved_tags.get('nicotine_strength', {}).get('tags', [])]
                    if strengths:
                        rule_tags.append(strengths[0])  # Take first valid strength
        
        # Nicotine type detection
        if 'nic' in text and 'salt' in text:
            rule_tags.append('nic_salt')
        
        # CBD strength detection
        if 'cbd' in text or 'cbg' in text:
            # CBD form detection - ordered by specificity, NO default fallback
            # Check specific forms first (capsule/softgel before topical to avoid 'gel' false positives)
            cbd_form_detected = False
            
            if any(word in text for word in ['capsule', 'cap', 'softgel', 'soft gel', 'soft-gel', 'gel cap', 'gelcap']):
                rule_tags.append('capsule')
                cbd_form_detected = True
            elif any(word in text for word in ['gummy', 'gummies', 'bear', 'candy', 'chew', 'jelly', 'sweets']):
                rule_tags.append('gummy')
                cbd_form_detected = True
            elif any(word in text for word in ['topical', 'cream', 'balm', 'salve', 'lotion', 'rub', 'roll-on', 'roller', 'muscle gel', 'skin gel']):
                rule_tags.append('topical')
                cbd_form_detected = True
            elif any(word in text for word in ['tincture', 'drop', 'drops', 'sublingual', 'extract']):
                rule_tags.append('tincture')
                cbd_form_detected = True
            elif any(word in text for word in ['paste', 'crumble', 'shatter', 'wax', 'concentrate', 'raw paste', 'dab']):
                rule_tags.append('paste')
                cbd_form_detected = True
            elif any(word in text for word in ['shot', 'beverage', 'drink', 'sparkling', 'energy drink', 'soda', 'tea', 'coffee', 'infusion']):
                rule_tags.append('beverage')
                cbd_form_detected = True
            elif any(word in text for word in ['edible', 'cookie', 'brownie', 'chocolate', 'bar', 'snack']):
                rule_tags.append('edible')
                cbd_form_detected = True
            elif any(word in text for word in ['patch', 'transdermal', 'skin patch']):
                rule_tags.append('patch')
                cbd_form_detected = True
            elif any(word in text for word in ['vape', 'cartridge', 'cart', 'disposable', 'e-liquid', 'eliquid']):
                rule_tags.append('vape')
                cbd_form_detected = True
            elif any(word in text for word in ['flower', 'bud', 'hemp flower', 'pre-roll', 'preroll']):
                rule_tags.append('flower')
                cbd_form_detected = True
            
            # Only check for 'oil' if no other form was detected (avoid false positives)
            if not cbd_form_detected and 'oil' in text:
                rule_tags.append('tincture')  # Oil typically means tincture
            
            # NO default fallback - let AI handle ambiguous products
            
            # CBD spectrum type detection - NO default fallback
            if 'full spectrum' in text or 'full-spectrum' in text or 'fullspectrum' in text:
                rule_tags.append('full_spectrum')
            elif 'broad spectrum' in text or 'broad-spectrum' in text or 'broadspectrum' in text:
                rule_tags.append('broad_spectrum')
            elif 'isolate' in text or 'pure cbd' in text:
                rule_tags.append('isolate')
            elif 'cbg' in text and 'cbd' not in text:
                rule_tags.append('cbg')
            elif 'cbda' in text:
                rule_tags.append('cbda')
            # NO default to full_spectrum - let AI determine if ambiguous
            
            mg_matches = re.findall(r'(\d+)mg', text)
            if mg_matches:
                cbd_strength_config = self.approved_tags.get('cbd_strength', {})
                range_config = cbd_strength_config.get('range')
                
                if range_config:
                    # Use range-based validation
                    min_val = range_config.get('min', 0)
                    max_val = range_config.get('max', 50000)
                    unit = range_config.get('unit', 'mg')
                    
                    for mg in mg_matches:
                        try:
                            mg_value = int(mg)
                            if min_val <= mg_value <= max_val:
                                rule_tags.append(f"{mg}{unit}")
                                break
                        except ValueError:
                            continue
                else:
                    # Fallback to tag-based validation (legacy)
                    for mg in mg_matches:
                        cbd_tag = f"{mg}mg"
                        if cbd_tag in cbd_strength_config.get('tags', []):
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
        
        # VG/PG ratio detection - advanced patterns
        ratio_matches = re.findall(r'(\d+)\s*vg\s*[/-]\s*(\d+)\s*pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try alternative format like "50/50 VG/PG"
            ratio_matches = re.findall(r'(\d+)[/-](\d+)\s*vg[/-]pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "VG/PG 50/50" format
            ratio_matches = re.findall(r'vg[/-]pg\s*(\d+)[/-](\d+)', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "50% VG / 50% PG" format
            ratio_matches = re.findall(r'(\d+)%?\s*vg\s*[/-]\s*(\d+)%?\s*pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "VG:PG 50:50" format
            ratio_matches = re.findall(r'vg\s*:\s*pg\s*(\d+)\s*:\s*(\d+)', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "50VG 50PG" format (no separator)
            ratio_matches = re.findall(r'(\d+)\s*vg\s+(\d+)\s*pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try percentage format "50% VG 50% PG"
            percent_matches = re.findall(r'(\d+)%\s*vg.*?(\d+)%\s*pg', text, re.IGNORECASE)
            if percent_matches:
                ratio_matches = percent_matches
        if not ratio_matches:
            # Try "70VG30PG" format (no spaces)
            ratio_matches = re.findall(r'(\d+)vg(\d+)pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "VG 70 / PG 30" format
            ratio_matches = re.findall(r'vg\s+(\d+)[/-]\s*pg\s+(\d+)', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "70/30 VG PG" format
            ratio_matches = re.findall(r'(\d+)[/-](\d+)\s*vg\s*pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "70VG/30PG" format
            ratio_matches = re.findall(r'(\d+)vg[/-](\d+)pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "VG70PG30" format (compact)
            ratio_matches = re.findall(r'vg(\d+)pg(\d+)', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "70-30" with VG/PG context
            if 'vg' in text and 'pg' in text:
                dash_matches = re.findall(r'(\d+)[/-](\d+)', text)
                if dash_matches:
                    ratio_matches = dash_matches
        
        if ratio_matches:
            for vg, pg in ratio_matches:
                # Handle cases where VG/PG might be swapped
                try:
                    vg_val = int(vg)
                    pg_val = int(pg)
                    # Ensure VG >= PG (typical ratios)
                    if pg_val > vg_val:
                        vg, pg = pg, vg
                    ratio = f"{vg}/{pg}"
                    if ratio in self.approved_tags.get('vg_ratio', {}).get('tags', []):
                        rule_tags.append(ratio)
                        break  # Take first valid ratio
                except ValueError:
                    continue
        
        # Pure VG detection
        if not ratio_matches and ('100% vg' in text.lower() or 'pure vg' in text.lower() or 'max vg' in text.lower()):
            rule_tags.append('100/0')
        elif not ratio_matches and 'vg' in text and 'pg' not in text:
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
            
            # Pod capacity detection
            capacity_matches = re.findall(r'(\d+(?:\.\d+)?)\s*ml', text, re.IGNORECASE)
            if capacity_matches:
                capacity_config = self.approved_tags.get('capacity', {})
                for cap in capacity_matches:
                    cap_tag = f"{cap}ml"
                    if cap_tag in capacity_config.get('tags', []):
                        rule_tags.append(cap_tag)
                        break  # Take first valid capacity
        
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
    
    def _process_single_product(self, product, index, total):
        """Process a single product and return result dict. Thread-safe."""
        handle = product.get('Handle', '')
        
        product_dict = {
            'handle': handle,
            'title': product.get('Title', ''),
            'description': product.get('Body (HTML)', ''),
            'option1_name': product.get('Option1 Name', ''),
            'option1_value': product.get('Option1 Value', ''),
            'option2_name': product.get('Option2 Name', ''),
            'option2_value': product.get('Option2 Value', ''),
            'option3_name': product.get('Option3 Name', ''),
            'option3_value': product.get('Option3 Value', ''),
        }
        
        # Get rule-based tags first to determine category
        rule_tags, forced_category = self.get_rule_based_tags(
            product_dict['handle'], product_dict['title'], product_dict['description']
        )
        
        # Determine preliminary product category for AI prompting
        preliminary_category = None
        max_priority = -1
        for tag in rule_tags:
            if tag in self.category_tags:
                priority = self.category_priority.get(tag, 0)
                if priority > max_priority:
                    max_priority = priority
                    preliminary_category = tag
        
        # Override with forced category from handle
        if forced_category:
            preliminary_category = forced_category
        
        # OPTIMIZATION: Skip AI for high-confidence rule matches
        # Skip AI if we have: category + at least 2 other tags from rules
        ai_tags = []
        ai_metadata = {
            'prompt': None,
            'model_output': None,
            'confidence': None,
            'reasoning': None,
            'skipped_ai': False
        }
        
        non_category_rule_tags = [t for t in rule_tags if t not in self.category_tags]
        skip_ai = (
            preliminary_category is not None and 
            len(non_category_rule_tags) >= 2 and
            not self.no_ai
        )
        
        if skip_ai:
            # High-confidence rule match - skip expensive AI call
            ai_metadata['skipped_ai'] = True
            ai_metadata['confidence'] = 0.85  # Synthetic confidence for rule-only
            ai_metadata['reasoning'] = f"Skipped AI: Strong rule match ({len(rule_tags)} tags including category)"
            self.logger.debug(f"Skipping AI for {handle}: {rule_tags}")
            # Track skip count (thread-safe)
            if self._lock:
                with self._lock:
                    self._ai_skipped_count += 1
            else:
                self._ai_skipped_count += 1
        else:
            # Get AI suggestions with category-aware prompting
            ai_tags, ai_metadata = self.get_ai_tags(product_dict, category=preliminary_category)
        
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
                            inferred_tags.append('restricted-direct-to-lung')
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
            
            # Special handling for range-based categories
            if not cat:
                if re.match(r'^\d+mg$', tag):
                    cbd_config = self.approved_tags.get('cbd_strength', {})
                    if cbd_config.get('range') and product_category == 'CBD':
                        cat = 'cbd_strength'
            
            if cat == 'category':
                continue
            cat_data = self.approved_tags.get(cat, {})
            applies_to = cat_data.get('applies_to', ['all']) if isinstance(cat_data, dict) else ['all']
            if 'all' in applies_to or product_category in applies_to:
                tag_by_cat[cat].append(tag)
        
        # Sort tags within each category
        for cat in tag_by_cat:
            if cat == 'accessory_type':
                tag_by_cat[cat].sort(key=lambda t: (0 if t == 'charger' else 1 if t == 'battery' else 2, -len(t)))
            else:
                tag_by_cat[cat].sort(key=len, reverse=True)
        
        final_tags = []
        for cat, tags in tag_by_cat.items():
            final_tags.extend(tags[:1])  # Keep at most one per category
        
        # Update performance counter (thread-safe)
        if self._lock:
            with self._lock:
                self._processed_count += 1
                count = self._processed_count
        else:
            self._processed_count += 1
            count = self._processed_count
        
        # Log progress periodically
        if count % 10 == 0 or count == total:
            elapsed = time.time() - self._start_time
            rate = count / (elapsed / 60) if elapsed > 0 else 0
            self.logger.info(f"Progress: {count}/{total} ({count/total*100:.1f}%) | Rate: {rate:.1f} products/min")
        
        return {
            'handle': handle,
            'product': product,
            'product_dict': product_dict,
            'rule_tags': rule_tags,
            'ai_tags': ai_tags,
            'final_tags': final_tags,
            'forced_category': forced_category,
            'product_category': product_category,
            'ai_metadata': ai_metadata,
            'tag_by_cat': dict(tag_by_cat),
        }
    
    def _log_performance_summary(self, total, start_time, ai_skipped=0):
        """Log final performance statistics"""
        elapsed = time.time() - start_time
        rate = total / (elapsed / 60) if elapsed > 0 else 0
        ai_calls = total - ai_skipped
        skip_pct = (ai_skipped / total * 100) if total > 0 else 0
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info("PERFORMANCE SUMMARY")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"  Total products processed: {total}")
        self.logger.info(f"  Total time: {elapsed:.1f} seconds ({elapsed/60:.2f} minutes)")
        self.logger.info(f"  Average rate: {rate:.1f} products/minute")
        self.logger.info(f"  Workers: {self.max_workers if self.parallel_processing else 1}")
        self.logger.info(f"  Parallel processing: {'enabled' if self.parallel_processing else 'disabled'}")
        self.logger.info(f"{'─'*60}")
        self.logger.info(f"  AI calls made: {ai_calls}")
        self.logger.info(f"  AI calls skipped: {ai_skipped} ({skip_pct:.1f}%)")
        self.logger.info(f"{'='*60}\n")
    
    def tag_products(self, input_file, output_file=None, limit=None):
        """Tag products from input CSV with optional parallel processing"""
        
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
        
        # Load already processed products if resuming
        processed_handles = set()
        if self.audit_db and self.run_id:
            conn = self.audit_db._get_connection()
            cur = conn.cursor()
            cur.execute('SELECT handle FROM products WHERE run_id = ?', (self.run_id,))
            processed_handles = {row[0] for row in cur.fetchall()}
            self.logger.info(f"Found {len(processed_handles)} already processed products")
        
        # Filter out already processed
        products_to_process = [p for p in products if p.get('Handle', '') not in processed_handles]
        skipped_count = len(products) - len(products_to_process)
        if skipped_count > 0:
            self.logger.info(f"Skipping {skipped_count} already processed products")
        
        total = len(products_to_process)
        if total == 0:
            self.logger.info("No products to process")
            return
        
        # Initialize performance tracking
        self._processed_count = 0
        self._ai_skipped_count = 0
        self._start_time = time.time()
        self._lock = threading.Lock()
        
        self.logger.info(f"Processing {total} products with {'parallel' if self.parallel_processing else 'sequential'} mode")
        if self.parallel_processing:
            self.logger.info(f"Using {self.max_workers} workers")
        
        # Process products
        results = []
        
        if self.parallel_processing and total > 1:
            # Parallel processing with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._process_single_product, product, i, total): (i, product)
                    for i, product in enumerate(products_to_process, 1)
                }
                
                for future in as_completed(futures):
                    i, product = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        handle = product.get('Handle', 'unknown')
                        self.logger.error(f"Error processing {handle}: {e}")
        else:
            # Sequential processing
            for i, product in enumerate(products_to_process, 1):
                try:
                    result = self._process_single_product(product, i, total)
                    results.append(result)
                except Exception as e:
                    handle = product.get('Handle', 'unknown')
                    self.logger.error(f"Error processing {handle}: {e}")
        
        # Log performance summary
        self._log_performance_summary(len(results), self._start_time, self._ai_skipped_count)
        
        # Collect tagged and untagged products
        tagged_products = []
        untagged_products = []
        untagged_originals = []
        
        for result in results:
            handle = result['handle']
            product = result['product']
            product_dict = result['product_dict']
            rule_tags = result['rule_tags']
            ai_tags = result['ai_tags']
            final_tags = result['final_tags']
            forced_category = result['forced_category']
            product_category = result['product_category']
            ai_metadata = result['ai_metadata']
            
            self.logger.debug(f"Product: {handle} | Category: {product_category} | Final tags: {final_tags}")
            
            # Insert into audit DB with AI metadata (thread-safe)
            if self.audit_db and self.run_id:
                with self._lock:
                    self.audit_db.insert_product(
                        run_id=self.run_id,
                        handle=handle,
                        title=product_dict['title'],
                        csv_type=self.default_product_type or '',
                        effective_type=product_category or '',
                        description=product_dict['description'],
                        rule_tags=rule_tags,
                        ai_tags=ai_tags,
                        final_tags=final_tags,
                        forced_category=forced_category,
                        device_evidence=bool('device' in final_tags),
                        skipped=0,
                        ai_prompt=ai_metadata.get('prompt'),
                        ai_model_output=ai_metadata.get('model_output'),
                        ai_confidence=ai_metadata.get('confidence'),
                        ai_reasoning=ai_metadata.get('reasoning')
                    )
            
            # Create output product
            product_output = {
                'Handle': product.get('Handle', ''),
                'Variant SKU': product.get('Variant SKU', ''),
                'Tags': ', '.join(final_tags)
            }
            
            if product_output['Tags'].strip():
                tagged_products.append(product_output)
            else:
                untagged_products.append(product_output)
                untagged_originals.append(product)
        
        # Complete the run if audit DB is used
        if self.audit_db and self.run_id:
            self.audit_db.complete_run(self.run_id)
            self.logger.info(f"Completed run {self.run_id}")
        
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
        self.logger.info(f"  Tagged: {len(tagged_products)}, Untagged: {len(untagged_products)}")
        
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
                
                # Determine preliminary category for secondary AI
                preliminary_category_secondary = None
                max_priority_secondary = -1
                for tag in rule_tags_secondary:
                    if tag in self.category_tags:
                        priority = self.category_priority.get(tag, 0)
                        if priority > max_priority_secondary:
                            max_priority_secondary = priority
                            preliminary_category_secondary = tag
                
                # Override with forced category
                if forced_category_secondary:
                    preliminary_category_secondary = forced_category_secondary
                
                # Get secondary AI tags with category-aware prompting
                ai_tags_secondary, _ = self.get_ai_tags(handle, title, description, category=preliminary_category_secondary)
                
                # Combine (use secondary results, not outer variables)
                all_tags = list(set(ai_tags_secondary + rule_tags_secondary))
                
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
                                    inferred_tags.append('restricted-direct-to-lung')
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
        verbose=args.verbose,
        default_product_type=args.type,
        audit_db_path=args.audit_db,
        run_id=args.run_id,
        max_workers=args.workers,
        no_parallel=args.no_parallel
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
