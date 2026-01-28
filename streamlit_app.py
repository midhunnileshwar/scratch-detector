import streamlit as st
import zipfile
import json
import hashlib
import difflib
from itertools import combinations
import io
from PIL import Image
import imagehash

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
        # phash is excellent for finding modified/resized images
        return imagehash.phash(img)
    except:
        return None

def extract_project_data(bytes_data, filename):
    """Extracts Logic from .sb3 and .p3b (Pictoblox) files"""
    logic_signature = []
    asset_hashes = set()
    sprite_names = []
    
    try:
        # Pictoblox and Scratch are both ZIPs
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

# --- Sidebar ---
with st.sidebar:
    st.title("🕵️‍♂️ Forensics Controls")
    
    st.markdown("### ⚙️ Thresholds")
    code_sim_threshold = st.slider("Code Similarity (%)", 50, 100, 85)
    visual_sim_threshold = st.slider("Image Similarity (Diff)", 0, 20, 10, help="Lower is stricter. 0 = Exact, 10 = Similar")
    
    st.info("""
    **Supported Files:**
    * 🐱 Scratch (`.sb3`)
    * 🤖 Pictoblox (`.p3b`)
    * 🖼️ Images (`.jpg`, `.png`)
    """)
    st.caption("v3.0 - Visual & Logic Core")

# --- Main UI ---
st.title("Little KITES Forensics Suite")
st.markdown("### 🤖 Pictoblox, Scratch & Digital Poster Analysis")

uploaded_files = st.file_uploader(
    "Upload Assignments (.sb3, .p3b, .png, .jpg)", 
    type=["sb3", "p3b", "png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if uploaded_files:
    if len(uploaded_files) < 2:
        st.warning("⚠️ Upload at least 2 files to compare.")
    else:
        with st.spinner(f"Analyzing {len(uploaded_files)} files..."):
            
            # --- Categorize Files ---
            project_files = {} # for sb3/p3b
            image_files = {}   # for png/jpg
            
            for f in uploaded_files:
                ext = f.name.split('.')[-1].lower()
                f.seek(0) # Reset pointer
                
                if ext in ['sb3', 'p3b']:
                    h = get_file_hash(f.getvalue())
                    l, a, s = extract_project_data(f, f.name)
                    if l is not None:
                        project_files[f.name] = {'hash': h, 'logic': l, 'assets': a, 'sprites': s}
                
                elif ext in ['png', 'jpg', 'jpeg']:
                    h = get_file_hash(f.getvalue()) # Binary hash
                    ph = get_image_phash(f)         # Visual hash
                    if ph:
                        image_files[f.name] = {'hash': h, 'phash': ph, 'obj': f}

            # --- TABS ---
            tab1, tab2, tab3 = st.tabs(["💻 Code/Project Analysis", "🖼️ Visual Forensics (Posters)", "📊 Full Report"])

            # ==========================
            # TAB 1: CODE & PROJECTS
            # ==========================
            with tab1:
                st.subheader("Scratch & Pictoblox Assessment")
                if len(project_files) < 2:
                    st.info("Not enough project files (.sb3/.p3b) to compare.")
                else:
                    pairs = list(combinations(project_files.keys(), 2))
                    found_issues = False
                    
                    for n1, n2 in pairs:
                        d1, d2 = project_files[n1], project_files[n2]
                        
                        # 1. Exact Binary Check
                        if d1['hash'] == d2['hash']:
                            st.error(f"🚨 **EXACT COPY:** `{n1}` is identical to `{n2}`")
                            found_issues = True
                            continue

                        # 2. Logic Check
                        matcher = difflib.SequenceMatcher(None, d1['logic'], d2['logic'])
                        sim = matcher.ratio() * 100
                        shared_assets = len(d1['assets'].intersection(d2['assets']))
                        
                        if sim >= code_sim_threshold:
                            found_issues = True
                            with st.expander(f"⚠️ {n1} vs {n2} (Logic: {sim:.1f}%)", expanded=True):
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Code Similarity", f"{sim:.1f}%")
                                c2.metric("Shared Assets", f"{shared_assets}")
                                c3.metric("Sprite Count", f"{len(d1['sprites'])} / {len(d2['sprites'])}")
                                
                                if "Pictoblox" in d1['logic'] or "Pictoblox" in d2['logic']:
                                    st.caption("🤖 Pictoblox extensions detected.")

                    if not found_issues:
                        st.success("✅ No code plagiarism detected.")

            # ==========================
            # TAB 2: VISUAL FORENSICS
            # ==========================
            with tab2:
                st.subheader("Digital Poster & Image Analysis")
                st.caption("Uses AI Vision to detect images that look similar, even if renamed or resized.")
                
                if len(image_files) < 2:
                    st.info("Not enough image files to compare.")
                else:
                    img_pairs = list(combinations(image_files.keys(), 2))
                    visual_issues = False
                    
                    for n1, n2 in img_pairs:
                        d1, d2 = image_files[n1], image_files[n2]
                        
                        # 1. Exact Binary Match
                        if d1['hash'] == d2['hash']:
                            st.error(f"🚨 **EXACT DUPLICATE:** `{n1}` == `{n2}` (Binary Match)")
                            visual_issues = True
                            continue
                            
                        # 2. Visual Similarity (Perceptual Hash)
                        # The difference between hashes tells us how different the images look
                        diff = d1['phash'] - d2['phash']
                        
                        if diff <= visual_sim_threshold:
                            visual_issues = True
                            st.markdown(f"**⚠️ Visual Match Found:** `{n1}` vs `{n2}`")
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.image(d1['obj'], caption=n1, use_container_width=True)
                            with col_b:
                                st.image(d2['obj'], caption=n2, use_container_width=True)
                            
                            st.caption(f"Visual Difference Score: {diff} (Lower is more similar)")
                            st.divider()

                    if not visual_issues:
                        st.success("✅ No suspicious images found.")

            # ==========================
            # TAB 3: REPORT
            # ==========================
            with tab3:
                st.write("Generate a text summary of all findings above.")
                if st.button("📄 Generate Report Log"):
                    st.text("Processing complete. (Use screenshots of tabs above for evidence).")
