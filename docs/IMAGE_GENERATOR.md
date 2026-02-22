# Image Generator - Janus-Pro-7B

Generate images from AI prompts using DeepSeek's Janus-Pro-7B multimodal model.

## Features

- 🖼️ Generate images from text prompts using Janus-Pro-7B
- 📁 Batch generation from image prompts file (`05_image_prompts.json`)
- 🔄 Retry failed generations individually
- 📊 Real-time progress tracking with console logs
- 💾 Download individual images or all as ZIP
- ⚙️ Configurable generation settings (guidance scale, steps, resolution)

## Installation

### 1. Install Dependencies

```bash
cd /mnt/work/projects/video.pipeline
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Janus Package

```bash
# Clone and install Janus
git clone https://github.com/deepseek-ai/Janus.git /tmp/janus_repo
pip install /tmp/janus_repo
```

### 3. Download Model (if not already downloaded)

The model should already be downloaded at:
```
~/.cache/huggingface/hub/models--deepseek-ai--Janus-Pro-7B/
```

If not, run:
```bash
bash scripts/setup_janus.sh
# or manually:
huggingface-cli download deepseek-ai/Janus-Pro-7B
```

### 4. Verify Installation

```bash
python -c "
from janus.models import MultiModalityCausalLM, VLChatProcessor
print('✅ Janus installed successfully')
"
```

## Usage

### Via Web UI

1. Navigate to the **🖼️ Image** tab in the web interface
2. Select a project that has generated image prompts
3. Configure generation settings:
   - **Guidance Scale**: How faithfully to follow the prompt (1-20, default: 7.5)
   - **Inference Steps**: Quality vs. speed trade-off (10-100, default: 50)
   - **Resolution**: Output image size (default: 1024x1024)
4. Click **Generate All Images** to start batch generation
5. Monitor progress in the console log viewer
6. Download generated images individually or as a ZIP file

### Via CLI

```bash
python core/gen_janus_image.py --workspace ./workspace --project <project-id>
```

Or test with a single prompt:

```bash
python core/gen_janus_image.py --workspace ./workspace --project <project-id> \
    --prompt "A beautiful sunset over mountains, cinematic lighting"
```

## Output

Generated images are saved to:
```
workspace/{project-id}/images/generated/
```

File naming convention:
- `scene{N}_sub{N}_first.png` - Opening shot of sub-scene
- `scene{N}_sub{N}_last.png` - Closing shot of sub-scene

## Settings

| Setting | Range | Default | Description |
|---------|-------|---------|-------------|
| Guidance Scale | 1-20 | 5.0 | Higher values follow prompts more strictly |
| Inference Steps | 10-100 | 30 | More steps = better quality, slower |
| Resolution | 384-768 | 384 | Output image width/height |
| Seed | 0-2³¹-1 | 42 | Same seed = same result (if Random Seed is off) |

### Speed Tips

1. **Lower Resolution**: 384x384 is fastest (native resolution)
2. **Fewer Steps**: 30 steps is good balance
3. **Fixed Seed**: Use same seed for reproducible results

### Model Download Fails

Ensure you have `huggingface_hub` installed and try again:
```bash
pip install --upgrade huggingface_hub
huggingface-cli login  # If using private models
```

### Out of Memory

Reduce resolution or batch size. Janus-Pro-7B requires significant VRAM:
- 1024x1024: ~16GB VRAM recommended
- 512x512: ~8GB VRAM minimum

### Slow Generation

- Ensure GPU acceleration is working: `python -c "import torch; print(torch.cuda.is_available())"`
- Reduce inference steps for faster (lower quality) generation
- Close other GPU-intensive applications

## References

- [Janus-Pro-7B GitHub](https://github.com/deepseek-ai/Janus)
- [HuggingFace Model Page](https://huggingface.co/deepseek-ai/Janus-Pro-7B)
- [ROCm PyTorch Installation](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/native_linux/install-pytorch.html)
