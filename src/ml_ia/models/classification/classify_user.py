#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import joblib

sys.path.append(str(Path(__file__).parent.parent.parent))

def load_model_components(model_dir: Path) -> tuple:
    try:
        model_files = list(model_dir.glob("best_classifier_*.joblib"))
        if not model_files:
            raise FileNotFoundError(f"No model files found in {model_dir}")
        
        latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
        
        timestamp = latest_model.stem.split('_')[-1]
        scaler_path = model_dir / f"scaler_{timestamp}.joblib"
        metadata_path = model_dir / f"metadata_{timestamp}.json"
        
        if not scaler_path.exists():
            raise FileNotFoundError(f"Scaler file not found: {scaler_path}")
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        
        model = joblib.load(latest_model)
        scaler = joblib.load(scaler_path)
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        return model, scaler, metadata, latest_model.name
        
    except Exception as e:
        print(f"Error loading model components: {e}")
        sys.exit(1)

def validate_user_data(user_data: Dict, required_features: List[str]) -> Dict:
    validated_data = {}
    
    for feature in required_features:
        if feature in user_data:
            value = user_data[feature]
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    print(f"Warning: Could not convert {feature} value '{value}' to number, using 0")
                    value = 0.0
            validated_data[feature] = value
        elif not any(df in feature for df in ['events_per_day', 'spend_per_event', 'view_to_purchase_ratio']):
            print(f"Warning: Missing feature '{feature}', using 0")
            validated_data[feature] = 0.0
    
    if 'events_per_day' not in validated_data and 'total_events' in validated_data and 'days_since_last_event' in validated_data:
        days = max(validated_data['days_since_last_event'], 1)
        validated_data['events_per_day'] = validated_data['total_events'] / days
    
    if 'spend_per_event' not in validated_data and 'total_spent' in validated_data and 'total_events' in validated_data:
        events = max(validated_data['total_events'], 1)
        validated_data['spend_per_event'] = validated_data['total_spent'] / events
    
    if 'view_to_purchase_ratio' not in validated_data and 'total_views' in validated_data and 'total_purchases' in validated_data:
        purchases = max(validated_data['total_purchases'], 1)
        validated_data['view_to_purchase_ratio'] = validated_data['total_views'] / purchases
    
    return validated_data

def classify_user(user_data: Dict, model, scaler, metadata: Dict) -> Dict:
    validated_data = validate_user_data(user_data, metadata['features'])
    
    features = []
    for feature_name in metadata['features']:
        features.append(validated_data.get(feature_name, 0.0))
    
    features_array = np.array(features).reshape(1, -1)
    
    features_array = np.nan_to_num(features_array, nan=0.0, posinf=0.0, neginf=0.0)
    
    features_scaled = scaler.transform(features_array)
    
    predicted_segment = model.predict(features_scaled)[0]
    prediction_proba = model.predict_proba(features_scaled)[0]
    
    results = {
        'predicted_segment': int(predicted_segment),
        'confidence': float(np.max(prediction_proba)),
        'all_probabilities': {
            str(cls): float(prob) for cls, prob in zip(metadata['classes'], prediction_proba)
        },
        'model_name': metadata['model_name'],
        'model_accuracy': metadata['accuracy'],
        'features_used': metadata['features'],
        'input_data': validated_data
    }
    
    return results

def classify_batch(users_data: List[Dict], model, scaler, metadata: Dict) -> List[Dict]:
    results = []
    
    for i, user_data in enumerate(users_data):
        try:
            result = classify_user(user_data, model, scaler, metadata)
            result['user_index'] = i
            results.append(result)
        except Exception as e:
            print(f"Error classifying user {i}: {e}")
            results.append({
                'user_index': i,
                'error': str(e),
                'predicted_segment': -1
            })
    
    return results

def interactive_classification(model, scaler, metadata: Dict):
    print("\n" + "="*60)
    print("INTERACTIVE USER CLASSIFICATION")
    print("="*60)
    print(f"\nModel: {metadata['model_name']}")
    print(f"Accuracy: {metadata['accuracy']:.4f}")
    print(f"Features required: {', '.join(metadata['features'])}")
    print("\nEnter 'quit' to exit\n")
    
    while True:
        print("\nEnter user data (feature=value format, one per line):")
        user_data = {}
        
        for feature in metadata['features']:
            value = input(f"{feature}: ").strip()
            if value.lower() == 'quit':
                return
            if value:
                try:
                    user_data[feature] = float(value)
                except ValueError:
                    print(f"Invalid number for {feature}, using 0")
                    user_data[feature] = 0.0
            else:
                user_data[feature] = 0.0
        
        result = classify_user(user_data, model, scaler, metadata)
        
        print("\n" + "-"*40)
        print("CLASSIFICATION RESULT")
        print("-"*40)
        print(f"Predicted Segment: {result['predicted_segment']}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Model: {result['model_name']}")
        
        print("\nAll Probabilities:")
        for segment, prob in result['all_probabilities'].items():
            print(f"  Segment {segment}: {prob:.2%}")
        
        continue_input = input("\nClassify another user? (y/n): ").strip().lower()
        if continue_input != 'y':
            break

def main():
    parser = argparse.ArgumentParser(description='Classify users into segments')
    parser.add_argument('--user-data', type=str, help='JSON file with user data')
    parser.add_argument('--batch', type=str, help='JSON file with batch of users')
    parser.add_argument('--interactive', action='store_true', help='Interactive classification mode')
    parser.add_argument('--model-dir', type=str, default='saved_models', help='Directory containing saved models')
    
    args = parser.parse_args()
    
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        print(f"Model directory not found: {model_dir}")
        print("Please ensure models are trained and saved first.")
        sys.exit(1)
    
    model, scaler, metadata, model_filename = load_model_components(model_dir)
    
    print(f"Loaded model: {model_filename}")
    print(f"Model type: {metadata['model_name']}")
    print(f"Accuracy: {metadata['accuracy']:.4f}")
    
    if args.interactive:
        interactive_classification(model, scaler, metadata)
    
    elif args.user_data:
        try:
            with open(args.user_data, 'r') as f:
                user_data = json.load(f)
            
            result = classify_user(user_data, model, scaler, metadata)
            
            print("\nClassification Results:")
            print(json.dumps(result, indent=2))
            
            output_file = Path(args.user_data).with_suffix('.results.json')
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nResults saved to: {output_file}")
            
        except Exception as e:
            print(f"Error processing user data: {e}")
            sys.exit(1)
    
    elif args.batch:
        try:
            with open(args.batch, 'r') as f:
                users_data = json.load(f)
            
            if not isinstance(users_data, list):
                print("Batch file should contain a list of user dictionaries")
                sys.exit(1)
            
            results = classify_batch(users_data, model, scaler, metadata)
            
            successful = [r for r in results if 'error' not in r]
            failed = [r for r in results if 'error' in r]
            
            print(f"\nBatch Classification Summary:")
            print(f"Total users: {len(results)}")
            print(f"Successful: {len(successful)}")
            print(f"Failed: {len(failed)}")
            
            if successful:
                segment_counts = {}
                for result in successful:
                    segment = result['predicted_segment']
                    segment_counts[segment] = segment_counts.get(segment, 0) + 1
                
                print("\nSegment Distribution:")
                for segment, count in sorted(segment_counts.items()):
                    print(f"  Segment {segment}: {count} users")
            
            output_file = Path(args.batch).with_suffix('.results.json')
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {output_file}")
            
        except Exception as e:
            print(f"Error processing batch data: {e}")
            sys.exit(1)
    
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python classify_user.py --interactive")
        print("  python classify_user.py --user-data user.json")
        print("  python classify_user.py --batch users.json")

if __name__ == "__main__":
    main()