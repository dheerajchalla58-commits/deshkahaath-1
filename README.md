# Desh Ke Haath

Discover Indian handicrafts and create new craft concepts.

## Download for Mac

[Download the Apple Silicon Mac preview](https://github.com/dheerajchalla58-commits/deshkahaath-1/releases/tag/mac-preview). The download appears on that page after the Mac build completes successfully. Choose **DeshKeHaath-macOS-arm64.zip**, unzip it and open **Desh Ke Haath.app**.

This is an experimental build for Apple Silicon Macs. It is not notarized by Apple; macOS may warn before opening it. The app, image generation, voice, location and image search need testing on a physical Mac.

On first launch, the app downloads the approximately 4.62 GB FLUX.2 Klein 4B image model. Keep the app open and connected to the internet until it says the model is ready. Afterward, image generation runs locally and does not use paid image API credits. Allow at least 15 GB of free storage for the app, model, temporary files and generated images. Image quality and generation time depend on your Mac. Craft-specific prompting guides the model; the model has not been fine-tuned on the catalog.

The collection and vendor acceptance are demonstrations; payment and real vendor fulfilment are not connected.

## Developer notes

The Mac preview is built by the [Mac build workflow](https://github.com/dheerajchalla58-commits/deshkahaath-1/actions/workflows/mac-build.yml). It builds on Apple Silicon, bundles a Python runtime and dependencies, and smoke-checks the local server. The workflow cannot verify image generation on a physical Mac GPU.

For a local macOS build, install Xcode command-line tools and [uv](https://docs.astral.sh/uv/), then run `bash mac/build.sh`. The app zip appears in `dist/`.

For web development, create a Python virtual environment, install `requirements.txt`, and run `python app.py`. The web version uses a configured image provider and may consume paid credits; copy `.env.example` to `.env` and keep secrets private.
