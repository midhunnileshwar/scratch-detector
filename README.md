# 🔍 Scratch Plagiarism Detector (Little KITES)

A digital forensics tool designed for KITE Masters and Teachers to detect plagiarism in Scratch (`.sb3`) assignments.

## 🚀 What it Does
1. **Detects Exact Copies:** Identifies students who simply renamed another student's file.
2. **Logic Analysis:** Ignores visual changes (renamed sprites, moved blocks) and checks if the *code logic* is identical.
3. **Asset Forensics:** Checks if students are sharing identical custom images or audio files.

## 💻 How to Run (Web Version)
*(If you have set up Streamlit)*
[Click here to run the App](https://share.streamlit.io/midhunnileshwar/scratch-detector/main)

## 🐧 How to Run (Linux/Ubuntu)
1. Download this repository (Code -> Download ZIP).
2. Open the folder in Terminal.
3. Run:
   ```bash
   pip3 install -r requirements.txt
   streamlit run streamlit_app.py
