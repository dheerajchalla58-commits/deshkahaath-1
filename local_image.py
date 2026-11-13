"""Apple Silicon image generation through MFLUX, enabled only in the Mac app."""
import base64
import os
import platform
import subprocess
import sys
import tempfile
import threading

MODEL_REPO = "mflux-community/flux2-klein-4b-mflux-q4"
MODEL_SIZE = "about 4.62 GB"
_lock = threading.Lock()
_state_lock = threading.Lock()
_state = {"state": "waiting", "message": "Preparing local image model."}


def status():
    with _state_lock:
        return dict(_state)


def _update(state, message):
    with _state_lock:
        _state.update(state=state, message=message)


def prepare_model():
    """Download the pinned model repository into the user's Hugging Face cache."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        _update("error", "Local image generation needs an Apple Silicon Mac.")
        return
    _update("downloading", f"Downloading the image model ({MODEL_SIZE}). Keep the app open and connected to the internet.")
    try:
        from huggingface_hub import snapshot_download
        try:
            snapshot = snapshot_download(repo_id=MODEL_REPO, local_files_only=True)
            required = (
                "text_encoder/0.safetensors", "text_encoder/1.safetensors",
                "transformer/0.safetensors", "transformer/1.safetensors",
                "vae/0.safetensors", "tokenizer/tokenizer.json",
            )
            if not all(os.path.isfile(os.path.join(snapshot, name)) for name in required):
                raise FileNotFoundError("The cached model download is incomplete.")
        except Exception:
            snapshot_download(repo_id=MODEL_REPO)
        _update("ready", "Local image model is ready.")
    except Exception:
        _update("error", "Model download failed. Check your internet connection and restart the app to retry.")


def start_preparation():
    threading.Thread(target=prepare_model, name="model-download", daemon=True).start()


def generate(prompt):
    if status()["state"] != "ready":
        return None, status()["message"]
    if not _lock.acquire(blocking=False):
        return None, "An image is already being created. Please wait."
    try:
        with tempfile.TemporaryDirectory(prefix="desh-craft-") as directory:
            output = os.path.join(directory, "craft.png")
            command = [
                sys.executable, "-c",
                "from mflux.models.flux2.cli.flux2_generate import main; main()",
                "--model", "flux2-klein-4b", "--quantize", "4",
                "--prompt", prompt, "--steps", "4", "--width", "512",
                "--height", "512", "--output", output,
            ]
            try:
                result = subprocess.run(command, capture_output=True, timeout=1200, check=False)
            except subprocess.TimeoutExpired:
                return None, "Image generation took too long. Close other apps and try again."
            if result.returncode != 0 or not os.path.isfile(output):
                return None, "Local image generation failed. Check available memory and try again."
            with open(output, "rb") as generated:
                content = generated.read()
            if not content.startswith(b"\x89PNG\r\n\x1a\n"):
                return None, "The local generator returned an invalid image."
            return "data:image/png;base64," + base64.b64encode(content).decode("ascii"), None
    finally:
        _lock.release()
