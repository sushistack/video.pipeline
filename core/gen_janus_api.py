"""Janus-Pro-7B Image Generator via SiliconFlow API"""
import os
import json
import aiohttp
import io
import base64
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

from dotenv import load_dotenv
load_dotenv()


SILICONFLOW_BASE_URL = "https://api.siliconflow.com/v1"
MODEL_ID = "Tongyi-MAI/Z-Image-Turbo"
# black-forest-labs/FLUX.2-pro
# Qwen/Qwen-Image


class JanusAPIGenerator:
    """Generate images using Janus-Pro-7B via SiliconFlow API"""

    def __init__(self, workspace_dir: Path):
        """
        Initialize Janus-Pro-7B API generator

        Args:
            workspace_dir: Path to workspace directory
            **kwargs: Ignored (API compatibility)
        """
        self.workspace_dir = workspace_dir
        self.api_key = os.getenv("SILICONFLOW_API_KEY")
        print(f"[DEBUG] SILICONFLOW_API_KEY loaded: '{self.api_key}'")
        print(f"[DEBUG] SILICONFLOW_API_KEY length: {len(self.api_key) if self.api_key else 0}")
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY not set in environment")

    def load_model(self, log_callback: Optional[Callable[[str], None]] = None):
        """No-op: API-based generator doesn't need model loading"""
        msg = f"[*] SiliconFlow API ready: {MODEL_ID}"
        if log_callback:
            log_callback(msg)
        print(msg)

    async def generate_image(
        self,
        prompt: str,
        output_path: Optional[Path] = None,
        width: int = 1024,
        height: int = 1024,
        temperature: float = 1.0,
        cfg_weight: float = 5.0,
        num_inference_steps: int = 30,
        seed: Optional[int] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Generate image via SiliconFlow API

        Args:
            prompt: Text prompt for image generation
            output_path: Optional path to save generated image
            width: Image width
            height: Image height
            temperature: Unused (API compatibility)
            cfg_weight: Guidance scale
            num_inference_steps: Denoising steps
            seed: Random seed for reproducibility
            log_callback: Optional callback for logging

        Returns:
            Dict with image data and metadata
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)
            print(msg)

        image_size = f"{width}x{height}"
        log(f"[*] Generating {image_size} image via SiliconFlow API...")
        log(f"[*] Model: {MODEL_ID}")
        log(f"[*] Steps: {num_inference_steps}, Guidance: {cfg_weight}, Seed: {seed}")

        payload: Dict[str, Any] = {
            "model": MODEL_ID,
            "prompt": prompt,
            "image_size": image_size,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": cfg_weight,
            "n": 1,
        }
        if seed is not None:
            payload["seed"] = seed

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        url = f"{SILICONFLOW_BASE_URL}/images/generations"
        
        log(f"[DEBUG] Request URL: {url}")
        log(f"[DEBUG] Authorization header: Bearer {self.api_key[:10]}...{self.api_key[-10:] if len(self.api_key) > 20 else self.api_key}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=180),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"SiliconFlow API error {response.status}: {error_text}")
                result = await response.json()

            image_url = result["images"][0]["url"]
            returned_seed = result["images"][0].get("seed", seed)
            log(f"[*] Image URL received, downloading...")

            async with session.get(
                image_url,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as img_response:
                img_response.raise_for_status()
                image_bytes = await img_response.read()

        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))

        image_path = None
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, format="PNG")
            log(f"✅ Image saved to: {output_path}")
            image_path = str(output_path)

        preview_buffer = io.BytesIO()
        preview_img = image.copy()
        preview_img.thumbnail((512, 512))
        preview_img.save(preview_buffer, format="PNG")
        preview_base64 = base64.b64encode(preview_buffer.getvalue()).decode()

        log("✅ Image generation complete")
        return {
            "image": image,
            "image_path": image_path,
            "width": image.width,
            "height": image.height,
            "preview": f"data:image/png;base64,{preview_base64}",
            "prompt": prompt,
            "seed": returned_seed,
            "cfg_weight": cfg_weight,
            "temperature": temperature,
        }

    def generate_from_prompts_file(
        self,
        project_id: str,
        output_dir: Optional[Path] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate images from prompts file (synchronous CLI wrapper)

        Args:
            project_id: Project ID
            output_dir: Output directory for generated images
            log_callback: Optional callback for logging

        Returns:
            List of generation results
        """
        import asyncio

        async def _run() -> List[Dict[str, Any]]:
            return await self._generate_from_prompts_file_async(
                project_id, output_dir, log_callback
            )

        return asyncio.run(_run())

    async def _generate_from_prompts_file_async(
        self,
        project_id: str,
        output_dir: Optional[Path] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> List[Dict[str, Any]]:
        def log(msg: str):
            if log_callback:
                log_callback(msg)
            print(msg)

        prompts_file = self.workspace_dir / project_id / "scripts" / "05_image_prompts.json"
        if not prompts_file.exists():
            raise FileNotFoundError(f"Prompts file not found: {prompts_file}")

        with open(prompts_file, "r", encoding="utf-8") as f:
            prompts_data = json.load(f)

        if output_dir is None:
            output_dir = self.workspace_dir / project_id / "images" / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        total_images = 0

        for scene in prompts_data:
            for sub_scene in scene.get("sub_scenes", []):
                if sub_scene.get("first_shot", {}).get("image_prompt", {}).get("prompt"):
                    total_images += 1
                if sub_scene.get("last_shot", {}).get("image_prompt", {}).get("prompt"):
                    total_images += 1

        log(f"[*] Found {total_images} images to generate")

        image_counter = 0
        for scene_idx, scene in enumerate(prompts_data):
            scene_title = scene.get("scene_title", f"Scene_{scene_idx + 1}")

            for sub_idx, sub_scene in enumerate(scene.get("sub_scenes", [])):
                for shot_type in ("first", "last"):
                    shot_data = sub_scene.get(f"{shot_type}_shot", {})
                    prompt_data = shot_data.get("image_prompt", {})
                    if not (isinstance(prompt_data, dict) and prompt_data.get("prompt")):
                        continue

                    image_counter += 1
                    prompt = prompt_data["prompt"]
                    output_path = output_dir / f"scene{scene_idx + 1}_sub{sub_idx + 1}_{shot_type}.png"

                    log(f"[*] [{image_counter}/{total_images}] {shot_type} shot: {prompt[:50]}...")

                    try:
                        result = await self.generate_image(
                            prompt=prompt,
                            output_path=output_path,
                            log_callback=log_callback,
                        )
                        result.update({
                            "scene_index": scene_idx,
                            "sub_scene_index": sub_idx,
                            "shot_type": shot_type,
                            "scene_title": scene_title,
                        })
                        results.append(result)
                    except Exception as e:
                        log(f"❌ Failed: {e}")
                        results.append({
                            "scene_index": scene_idx,
                            "sub_scene_index": sub_idx,
                            "shot_type": shot_type,
                            "scene_title": scene_title,
                            "error": str(e),
                        })

        log(f"✅ Generated {len(results)} images")
        return results


def main():
    """CLI entry point for testing"""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Generate images using Janus-Pro-7B via SiliconFlow API")
    parser.add_argument("--workspace", type=str, default="./workspace", help="Workspace directory")
    parser.add_argument("--project", type=str, required=True, help="Project ID")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--prompt", type=str, default=None, help="Single prompt to test")

    args = parser.parse_args()

    workspace = Path(args.workspace)
    generator = JanusAPIGenerator(workspace_dir=workspace)

    if args.prompt:
        result = asyncio.run(generator.generate_image(
            prompt=args.prompt,
            output_path=Path(args.output) if args.output else None,
            log_callback=print,
        ))
        print(f"Generated: {result['image_path']}")
    else:
        results = generator.generate_from_prompts_file(
            project_id=args.project,
            output_dir=Path(args.output) if args.output else None,
            log_callback=print,
        )
        print(f"Generated {len(results)} images")


if __name__ == "__main__":
    main()
