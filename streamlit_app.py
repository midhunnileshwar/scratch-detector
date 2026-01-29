import streamlit as st
import zipfile
import json
import hashlib
import difflib
from itertools import combinations
import io
from PIL import Image
import imagehash
import os
import re

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(
    page_title="Little KITES Master Forensics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE INITIALIZATION (Fix for disappearing reports) ---
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'report_data' not in st.session_state:
    st.session_state.report_data = ""
if 'project_db' not in st.session_state:
    st.session_state.project_db = {}
if 'image_db' not in st.session_state:
    st.session_state.image_db = {}
if 'video_db' not in st.session_state:
    st.session_state.video_db = {}

# --- CUSTOM CSS (KITE THEME) ---
st.markdown("""
    <style>
    .main {background-color: #f4f6f9;}
    h1 {color: #2c3e50; font-family: 'Arial', sans-serif;}
    .stButton>button {background-color: #2980b9; color: white; border-radius: 8px; font-weight: bold;}
    .report-card {background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #e74c3c; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px;}
    .success-card {background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #2ecc71; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
    .student-name {font-size: 1.1em; font-weight: bold; color: #2c3e50;}
    .footer {text-align: center; margin-top: 50px; color: #7f8c8d; font-size: 0.8em;}
    </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def get_file_hash(bytes_data):
    """Returns MD5 hash for exact binary check."""
    return hashlib.md5(bytes_data).hexdigest()

def get_image_phash(image_file):
    """AI Vision: Returns a perceptual hash (fingerprint) of the image structure."""
    try:
        img = Image.open(image_file)
        # phash is robust against resizing, brightness, and minor edits
        return imagehash.phash(img)
    except:
        return None

def determine_student_name(path):
    """
    Smart Name Extractor:
    - zip/Class9/Abhishek/Project.sb3 -> 'Abhishek'
    - zip/Abhishek.sb3 -> 'Abhishek'
    """
    parts = path.replace("\\", "/").split("/")
    filename = parts[-1]
    
    # If deeply nested, take the parent folder as the name
    if len(parts) > 1:
        # Ignore generic folder names
        valid_parts = [p for p in parts[:-1] if p.lower() not in ['sb3', 'assignment', 'new folder', 'desktop', 'project']]
        if valid_parts:
            return valid_parts[-1] # Return the last valid folder name
            
    return os.path.splitext(filename)[0]

def extract_project_logic(bytes_data):
    """
    Reads .sb3 and .p3b (Pictoblox) files.
    Returns: Logic String, Asset Hashes, Sprite Count
    """
    logic_signature = []
    asset_hashes = set()
    sprite_count = 0
    
    try:
        with zipfile.ZipFile(bytes_data) as z:
            # 1. Asset Forensics
            for f in z.namelist():
                if f != 'project.json':
                    data = z.read(f)
                    asset_hashes.add(hashlib.md5(data).hexdigest())

            # 2. Code Logic
            if 'project.json' in z.namelist():
                json_data = z.read('project.json').decode('utf-8')
                project = json.loads(json_data)
                
                targets = project.get('targets', [])
                sprite_count = len(targets)
                # Sort targets to handle sprite reordering
                targets.sort(key=lambda x: x.get('name', '')) 

                for target in targets:
                    blocks = target.get('blocks', {})
                    if isinstance(blocks, dict):
                        for block in blocks.values():
                            if isinstance(block, dict) and not block.get('shadow'):
                                opcode = block.get('opcode', 'unknown')
                                logic_signature.append(opcode)
                                
    except Exception:
        return None, None, 0

    return "\n".join(logic_signature), asset_hashes, sprite_count

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/121px-Python-logo-notext.svg.png", width=50)
    st.title("Master Controls")
    
    st.markdown("### 👨‍💻 Developer")
    st.markdown("**Midhun T V**\n*Master Trainer, KITE Kasaragod*")
    st.markdown("---")
    
    st.markdown("### ⚙️ Sensitivity")
    code_sim_threshold = st.slider("Code Similarity (%)", 50, 100, 85)
    visual_sim_threshold = st.slider("Image Tolerance", 0, 20, 12, help="Higher = looser match. Lower = stricter.")
    
    if st.button("🔄 Reset Analysis"):
        st.session_state.clear()
        st.rerun()

# --- MAIN INTERFACE ---
st.title("🛡️ Little KITES Forensics Suite (v6.0)")
st.markdown("##### Upload Assignments (Supports: .zip, .sb3, .p3b, .png, .jpg, .mp4)")

uploaded_file_obj = st.file_uploader("📂 Drop files here", type=["zip", "sb3", "p3b", "png", "jpg", "jpeg", "mp4", "avi", "mkv"], accept_multiple_files=True)

if uploaded_file_obj:
    # Only process if we haven't already (prevents rerun loop)
    if not st.session_state.analysis_complete:
        
        with st.status("🔍 unpacking and analyzing..."):
            
            # Temporary storage before saving to session
            temp_projects = {}
            temp_images = {}
            temp_videos = {}
            
            # Function to process a single file stream
            def process_single_file(fname, fbytes, container_name=None):
                # Determine owner
                if container_name:
                    owner = container_name
                else:
                    owner = determine_student_name(fname)
                
                # Deduplicate names (Abhishek, Abhishek_1, Abhishek_2)
                original_owner = owner
                count = 1
                while owner in temp_projects or owner in temp_images or owner in temp_videos:
                    owner = f"{original_owner}_{count}"
                    count += 1
                
                ext = fname.split('.')[-1].lower()
                fbytes.seek(0)
                
                # --- SCRATCH / PICTOBLOX ---
                if ext in ['sb3', 'p3b']:
                    h = get_file_hash(fbytes.read())
                    fbytes.seek(0)
                    l, a, s = extract_project_logic(fbytes)
                    if l:
                        temp_projects[owner] = {'file': fname, 'hash': h, 'logic': l, 'assets': a, 'sprites': s}
                
                # --- IMAGES ---
                elif ext in ['png', 'jpg', 'jpeg']:
                    fbytes.seek(0)
                    h = get_file_hash(fbytes.read())
                    fbytes.seek(0)
                    ph = get_image_phash(fbytes)
                    if ph:
                        temp_images[owner] = {'file': fname, 'hash': h, 'phash': ph, 'obj': fbytes}

                # --- VIDEOS (Size + Hash Check) ---
                elif ext in ['mp4', 'avi', 'mkv']:
                    fbytes.seek(0)
                    data = fbytes.read()
                    h = get_file_hash(data)
                    size = len(data)
                    temp_videos[owner] = {'file': fname, 'hash': h, 'size': size}

            # --- PROCESS UPLOADS ---
            for up_file in uploaded_file_obj:
                # If ZIP
                if up_file.name.endswith(".zip"):
                    try:
                        with zipfile.ZipFile(up_file) as z:
                            for zfname in z.namelist():
                                if not zfname.endswith('/') and "__MACOSX" not in zfname:
                                    z_bytes = io.BytesIO(z.read(zfname))
                                    # Pass folder structure for naming
                                    s_name = determine_student_name(zfname)
                                    process_single_file(zfname, z_bytes, container_name=s_name)
                    except:
                        st.error(f"Failed to unzip {up_file.name}")
                # If Individual File
                else:
                    process_single_file(up_file.name, up_file)

            # Save to Session State
            st.session_state.project_db = temp_projects
            st.session_state.image_db = temp_images
            st.session_state.video_db = temp_videos
            st.session_state.analysis_complete = True
            st.rerun()

# --- RESULTS DISPLAY ---
if st.session_state.analysis_complete:
    
    tab1, tab2, tab3, tab4 = st.tabs(["🧩 Projects (Code)", "🖼️ Images (Visual)", "🎬 Videos", "📄 Final Report"])
    
    report_lines = []

    # === TAB 1: PROJECTS ===
    with tab1:
        if len(st.session_state.project_db) < 2:
            st.info("⚠️ Need at least 2 Scratch/Pictoblox files to compare.")
        else:
            pairs = list(combinations(st.session_state.project_db.keys(), 2))
            found_proj = False
            
            for n1, n2 in pairs:
                d1 = st.session_state.project_db[n1]
                d2 = st.session_state.project_db[n2]
                
                # 1. Exact Binary
                if d1['hash'] == d2['hash']:
                    found_proj = True
                    st.markdown(f"""<div class="report-card"><h4>🚨 EXACT FILE COPY</h4><p><b class="student-name">{n1}</b> & <b class="student-name">{n2}</b></p><p>Files are 100% binary identical.</p></div>""", unsafe_allow_html=True)
                    report_lines.append(f"[CRITICAL] Exact Project Copy: {n1} == {n2}")
                    continue

                # 2. Logic Similarity
                matcher = difflib.SequenceMatcher(None, d1['logic'], d2['logic'])
                sim = matcher.ratio() * 100
                
                if sim >= code_sim_threshold:
                    found_proj = True
                    shared_assets = len(d1['assets'].intersection(d2['assets']))
                    
                    with st.expander(f"⚠️ {n1} vs {n2} (Match: {sim:.1f}%)"):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Logic Match", f"{sim:.1f}%")
                        c2.metric("Shared Assets", f"{shared_assets}")
                        c3.metric("Sprites", f"{d1['sprites']} / {d2['sprites']}")
                        
                        st.warning(f"Suspected copying of code logic.")
                        report_lines.append(f"[WARNING] Code Logic Match: {n1} vs {n2} ({sim:.1f}%)")
            
            if not found_proj:
                st.success("✅ No code plagiarism detected.")

    # === TAB 2: IMAGES ===
    with tab2:
        if len(st.session_state.image_db) < 2:
            st.info("⚠️ Need at least 2 images to compare.")
        else:
            pairs = list(combinations(st.session_state.image_db.keys(), 2))
            found_img = False
            
            for n1, n2 in pairs:
                d1 = st.session_state.image_db[n1]
                d2 = st.session_state.image_db[n2]
                
                # Visual Diff (Hamming Distance)
                diff = d1['phash'] - d2['phash']
                
                if diff <= visual_sim_threshold:
                    found_img = True
                    st.markdown(f"#### 👁️ Visual Match Detected")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.image(d1['obj'], caption=f"Student: {n1}", use_container_width=True)
                    with c2:
                        st.image(d2['obj'], caption=f"Student: {n2}", use_container_width=True)
                    
                    st.caption(f"Difference Score: {diff} (Lower is more similar)")
                    st.divider()
                    report_lines.append(f"[VISUAL] Image Match: {n1} vs {n2} (Diff: {diff})")
            
            if not found_img:
                st.success("✅ No suspicious images found.")

    # === TAB 3: VIDEOS ===
    with tab3:
        if len(st.session_state.video_db) < 2:
            st.info("⚠️ Need at least 2 videos to compare.")
        else:
            pairs = list(combinations(st.session_state.video_db.keys(), 2))
            found_vid = False
            
            for n1, n2 in pairs:
                d1 = st.session_state.video_db[n1]
                d2 = st.session_state.video_db[n2]
                
                # Check Size AND Hash (Fast & Accurate)
                if d1['size'] == d2['size'] and d1['hash'] == d2['hash']:
                    found_vid = True
                    st.markdown(f"""<div class="report-card"><h4>🎬 DUPLICATE VIDEO FILE</h4><p><b class="student-name">{n1}</b> & <b class="student-name">{n2}</b></p><p>Video files are identical in size and data.</p></div>""", unsafe_allow_html=True)
                    report_lines.append(f"[VIDEO] Exact Copy: {n1} == {n2}")
            
            if not found_vid:
                st.success("✅ No duplicate videos found.")

    # === TAB 4: REPORT ===
    with tab4:
        st.subheader("📝 Official Forensics Report")
        
        final_report = "\n".join(report_lines)
        if not final_report:
            final_report = "Analysis Complete. No plagiarism issues detected in this batch."
            
        st.text_area("Log", final_report, height=300)
        
        st.download_button(
            label="📥 Download Official Report (.txt)",
            data="LITTLE KITES FORENSICS REPORT\nEvaluate by: Midhun T V\n----------------------------------\n" + final_report,
            file_name="forensics_report.txt",
            mime="text/plain"
        )

# --- FOOTER ---
st.markdown("""
<div class="footer">
    <b>Little KITES Forensics Suite</b><br>
    Developed by <b>Midhun T V</b>, Master Trainer, KITE Kasaragod
</div>
""", unsafe_allow_html=True)
