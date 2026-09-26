# RecoverAI Core

Custom format-aware file damage analysis engine used by RecoverAI.

## Image analysis

The image detector combines independent signals instead of treating Pillow's
`verify()` result as a corruption percentage:

- JPEG marker/scan structure and EOI detection
- PNG chunk-boundary and CRC validation
- strict decoding followed by an isolated salvage decode for truncated files
- bounded block-level RGB/luminance/variance/edge statistics
- robust neighbor-discontinuity detection
- persistent horizontal/vertical/statistical region detection
- confidence and evidence attached to every estimate

A visual percentage is an **estimate of affected decoded content**, not a claim
about exact lost bytes. Exact original-byte loss cannot be inferred from a
single damaged image without a known-good reference.

The detector is designed to avoid common false positives such as natural
texture and photographic noise; the test suite includes a synthetic noise
image to guard against that regression.

## Recovery engine

`recoverai_core.recovery.engine` provides non-destructive format-aware recovery. It always keeps the uploaded bytes unchanged and validates the generated candidate with the same analysis engine.

Current strategies:

- JPEG/PNG/BMP/WEBP/TIFF: decoded-pixel salvage, localized repair, and boundary texture continuation; OpenCV Telea inpainting is used when available for interior regions.
- Truncated JPEGs: Pillow's truncated-image salvage is enabled only for the recovery operation, then the recovered pixels are re-encoded.
- DOCX/ZIP: rebuild readable ZIP members; malformed `word/document.xml` can be reconstructed from surviving text nodes.
- PDF: rebuild readable pages with lenient `pypdf` parsing. Optional `qpdf` integration can be added for more severely damaged PDFs.

Recovery is not guaranteed to restore information that is no longer present in the input. The API reports the before/after analysis and the recovery improvement estimate instead of claiming byte-exact reconstruction.
