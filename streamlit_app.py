import streamlit as st
import zipfile
import json
import hashlib
import io
import os
import cv2
import numpy as np
from collections import Counter
from itertools import combinations

# -------------------------------------------------
# 1. CONFIGURATION
# -------------------------------------------------
st.set_page_config(
    page_title="KITE Forensics Master",
    page_icon="🛡️",
    layout="wide"
)

# -------------------------------------------------
# 2. CSS STYLING
# -------------------------------------------------
st.markdown("""
<style>
.main {background-color: #f4f7f6;}
.report-card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    border-left: 6px solid #e74c3c;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 12px;
}
.student-tag {
    background-color: #2980b9;
    color: white;
    padding: 5px 10px;
    border-radius: 15px;
    font-weight: bold;
    font-size: 0.9em;
}
.stat-box {
    background: white;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    border-bottom: 4px solid #2980b9;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# 3. UTILITIES
# -------------------------------------------------
def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def extract_student_name(zip_path: str) -> str:
    """
    Robust owner extraction for ANY zip structure
    """
    path = zip_path.replace("\\", "/")
    parts = [p for p in path.split("/") if p and "__MACOSX" not in p]

    ignore = {
        "kids", "kid", "students", "student", "class", "class9", "class10",
        "assets", "files", "images", "image", "projects", "project",
        "src", "data", "uploads"
    }

    # Walk backwards ignoring wrappers
    for part in reversed(parts[:-1]):
        if part.lower() not in ignore:
            return part.replace("_", " ").title()

    # Fallback to filename
    return os.path.splitext(parts[-1])[0].replace("_", " ").title()

def get_image_histogram(file_obj):
    try:
        arr = np.asarray(bytearray(file_obj.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        img = cv2.resize(img, (256, 256))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None,
                            [8, 8, 8], [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        return hist.flatten()
    except Exception:
        return None

# -------------------------------------------------
# 4. SCRATCH / PICTOBLOX EXTRACTION
# -------------------------------------------------
def extract_project_logic(file_obj):
    opcode_list = []
    asset_hashes = set()
    sprite_count = 0

    try:
        with zipfile.ZipFile(file_obj) as z:
            for name in z.namelist():
                if name != "project.json" and not name.endswith("/"):
                    asset_hashes.add(sha256(z.read(name)))

            if "project.json" not in z.namelist():
                return None, None, 0

            data = json.loads(z.read("project.json"))
            targets = sorted(data.get("targets", []), key=lambda x: x.get("name", ""))
            sprite_count = len(targets)

            for t in targets:
                blocks = t.get("blocks", {})
                if isinstance(blocks, dict):
                    for b in blocks.values():
                        if isinstance(b, dict) and not b.get("shadow"):
                            opcode_list.append(b.get("opcode", "unknown"))
                elif isinstance(blocks, list):
                    for b in blocks:
                        if isinstance(b, dict) and not b.get("shadow"):
                            opcode_list.append(b.get("opcode", "unknown"))

    except Exception:
        return None, None, 0

    return Counter(opcode_list), asset_hashes, sprite_count

# -------------------------------------------------
# 5. SIDEBAR
# -------------------------------------------------
with st.sidebar:
    st.markdown("## 🛡️ Forensics Master")
    st.caption("v12.0 – Folder-Agnostic Engine")
    st.markdown("---")
    st.info("**Developed by Midhun T V**  \nMaster Trainer  \nKITE Kasaragod")
    st.markdown("---")
    code_thresh = st.slider("Code Similarity (%)", 60, 100, 85)
    img_thresh = st.slider("Poster Similarity (%)", 50, 100, 80)

# -------------------------------------------------
# 6. MAIN UI
# -------------------------------------------------
st.title("🛡️ Little KITES Forensics Suite")
st.markdown("#### Scratch • Posters • Videos (ZIP Safe Analysis)")

uploaded = st.file_uploader(
    "📂 Upload ZIP or Files",
    type=["zip", "sb3", "p3b", "png", "jpg", "jpeg", "mp4", "mkv"],
    accept_multiple_files=True
)

projects = {}
images = {}
videos = {}

# -------------------------------------------------
# 7. FILE INGESTION (ZIP-SAFE)
# -------------------------------------------------
if uploaded:
    with st.spinner("Analyzing submissions..."):
        for up in uploaded:
            if up.name.endswith(".zip"):
                with zipfile.ZipFile(up) as z:
                    for path in z.namelist():
                        if path.endswith("/") or "__MACOSX" in path:
                            continue

                        owner = extract_student_name(path)
                        ext = path.split(".")[-1].lower()
                        data = z.read(path)

                        if ext in ["sb3", "p3b"]:
                            logic, assets, sprites = extract_project_logic(io.BytesIO(data))
                            if logic:
                                projects[owner] = {
                                    "hash": sha256(data),
                                    "logic": logic,
                                    "assets": assets,
                                    "sprites": sprites
                                }

                        elif ext in ["png", "jpg", "jpeg"]:
                            hist = get_image_histogram(io.BytesIO(data))
                            if hist is not None:
                                images.setdefault(owner, []).append({
                                    "hist": hist,
                                    "obj": io.BytesIO(data)
                                })

                        elif ext in ["mp4", "mkv"]:
                            videos.setdefault(owner, []).append(sha256(data))

# -------------------------------------------------
# 8. DASHBOARD
# -------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.markdown(f"<div class='stat-box'><h4>🧩 Projects</h4><h2>{len(projects)}</h2></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='stat-box'><h4>🖼️ Students with Posters</h4><h2>{len(images)}</h2></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='stat-box'><h4>🎥 Students with Videos</h4><h2>{len(videos)}</h2></div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🧩 Code", "🖼️ Posters", "🎥 Videos"])

# -------------------------------------------------
# 9. POSTER ANALYSIS (FIXED)
# -------------------------------------------------
with tab2:
    owners = list(images.keys())
    if len(owners) < 2:
        st.warning("Upload posters from at least two different students.")
    else:
        found = False
        for s1, s2 in combinations(owners, 2):
            for i1 in images[s1]:
                for i2 in images[s2]:
                    sim = cv2.compareHist(i1["hist"], i2["hist"],
                                          cv2.HISTCMP_CORREL) * 100
                    if sim >= img_thresh:
                        found = True
                        st.markdown(f"""
                        <div class="report-card">
                            <h4>🎨 Visual Similarity: {sim:.1f}%</h4>
                            <span class="student-tag">{s1}</span>
                            vs
                            <span class="student-tag">{s2}</span>
                        </div>
                        """, unsafe_allow_html=True)
        if not found:
            st.success("✅ No poster plagiarism detected.")

