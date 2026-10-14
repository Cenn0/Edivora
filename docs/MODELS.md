# Model decisions and provenance

Historical model research originally checked on 2026-10-12. **Current `main` source (0.3.0a1)** uses pinned **U2NETP** for Photo and one Video still frame, plus pinned **Silero VAD v6.2.1 ONNX** for Audio speech-activity regions ([media implementation](MEDIA_PROJECTS_AI.md)). The older verified photo ZIP includes **U2NETP only**. The optional expanded model-profile proposal in [PR #17](https://github.com/Cenn0/Edivora/pull/17) is **not part of `main` or a released download**. "Local inference is technically possible" is not hardware certification, GPU support, proven quality or release approval.

## Initial model: U2NETP

- Purpose: salient foreground segmentation for background removal. It does not interpret edit instructions and does not generate replacement image content.
- Original project: <https://github.com/xuebinqin/U-2-Net>.
- Original repository license: Apache-2.0; full upstream license is retained in `LICENSE` / package notices.
- ONNX distributor and adapter: <https://github.com/danielgatis/rembg/blob/main/rembg/sessions/u2netp.py>.
- Fixed artifact: <https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx>.
- GitHub release asset ID: 85857953; API metadata reports 4,574,861 bytes and no SHA-256 digest.
- Upstream adapter's legacy MD5: `8e83ca70e441ab06c318d82300c84806`.
- Expected SHA-256: `309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8`.
- SHA-256 provenance: independently published by the integrating project [Soundscaper](https://github.com/LeoWattenberg/Soundscaper/blob/main/THIRD_PARTY_LICENSES.md), not by the original model author. Our own download, size check, SHA-256 and upstream MD5 comparison succeeded on 2026-10-12 in [Windows Actions run 38300342083](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38300342083), against source commit `80a3456d728323605aa6677b7a1fb5c5e3e0ccf0`. Real source-worker inference also passed there. That run subsequently failed its GUI shutdown check and did not produce a portable package; byte verification is a separate result. Future builds must fail if any pinned value differs.

The upstream source repository is explicitly Apache-2.0 and its README recommends rembg. Applying that repository license to the released standard weights and converted ONNX file is an interpretation of that distribution; no separate written weight-redistribution confirmation was found in this research. Retain upstream attribution and the license, and resolve any contrary artifact terms before public distribution. Do not treat a future model with a similarly named repository as having the same license.

Preprocessing uses RGB resized to 320×320, the upstream maximum-value scaling convention, and ImageNet channel normalization. Inference is ONNX Runtime CPU only. Compositing multiplies the foreground mask with any existing alpha and retains the original RGB values. This preserves foreground pixels; mask quality is still imperfect, particularly around hair, fur, glass and low-contrast edges. It is a compact baseline, not a claim of best available segmentation quality.

## Quality option: BiRefNet Lite

The [official BiRefNet Lite model repository](https://huggingface.co/ZhengPeng7/BiRefNet_lite) identifies its weights as official and marks them MIT. The safetensors artifact is not the same file as a converted ONNX export. The [rembg Lite adapter](https://github.com/danielgatis/rembg/blob/main/rembg/sessions/birefnet_general_lite.py) provides an ONNX execution path; GitHub reports 224,005,088 bytes for its `BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx` asset.

It is a candidate for a later quality package, subject to measured quality, memory, latency, and export-provenance checks. Use a pinned local ONNX export, not runtime execution of a model repository's Python via `trust_remote_code=True`.

## Generative option: FLUX.2 klein 4B

The [official model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) supports instruction-based editing with reference images and explicitly lists Apache-2.0 for the weights. The [official inference repository](https://github.com/black-forest-labs/flux2) distinguishes 4B's Apache license from the separate non-commercial license for 9B and other variants. These are not interchangeable.

Memory statements differ: the model card lists approximately 13 GB VRAM while the inference repository lists approximately 8 GB for klein 4B. These figures do not fully specify the same runtime configuration. We therefore make no 12 GB GPU guarantee and no speed guarantee. Quantization, offload, input size and full pipeline memory must be benchmarked as one concrete configuration.

This is a complete optional runtime package: transformer, text encoder, VAE, tokenizer, configuration files and an appropriate inference engine. One transformer file's download size is not the total installation size. Runtime networking remains disabled, including during model initialization.

## Alternatives not selected for the alpha

- LaMa: plausible local inpainting, but code license and separately distributed weights need distinct verification. [Upstream issue 366](https://github.com/advimman/lama/issues/366) documents unresolved questions about the latter. Do not ship an assumed license.
- Real-ESRGAN: useful later for super-resolution; [upstream](https://github.com/xinntao/Real-ESRGAN) offers portable NCNN/Vulkan programs. Evaluate a specific complete package rather than claiming every GPU is supported.
- BRIA RMBG-2.0: the [model card](https://huggingface.co/briaai/RMBG-2.0) uses non-commercial conditions and a separate commercial path. Not selected as a default generally redistributable package.
- Unrestricted rembg integration: not required. We use one narrow local ONNX adapter, because a library's other backends can have network behaviour that contradicts the product contract.

