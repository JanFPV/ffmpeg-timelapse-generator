
# ffmpeg-timelapse-generator

A lightweight Python + FFmpeg tool to generate timelapse videos from image sequences (e.g., from GoPro or DSLR cameras), with optional timestamp overlays.

## 🚀 Features

- Generates high-quality timelapse videos using `ffmpeg`
- Automatically extracts timestamps from image EXIF data
- Falls back to file modification time when EXIF is missing
- Optionally overlays timestamps onto video frames
- Designed to work in Jupyter notebooks or standalone scripts
- Flexible and extensible — ready for automation

## 📦 Requirements

- Python 3.7 or newer
- `ffmpeg` installed and accessible in your system's PATH

Python packages:
- `pandas`
- `Pillow`

## 🔧 Setup Instructions

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

## 📂 Project Structure

```
ffmpeg-timelapse-generator/
│
├── tools/timelapse.py    # Core functions
├── notebook.ipynb        # Example notebook for experimentation
├── requirements.txt      # Python dependencies
└── README.md             # Documentation
```

## 📝 License

GNU GPL-3.0 License
