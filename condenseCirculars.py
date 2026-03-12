import json
import os
import argparse

def condense_circulars(circulars_folder, output_file, keys_to_include=None):
    circulars_dict = {}
    for filename in os.listdir(circulars_folder):
        if filename.endswith('.json'):
            with open(os.path.join(circulars_folder, filename), 'r') as f:
                circular = json.load(f)
                circular_id = circular.get('circularID', filename[:-5])  # Use filename without .json as fallback
                if keys_to_include:
                    circular = {key: circular[key] for key in keys_to_include if key in circular}
                circulars_dict[circular_id] = circular

    with open(output_file, 'w') as f:
        json.dump(circulars_dict, f, indent=4)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Condense circulars into one JSON file.')
    parser.add_argument('--folder', '-f', type=str, default='./archive', help='Path to the folder containing circular JSON files.')
    parser.add_argument('--output_file', '-o', type=str, default='circulars.json', help='Name of the output JSON file (default: circulars.json).')
    parser.add_argument('--keys', '-k', nargs='+', help='List of keys to include in the output (default: include all keys).')
    
    args = parser.parse_args()
    
    condense_circulars(args.folder, args.output_file, args.keys)