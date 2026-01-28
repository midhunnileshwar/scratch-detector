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
    page_title="Little KITES Forensics Tool",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROFESSIONAL UI STYLING (CSS) ---
st.markdown("""
    <style>
    /* Main Background */
    .main {
        background-color: #f4f6f9;
    }
    
    /* Header Styling */
    h1 {
        color: #2c3e50;
        font-family: 'Helvetica Neue', sans-serif;
    }
    h3 {
        color: #34495e;
    }
    
    /* Card Container for Results */
    .result-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        border-left: 5px solid #3498db;
    }
    
    /* Critical Alert Card */
    .alert-card {
        background-color: #fff5f5;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        border-left: 5px solid #e74c3c;
    }
    
    /* Developer Footer */
    .dev-footer {
        text-align: center;
        margin-top: 50px;
        padding: 20px;
        color: #7f8c8d;
        font-size: 0.9em;
        border-top: 1px solid #bdc3c7;
    }
    
    /* Button Styling */
    .stButton>button {
        background-color: #2980b9;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #3498db;
        border-color: #3498db;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC FUNCTIONS (Core Forensics) ---
def get_file_hash(bytes_data):
    return hashlib.md5(bytes_data).hexdigest()

def get_image_phash(image_file):
    try:
        img = Image.open(image_file)
        return imagehash.phash(img)
    except:
        return None

def extract_project_data(bytes_data):
    logic_signature = []
    asset_hashes = set()
    sprite_names = []
    
    try:
        with zipfile.ZipFile(bytes_data) as z:
            for f in z.namelist():
                if f != 'project.json':
                    data = z.read(f)
                    asset_hashes.add(hashlib.md5(data).hexdigest())
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
    parts = path.replace("\\", "/").split("/")
    filename = parts[-1]
    if len(parts) > 1:
        if any(x in filename.lower() for x in ['assignment', 'project', 'untitled', 'game']):
            return parts[-2]
    return os.path.splitext(filename)[0]

# --- SIDEBAR (Developer Profile) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/121px-Python-logo-notext.svg.png", width=60)
    
    st.markdown("""
    ## 🛡️ Forensics Tool
    **Version 5.0**
    """)
    
    st.markdown("---")
    
    # DEVELOPER PROFILE
    st.markdown("### 👨‍💻 Developed By")
    st.markdown("""
    **Midhun T V** *Master Trainer* KITE Kasaragod
    """)
    
    st.markdown("---")
    
    st.markdown("### ⚙️ Sensitivity")
    code_sim_threshold = st.slider("Code Similarity (%)", 50, 100, 85)
    visual_sim_threshold = st.slider("Image Tolerance", 0, 20, 10)
    
    st.info("Tip: For class folders, zip the entire folder and upload one .zip file.")

# --- MAIN PAGE ---
st.title("🛡️ Little KITES Forensics Suite")
st.markdown("#### Advanced Plagiarism Detection for Scratch, Pictoblox & Digital Posters")
st.markdown("---")

# File Uploader
uploaded_files = st.file_uploader(
    "📂 Drop Student Files Here (Support: .sb3, .p3b, .png, .jpg, .zip)", 
    type=["sb3", "p3b", "png", "jpg", "jpeg", "zip"], 
    accept_multiple_files=True
)

if uploaded_files:
    # Processing Visual
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    project_files = {} 
    image_files = {}   
    
    # --- FILE PROCESSING ENGINE ---
    status_text.text("📦 Unpacking and indexing files...")
    
    for i, up_file in enumerate(uploaded_files):
        # Update progress
        progress = int((i + 1) / len(uploaded_files) * 100)
        progress_bar.progress(progress)
        
        # ZIP HANDLING
        if up_file.name.endswith(".zip"):
            try:
                with zipfile.ZipFile(up_file) as z:
                    for filename in z.namelist():
                        if "__MACOSX" in filename or filename.startswith("."): continue
                        ext = filename.split('.')[-1].lower()
                        
                        if ext in ['sb3', 'p3b']:
                            f_bytes = io.BytesIO(z.read(filename))
                            s_name = determine_student_name(filename)
                            h = get_file_hash(f_bytes.getvalue())
                            l, a, s = extract_project_data(f_bytes)
                            if l:
                                if s_name in project_files: s_name += f"_{len(project_files)}"
                                project_files[s_name] = {'hash': h, 'logic': l, 'assets': a, 'sprites': s}

                        elif ext in ['png', 'jpg', 'jpeg']:
                            f_bytes = io.BytesIO(z.read(filename))
                            s_name = determine_student_name(filename)
                            h = get_file_hash(f_bytes.getvalue())
                            ph = get_image_phash(f_bytes)
                            if ph:
                                if s_name in image_files: s_name += f"_{len(image_files)}"
                                image_files[s_name] = {'hash': h, 'phash': ph, 'obj': f_bytes}
            except: st.error(f"Error reading zip: {up_file.name}")

        # SINGLE FILE HANDLING
        else:
            ext = up_file.name.split('.')[-1].lower()
            s_name = os.path.splitext(up_file.name)[0]
            up_file.seek(0)
            
            if ext in ['sb3', 'p3b']:
                h = get_file_hash(up_file.getvalue())
                l, a, s = extract_project_data(up_file)
                if l: project_files[s_name] = {'hash': h, 'logic': l, 'assets': a, 'sprites': s}
            
            elif ext in ['png', 'jpg', 'jpeg']:
                h = get_file_hash(up_file.getvalue())
                ph = get_image_phash(up_file)
                if ph: image_files[s_name] = {'hash': h, 'phash': ph, 'obj': up_file}

    progress_bar.empty()
    status_text.empty()
    
    # --- TABS INTERFACE ---
    tab1, tab2, tab3 = st.tabs(["🧩 Project Forensics", "🖼️ Visual Forensics", "📄 Official Report"])

    # TAB 1: CODE ANALYSIS
    with tab1:
        st.subheader("Scratch & Pictoblox Logic Analysis")
        if len(project_files) < 2:
            st.info("⚠️ Needs at least 2 project files to compare.")
        else:
            pairs = list(combinations(project_files.keys(), 2))
            found_any = False
            
            for n1, n2 in pairs:
                d1, d2 = project_files[n1], project_files[n2]
                
                # Check 1: EXACT COPY
                if d1['hash'] == d2['hash']:
                    found_any = True
                    st.markdown(f"""
                    <div class="alert-card">
                        <h4>🚨 EXACT BINARY COPY DETECTED</h4>
                        <p><b>{n1}</b> is identical to <b>{n2}</b></p>
                        <p><i>The file was renamed without being opened or modified.</i></p>
                    </div>
                    """, unsafe_allow_html=True)
                    continue

                # Check 2: LOGIC SIMILARITY
                matcher = difflib.SequenceMatcher(None, d1['logic'], d2['logic'])
                sim = matcher.ratio() * 100
                
                if sim >= code_sim_threshold:
                    found_any = True
                    with st.container():
                        st.markdown(f"""
                        <div class="result-card">
                            <h4>⚠️ Suspicious Similarity: {n1} vs {n2}</h4>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Logic Match", f"{sim:.1f}%", delta="Critical" if sim > 95 else "High")
                        c2.metric("Shared Assets", f"{len(d1['assets'].intersection(d2['assets']))}")
                        c3.metric("Sprite Count", f"{len(d1['sprites'])} vs {len(d2['sprites'])}")
                        
                        with st.expander("View Details"):
                            st.write(f"Sprite List A: {d1['sprites']}")
                            st.write(f"Sprite List B: {d2['sprites']}")

            if not found_any:
                st.success("✅ No plagiarism detected in projects.")

    # TAB 2: VISUAL ANALYSIS
    with tab2:
        st.subheader("Digital Poster Forensics (AI Vision)")
        if len(image_files) < 2:
            st.info("⚠️ Needs at least 2 images to compare.")
        else:
            pairs = list(combinations(image_files.keys(), 2))
            found_any = False
            
            for n1, n2 in pairs:
                d1, d2 = image_files[n1], image_files[n2]
                
                diff = d1['phash'] - d2['phash']
                if diff <= visual_sim_threshold:
                    found_any = True
                    st.markdown(f"""
                    <div class="result-card">
                        <h4>🖼️ Visual Match: {n1} vs {n2}</h4>
                        <p>Difference Score: {diff} (Lower is more similar)</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    c1.image(d1['obj'], caption=n1, use_container_width=True)
                    c2.image(d2['obj'], caption=n2, use_container_width=True)
                    st.divider()
            
            if not found_any:
                st.success("✅ No suspicious images found.")

    # TAB 3: FOOTER CREDIT
    st.markdown("""
    <div class="dev-footer">
        <b>Little KITES Forensics Suite</b><br>
        Developed by <b>Midhun T V</b>, Master Trainer, KITE Kasaragod<br>
        <i>Strictly for academic evaluation purposes.</i>
    </div>
    """, unsafe_allow_html=True)

else:
    # Empty State (Welcome Screen)
    st.markdown("""
    <div style='text-align: center; padding: 50px; color: #7f8c8d;'>
        <h3>👋 Welcome, Midhun Sir!</h3>
        <p>Upload a <b>ZIP file</b> of the class folder to begin analysis.</p>
    </div>
    """, unsafe_allow_html=True)
