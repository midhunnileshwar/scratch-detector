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
st.set_page_config("KITE Forensics Master", "🛡️", layout="wide")

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

def extract_project_logic(file_obj):
    opcodes = []
    assets = set()
    sprites = 0

    try:
        with zipfile.ZipFile(file_obj) as z:
            for f in z.namelist():
                if f != "project.json" and not f.endswith("/"):
                    assets.add(sha256(z.read(f)))

            data = json.loads(z.read("project.json"))
            targets = data.get("targets", [])
            sprites = len(targets)

            for t in targets:
                blocks = t.get("blocks", {})
                for b in blocks.values():
                    if isinstance(b, dict) and not b.get("shadow"):
                        opcodes.append(b.get("opcode", "unknown"))
    except:
        return None

    return {
        "logic": Counter(opcodes),
        "assets": assets,
        "sprites": sprites
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
    except:
        return None

# -------------------------------------------------
# DATA CONTAINERS (FIXED)
# -------------------------------------------------
projects = []   # LIST — NOT dict
videos = []     # LIST — NOT dict
images = {}     # dict[owner] = list

# -------------------------------------------------
# UI
# -------------------------------------------------
st.title("🛡️ Little KITES Forensics Suite")

uploads = st.file_uploader(
    "Upload ZIP or Files",
    type=["zip","sb3","p3b","png","jpg","jpeg","mp4","mkv"],
    accept_multiple_files=True
)

# -------------------------------------------------
# INGESTION
# -------------------------------------------------
if uploads:
    with st.spinner("Processing files..."):
        for up in uploads:

            def process_file(name, data):
                owner = extract_student_name(name)
                ext = name.split(".")[-1].lower()

                if ext in ["sb3","p3b"]:
                    logic = extract_project_logic(io.BytesIO(data))
                    if logic:
                        projects.append({
                            "owner": owner,
                            "hash": sha256(data),
                            **logic
                        })

                elif ext in ["png","jpg","jpeg"]:
                    hist = image_hist(io.BytesIO(data))
                    if hist is not None:
                        images.setdefault(owner, []).append({
                            "hist": hist,
                            "obj": io.BytesIO(data)
                        })

                elif ext in ["mp4","mkv"]:
                    videos.append({
                        "owner": owner,
                        "hash": sha256(data),
                        "size": len(data)
                    })

            if up.name.endswith(".zip"):
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
c1,c2,c3 = st.columns(3)
c1.metric("Projects", len(projects))
c2.metric("Students with Posters", len(images))
c3.metric("Videos", len(videos))

tabs = st.tabs(["🧩 Code", "🖼️ Posters", "🎥 Videos"])

# -------------------------------------------------
# CODE ANALYSIS (NOW WORKS)
# -------------------------------------------------
with tabs[0]:
    if len(projects) < 2:
        st.warning("Upload at least two Scratch/PictoBlox projects.")
    else:
        for a,b in combinations(projects,2):
            if a["hash"] == b["hash"]:
                st.error(f"🚨 Exact Copy: {a['owner']} == {b['owner']}")
            else:
                sim = (
                    sum((a["logic"] & b["logic"]).values()) /
                    max(sum(a["logic"].values()), sum(b["logic"].values()))
                ) * 100
                if sim > 85:
                    st.warning(f"⚠️ {a['owner']} vs {b['owner']} — {sim:.1f}% similarity")

# -------------------------------------------------
# POSTER ANALYSIS (WITH PREVIEW)
# -------------------------------------------------
with tabs[1]:
    owners = list(images.keys())
    if len(owners) < 2:
        st.warning("Upload at least two students' posters.")
    else:
        for s1,s2 in combinations(owners,2):
            for i1 in images[s1]:
                for i2 in images[s2]:
                    sim = cv2.compareHist(i1["hist"], i2["hist"], cv2.HISTCMP_CORREL)*100
                    if sim > 80:
                        st.info(f"🎨 {s1} vs {s2} — {sim:.1f}%")
                        col1,col2 = st.columns(2)
                        col1.image(i1["obj"], caption=s1, width=220)
                        col2.image(i2["obj"], caption=s2, width=220)

# -------------------------------------------------
# VIDEO ANALYSIS (NOW WORKS)
# -------------------------------------------------
with tabs[2]:
    if len(videos) < 2:
        st.warning("Upload at least two videos.")
    else:
        for a,b in combinations(videos,2):
            if a["hash"] == b["hash"]:
                st.error(f"🎥 Duplicate Video: {a['owner']} == {b['owner']}")
