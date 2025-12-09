#!/usr/bin/env python3
"""
QLoRA Training Script for Product Tagging

Fine-tunes Llama 3.1 8B Instruct with QLoRA for vaping/CBD product tagging.
Designed for Vast.ai GPU instances (24GB+ VRAM).

Usage:
  # Export training data as JSONL
  python train_tag_model.py --export --input audit_training_dataset.csv --output training_data.jsonl

  # Train with QLoRA (on Vast.ai)
  python train_tag_model.py --train --input training_data.jsonl --push-to-hub

  # Generate predictions for evaluation
  python train_tag_model.py --generate-predictions --model-path ./model_output --input test.jsonl --output predictions.jsonl

  # Evaluate predictions
  python train_tag_model.py --evaluate --predictions predictions.jsonl --corrections audit_training_dataset.csv
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('config.env')
except ImportError:
    pass


def get_config():
    """Load configuration from environment variables"""
    return {
        # Model
        'base_model': os.getenv('BASE_MODEL', 'meta-llama/Meta-Llama-3.1-8B-Instruct'),
        'model_backend': os.getenv('MODEL_BACKEND', 'ollama'),
        
        # HF Hub
        'hf_token': os.getenv('HF_TOKEN'),
        'hf_repo_id': os.getenv('HF_REPO_ID'),
        
        # QLoRA
        'quantization_bits': int(os.getenv('QUANTIZATION_BITS', '4')),
        'lora_r': int(os.getenv('LORA_R', '64')),
        'lora_alpha': int(os.getenv('LORA_ALPHA', '128')),
        'lora_dropout': float(os.getenv('LORA_DROPOUT', '0.05')),
        
        # Training
        'train_val_split': float(os.getenv('TRAIN_VAL_SPLIT', '0.8')),
        'max_seq_length': int(os.getenv('MAX_SEQ_LENGTH', '2048')),
        'learning_rate': float(os.getenv('LEARNING_RATE', '2e-4')),
        'warmup_ratio': float(os.getenv('WARMUP_RATIO', '0.03')),
        'gradient_accumulation_steps': int(os.getenv('GRADIENT_ACCUMULATION_STEPS', '4')),
    }


def load_audit_csv(csv_path: str) -> List[Dict]:
    """Load audit training dataset CSV"""
    products = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(row)
    return products


def create_training_prompt(product: Dict, approved_tags_path: str = 'approved_tags.json') -> str:
    """Create a training prompt from product data"""
    # Load approved tags for context
    approved_tags = {}
    if os.path.exists(approved_tags_path):
        with open(approved_tags_path) as f:
            approved_tags = json.load(f)
            approved_tags.pop('rules', None)

    handle = product.get('Handle', '')
    title = product.get('Title', '')
    description = product.get('Description', '')[:500] if product.get('Description') else ''

    prompt = f"""You are a product tagging expert. Analyze this product and suggest tags from the approved vocabulary.

PRODUCT HANDLE: {handle}
PRODUCT TITLE: {title}
DESCRIPTION: {description}

APPROVED TAGS:
{json.dumps(approved_tags, indent=2)}

Respond with ONLY a JSON object:
{{"tags": ["tag1", "tag2"], "confidence": 0.95, "reasoning": "brief explanation"}}"""

    return prompt


def create_completion(product: Dict) -> str:
    """Create a completion (expected output) from product data"""
    correction = product.get('Correction', '').strip()
    if correction:
        tags = [t.strip() for t in correction.split(',') if t.strip()]
    else:
        final_tags = product.get('Final Tags', '')
        tags = [t.strip() for t in final_tags.split(',') if t.strip()]

    # Vary confidence based on whether it's a correction or original
    confidence = 0.95 if correction else 0.85
    
    completion = json.dumps({
        "tags": tags,
        "confidence": confidence,
        "reasoning": "Tags assigned based on product analysis"
    })
    return completion


def export_jsonl(products: List[Dict], output_path: str, only_with_corrections: bool = False) -> int:
    """Export training data as JSONL for fine-tuning"""
    count = 0
    with open(output_path, 'w', encoding='utf-8') as f:
        for product in products:
            if only_with_corrections and not product.get('Correction', '').strip():
                continue

            prompt = create_training_prompt(product)
            completion = create_completion(product)

            # Chat format for instruction-tuned models
            record = {
                "messages": [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": completion}
                ],
                "metadata": {
                    "handle": product.get('Handle', ''),
                    "category": product.get('Category', ''),
                    "has_correction": bool(product.get('Correction', '').strip())
                }
            }
            f.write(json.dumps(record) + '\n')
            count += 1

    print(f"✅ Exported {count} training examples to {output_path}")
    return count


def prepare_datasets(jsonl_path: str, val_split: float = 0.2) -> Tuple:
    """Load JSONL and split into train/validation sets stratified by category"""
    try:
        from datasets import Dataset
        from sklearn.model_selection import train_test_split
    except ImportError:
        print("❌ Missing dependencies. Install with: pip install datasets scikit-learn")
        sys.exit(1)
    
    # Load data
    data = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    
    if not data:
        print("❌ No training data found")
        sys.exit(1)
    
    # Extract categories for stratification
    categories = [d.get('metadata', {}).get('category', 'unknown') for d in data]
    
    # Check if stratification is possible (need at least 2 examples per category)
    from collections import Counter
    category_counts = Counter(categories)
    min_count = min(category_counts.values())
    can_stratify = len(set(categories)) > 1 and len(data) >= 10 and min_count >= 2
    
    # Stratified split if possible
    if can_stratify:
        print(f"   Using stratified split ({len(set(categories))} categories)")
        train_data, val_data = train_test_split(
            data, test_size=val_split, stratify=categories, random_state=42
        )
    else:
        print(f"   Using random split (stratification not possible: min_count={min_count})")
        train_data, val_data = train_test_split(
            data, test_size=val_split, random_state=42
        )
    
    # Convert to datasets
    def format_for_training(examples):
        """Format examples for SFTTrainer"""
        texts = []
        for msg_list in examples['messages']:
            text = ""
            for msg in msg_list:
                if msg['role'] == 'user':
                    text += f"<|user|>\n{msg['content']}\n"
                elif msg['role'] == 'assistant':
                    text += f"<|assistant|>\n{msg['content']}\n"
            texts.append(text)
        return {"text": texts}
    
    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)
    
    train_dataset = train_dataset.map(format_for_training, batched=True, remove_columns=['metadata'])
    val_dataset = val_dataset.map(format_for_training, batched=True, remove_columns=['metadata'])
    
    print(f"📊 Dataset split: {len(train_dataset)} train, {len(val_dataset)} validation")
    return train_dataset, val_dataset


def run_qlora_training(
    jsonl_path: str,
    output_dir: str,
    epochs: int,
    batch_size: int,
    push_to_hub: bool = False,
    checkpoint_path: Optional[str] = None
):
    """Run QLoRA fine-tuning with Llama 3.1 8B"""
    
    config = get_config()
    
    # Check for required dependencies
    try:
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import SFTTrainer
    except ImportError as e:
        print(f"❌ Missing training dependencies: {e}")
        print("   Install with: pip install torch transformers peft trl bitsandbytes")
        sys.exit(1)
    
    # Check GPU
    if not torch.cuda.is_available():
        print("❌ CUDA not available. Training requires a GPU.")
        sys.exit(1)
    
    print("\n🚀 QLoRA TRAINING")
    print("=" * 60)
    print(f"   Base model: {config['base_model']}")
    print(f"   Quantization: {config['quantization_bits']}-bit")
    print(f"   LoRA rank: {config['lora_r']}, alpha: {config['lora_alpha']}")
    print(f"   Training data: {jsonl_path}")
    print(f"   Output: {output_dir}")
    print(f"   GPU: {torch.cuda.get_device_name(0)}")
    print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # HF Hub login
    if push_to_hub:
        if not config['hf_token']:
            print("❌ HF_TOKEN required for --push-to-hub")
            sys.exit(1)
        from huggingface_hub import login
        login(token=config['hf_token'])
        print(f"   HF Hub: {config['hf_repo_id']}")
    
    # Prepare datasets
    train_dataset, val_dataset = prepare_datasets(jsonl_path, 1 - config['train_val_split'])
    
    # Quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=(config['quantization_bits'] == 4),
        load_in_8bit=(config['quantization_bits'] == 8),
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    
    # Load model
    print(f"\n📥 Loading model: {config['base_model']}")
    model = AutoModelForCausalLM.from_pretrained(
        config['base_model'],
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(config['base_model'], trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(model)
    
    # LoRA config
    lora_config = LoraConfig(
        r=config['lora_r'],
        lora_alpha=config['lora_alpha'],
        lora_dropout=config['lora_dropout'],
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    
    # Apply LoRA
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=config['gradient_accumulation_steps'],
        learning_rate=config['learning_rate'],
        warmup_ratio=config['warmup_ratio'],
        logging_steps=10,
        save_steps=100,
        eval_strategy="steps",
        eval_steps=100,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        bf16=True,
        optim="paged_adamw_8bit",
        report_to=["tensorboard"],
        push_to_hub=push_to_hub,
        hub_model_id=config['hf_repo_id'] if push_to_hub else None,
        hub_token=config['hf_token'] if push_to_hub else None,
    )
    
    # Resume from checkpoint
    if checkpoint_path and os.path.exists(checkpoint_path):
        print(f"   Resuming from: {checkpoint_path}")
    
    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=config['max_seq_length'],
        packing=False,
    )
    
    # Train
    print("\n🏋️ Starting training...")
    trainer.train(resume_from_checkpoint=checkpoint_path)
    
    # Save final model
    print(f"\n💾 Saving model to {output_dir}")
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)
    
    # Push to Hub
    if push_to_hub:
        print(f"\n☁️ Pushing to HF Hub: {config['hf_repo_id']}")
        trainer.push_to_hub()
    
    print("\n✅ Training complete!")
    return output_dir


def generate_predictions(
    model_path: str,
    input_jsonl: str,
    output_jsonl: str,
):
    """Generate predictions using fine-tuned model"""
    config = get_config()
    
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        sys.exit(1)
    
    print("\n🔮 GENERATING PREDICTIONS")
    print("=" * 60)
    print(f"   Model: {model_path}")
    print(f"   Input: {input_jsonl}")
    print(f"   Output: {output_jsonl}")
    
    # Load base model with quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    
    base_model = AutoModelForCausalLM.from_pretrained(
        config['base_model'],
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    
    # Load LoRA adapters
    model = PeftModel.from_pretrained(base_model, model_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    model.eval()
    
    # Process inputs
    results = []
    with open(input_jsonl, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        data = json.loads(line)
        messages = data.get('messages', [])
        
        # Get user prompt
        user_msg = next((m['content'] for m in messages if m['role'] == 'user'), '')
        
        # Format input
        input_text = f"<|user|>\n{user_msg}\n<|assistant|>\n"
        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        
        # Parse response
        try:
            prediction = json.loads(response.strip())
        except json.JSONDecodeError:
            prediction = {"tags": [], "confidence": 0.0, "reasoning": "Parse error"}
        
        results.append({
            "metadata": data.get('metadata', {}),
            "prediction": prediction,
        })
        
        if (i + 1) % 10 == 0:
            print(f"   Processed {i + 1}/{len(lines)}")
    
    # Save predictions
    with open(output_jsonl, 'w') as f:
        for r in results:
            f.write(json.dumps(r) + '\n')
    
    print(f"\n✅ Predictions saved to {output_jsonl}")


def evaluate_predictions(predictions_path: str, corrections_csv: str) -> Dict:
    """Evaluate model predictions against corrections"""
    corrections = {}
    with open(corrections_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            handle = row.get('Handle', '')
            correction = row.get('Correction', '').strip()
            if correction:
                corrections[handle] = {t.strip() for t in correction.split(',') if t.strip()}
            else:
                final_tags = row.get('Final Tags', '')
                corrections[handle] = {t.strip() for t in final_tags.split(',') if t.strip()}

    predictions = {}
    with open(predictions_path, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            handle = record.get('metadata', {}).get('handle', '')
            pred = record.get('prediction', {})
            if isinstance(pred, str):
                try:
                    pred = json.loads(pred)
                except json.JSONDecodeError:
                    pred = {}
            tags = set(pred.get('tags', []))
            predictions[handle] = tags

    total = 0
    exact_match = 0
    partial_match = 0
    precision_sum = 0
    recall_sum = 0
    f1_sum = 0
    per_product = []

    for handle, true_tags in corrections.items():
        if handle not in predictions:
            continue

        pred_tags = predictions[handle]
        total += 1

        if pred_tags == true_tags:
            exact_match += 1

        intersection = pred_tags & true_tags
        if intersection:
            partial_match += 1

        precision = len(intersection) / len(pred_tags) if pred_tags else 0
        recall = len(intersection) / len(true_tags) if true_tags else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        precision_sum += precision
        recall_sum += recall
        f1_sum += f1

        per_product.append({
            'handle': handle,
            'true_tags': sorted(true_tags),
            'pred_tags': sorted(pred_tags),
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'exact_match': pred_tags == true_tags
        })

    return {
        'total_evaluated': total,
        'exact_match_count': exact_match,
        'exact_match_rate': exact_match / total if total > 0 else 0,
        'partial_match_count': partial_match,
        'partial_match_rate': partial_match / total if total > 0 else 0,
        'avg_precision': precision_sum / total if total > 0 else 0,
        'avg_recall': recall_sum / total if total > 0 else 0,
        'avg_f1': f1_sum / total if total > 0 else 0,
        'per_product': per_product
    }


def print_evaluation_report(results: Dict):
    """Print evaluation report"""
    print("\n📊 EVALUATION REPORT")
    print("=" * 60)
    print(f"Total products evaluated: {results['total_evaluated']}")
    print("\n🎯 ACCURACY METRICS")
    print(f"   Exact match rate: {results['exact_match_rate']*100:.1f}% ({results['exact_match_count']}/{results['total_evaluated']})")
    print(f"   Partial match rate: {results['partial_match_rate']*100:.1f}% ({results['partial_match_count']}/{results['total_evaluated']})")
    print("\n📈 AGGREGATE METRICS")
    print(f"   Average Precision: {results['avg_precision']*100:.1f}%")
    print(f"   Average Recall: {results['avg_recall']*100:.1f}%")
    print(f"   Average F1 Score: {results['avg_f1']*100:.1f}%")

    if results['per_product']:
        print("\n⚠️  LOWEST F1 SCORES (Bottom 5)")
        sorted_products = sorted(results['per_product'], key=lambda x: x['f1'])
        for p in sorted_products[:5]:
            print(f"   {p['handle']}: F1={p['f1']*100:.1f}% | True: {p['true_tags']} | Pred: {p['pred_tags']}")


def save_evaluation_csv(results: Dict, output_path: str):
    """Save detailed evaluation results to CSV"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Handle', 'True Tags', 'Predicted Tags', 'Precision', 'Recall', 'F1', 'Exact Match'])
        for p in results['per_product']:
            writer.writerow([
                p['handle'],
                ','.join(p['true_tags']),
                ','.join(p['pred_tags']),
                f"{p['precision']:.3f}",
                f"{p['recall']:.3f}",
                f"{p['f1']:.3f}",
                'Yes' if p['exact_match'] else 'No'
            ])
    print(f"\n📄 Detailed evaluation saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='QLoRA Training for Product Tagging (Vast.ai)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export training data
  python train_tag_model.py --export --input audit_training_dataset.csv --output training_data.jsonl

  # Train on Vast.ai (24GB+ VRAM)
  python train_tag_model.py --train --input training_data.jsonl --epochs 3 --push-to-hub

  # Generate predictions
  python train_tag_model.py --generate-predictions --model-path ./model_output --input test.jsonl --output predictions.jsonl

  # Evaluate
  python train_tag_model.py --evaluate --predictions predictions.jsonl --corrections audit_training_dataset.csv
        """
    )

    # Modes
    parser.add_argument('--export', action='store_true', help='Export CSV to JSONL')
    parser.add_argument('--train', action='store_true', help='Run QLoRA training')
    parser.add_argument('--generate-predictions', action='store_true', help='Generate predictions')
    parser.add_argument('--evaluate', action='store_true', help='Evaluate predictions')

    # Input/Output
    parser.add_argument('--input', '-i', type=str, help='Input file (CSV for export, JSONL for train/predict)')
    parser.add_argument('--output', '-o', type=str, default='training_data.jsonl', help='Output file')
    parser.add_argument('--only-corrections', action='store_true', help='Export only products with corrections')

    # Training
    parser.add_argument('--epochs', type=int, default=3, help='Training epochs')
    parser.add_argument('--batch-size', type=int, default=4, help='Batch size')
    parser.add_argument('--checkpoint', type=str, help='Resume from checkpoint')
    parser.add_argument('--output-dir', type=str, default='./model_output', help='Model output directory')
    parser.add_argument('--push-to-hub', action='store_true', help='Push to HF Hub after training')

    # Prediction
    parser.add_argument('--model-path', type=str, help='Path to fine-tuned model')

    # Evaluation
    parser.add_argument('--predictions', type=str, help='Predictions JSONL')
    parser.add_argument('--corrections', type=str, help='Corrections CSV')
    parser.add_argument('--eval-output', type=str, default='evaluation_results.csv', help='Evaluation output')

    args = parser.parse_args()

    # Export mode
    if args.export:
        if not args.input:
            print("❌ --export requires --input CSV file")
            sys.exit(1)
        print(f"📂 Loading audit data from {args.input}")
        products = load_audit_csv(args.input)
        print(f"   Loaded {len(products)} products")
        export_jsonl(products, args.output, only_with_corrections=args.only_corrections)

    # Training mode
    elif args.train:
        if not args.input:
            print("❌ --train requires --input JSONL file")
            sys.exit(1)
        run_qlora_training(
            jsonl_path=args.input,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            push_to_hub=args.push_to_hub,
            checkpoint_path=args.checkpoint,
        )

    # Prediction mode
    elif args.generate_predictions:
        if not args.model_path or not args.input:
            print("❌ --generate-predictions requires --model-path and --input")
            sys.exit(1)
        generate_predictions(args.model_path, args.input, args.output)

    # Evaluation mode
    elif args.evaluate:
        if not args.predictions or not args.corrections:
            print("❌ --evaluate requires --predictions and --corrections")
            sys.exit(1)
        print(f"📂 Evaluating predictions from {args.predictions}")
        results = evaluate_predictions(args.predictions, args.corrections)
        print_evaluation_report(results)
        save_evaluation_csv(results, args.eval_output)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
