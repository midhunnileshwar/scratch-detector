import streamlit as st
import zipfile
import json
import hashlib
import difflib
from itertools import combinations
import os

# --- Page Configuration ---
st.set_page_config(page_title="Little KITES Forensics", page_icon="🔍")

st.title("🔍 Scratch Plagiarism Detector")
st.markdown("""
**Upload multiple `.sb3` files** to check for:
1. **Exact Copies:** Students who just renamed the file.
2. **Logic Clones:** Students who copied the code but changed sprites/names.
""")

# --- Logic Functions ---
def get_file_hash(bytes_data):
    return hashlib.md5(bytes_data).hexdigest()

def extract_project_data(bytes_data):
    logic_signature = []
    asset_hashes = set()
    
    try:
        with zipfile.ZipFile(bytes_data) as z:
            for filename in z.namelist():
                if filename != 'project.json':
                    data = z.read(filename)
                    asset_hashes.add(hashlib.md5(data).hexdigest())

            if 'project.json' in z.namelist():
                project = json.loads(z.read('project.json'))
                targets = project.get('targets', [])
                targets.sort(key=lambda x: x.get('name', '')) # Sort by name

                for target in targets:
                    blocks = target.get('blocks', {})
                    if isinstance(blocks, dict):
                        for block in blocks.values():
                            if isinstance(block, dict) and not block.get('shadow'):
                                opcode = block.get('opcode', 'unknown')
                                logic_signature.append(opcode)
    except Exception:
        return None, None

    return "\n".join(logic_signature), asset_hashes

# --- The Web Interface ---
uploaded_files = st.file_uploader("Upload .sb3 files here", type="sb3", accept_multiple_files=True)

if uploaded_files:
    if len(uploaded_files) < 2:
        st.warning("Please upload at least 2 files to compare.")
    else:
        st.success(f"Processing {len(uploaded_files)} files...")
        
        file_data = {}
        
        # 1. Process Files
        for uploaded_file in uploaded_files:
            bytes_data = uploaded_file
            fname = uploaded_file.name
            
            h = get_file_hash(bytes_data)
            l, a = extract_project_data(bytes_data)
            
            if l is not None:
                file_data[fname] = {'hash': h, 'logic': l, 'assets': a}
            else:
                st.error(f"Error reading {fname}")

        # 2. Check Exact Duplicates
        st.subheader("1. Exact Binary Copies (Renamed Files)")
        seen_hashes = {}
        duplicates = []
        
        for name, data in file_data.items():
            h = data['hash']
            if h in seen_hashes:
                duplicates.append(f"🚨 **{name}** is an exact copy of **{seen_hashes[h]}**")
            else:
                seen_hashes[h] = name
        
        if duplicates:
            for d in duplicates: st.write(d)
        else:
            st.info("No exact binary duplicates found.")

        # 3. Deep Logic Analysis
        st.subheader("2. Smart Logic Analysis (Code Structure)")
        
        pairs = list(combinations(file_data.keys(), 2))
        suspicious_pairs = []

        for n1, n2 in pairs:
            d1, d2 = file_data[n1], file_data[n2]
            
            # Logic Similarity
            matcher = difflib.SequenceMatcher(None, d1['logic'], d2['logic'])
            sim = matcher.ratio() * 100
            
            # Asset Similarity
            shared = len(d1['assets'].intersection(d2['assets']))
            
            if sim > 85.0 or shared > 3:
                suspicious_pairs.append({
                    "Student A": n1,
                    "Student B": n2,
                    "Similarity": f"{sim:.1f}%",
                    "Notes": f"Shared {shared} Assets" if shared > 3 else "High Code Match"
                })

        if suspicious_pairs:
            st.table(suspicious_pairs)
        else:
            st.success("No suspicious logic similarities found.")
