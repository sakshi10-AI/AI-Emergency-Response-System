"""
EOC Command Center - Streamlit Application Launcher

Run this file from the project root with:
    streamlit run streamlit_app.py
"""
import sys
from pathlib import Path

# Guarantee project root is first on sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Now import and run the actual Streamlit app
from frontend.app import main

main()
