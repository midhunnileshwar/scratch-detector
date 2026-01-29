import zipfile
import json
import os
import difflib
from itertools import combinations

def extract_code_signature(file_path):
    """
    Opens a .sb3 file and creates a text signature of the logic inside.
    It ignores visual placement (x,y) and IDs, focusing only on 
    WHAT the blocks do (opcode) and their parameters (inputs).
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            if 'project.json' not in z.namelist():
                return ""
            
            data = json.loads(z.read('project.json'))
            
            # We will build a list of all "logic" found in the project
            code_elements = []

            # Iterate through all targets (The Stage and every Sprite)
            for target in data.get('targets', []):
                blocks = target.get('blocks', {})
                
                # If blocks is a list (rare, usually dict), skip complex parsing
                if not isinstance(blocks, dict):
                    continue

                for block_id, block_data in blocks.items():
                    # extract the block type (e.g., "event_whenflagclicked")
                    opcode = block_data.get('opcode', '')
                    
                    # We skip "shadow" blocks which are just menu items
                    if not block_data.get('shadow', False):
                        # We collect the Opcode and the Inputs (values)
                        # We ignore 'parent', 'next', 'x', 'y' (visual/structure stuff)
                        inputs = str(block_data.get('inputs', ''))
                        fields = str(block_data.get('fields', ''))
                        
                        # Create a string representing this single block of logic
                        block_signature = f"{opcode}|{inputs}|{fields}"
                        code_elements.append(block_signature)

            # Sort the elements to ensure order doesn't confuse the comparison
            # (Since Scratch saves blocks in random dictionary order)
            code_elements.sort()
            
            return "\n".join(code_elements)

    except (zipfile.BadZipFile, json.JSONDecodeError):
        return None

def check_similarity(directory):
    files = [f for f in os.listdir(directory) if f.endswith('.sb3')]
    project_signatures = {}

    print(f"Processing {len(files)} assignments for deep logic checking...\n")

    # Step 1: Extract signatures
    for filename in files:
        path = os.path.join(directory, filename)
        signature = extract_code_signature(path)
        if signature is not None:
            project_signatures[filename] = signature

    # Step 2: Compare every file against every other file
    print(f"{'File A':<30} | {'File B':<30} | {'Similarity'}")
    print("-" * 75)

    # combinations() lets us compare unique pairs without repeating
    for file_a, file_b in combinations(project_signatures.keys(), 2):
        sig_a = project_signatures[file_a]
        sig_b = project_signatures[file_b]
        
        # If both files are empty or have no blocks, skip
        if not sig_a or not sig_b:
            continue

        # Calculate similarity ratio
        matcher = difflib.SequenceMatcher(None, sig_a, sig_b)
        similarity = matcher.ratio() * 100

        # ALERT THRESHOLD: Show only if similarity is > 85%
        if similarity > 85:
            # Highlight 100% matches with an icon
            alert = "🔴 EXACT MATCH" if similarity > 99.9 else "⚠️  High Similarity"
            print(f"{file_a[:28]:<30} | {file_b[:28]:<30} | {similarity:.1f}%  {alert}")

if __name__ == "__main__":
    current_folder = os.getcwd()
    check_similarity(current_folder)
