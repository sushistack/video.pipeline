# Video Pipeline - Qwen3-TTS

Qwen3-TTS를 활용한 고성능 TTS(Text-to-Speech) 및 보이스 클로닝 웹 애플리케이션입니다.

## 📋 Prerequisites

- Python 3.12 LTS
- Git
- (Optional) CUDA-capable GPU for faster inference

## 🚀 Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd video.pipeline
```

### 2. Create and activate virtual environment

**Windows:**
```bash
py -3.12 -m venv .venv
.\.venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
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

1. **Select Project**: Choose a project with scenario files
2. **Configure TTS**: Select model and language options
3. **Generate**: Click "Generate Audio Tracks" to start generation
4. **Listen & Download**: Once complete, you can play the audio

## 📁 Project Structure

```
video.pipeline/
├── core/                   # Core business logic
│   ├── __init__.py
│   ├── gen_audio.py        # Audio generation orchestrator
│   ├── gen_caption.py      # Caption generation
│   └── tts/                # TTS providers
│       ├── base.py         # Abstract base class
│       └── qwen3_tts.py    # Qwen3-TTS implementation
├── ui/                     # Reflex UI components
│   ├── states/             # State management
│   ├── components/         # Reusable UI components
│   └── pages/              # Page definitions
├── assets/                 # Static files
│   └── audios/             # Reference audio files
├── workspace/              # Project workspaces
├── tests/                  # Unit tests
├── rxconfig.py             # Reflex configuration
├── requirements.txt        # Python dependencies
└── README.md
```

## 🧪 Testing

### Run unit tests

```bash
pytest tests/
```

## 🛠️ Development

### Check Python version

```bash
python --version  # Should show Python 3.12.x
```

### Update dependencies

```bash
pip install -r requirements.txt --upgrade
```

## 📝 Notes

- Qwen3-TTS supports both preset speakers and voice cloning
- GPU acceleration is automatically detected and used if available
- All generated audio files are saved in `workspace/<project>/audios/`

## 🔧 Troubleshooting

### GPU out of memory

The system will automatically fall back to CPU mode if GPU memory is insufficient.

### Permission errors

Make sure you have write permissions for the `workspace/` directory.

## 📄 License

[Add your license here]
