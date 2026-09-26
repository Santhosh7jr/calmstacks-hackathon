# LaMa image inpainting model

RecoverAI optionally uses the OpenCV `inpainting_lama_2025jan.onnx` model for
localized image restoration.

The weights are intentionally **not committed** to the Git repository because
they are approximately 88 MB. Install them locally with:

```bash
cd api
python ml/download_models.py
```

The model is downloaded from the OpenCV-hosted Hugging Face artifact:

`https://huggingface.co/opencv/inpainting_lama`

The OpenCV model card identifies the artifact as an ONNX LaMa inpainting model
and states that the files in that distribution are Apache licensed.

RecoverAI only applies the model inside its detected damage mask; it does not
rewrite untouched pixels.
