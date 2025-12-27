# GPT-SoVITS Video Pipeline

GPT-SoVITS를 활용한 고성능 TTS(Text-to-Speech) 및 보이스 클로닝 웹 애플리케이션입니다.

## 📋 Prerequisites

- Python 3.12 LTS
- Git
- (Optional) CUDA-capable GPU for faster inference

## 🚀 Setup

### 1. Clone the repository and initialize submodules

```bash
git clone <repo-url>
cd video.pipeline
git submodule update --init --recursive
```

### 2. Create and activate virtual environment

**Windows:**
```bash
py -3.12 -m venv venv
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 🎯 Usage

### Run the application

```bash
reflex run
```

The application will start on `http://localhost:3000`

### Using the TTS Generator

1. **Upload Reference Audio**: Click "파일 선택" to upload a reference audio file (.wav, .mp3, or .flac)
2. **Enter Text**: Type the text you want to synthesize in the text area
3. **Generate**: Click "오디오 생성" to start the generation process
4. **Listen & Download**: Once complete, you can play the audio or download it

## 📁 Project Structure

```
video.pipeline/
├── core/                   # Core business logic
│   ├── __init__.py
│   ├── wrapper.py          # GPT-SoVITS wrapper interface
│   ├── models.py           # Pydantic data models
│   ├── utils.py            # Utility functions
│   └── exceptions.py       # Custom exceptions
├── ui/                     # Reflex UI components
│   ├── __init__.py
│   ├── state.py            # Reflex State management
│   └── pages/
│       └── index.py        # Main page
├── external/
│   └── GPT-SoVITS/         # Git submodule
├── assets/                 # Static files
│   ├── uploaded/           # Uploaded reference audio
│   └── outputs/            # Generated audio files
├── tests/                  # Unit tests
│   ├── test_core.py
│   └── test_basic.py
├── video_pipeline.py       # Main application entry point
├── rxconfig.py             # Reflex configuration
├── requirements.txt        # Python dependencies
└── README.md
```

## 🧪 Testing

### Run unit tests

```bash
pytest tests/
```

### Run basic test script

```bash
python tests/test_basic.py
```

## 🛠️ Development

### Check Python version

```bash
python --version  # Should show Python 3.12.x
```

### Verify submodule

```bash
git submodule status
```

### Update dependencies

```bash
pip install -r requirements.txt --upgrade
```

## 📝 Notes

- The current implementation uses placeholder inference logic. Actual GPT-SoVITS integration needs to be completed.
- GPU acceleration is automatically detected and used if available.
- All generated audio files are saved in `assets/outputs/`

## 🔧 Troubleshooting

### Submodule not found

```bash
git submodule update --init --recursive
```

### GPU out of memory

The system will automatically fall back to CPU mode if GPU memory is insufficient.

### Permission errors

Make sure you have write permissions for the `assets/` directory.

## 📄 License

[Add your license here]
