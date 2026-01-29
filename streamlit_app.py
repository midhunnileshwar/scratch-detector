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

# --- 3. PROFESSIONAL STYLING (PRESERVED) ---
st.markdown("""
    <style>
    /* Main Theme */
    .main {background-color: #f4f7f6;}
    h1 {color: #2c3e50; font-family: 'Helvetica', sans-serif;}
    
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
        background: white;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #27ae60;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Tags */
    .student-tag {
        background-color: #3498db;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9em;
    }
    
    /* Developer Footer */
    .dev-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #2c3e50;
        color: white;
        text-align: center;
        padding: 10px;
        font-size: 0.8em;
        z-index: 999;
    }
    
    /* Button Style */
    .stButton>button {
        background-color: #2980b9;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. CORE INTELLIGENCE FUNCTIONS ---

def get_file_hash(bytes_data):
    """MD5 Hash for Exact Binary Copies"""
    return hashlib.md5(bytes_data).hexdigest()

def get_image_histogram(image_bytes):
    """OpenCV Smart Color Analysis"""
    try:
        file_bytes = np.asarray(bytearray(image_bytes.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        return hist.flatten()
    except Exception:
        return None

def extract_project_code(bytes_data):
    """Extract Logic from Scratch/Pictoblox"""
    logic_codes = []
    assets = set()
    sprite_count = 0
    try:
        with zipfile.ZipFile(bytes_data) as z:
            for f in z.namelist():
                if f != 'project.json':
                    assets.add(hashlib.md5(z.read(f)).hexdigest())
            
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
                except json.JSONDecodeError:
                    return "ERROR_JSON", assets, 0
    except Exception:
        return None, None, 0
    return "\n".join(logic_codes), assets, sprite_count

def extract_owner_name(filepath):
    """
    FIXED: Prioritizes Folder Names over Filenames
    Example: "Class9/Abhishek/Assignment.sb3" -> "Abhishek"
    """
    path = filepath.replace("\\", "/")
    parts = path.split("/")
    
    # Clean up system junk
    parts = [p for p in parts if "__MACOSX" not in p and p != "." and p.strip() != ""]
    
    filename = parts[-1]
    name_candidate = os.path.splitext(filename)[0]

    # If the file is inside a folder, that folder name is likely the student
    if len(parts) >= 2:
        parent_folder = parts[-2]
        
        # List of generic names to IGNORE
        generic_names = ['source', 'images', 'sounds', 'project', 'assignment', 'submission', 'scratch', 'desktop']
        
        # If the filename is generic (e.g. "Project.sb3"), definitely use folder name
        if any(x in name_candidate.lower() for x in ['assignment', 'project', 'untitled', 'game', 'activity']):
            if parent_folder.lower() not in generic_names:
                return parent_folder

        # Otherwise, check if parent folder looks like a real name
        if parent_folder.lower() not in generic_names:
             # Use "FolderName - FileName" to be safe
             return f"{parent_folder} ({name_candidate})"
             
    return name_candidate.replace("_", " ").title()

# --- 5. SIDEBAR PROFILE ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/121px-Python-logo-notext.svg.png", width=60)
    st.markdown("## 🛡️ Forensics Master")
    st.caption("Version 8.1 (Name Fix)")
    st.markdown("---")
    
    st.markdown("### 👨‍💻 Developed By")
    st.info("**Midhun T V**\n\nMaster Trainer\nKITE Kasaragod")
    
    st.markdown("---")
    st.markdown("### ⚙️ Sensitivity")
    code_thresh = st.slider("Code Logic Match", 70, 100, 85, format="%d%%")
    img_thresh = st.slider("Visual Match", 50, 100, 80, format="%d%%")
    
    if st.button("🗑️ Reset All Data"):
        st.session_state.log_history = []
        st.experimental_rerun()

# --- 6. MAIN INTERFACE ---
st.title("🛡️ Forensics Suite")
st.markdown("#### Advanced Analysis for Scratch, Pictoblox, Posters & Videos")

# Upload Area
uploaded_files = st.file_uploader(
    "📂 Drop Class Zip (Recommended) or Individual Files", 
    type=["zip", "sb3", "p3b", "png", "jpg", "jpeg", "mp4", "mkv"], 
    accept_multiple_files=True
)

if uploaded_files:
    projects = {} 
    images = {}   
    videos = {}   

    with st.spinner("🚀 Unpacking and Analyzing..."):
        for up_file in uploaded_files:
            
            # --- ZIP HANDLING ---
            if up_file.name.endswith(".zip"):
                try:
                    with zipfile.ZipFile(up_file) as z:
                        for filename in z.namelist():
                            if filename.startswith("__") or filename.startswith(".") or filename.endswith("/"): continue
                            
                            # === LOGIC FIX: Better Name Extraction ===
                            owner = extract_owner_name(filename)
                            ext = filename.split('.')[-1].lower()
                            
                            # 1. Projects
                            if ext in ['sb3', 'p3b']:
                                raw = io.BytesIO(z.read(filename))
                                l, a, s = extract_project_code(raw)
                                if l: 
                                    # Unique ID handling
                                    key = owner
                                    if key in projects: key = f"{owner} ({len(projects)+1})"
                                    projects[key] = {'hash': get_file_hash(raw.getvalue()), 'logic': l, 'sprites': s}
                            
                            # 2. Images
                            elif ext in ['jpg', 'jpeg', 'png']:
                                raw = io.BytesIO(z.read(filename))
                                raw.seek(0)
                                hist = get_image_histogram(raw)
                                if hist is not None:
                                    raw.seek(0)
                                    key = owner
                                    if key in images: key = f"{owner} ({len(images)+1})"
                                    images[key] = {'hist': hist, 'obj': raw}
                                    
                            # 3. Videos
                            elif ext in ['mp4', 'mkv', 'avi']:
                                raw_bytes = z.read(filename)
                                key = owner
                                if key in videos: key = f"{owner} ({len(videos)+1})"
                                videos[key] = {'hash': get_file_hash(raw_bytes), 'size': len(raw_bytes)}

                except Exception as e:
                    st.toast(f"Error reading zip: {up_file.name}")

            # --- SINGLE FILE HANDLING ---
            else:
                up_file.seek(0)
                # Use filename as owner for single uploads
                owner = os.path.splitext(up_file.name)[0].replace("_", " ").title()
                ext = up_file.name.split('.')[-1].lower()
                
                if ext in ['sb3', 'p3b']:
                    l, a, s = extract_project_code(up_file)
                    if l: projects[owner] = {'hash': get_file_hash(up_file.getvalue()), 'logic': l, 'sprites': s}
                
                elif ext in ['jpg', 'png', 'jpeg']:
                    hist = get_image_histogram(up_file)
                    if hist is not None:
                        up_file.seek(0)
                        images[owner] = {'hist': hist, 'obj': up_file}

    # --- 7. RESULTS TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["🧩 Projects", "🖼️ Posters", "🎥 Videos", "📄 Report"])

    # TAB 1: PROJECTS
    with tab1:
        if len(projects) < 2:
            st.info("Upload at least 2 project files to compare.")
        else:
            pairs = list(combinations(projects.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = projects[p1], projects[p2]
                
                # Binary Check
                if d1['hash'] == d2['hash']:
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>🚨 EXACT COPY DETECTED</h4>
                        <span class="student-tag">{p1}</span> is identical to <span class="student-tag">{p2}</span>
                    </div>""", unsafe_allow_html=True)
                    st.session_state.log_history.append(f"[PROJECT BINARY] {p1} == {p2}")
                    found = True
                    continue

                # Logic Check
                sim = difflib.SequenceMatcher(None, d1['logic'], d2['logic']).ratio() * 100
                if sim > code_thresh:
                    found = True
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>⚠️ Logic Similarity: {sim:.1f}%</h4>
                        <span class="student-tag">{p1}</span> vs <span class="student-tag">{p2}</span>
                        <p>Sprites: {d1['sprites']} / {d2['sprites']}</p>
                    </div>""", unsafe_allow_html=True)
                    st.session_state.log_history.append(f"[PROJECT LOGIC] {p1} vs {p2} ({sim:.1f}%)")
            
            if not found: st.markdown('<div class="success-card">✅ No Project Plagiarism</div>', unsafe_allow_html=True)

    # TAB 2: POSTERS
    with tab2:
        if len(images) < 2:
            st.info("Upload at least 2 images.")
        else:
            pairs = list(combinations(images.keys(), 2))
            found = False
            for p1, p2 in pairs:
                d1, d2 = images[p1], images[p2]
                
                # OpenCV Compare
                sim = cv2.compareHist(d1['hist'], d2['hist'], cv2.HISTCMP_CORREL) * 100
                if sim > img_thresh:
                    found = True
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>🎨 Visual Match: {sim:.1f}%</h4>
                        <span class="student-tag">{p1}</span> vs <span class="student-tag">{p2}</span>
                    </div>""", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    c1.image(d1['obj'], caption=p1, width=200)
                    c2.image(d2['obj'], caption=p2, width=200)
                    st.session_state.log_history.append(f"[IMAGE VISUAL] {p1} vs {p2} ({sim:.1f}%)")

            if not found: st.markdown('<div class="success-card">✅ No Poster Plagiarism</div>', unsafe_allow_html=True)

    # TAB 3: VIDEOS
    with tab3:
        if len(videos) < 2:
            st.info("Upload at least 2 videos.")
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
                        <p>Size: {d1['size']/1024/1024:.2f} MB</p>
                    </div>""", unsafe_allow_html=True)
                    st.session_state.log_history.append(f"[VIDEO DUPLICATE] {p1} == {p2}")
            if not found: st.markdown('<div class="success-card">✅ No Video Plagiarism</div>', unsafe_allow_html=True)

    # TAB 4: REPORT
    with tab4:
        st.subheader("📝 Official Forensics Log")
        if st.session_state.log_history:
            unique_logs = sorted(list(set(st.session_state.log_history)))
            report_text = f"LITTLE KITES PLAGIARISM REPORT\nEvaluator: Midhun T V\n----------------------------------\n" + "\n".join(unique_logs)
            
            st.text_area("Log View", report_text, height=300)
            st.download_button("📥 Download Report.txt", report_text, "forensics_report.txt")
        else:
            st.info("No suspicious activity detected in this batch.")

else:
    st.markdown("""
    <div style='text-align: center; padding: 50px; background: white; border-radius: 12px; margin-top: 20px;'>
        <h3>👋 Welcome, Midhun Sir!</h3>
        <p>This tool is optimized for <b>Little KITES</b> evaluation.</p>
        <p>Please upload a <b>Class Zip File</b> to begin analysis.</p>
    </div>
    """, unsafe_allow_html=True)
