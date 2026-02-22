"""UI package initialization."""
import warnings

# Suppress transformers FutureWarning about image_processor_class
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
