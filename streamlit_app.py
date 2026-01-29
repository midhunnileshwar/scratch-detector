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

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Little KITES Forensics",
    page_icon="🛡️",
    layout="wide"
)

# --- SESSION STATE (Memory) ---
if 'log_history' not in st.session_state:
    st.session_state.log_history = []

# --- STYLING ---
st.markdown("""
    <style>
    .main {background-color: #f4f6f9;}
    .report-card {background: white; padding: 15px; border-radius: 8px; border-left: 5px solid #e74c3c; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    .success-msg {padding: 15px; background: #d4edda; color: #155724; border-radius: 5px;}
    </style>
""", unsafe_allow_html=True)

# --- CORE FUNCTIONS ---

def get_file_hash(bytes_data):
    return hashlib.md5(bytes_data).hexdigest()

def get_image_histogram(image_bytes):
    try:
        file_bytes = np.asarray(bytearray(image_bytes.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        return hist.flatten()
    except:
        return None

def extract_project_code(bytes_data):
    logic_codes = []
    assets = set()
    sprite_count = 0
    try:
        with zipfile.ZipFile(bytes_data) as z:
            # Assets
            for f in z.namelist():
                if f != 'project.json':
                    assets.add(hashlib.md5(z.read(f)).hexdigest())
            # Logic
            if 'project.json' in z.namelist():
                try:
                    project = json.loads(z.read('project.json'))
                    targets = project.get('targets', [])
                    targets.sort(key=lambda x: x.get('name', ''))
                    sprite_count = len(targets)
                    for target in targets:
                        blocks = target.get('blocks', {})
                        if isinstance(blocks, dict):
                            for block in blocks.values():
                                if isinstance(block, dict) and not block.get('shadow'):
                                    logic_codes.append(block.get('opcode', 'unknown'))
                except:
                    return "ERROR", assets, 0
    except:
        return None, None, 0
    return "\n".join(logic_codes), assets, sprite_count

def get_name_from_path(filename):
    # Tries to find student name from folder structure inside Zip
    parts = filename.replace("\\", "/").split("/")
    if len(parts) > 1 and parts[-2].lower() not in ['images', 'sounds']:
        return parts[-2]
    return os.path.splitext(parts[-1])[0]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Forensics Controls")
    code_thresh = st.slider("Code Match Threshold", 70, 100, 85)
    img_thresh = st.slider("Image Match Threshold", 50, 100, 80)
    st.info("Version 7.0 (Stable)\nSupports: .sb3, .p3b, .zip, Images")
    if st.button("🗑️ Clear Report History"):
        st.session_state.log_history = []
        st.experimental_rerun()

# --- MAIN APP ---
st.title("Little KITES Forensics Suite")
st.markdown("### Master Trainer Edition")

# UPLOADER (Fixed to allow multiple types again)
uploaded_files = st.file_uploader(
    "Upload Files (Drag .sb3 files directly OR a Class Zip)", 
    type=["zip", "sb3", "p3b", "png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if uploaded_files:
    # 1. PRE-PROCESSING
    projects = {}
    images = {}
    
    # We use a loop to handle both Zips and individual files
    for up_file in uploaded_files:
        
        # --- IF ZIP ---
        if up_file.name.endswith(".zip"):
            try:
                with zipfile.ZipFile(up_file) as z:
                    for filename in z.namelist():
                        if filename.startswith("__") or filename.startswith(".") or filename.endswith("/"): continue
                        
                        raw = io.BytesIO(z.read(filename))
                        owner = get_name_from_path(filename)
                        ext = filename.split('.')[-1].lower()
                        
                        if ext in ['sb3', 'p3b']:
                            l, a, s = extract_project_code(raw)
                            if l: 
                                if owner in projects: owner += f"_{len(projects)}"
                                projects[owner] = {'hash': get_file_hash(raw.getvalue()), 'logic': l, 'sprites': s}
                        
                        elif ext in ['jpg', 'png', 'jpeg']:
                            raw.seek(0)
                            hist = get_image_histogram(raw)
                            if hist is not None:
                                raw.seek(0)
                                if owner in images: owner += f"_{len(images)}"
                                images[owner] = {'hist': hist, 'obj': raw}
            except:
                st.error(f"Error reading zip: {up_file.name}")

        # --- IF INDIVIDUAL FILE ---
        else:
            up_file.seek(0)
            owner = os.path.splitext(up_file.name)[0]
            ext = up_file.name.split('.')[-1].lower()
            
            if ext in ['sb3', 'p3b']:
                l, a, s = extract_project_code(up_file)
                if l: projects[owner] = {'hash': get_file_hash(up_file.getvalue()), 'logic': l, 'sprites': s}
            
            elif ext in ['jpg', 'png', 'jpeg']:
                hist = get_image_histogram(up_file)
                if hist is not None:
                    up_file.seek(0)
                    images[owner] = {'hist': hist, 'obj': up_file}

    # 2. ANALYSIS TABS
    tab1, tab2, tab3 = st.tabs(["🧩 Projects", "🖼️ Posters", "📄 Report"])

    with tab1:
        if len(projects) < 2:
            st.warning("Need at least 2 project files to compare.")
        else:
            pairs = list(combinations(projects.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = projects[p1], projects[p2]
                
                # Binary Check
                if d1['hash'] == d2['hash']:
                    st.error(f"🚨 EXACT COPY: {p1} == {p2}")
                    st.session_state.log_history.append(f"[BINARY] {p1} == {p2}")
                    found = True
                    continue
                
                # Logic Check
                sim = difflib.SequenceMatcher(None, d1['logic'], d2['logic']).ratio() * 100
                if sim > code_thresh:
                    found = True
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>⚠️ Logic Match: {p1} vs {p2}</h4>
                        <p>Similarity: <b>{sim:.1f}%</b> | Sprites: {d1['sprites']} vs {d2['sprites']}</p>
                    </div>""", unsafe_allow_html=True)
                    st.session_state.log_history.append(f"[LOGIC] {p1} vs {p2} ({sim:.1f}%)")
            
            if not found: st.markdown('<div class="success-msg">✅ No Project Plagiarism Detected</div>', unsafe_allow_html=True)

    with tab2:
        if len(images) < 2:
            st.warning("Need at least 2 images to compare.")
        else:
            pairs = list(combinations(images.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = images[p1], images[p2]
                
                # Visual Check (Histogram)
                sim = cv2.compareHist(d1['hist'], d2['hist'], cv2.HISTCMP_CORREL) * 100
                if sim > img_thresh:
                    found = True
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>🎨 Visual Match: {p1} vs {p2}</h4>
                        <p>Correlation: <b>{sim:.1f}%</b></p>
                    </div>""", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    c1.image(d1['obj'], caption=p1)
                    c2.image(d2['obj'], caption=p2)
                    st.session_state.log_history.append(f"[IMAGE] {p1} vs {p2} ({sim:.1f}%)")
            
            if not found: st.markdown('<div class="success-msg">✅ No Poster Plagiarism Detected</div>', unsafe_allow_html=True)

    with tab3:
        if st.session_state.log_history:
            report_txt = "\n".join(set(st.session_state.log_history)) # Remove dupes
            st.text_area("Evidence Log", report_txt, height=300)
            st.download_button("📥 Download Report", report_txt, "report.txt")
        else:
            st.info("No issues found yet.")
