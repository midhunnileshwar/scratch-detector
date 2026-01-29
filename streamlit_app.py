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

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Little KITES Forensics Master",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE ---
if 'log_history' not in st.session_state:
    st.session_state.log_history = []

# --- 3. PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    /* Main Theme */
    .main {background-color: #f4f7f6;}
    h1 {color: #2c3e50; font-family: 'Helvetica', sans-serif;}
    
    /* Stats Dashboard */
    .stat-box {
        background: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border-bottom: 4px solid #3498db;
    }
    
    /* Result Cards */
    .report-card {
        background: white; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 6px solid #e74c3c; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .success-card {
        background: white; padding: 20px; border-radius: 12px;
        border-left: 6px solid #27ae60; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Tags */
    .student-tag {
        background-color: #3498db; color: white; padding: 4px 10px;
        border-radius: 20px; font-weight: bold; font-size: 0.9em;
    }
    
    /* Developer Footer */
    .dev-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #2c3e50; color: white;
        text-align: center; padding: 10px; font-size: 0.8em; z-index: 999;
    }
    .stButton>button { background-color: #2980b9; color: white; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 4. INTELLIGENCE FUNCTIONS ---

def get_large_file_hash(file_obj):
    """
    Safe Hash for Large Videos (MP4/MKV).
    Reads chunks instead of crashing memory.
    """
    file_hash = hashlib.md5()
    file_obj.seek(0)
    # Read first 1MB and last 1MB for speed
    chunk1 = file_obj.read(1024 * 1024)
    file_hash.update(chunk1)
    try:
        file_obj.seek(-1024 * 1024, 2)
        chunk2 = file_obj.read(1024 * 1024)
        file_hash.update(chunk2)
    except:
        pass # File is smaller than 1MB
    return file_hash.hexdigest()

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
    """Robust Logic Extractor (Scratch + Pictoblox Safe Mode)"""
    logic_codes = []
    assets = set()
    sprite_count = 0
    try:
        with zipfile.ZipFile(bytes_data) as z:
            # Asset Hashing
            for f in z.namelist():
                if f != 'project.json':
                    assets.add(hashlib.md5(z.read(f)).hexdigest())
            
            # Logic Extraction
            if 'project.json' in z.namelist():
                raw_json = z.read('project.json')
                try:
                    project = json.loads(raw_json)
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
                    # FALLBACK: If JSON fails (Pictoblox sometimes), scan text
                    str_data = str(raw_json)
                    if "opcode" in str_data:
                        logic_codes.append("raw_text_match") # Just mark it readable
    except:
        return None, None, 0
    
    return "\n".join(logic_codes), assets, sprite_count

def extract_owner_name(filepath):
    """
    Prioritizes Folder Name. 
    Fixes the 'Assignment_25' generic name issue.
    """
    path = filepath.replace("\\", "/")
    parts = path.split("/")
    parts = [p for p in parts if "__MACOSX" not in p and p != "." and p.strip() != ""]
    
    filename = parts[-1]
    
    # Generic Check List
    generic_terms = ['assignment', 'project', 'untitled', 'game', 'submission', 'scratch', 'individual', 'group']
    
    # Strategy 1: If folder exists, use it
    if len(parts) >= 2:
        parent = parts[-2]
        if parent.lower() not in ['images', 'sounds', 'src']:
            return parent # Assume Folder Name is Student Name
            
    # Strategy 2: If filename is the only option
    name = os.path.splitext(filename)[0]
    # Clean up "Assignment_2" -> "Assignment"
    return name.replace("_", " ").title()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/121px-Python-logo-notext.svg.png", width=60)
    st.markdown("## 🛡️ Forensics Master")
    st.caption("Version 9.0 (Diagnosis Edition)")
    st.markdown("---")
    
    st.info("**Midhun T V**\n\nMaster Trainer\nKITE Kasaragod")
    st.markdown("---")
    
    code_thresh = st.slider("Code Logic Match", 70, 100, 85, format="%d%%")
    img_thresh = st.slider("Visual Match", 50, 100, 80, format="%d%%")
    
    if st.button("🗑️ Reset"):
        st.session_state.log_history = []
        st.experimental_rerun()

# --- 6. MAIN UI ---
st.title("🛡️ Little KITES Forensics Suite")
st.markdown("#### Advanced Analysis for Scratch, Pictoblox, Posters & Videos")

uploaded_files = st.file_uploader(
    "📂 Drop Class Zip or Files", 
    type=["zip", "sb3", "p3b", "png", "jpg", "jpeg", "mp4", "mkv", "avi", "mov", "mpeg"], 
    accept_multiple_files=True
)

if uploaded_files:
    projects = {} 
    images = {}   
    videos = {}   

    # --- PROCESSING ---
    with st.spinner("🚀 Analyzing File Structure..."):
        for up_file in uploaded_files:
            
            # ZIP Handler
            if up_file.name.endswith(".zip"):
                try:
                    with zipfile.ZipFile(up_file) as z:
                        for filename in z.namelist():
                            if filename.startswith("__") or filename.startswith(".") or filename.endswith("/"): continue
                            
                            owner = extract_owner_name(filename)
                            ext = filename.split('.')[-1].lower()
                            
                            # Projects
                            if ext in ['sb3', 'p3b']:
                                raw = io.BytesIO(z.read(filename))
                                l, a, s = extract_project_code(raw)
                                if l: 
                                    if owner in projects: owner += f" ({len(projects)+1})"
                                    projects[owner] = {'hash': get_file_hash(raw.getvalue()), 'logic': l, 'sprites': s}
                            
                            # Images
                            elif ext in ['jpg', 'jpeg', 'png']:
                                raw = io.BytesIO(z.read(filename))
                                raw.seek(0)
                                hist = get_image_histogram(raw)
                                if hist is not None:
                                    raw.seek(0)
                                    if owner in images: owner += f" ({len(images)+1})"
                                    images[owner] = {'hist': hist, 'obj': raw}
                                    
                            # Videos (Chunk Read)
                            elif ext in ['mp4', 'mkv', 'avi', 'mov', 'mpeg']:
                                # Read as file object inside zip
                                with z.open(filename) as vid_file:
                                    v_hash = get_large_file_hash(vid_file)
                                    # Get size
                                    vid_info = z.getinfo(filename)
                                    if owner in videos: owner += f" ({len(videos)+1})"
                                    videos[owner] = {'hash': v_hash, 'size': vid_info.file_size}
                except:
                    st.error(f"Error reading zip: {up_file.name}")

            # Single File Handler
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
                elif ext in ['mp4', 'mkv', 'avi', 'mov', 'mpeg']:
                    v_hash = get_large_file_hash(up_file)
                    up_file.seek(0, 2) # seek end
                    v_size = up_file.tell()
                    videos[owner] = {'hash': v_hash, 'size': v_size}

    # --- DASHBOARD STATS (Diagnosis) ---
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='stat-box'><h4>🧩 Projects</h4><h2>{len(projects)}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-box'><h4>🖼️ Posters</h4><h2>{len(images)}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-box'><h4>🎥 Videos</h4><h2>{len(videos)}</h2></div>", unsafe_allow_html=True)

    # --- TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["🧩 Projects", "🖼️ Posters", "🎥 Videos", "📄 Report"])

    # PROJECTS
    with tab1:
        if len(projects) < 2: st.info("Need 2+ projects.")
        else:
            pairs = list(combinations(projects.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = projects[p1], projects[p2]
                if d1['hash'] == d2['hash']:
                    st.markdown(f"<div class='report-card'><h4>🚨 EXACT COPY</h4><span class='student-tag'>{p1}</span> == <span class='student-tag'>{p2}</span></div>", unsafe_allow_html=True)
                    st.session_state.log_history.append(f"[PROJECT BINARY] {p1} == {p2}")
                    found = True; continue
                
                sim = difflib.SequenceMatcher(None, d1['logic'], d2['logic']).ratio() * 100
                if sim > code_thresh:
                    found = True
                    st.markdown(f"<div class='report-card'><h4>⚠️ Logic: {sim:.1f}%</h4><span class='student-tag'>{p1}</span> vs <span class='student-tag'>{p2}</span><br><small>Sprites: {d1['sprites']}/{d2['sprites']}</small></div>", unsafe_allow_html=True)
                    st.session_state.log_history.append(f"[PROJECT LOGIC] {p1} vs {p2} ({sim:.1f}%)")
            if not found: st.success("✅ Clean")

    # POSTERS
    with tab2:
        if len(images) < 2: st.info("Need 2+ images.")
        else:
            pairs = list(combinations(images.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = images[p1], images[p2]
                sim = cv2.compareHist(d1['hist'], d2['hist'], cv2.HISTCMP_CORREL) * 100
                if sim > img_thresh:
                    found = True
                    st.markdown(f"<div class='report-card'><h4>🎨 Visual: {sim:.1f}%</h4><span class='student-tag'>{p1}</span> vs <span class='student-tag'>{p2}</span></div>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    c1.image(d1['obj'], caption=p1, width=200)
                    c2.image(d2['obj'], caption=p2, width=200)
                    st.session_state.log_history.append(f"[POSTER] {p1} vs {p2} ({sim:.1f}%)")
            if not found: st.success("✅ Clean")

    # VIDEOS
    with tab3:
        if len(videos) < 2: st.info("Need 2+ videos.")
        else:
            pairs = list(combinations(videos.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = videos[p1], videos[p2]
                if d1['hash'] == d2['hash']:
                    found = True
                    st.markdown(f"<div class='report-card'><h4>🎥 Same Video</h4><span class='student-tag'>{p1}</span> == <span class='student-tag'>{p2}</span></div>", unsafe_allow_html=True)
                    st.session_state.log_history.append(f"[VIDEO] {p1} == {p2}")
            if not found: st.success("✅ Clean")

    # REPORT
    with tab4:
        if st.session_state.log_history:
            rpt = "\n".join(list(set(st.session_state.log_history)))
            st.text_area("Log", rpt)
            st.download_button("Download Report", rpt, "report.txt")
