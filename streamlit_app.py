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

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="KITE Forensics Master", page_icon="🛡️", layout="wide")

# --- 2. CSS STYLING ---
st.markdown("""
    <style>
    .main {background-color: #f4f7f6;}
    .report-card {
        background: white; padding: 20px; border-radius: 10px;
        border-left: 6px solid #e74c3c; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px;
    }
    .student-tag {
        background-color: #2980b9; color: white; padding: 5px 10px;
        border-radius: 15px; font-weight: bold; font-size: 0.9em;
    }
    .stat-box {
        background: white; padding: 15px; border-radius: 8px;
        text-align: center; border-bottom: 4px solid #2980b9;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. CORE LOGIC EXTRACTOR (THE FIX) ---
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

def extract_project_logic(file_bytes):
    """
    Reads .sb3 and .p3b files properly.
    Returns: (Logic String, Asset Hashes, Sprite Count)
    """
    logic = []
    assets = set()
    sprite_count = 0
    
    try:
        with zipfile.ZipFile(file_bytes) as z:
            # 1. Get Assets
            for f in z.namelist():
                if f != 'project.json':
                    assets.add(hashlib.md5(z.read(f)).hexdigest())
            
            # 2. Get Logic (project.json)
            if 'project.json' in z.namelist():
                data = json.loads(z.read('project.json'))
                targets = data.get('targets', [])
                targets.sort(key=lambda x: x.get('name', '')) # Sort sprites
                sprite_count = len(targets)
                
                for target in targets:
                    blocks = target.get('blocks', {})
                    # Handle both Dict and List formats (Pictoblox sometimes uses Lists)
                    if isinstance(blocks, dict):
                        for block in blocks.values():
                            if isinstance(block, dict) and not block.get('shadow'):
                                logic.append(block.get('opcode', 'unknown'))
                    elif isinstance(blocks, list): # Rare case
                        for block in blocks:
                            if isinstance(block, dict) and not block.get('shadow'):
                                logic.append(block.get('opcode', 'unknown'))
                                
    except Exception as e:
        return None, None, 0 # File is corrupt or not a zip
        
    return "\n".join(logic), assets, sprite_count

def extract_student_name(filename):
    """
    Folder-Aware Naming.
    Zip Path: "Class 9A/Midhun/Game.sb3" -> Returns "Midhun"
    """
    path = filename.replace("\\", "/")
    parts = [p for p in path.split("/") if "__MACOSX" not in p and p != "." and p]
    
    if len(parts) > 1:
        # Check parent folder
        folder = parts[-2]
        if folder.lower() not in ['images', 'sounds', 'project', 'src']:
            return folder
            
    # Fallback to filename
    return os.path.splitext(parts[-1])[0].replace("_", " ").title()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/121px-Python-logo-notext.svg.png", width=60)
    st.markdown("## 🛡️ Forensics Master")
    st.caption("v10.0 (Logic Restored)")
    st.markdown("---")
    st.info("**Developed by Midhun T V**\nMaster Trainer\nKITE Kasaragod")
    st.markdown("---")
    code_thresh = st.slider("Code Logic Match", 70, 100, 85, format="%d%%")
    img_thresh = st.slider("Visual Match", 50, 100, 80, format="%d%%")

# --- 5. MAIN INTERFACE ---
st.title("🛡️ Little KITES Forensics Suite")
st.markdown("#### Scratch (.sb3) & Pictoblox (.p3b) Analysis Tool")

uploaded_files = st.file_uploader(
    "📂 Upload Class Zip (Recommended) or Files", 
    type=["zip", "sb3", "p3b", "png", "jpg", "jpeg", "mp4", "mkv"], 
    accept_multiple_files=True
)

if uploaded_files:
    projects = {}
    images = {}
    videos = {}
    
    with st.spinner("Processing Files..."):
        for up_file in uploaded_files:
            
            # --- ZIP HANDLING ---
            if up_file.name.endswith(".zip"):
                try:
                    with zipfile.ZipFile(up_file) as z:
                        for filename in z.namelist():
                            if filename.startswith(".") or filename.endswith("/"): continue
                            if "__MACOSX" in filename: continue
                            
                            owner = extract_student_name(filename)
                            ext = filename.split('.')[-1].lower()
                            
                            # LOGIC: Projects
                            if ext in ['sb3', 'p3b']:
                                raw = io.BytesIO(z.read(filename))
                                l, a, s = extract_project_logic(raw)
                                if l: 
                                    if owner in projects: owner += f" ({len(projects)+1})"
                                    projects[owner] = {'hash': get_file_hash(raw.getvalue()), 'logic': l, 'sprites': s}
                            
                            # LOGIC: Images
                            elif ext in ['jpg', 'png', 'jpeg']:
                                raw = io.BytesIO(z.read(filename))
                                raw.seek(0)
                                hist = get_image_histogram(raw)
                                if hist is not None:
                                    raw.seek(0)
                                    if owner in images: owner += f" ({len(images)+1})"
                                    images[owner] = {'hist': hist, 'obj': raw}
                            
                            # LOGIC: Videos
                            elif ext in ['mp4', 'mkv']:
                                raw_bytes = z.read(filename)
                                if owner in videos: owner += f" ({len(videos)+1})"
                                videos[owner] = {'hash': get_file_hash(raw_bytes), 'size': len(raw_bytes)}

                except:
                    st.error(f"Error reading zip: {up_file.name}")

            # --- SINGLE FILE HANDLING ---
            else:
                up_file.seek(0)
                owner = os.path.splitext(up_file.name)[0].replace("_", " ").title()
                ext = up_file.name.split('.')[-1].lower()
                
                if ext in ['sb3', 'p3b']:
                    l, a, s = extract_project_logic(up_file)
                    if l: projects[owner] = {'hash': get_file_hash(up_file.getvalue()), 'logic': l, 'sprites': s}
                elif ext in ['jpg', 'png']:
                    hist = get_image_histogram(up_file)
                    if hist is not None:
                        up_file.seek(0)
                        images[owner] = {'hist': hist, 'obj': up_file}

    # --- RESULTS DASHBOARD ---
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='stat-box'><h4>🧩 Projects Found</h4><h2>{len(projects)}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-box'><h4>🖼️ Posters Found</h4><h2>{len(images)}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-box'><h4>🎥 Videos Found</h4><h2>{len(videos)}</h2></div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🧩 Projects Analysis", "🖼️ Poster Analysis", "🎥 Video Analysis"])

    # --- TAB 1: PROJECTS ---
    with tab1:
        if len(projects) < 2:
            st.warning("Needs at least 2 .sb3/.p3b files to compare.")
        else:
            pairs = list(combinations(projects.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = projects[p1], projects[p2]
                
                # Binary Match
                if d1['hash'] == d2['hash']:
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>🚨 EXACT COPY DETECTED</h4>
                        <span class="student-tag">{p1}</span> is identical to <span class="student-tag">{p2}</span>
                    </div>""", unsafe_allow_html=True)
                    found = True
                    continue

                # Logic Match
                sim = difflib.SequenceMatcher(None, d1['logic'], d2['logic']).ratio() * 100
                if sim > code_thresh:
                    found = True
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>⚠️ High Code Similarity: {sim:.1f}%</h4>
                        <span class="student-tag">{p1}</span> vs <span class="student-tag">{p2}</span>
                        <br><br><b>Sprite Count:</b> {d1['sprites']} vs {d2['sprites']}
                    </div>""", unsafe_allow_html=True)
            
            if not found: st.success("✅ No code plagiarism detected.")

    # --- TAB 2: POSTERS ---
    with tab2:
        if len(images) < 2: st.info("Needs 2+ images.")
        else:
            pairs = list(combinations(images.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = images[p1], images[p2]
                sim = cv2.compareHist(d1['hist'], d2['hist'], cv2.HISTCMP_CORREL) * 100
                if sim > img_thresh:
                    found = True
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>🎨 Visual Match: {sim:.1f}%</h4>
                        <span class="student-tag">{p1}</span> vs <span class="student-tag">{p2}</span>
                    </div>""", unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    col1.image(d1['obj'], caption=p1, width=200)
                    col2.image(d2['obj'], caption=p2, width=200)
            if not found: st.success("✅ No poster plagiarism detected.")

    # --- TAB 3: VIDEOS ---
    with tab3:
        if len(videos) < 2: st.info("Needs 2+ videos.")
        else:
            pairs = list(combinations(videos.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = videos[p1], videos[p2]
                if d1['hash'] == d2['hash']:
                    found = True
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>🎥 Duplicate Video File</h4>
                        <span class="student-tag">{p1}</span> == <span class="student-tag">{p2}</span>
                    </div>""", unsafe_allow_html=True)
            if not found: st.success("✅ No video duplicates found.")
