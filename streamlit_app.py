import streamlit as st
import zipfile
import json
import hashlib
import difflib
import io
import os
import cv2
import numpy as np
from collections import Counter
from PIL import Image
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
# 3. CORE UTILITIES
# -------------------------------------------------
def get_file_hash(bytes_data: bytes) -> str:
    """SHA-256 hash for reliable duplicate detection"""
    return hashlib.sha256(bytes_data).hexdigest()

def get_image_histogram(file_obj):
    """Normalized HSV histogram for poster similarity"""
    try:
        file_bytes = np.asarray(bytearray(file_obj.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
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
def extract_project_logic(file_bytes):
    """
    Reads .sb3 and .p3b files
    Returns:
        opcode_counter (Counter)
        asset_hashes (set)
        sprite_count (int)
    """
    opcode_list = []
    asset_hashes = set()
    sprite_count = 0

    try:
        with zipfile.ZipFile(file_bytes) as z:
            for f in z.namelist():
                if f != "project.json" and not f.endswith("/"):
                    asset_hashes.add(get_file_hash(z.read(f)))

            if "project.json" not in z.namelist():
                return None, None, 0

            data = json.loads(z.read("project.json"))
            targets = data.get("targets", [])
            targets.sort(key=lambda x: x.get("name", ""))
            sprite_count = len(targets)

            for target in targets:
                blocks = target.get("blocks", {})
                if isinstance(blocks, dict):
                    for block in blocks.values():
                        if isinstance(block, dict) and not block.get("shadow"):
                            opcode_list.append(block.get("opcode", "unknown"))
                elif isinstance(blocks, list):
                    for block in blocks:
                        if isinstance(block, dict) and not block.get("shadow"):
                            opcode_list.append(block.get("opcode", "unknown"))

    except Exception:
        return None, None, 0

    return Counter(opcode_list), asset_hashes, sprite_count

def extract_student_name(path):
    path = path.replace("\\", "/")
    parts = [p for p in path.split("/") if p and "__MACOSX" not in p]

    if len(parts) > 1:
        folder = parts[-2]
        if folder.lower() not in ["images", "sounds", "src", "project"]:
            return folder

    return os.path.splitext(parts[-1])[0].replace("_", " ").title()

# -------------------------------------------------
# 5. SIDEBAR
# -------------------------------------------------
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/121px-Python-logo-notext.svg.png",
        width=60
    )
    st.markdown("## 🛡️ Forensics Master")
    st.caption("v11.0 – Structural Logic Engine")
    st.markdown("---")
    st.info("**Developed by Midhun T V**  \nMaster Trainer  \nKITE Kasaragod")
    st.markdown("---")

    code_thresh = st.slider("Code Similarity Threshold", 60, 100, 85)
    img_thresh = st.slider("Poster Similarity Threshold", 50, 100, 80)

# -------------------------------------------------
# 6. MAIN INTERFACE
# -------------------------------------------------
st.title("🛡️ Little KITES Forensics Suite V2.0")
st.markdown("#### Scratch (.sb3) & PictoBlox (.p3b) Plagiarism Analysis")

uploaded_files = st.file_uploader(
    "📂 Upload ZIP or Individual Files",
    type=["zip", "sb3", "p3b", "png", "jpg", "jpeg", "mp4", "mkv"],
    accept_multiple_files=True
)

projects, images, videos = {}, {}, {}

# -------------------------------------------------
# 7. FILE PROCESSING
# -------------------------------------------------
if uploaded_files:
    with st.spinner("Processing submissions..."):
        for up in uploaded_files:
            if up.name.endswith(".zip"):
                try:
                    with zipfile.ZipFile(up) as z:
                        for fname in z.namelist():
                            if fname.endswith("/") or "__MACOSX" in fname:
                                continue

                            owner = extract_student_name(fname)
                            ext = fname.split(".")[-1].lower()
                            data = z.read(fname)

                            if ext in ["sb3", "p3b"]:
                                raw = io.BytesIO(data)
                                logic, assets, sprites = extract_project_logic(raw)
                                if logic:
                                    projects[owner] = {
                                        "hash": get_file_hash(data),
                                        "logic": logic,
                                        "assets": assets,
                                        "sprites": sprites
                                    }

                            elif ext in ["png", "jpg", "jpeg"]:
                                raw = io.BytesIO(data)
                                hist = get_image_histogram(raw)
                                if hist is not None:
                                    images[owner] = {"hist": hist, "obj": raw}

                            elif ext in ["mp4", "mkv"]:
                                videos[owner] = {
                                    "hash": get_file_hash(data),
                                    "size": len(data)
                                }
                except Exception:
                    st.error(f"Error reading {up.name}")

# -------------------------------------------------
# 8. DASHBOARD
# -------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.markdown(f"<div class='stat-box'><h4>🧩 Projects</h4><h2>{len(projects)}</h2></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='stat-box'><h4>🖼️ Posters</h4><h2>{len(images)}</h2></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='stat-box'><h4>🎥 Videos</h4><h2>{len(videos)}</h2></div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🧩 Code Analysis", "🖼️ Poster Analysis", "🎥 Video Analysis"])

# -------------------------------------------------
# 9. PROJECT ANALYSIS
# -------------------------------------------------
with tab1:
    if len(projects) < 2:
        st.info("Upload at least two Scratch/PictoBlox files.")
    else:
        found = False
        for p1, p2 in combinations(projects.keys(), 2):
            d1, d2 = projects[p1], projects[p2]

            if d1["hash"] == d2["hash"]:
                found = True
                st.markdown(f"""
                <div class="report-card">
                    <h4>🚨 Exact Project Copy</h4>
                    <span class="student-tag">{p1}</span> == <span class="student-tag">{p2}</span>
                </div>
                """, unsafe_allow_html=True)
                continue

            common_assets = len(d1["assets"] & d2["assets"])
            total_assets = max(len(d1["assets"]), 1)

            opcode_similarity = (
                sum((d1["logic"] & d2["logic"]).values()) /
                max(sum(d1["logic"].values()), sum(d2["logic"].values()))
            ) * 100

            if opcode_similarity >= code_thresh:
                found = True
                st.markdown(f"""
                <div class="report-card">
                    <h4>⚠️ Structural Code Similarity: {opcode_similarity:.1f}%</h4>
                    <span class="student-tag">{p1}</span> vs <span class="student-tag">{p2}</span><br><br>
                    <b>Sprites:</b> {d1['sprites']} vs {d2['sprites']}<br>
                    <b>Shared Assets:</b> {common_assets}
                </div>
                """, unsafe_allow_html=True)

        if not found:
            st.success("✅ No significant code similarity detected.")

# -------------------------------------------------
# 10. POSTER ANALYSIS
# -------------------------------------------------
with tab2:
    if len(images) < 2:
        st.info("Upload at least two images.")
    else:
        found = False
        for p1, p2 in combinations(images.keys(), 2):
            sim = cv2.compareHist(images[p1]["hist"], images[p2]["hist"], cv2.HISTCMP_CORREL) * 100
            if sim >= img_thresh:
                found = True
                st.markdown(f"""
                <div class="report-card">
                    <h4>🎨 Visual Similarity: {sim:.1f}%</h4>
                    <span class="student-tag">{p1}</span> vs <span class="student-tag">{p2}</span>
                </div>
                """, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                col1.image(images[p1]["obj"], caption=p1, width=220)
                col2.image(images[p2]["obj"], caption=p2, width=220)

        if not found:
            st.success("✅ No poster plagiarism detected.")

# -------------------------------------------------
# 11. VIDEO ANALYSIS
# -------------------------------------------------
with tab3:
    if len(videos) < 2:
        st.info("Upload at least two videos.")
    else:
        found = False
        for p1, p2 in combinations(videos.keys(), 2):
            if videos[p1]["hash"] == videos[p2]["hash"]:
                found = True
                st.markdown(f"""
                <div class="report-card">
                    <h4>🎥 Duplicate Video Detected</h4>
                    <span class="student-tag">{p1}</span> == <span class="student-tag">{p2}</span>
                </div>
                """, unsafe_allow_html=True)

        if not found:
            st.success("✅ No duplicate videos detected.")
