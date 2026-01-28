import streamlit as st
import zipfile
import json
import hashlib
import difflib
from itertools import combinations
import io

# --- Page Config ---
st.set_page_config(
    page_title="Little KITES Forensics",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# --- Custom CSS for KITE Look ---
st.markdown("""
    <style>
    .main {background-color: #f0f2f6;}
    .stButton>button {width: 100%; border-radius: 5px; height: 3em;}
    .report-box {background-color: white; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b;}
    </style>
    """, unsafe_allow_html=True)

# --- Logic Functions ---
def get_file_hash(bytes_data):
    return hashlib.md5(bytes_data).hexdigest()

def extract_project_data(bytes_data):
    logic_signature = []
    asset_hashes = set()
    sprite_names = []
    
    try:
        with zipfile.ZipFile(bytes_data) as z:
            # 1. Asset Analysis
            for filename in z.namelist():
                if filename != 'project.json':
                    data = z.read(filename)
                    asset_hashes.add(hashlib.md5(data).hexdigest())

            # 2. Logic Analysis
            if 'project.json' in z.namelist():
                project = json.loads(z.read('project.json'))
                targets = project.get('targets', [])
                
                # Sort to ignore sprite order changes
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
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Python.svg/1200px-Python.svg.png", width=50)
    st.title("Forensics Controls")
    
    st.markdown("### ⚙️ Settings")
    similarity_threshold = st.slider("Similarity Threshold (%)", 50, 100, 85)
    min_assets = st.slider("Min Shared Assets", 1, 10, 3)
    
    st.info("""
    **How to use:**
    1. Upload all .sb3 files.
    2. Check the 'Binary Check' tab for exact copies.
    3. Check 'Deep Analysis' for modified copies.
    4. Download the report.
    """)
    st.markdown("---")
    st.caption("Developed for KITE KASARGOD")

# --- Main Interface ---
st.title("🕵️‍♂️ Scratch Plagiarism Detector")
st.markdown("### Digital Forensics Tool for Assignment Evaluation")

uploaded_files = st.file_uploader("Drop Student Assignments Here (.sb3)", type="sb3", accept_multiple_files=True)

if uploaded_files:
    if len(uploaded_files) < 2:
        st.warning("⚠️ Please upload at least 2 files to perform a comparison.")
    else:
        # --- Processing Indicator ---
        with st.spinner(f"Analyzing {len(uploaded_files)} files..."):
            file_data = {}
            report_lines = []
            
            # 1. Extraction Phase
            for uploaded_file in uploaded_files:
                bytes_data = uploaded_file
                fname = uploaded_file.name
                h = get_file_hash(bytes_data)
                l, a, s = extract_project_data(bytes_data)
                
                if l is not None:
                    file_data[fname] = {'hash': h, 'logic': l, 'assets': a, 'sprites': s}
                else:
                    st.toast(f"Error reading {fname}", icon="❌")

            # --- TABS LAYOUT ---
            tab1, tab2, tab3 = st.tabs(["⚡ Binary Check", "🧠 Deep Logic Analysis", "📂 Evidence Report"])

            # --- TAB 1: Exact Binary Duplicates ---
            with tab1:
                st.subheader("Phase 1: Exact File Duplicates")
                st.caption("Students who simply renamed the file without opening it.")
                
                seen_hashes = {}
                duplicates = []
                
                for name, data in file_data.items():
                    h = data['hash']
                    if h in seen_hashes:
                        duplicates.append((name, seen_hashes[h]))
                    else:
                        seen_hashes[h] = name
                
                if duplicates:
                    for copy, original in duplicates:
                        st.error(f"🚨 **MATCH FOUND:** `{copy}` is a binary copy of `{original}`")
                        report_lines.append(f"[BINARY MATCH] {copy} == {original}")
                else:
                    st.success("✅ No exact binary duplicates found.")

            # --- TAB 2: Deep Logic Analysis ---
            with tab2:
                st.subheader("Phase 2: Code Logic & Asset Forensics")
                st.caption(f"Flagging pairs with >{similarity_threshold}% code similarity.")
                
                pairs = list(combinations(file_data.keys(), 2))
                suspicious_found = False
                
                for n1, n2 in pairs:
                    d1, d2 = file_data[n1], file_data[n2]
                    
                    # Logic Check
                    matcher = difflib.SequenceMatcher(None, d1['logic'], d2['logic'])
                    sim = matcher.ratio() * 100
                    
                    # Asset Check
                    shared_assets = d1['assets'].intersection(d2['assets'])
                    shared_count = len(shared_assets)
                    
                    # Flags
                    is_logic_match = sim >= similarity_threshold
                    is_asset_match = shared_count >= min_assets
                    
                    if is_logic_match or is_asset_match:
                        suspicious_found = True
                        
                        # Visual Report Box
                        with st.expander(f"⚠️ {n1} vs {n2} ({sim:.1f}%)", expanded=True):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Logic Similarity", f"{sim:.1f}%")
                            with col2:
                                st.metric("Shared Assets", f"{shared_count} files")
                            with col3:
                                # Show sprite count difference
                                s1_count = len(d1['sprites'])
                                s2_count = len(d2['sprites'])
                                st.metric("Sprite Count", f"{s1_count} / {s2_count}")
                                
                            if is_asset_match:
                                st.warning(f"🎨 These students share {shared_count} identical custom images/sounds.")
                            
                            # Add to downloadable report
                            report_lines.append(f"[LOGIC MATCH] {n1} vs {n2} | Similarity: {sim:.1f}% | Shared Assets: {shared_count}")

                if not suspicious_found:
                    st.success("✨ No suspicious logic similarities detected.")

            # --- TAB 3: Download Report ---
            with tab3:
                st.subheader("Generated Forensics Report")
                
                report_text = "\n".join(report_lines)
                if not report_text:
                    report_text = "No plagiarism detected in this batch."
                    
                st.text_area("Log Preview", report_text, height=300)
                
                st.download_button(
                    label="📥 Download Full Report (.txt)",
                    data="LITTLE KITES PLAGIARISM REPORT\n------------------------------\n" + report_text,
                    file_name="plagiarism_report.txt",
                    mime="text/plain"
                )
