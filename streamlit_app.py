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

# --- Page Config ---
st.set_page_config(
    page_title="KITE Forensics: Pictoblox & Scratch",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    .main {background-color: #f8f9fa;}
    .stButton>button {width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white;}
    .report-box {padding: 15px; border-radius: 8px; border-left: 5px solid #dc3545; background: white; margin-bottom: 10px;}
    .img-match {border: 2px solid red; padding: 5px;}
    </style>
    """, unsafe_allow_html=True)

# --- Logic Functions ---
def get_file_hash(bytes_data):
    """MD5 Binary Hash (Exact Copy Check)"""
    return hashlib.md5(bytes_data).hexdigest()

def get_image_phash(image_file):
    """Perceptual Hash (Visual Similarity Check)"""
    try:
        img = Image.open(image_file)
        return imagehash.phash(img)
    except:
        return None

def extract_project_data(bytes_data):
    """Extracts Logic from .sb3 and .p3b files"""
    logic_signature = []
    asset_hashes = set()
    sprite_names = []
    
    try:
        with zipfile.ZipFile(bytes_data) as z:
            # 1. Internal Asset Analysis
            for f in z.namelist():
                if f != 'project.json':
                    data = z.read(f)
                    asset_hashes.add(hashlib.md5(data).hexdigest())

            # 2. Code Logic Analysis
            if 'project.json' in z.namelist():
                project = json.loads(z.read('project.json'))
                targets = project.get('targets', [])
                targets.sort(key=lambda x: x.get('name', '')) 

                for target in targets:
                    sprite_names.append(target.get('name', 'Unknown'))
                    blocks = target.get('blocks', {})
                    if isinstance(blocks, dict):
                        for block in blocks.values():
                            if isinstance(block, dict) and not block.get('shadow'):
                                opcode = block.get('opcode', 'unknown')
                                logic_signature.append(opcode)
    except Exception:
        return None, None, None

    return "\n".join(logic_signature), asset_hashes, sprite_names

def determine_student_name(path):
    """
    Intelligent Naming:
    - School/Abhishek/Assignment.sb3 -> 'Abhishek'
    - School/Abhishek.sb3 -> 'Abhishek'
    """
    parts = path.replace("\\", "/").split("/")
    filename = parts[-1]
    
    # If file is inside a folder (e.g., 'Abhishek/game.sb3')
    if len(parts) > 1:
        # Check if filename is generic
        if any(x in filename.lower() for x in ['assignment', 'project', 'untitled', 'game', 'activity']):
            return parts[-2] # Return folder name (e.g. 'Abhishek')
            
    # Default: return filename without extension
    return os.path.splitext(filename)[0]

# --- Sidebar ---
with st.sidebar:
    st.title("🕵️‍♂️ Forensics Controls")
    
    st.markdown("### ⚙️ Thresholds")
    code_sim_threshold = st.slider("Code Similarity (%)", 50, 100, 85)
    visual_sim_threshold = st.slider("Image Similarity", 0, 20, 10)
    
    st.info("""
    **New! Folder Support**
    For best results, right-click the
    School folder -> **Compress to Zip**.
    Upload that single `.zip` file!
    """)
    st.caption("v4.0 - Nested Folder Support")

# --- Main UI ---
st.title("Little KITES Forensics Suite")
st.markdown("### 🤖 Pictoblox, Scratch & Digital Poster Analysis")

uploaded_files = st.file_uploader(
    "Upload Assignments (Individual files OR School Folder as .zip)", 
    type=["sb3", "p3b", "png", "jpg", "jpeg", "zip"], 
    accept_multiple_files=True
)

if uploaded_files:
    with st.spinner("Unpacking and analyzing..."):
        
        project_files = {} 
        image_files = {}   
        
        for up_file in uploaded_files:
            # === HANDLING ZIP FOLDERS ===
            if up_file.name.endswith(".zip"):
                try:
                    with zipfile.ZipFile(up_file) as z:
                        for filename in z.namelist():
                            # Skip MacOS hidden folder trash
                            if "__MACOSX" in filename or filename.startswith("."):
                                continue
                            
                            # Identify File Type
                            ext = filename.split('.')[-1].lower()
                            
                            # Process Projects inside Zip
                            if ext in ['sb3', 'p3b']:
                                file_bytes = io.BytesIO(z.read(filename))
                                student_name = determine_student_name(filename)
                                
                                h = get_file_hash(file_bytes.getvalue())
                                l, a, s = extract_project_data(file_bytes)
                                
                                if l:
                                    # Handle duplicate names by appending count
                                    if student_name in project_files:
                                        student_name = f"{student_name}_{len(project_files)}"
                                    
                                    project_files[student_name] = {'hash': h, 'logic': l, 'assets': a, 'sprites': s}

                            # Process Images inside Zip
                            elif ext in ['png', 'jpg', 'jpeg']:
                                file_bytes = io.BytesIO(z.read(filename))
                                student_name = determine_student_name(filename)
                                
                                h = get_file_hash(file_bytes.getvalue())
                                ph = get_image_phash(file_bytes)
                                
                                if ph:
                                    if student_name in image_files:
                                        student_name = f"{student_name}_{len(image_files)}"
                                    image_files[student_name] = {'hash': h, 'phash': ph, 'obj': file_bytes}
                except:
                    st.error(f"Failed to unzip {up_file.name}")

            # === HANDLING INDIVIDUAL FILES ===
            else:
                ext = up_file.name.split('.')[-1].lower()
                student_name = os.path.splitext(up_file.name)[0]
                up_file.seek(0)
                
                if ext in ['sb3', 'p3b']:
                    h = get_file_hash(up_file.getvalue())
                    l, a, s = extract_project_data(up_file)
                    if l:
                        project_files[student_name] = {'hash': h, 'logic': l, 'assets': a, 'sprites': s}
                
                elif ext in ['png', 'jpg', 'jpeg']:
                    h = get_file_hash(up_file.getvalue())
                    ph = get_image_phash(up_file)
                    if ph:
                        image_files[student_name] = {'hash': h, 'phash': ph, 'obj': up_file}

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["💻 Code/Project Analysis", "🖼️ Visual Forensics", "📄 Report"])

        # TAB 1: CODE
        with tab1:
            if len(project_files) < 2:
                st.info("Upload at least 2 project files (or a Zip with multiple projects).")
            else:
                pairs = list(combinations(project_files.keys(), 2))
                found = False
                for n1, n2 in pairs:
                    d1, d2 = project_files[n1], project_files[n2]
                    
                    if d1['hash'] == d2['hash']:
                        st.error(f"🚨 **EXACT COPY:** `{n1}` == `{n2}`")
                        found = True
                        continue

                    matcher = difflib.SequenceMatcher(None, d1['logic'], d2['logic'])
                    sim = matcher.ratio() * 100
                    
                    if sim >= code_sim_threshold:
                        found = True
                        with st.expander(f"⚠️ {n1} vs {n2} ({sim:.1f}%)", expanded=True):
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Similarity", f"{sim:.1f}%")
                            c2.metric("Assets", f"{len(d1['assets'].intersection(d2['assets']))}")
                            c3.metric("Sprites", f"{len(d1['sprites'])} / {len(d2['sprites'])}")
                if not found: st.success("No code plagiarism detected.")

        # TAB 2: VISUAL
        with tab2:
            if len(image_files) < 2:
                st.info("Upload at least 2 images.")
            else:
                pairs = list(combinations(image_files.keys(), 2))
                found = False
                for n1, n2 in pairs:
                    d1, d2 = image_files[n1], image_files[n2]
                    
                    diff = d1['phash'] - d2['phash']
                    if diff <= visual_sim_threshold:
                        found = True
                        st.markdown(f"**⚠️ Visual Match:** `{n1}` vs `{n2}`")
                        c1, c2 = st.columns(2)
                        c1.image(d1['obj'], caption=n1)
                        c2.image(d2['obj'], caption=n2)
                        st.divider()
                if not found: st.success("No suspicious images.")
        
        # TAB 3: REPORT
        with tab3:
             st.write("Use screenshots of previous tabs for evidence.")
