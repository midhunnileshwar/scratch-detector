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
# CONFIG
# -------------------------------------------------
st.set_page_config("KITE Forensics Master 3.0", "🛡️", layout="wide")

# -------------------------------------------------
# UTILS
# -------------------------------------------------
def sha256(data):
    return hashlib.sha256(data).hexdigest()

def extract_student_name(path):
    path = path.replace("\\", "/")
    parts = [p for p in path.split("/") if p and "__MACOSX" not in p]

    ignore = {
        "kids", "students", "student", "class", "class9", "class10",
        "assets", "files", "images", "projects", "project",
        "src", "data", "uploads"
    }

    for part in reversed(parts[:-1]):
        if part.lower() not in ignore:
            return part.replace("_", " ").title()

    return os.path.splitext(parts[-1])[0].replace("_", " ").title()

# -------------------------------------------------
# PROJECT EXTRACTOR (CONFIRMED SAFE)
# -------------------------------------------------
def extract_project_logic(file_obj):
    opcodes = []
    assets = set()
    sprite_count = 0

    try:
        file_obj.seek(0)
        with zipfile.ZipFile(file_obj) as z:

            if "project.json" not in z.namelist():
                return None

            for name in z.namelist():
                if name != "project.json" and not name.endswith("/"):
                    assets.add(sha256(z.read(name)))

            data = json.loads(z.read("project.json"))
            targets = data.get("targets", [])
            sprite_count = len(targets)

            for t in targets:
                blocks = t.get("blocks")

                if isinstance(blocks, dict):
                    for b in blocks.values():
                        if isinstance(b, dict) and not b.get("shadow"):
                            opcodes.append(b.get("opcode", "unknown"))

                elif isinstance(blocks, list):
                    for b in blocks:
                        if isinstance(b, dict) and not b.get("shadow"):
                            opcodes.append(b.get("opcode", "unknown"))

    except Exception:
        return None

    return {
        "logic": Counter(opcodes),
        "assets": assets,
        "sprites": sprite_count
    }

def image_hist(file_obj):
    try:
        arr = np.asarray(bytearray(file_obj.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        img = cv2.resize(img, (256,256))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv],[0,1,2],None,[8,8,8],[0,180,0,256,0,256])
        cv2.normalize(hist, hist)
        return hist.flatten()
    except Exception:
        return None

# -------------------------------------------------
# DATA CONTAINERS
# -------------------------------------------------
projects = []
videos = []
images = {}

# -------------------------------------------------
# UI
# -------------------------------------------------
st.title("🛡️ Little KITES Forensics Suite 2.0")

uploads = st.file_uploader(
    "Upload ZIP or Files",
    type=["zip","sb3","p3b","png","jpg","jpeg","mp4","mkv"],
    accept_multiple_files=True
)

# -------------------------------------------------
# INGESTION (FINAL FIX)
# -------------------------------------------------
if uploads:
    with st.spinner("Processing files..."):

        def process_file(name, data):
            owner = extract_student_name(name)
            ext = os.path.splitext(name)[1].lower()   # ✅ FINAL FIX

            if ext in [".sb3", ".p3b"]:
                logic = extract_project_logic(io.BytesIO(data))
                if logic is not None:
                    projects.append({
                        "owner": owner,
                        "hash": sha256(data),
                        **logic
                    })

            elif ext in [".png", ".jpg", ".jpeg"]:
                hist = image_hist(io.BytesIO(data))
                if hist is not None:
                    images.setdefault(owner, []).append({
                        "hist": hist,
                        "obj": io.BytesIO(data)
                    })

            elif ext in [".mp4", ".mkv"]:
                videos.append({
                    "owner": owner,
                    "hash": sha256(data),
                    "size": len(data)
                })

        for up in uploads:
            if up.name.lower().endswith(".zip"):
                with zipfile.ZipFile(up) as z:
                    for name in z.namelist():
                        if name.endswith("/") or "__MACOSX" in name:
                            continue
                        process_file(name, z.read(name))
            else:
                process_file(up.name, up.read())

# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Projects", len(projects))
c2.metric("Students with Posters", len(images))
c3.metric("Videos", len(videos))

tabs = st.tabs(["🧩 Code", "🖼️ Posters", "🎥 Videos"])

# -------------------------------------------------
# CODE ANALYSIS
# -------------------------------------------------
with tabs[0]:
    if len(projects) < 2:
        st.warning("Upload at least two Scratch/PictoBlox projects.")
    else:
        for a, b in combinations(projects, 2):
            if a["hash"] == b["hash"]:
                st.error(f"🚨 Exact Copy: {a['owner']} == {b['owner']}")
            else:
                total = max(sum(a["logic"].values()), sum(b["logic"].values()), 1)
                sim = (sum((a["logic"] & b["logic"]).values()) / total) * 100
                if sim > 85:
                    st.warning(f"⚠️ {a['owner']} vs {b['owner']} — {sim:.1f}% similarity")

# -------------------------------------------------
# POSTER ANALYSIS (UNCHANGED)
# -------------------------------------------------
with tabs[1]:
    owners = list(images.keys())
    if len(owners) < 2:
        st.warning("Upload at least two students' posters.")
    else:
        for s1, s2 in combinations(owners, 2):
            for i1 in images[s1]:
                for i2 in images[s2]:
                    sim = cv2.compareHist(i1["hist"], i2["hist"], cv2.HISTCMP_CORREL)*100
                    if sim > 80:
                        st.info(f"🎨 {s1} vs {s2} — {sim:.1f}%")
                        col1, col2 = st.columns(2)
                        col1.image(i1["obj"], caption=s1, width=220)
                        col2.image(i2["obj"], caption=s2, width=220)

# -------------------------------------------------
# VIDEO ANALYSIS
# -------------------------------------------------
with tabs[2]:
    if len(videos) < 2:
        st.warning("Upload at least two videos.")
    else:
        for a, b in combinations(videos, 2):
            if a["hash"] == b["hash"]:
                st.error(f"🎥 Duplicate Video: {a['owner']} == {b['owner']}")
