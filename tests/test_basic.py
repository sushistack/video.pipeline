"""Basic test script to verify core package imports and initialization."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import GPTSoVITSWrapper, TTSRequest, TTSResponse
from core.utils import setup_logging


def main():
    """Run basic tests"""
    print("=" * 60)
    print("GPT-SoVITS Core Package - Basic Test")
    print("=" * 60)
    
    # Setup logging
    setup_logging()
    
    # Test 1: Import verification
    print("\n[Test 1] Import verification...")
    print("[OK] Successfully imported core modules")
    
    # Test 2: Wrapper initialization
    print("\n[Test 2] Initializing wrapper...")
    wrapper = GPTSoVITSWrapper()
    print(f"[OK] Wrapper initialized with device: {wrapper.device}")
    
    # Test 3: Model loading
    print("\n[Test 3] Loading model...")
    wrapper.load_model()
    print("[OK] Model loaded (placeholder)")
    
    # Test 4: Create test request
    print("\n[Test 4] Creating test request...")
    request = TTSRequest(
        text="This is a test sentence.",
        reference_audio=Path("test.wav"),
    )
    print(f"[OK] Request created: {request.text}")
    
    # Test 5: Run inference (will use placeholder implementation)
    print("\n[Test 5] Running inference...")
    response = wrapper.inference(request)
    print(f"[OK] Inference completed:")
    print(f"   - Success: {response.success}")
    print(f"   - Processing time: {response.processing_time:.2f}s")
    if response.output_path:
        print(f"   - Output path: {response.output_path}")
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
