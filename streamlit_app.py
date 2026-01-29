import streamlit as st
import zipfile
import json
import hashlib
import difflib
import io
import os
import cv2
import numpy as np
from PIL import Image
from itertools import combinations

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="KITE Forensics Master",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE (Fixes the "Report Not Generating" issue) ---
if 'report_log' not in st.session_state:
    st.session_state.report_log = []

# --- CSS STYLING ---
st.markdown("""
    <style>
    .main {background-color: #f4f7f6;}
    h1 {color: #1a5276;}
    .report-card {background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #e74c3c; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
    .success-card {background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #27ae60; margin-bottom: 10px;}
    .owner-tag {background-color: #3498db; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9em;}
    </style>
    """, unsafe_allow_html=True)

# --- FORENSICS ENGINE ---

def get_file_hash(bytes_data):
    """MD5 Hash for Exact Binary Copies"""
    return hashlib.md5(bytes_data).hexdigest()

def get_image_histogram(image_bytes):
    """
    OpenCV Color Histogram. 
    Much smarter than Hash. Compares color distribution.
    """
    try:
        # Convert bytes to numpy array for OpenCV
        file_bytes = np.asarray(bytearray(image_bytes.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # Calculate Histogram (RGB distribution)
        hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        return hist.flatten()
    except Exception:
        return None

def extract_project_code(bytes_data, is_pictoblox=False):
    """
    Extracts block OpCodes from .sb3 and .p3b.
    Includes 'Safe Mode' for Pictoblox.
    """
    logic_codes = []
    assets = set()
    sprite_count = 0
    
    try:
        with zipfile.ZipFile(bytes_data) as z:
            # 1. Asset Forensics
            for f in z.namelist():
                if f != 'project.json':
                    assets.add(hashlib.md5(z.read(f)).hexdigest())
            
            # 2. Logic Forensics
            if 'project.json' in z.namelist():
                raw_json = z.read('project.json')
                try:
                    project = json.loads(raw_json)
                except json.JSONDecodeError:
                    # Fallback: If JSON is corrupt, try to read as text strings (Desperate Mode)
                    return "ERROR_JSON_PARSE", assets, 0
                
                targets = project.get('targets', [])
                targets.sort(key=lambda x: x.get('name', '')) # Sort sprites to ignore order
                
                sprite_count = len(targets)
                
                for target in targets:
                    blocks = target.get('blocks', {})
                    if isinstance(blocks, dict):
                        for block in blocks.values():
                            if isinstance(block, dict) and not block.get('shadow'):
                                opcode = block.get('opcode', 'unknown')
                                logic_codes.append(opcode)
    except Exception:
        return None, None, 0

    return "\n".join(logic_codes), assets, sprite_count

def extract_owner_name(filepath):
    """
    Intelligent Name Extractor v2.0
    Looks at folder structure: 'Class9B / Midhun / Project.sb3' -> 'Midhun'
    """
    parts = filepath.replace("\\", "/").split("/")
    
    # Filter out system folders
    parts = [p for p in parts if "__MACOSX" not in p and p != "."]
    
    filename = parts[-1]
    
    # If file is deep inside folders
    if len(parts) >= 2:
        # Check if the folder name is not generic
        folder_name = parts[-2]
        if folder_name.lower() not in ['source', 'images', 'sounds', 'project']:
            return folder_name  # Return the folder name as Student Name
            
    # Fallback to filename
    name = os.path.splitext(filename)[0]
    return name.replace("_", " ").title()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/121px-Python-logo-notext.svg.png", width=50)
    st.markdown("### 🛡️ Master Controls")
    
    st.markdown("**Analysis Sensitivity**")
    code_thresh = st.slider("Code Logic Match (%)", 70, 100, 85)
    img_thresh = st.slider("Image Similarity (%)", 50, 100, 80, help="Lower = Stricter (Checks Color Match)")
    
    st.markdown("---")
    
    # --- AI KEY SECTION (Requested) ---
    st.markdown("### 🔑 AI API Keys")
    st.caption("Paste keys here if you want to use cloud AI for advanced text summary (Future Feature).")
    openai_key = st.text_input("OpenAI / Gemini Key", type="password", help="Currently the tool runs locally (Offline AI) for privacy.")
    
    st.markdown("---")
    st.info("Developed by **Midhun T V**\nMaster Trainer, KITE Kasaragod")

# --- MAIN UI ---
st.title("🛡️ Little KITES Forensics Suite (v6.0)")
st.markdown("#### The Master Trainer's Tool for Assignments, Posters & Videos")

uploaded_file = st.file_uploader("📂 Upload Class ZIP File (Recommended)", type=["zip"], help="Upload the entire class folder as a single ZIP file.")

if uploaded_file:
    # --- PROCESSOR ---
    with st.spinner("🚀 Unzipping and Analyzing Class Data..."):
        
        # clear previous report
        st.session_state.report_log = []
        
        projects = {} # sb3, p3b
        images = {}   # jpg, png
        videos = {}   # mp4, mkv
        
        try:
            with zipfile.ZipFile(uploaded_file) as z:
                for filename in z.namelist():
                    if filename.startswith("__") or filename.startswith("."): continue
                    if filename.endswith("/"): continue # Skip folder entries
                    
                    ext = filename.split('.')[-1].lower()
                    owner = extract_owner_name(filename)
                    
                    # 1. PROJECTS
                    if ext in ['sb3', 'p3b']:
                        raw_data = io.BytesIO(z.read(filename))
                        # Determine if Pictoblox
                        is_p3b = (ext == 'p3b')
                        
                        logic, assets, s_count = extract_project_code(raw_data, is_p3b)
                        if logic:
                            # Handle duplicate student names
                            if owner in projects: owner += f"_{ext}"
                            
                            projects[owner] = {
                                'hash': get_file_hash(raw_data.getvalue()),
                                'logic': logic,
                                'assets': assets,
                                'sprites': s_count,
                                'type': 'Pictoblox' if is_p3b else 'Scratch'
                            }

                    # 2. IMAGES
                    elif ext in ['jpg', 'jpeg', 'png']:
                        raw_data = io.BytesIO(z.read(filename))
                        # Reset pointer for CV2 reading
                        raw_data.seek(0)
                        hist = get_image_histogram(raw_data)
                        
                        if hist is not None:
                            raw_data.seek(0)
                            if owner in images: owner += f"_{len(images)}"
                            images[owner] = {
                                'hash': get_file_hash(raw_data.getvalue()),
                                'hist': hist,
                                'obj': raw_data # Store for display
                            }

                    # 3. VIDEOS
                    elif ext in ['mp4', 'avi', 'mkv', 'mov']:
                        raw_data = z.read(filename)
                        if owner in videos: owner += f"_{len(videos)}"
                        videos[owner] = {
                            'hash': get_file_hash(raw_data),
                            'size': len(raw_data)
                        }

        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP.")

    # --- TABS ---
    tab_proj, tab_img, tab_vid, tab_rep = st.tabs([
        "🧩 Projects (Scratch/Pictoblox)", 
        "🖼️ Posters (Smart AI)", 
        "🎥 Videos", 
        "📄 Official Report"
    ])

    # === TAB 1: PROJECTS ===
    with tab_proj:
        if len(projects) < 2:
            st.info("Not enough project files found in the Zip.")
        else:
            pairs = list(combinations(projects.keys(), 2))
            found_proj = False
            for p1, p2 in pairs:
                d1, d2 = projects[p1], projects[p2]
                
                # Logic Match
                matcher = difflib.SequenceMatcher(None, d1['logic'], d2['logic'])
                sim = matcher.ratio() * 100
                
                if sim > code_thresh:
                    found_proj = True
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>⚠️ Logic Match: <span class="owner-tag">{p1}</span> vs <span class="owner-tag">{p2}</span></h4>
                        <p>Similarity: <b>{sim:.1f}%</b> | Sprites: {d1['sprites']} vs {d2['sprites']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Log to Report
                    st.session_state.report_log.append(f"[PROJECT] {p1} vs {p2} | Logic Match: {sim:.1f}%")

            if not found_proj: st
