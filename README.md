# RecoverAI

## AI-Assisted Intelligent Data Recovery & Digital Evidence Reconstruction

RecoverAI is an AI-assisted digital forensics platform designed to analyze damaged, corrupted, fragmented, or partially recoverable digital files and provide investigators with actionable information about what can realistically be recovered.

The system combines **machine learning, binary/file analysis, corruption detection, fragment analysis, reconstruction techniques, and recovery-confidence estimation** into a single workflow.

---

# 🎯 Final Goal

The final goal of RecoverAI is to provide an intelligent forensic recovery pipeline that can:

1. **Analyze damaged digital evidence**
2. **Identify the type and structure of files**
3. **Detect corrupted or missing portions**
4. **Identify and match fragmented file pieces**
5. **Determine the correct ordering of fragments**
6. **Attempt structural reconstruction of recoverable files**
7. **Validate the reconstructed output**
8. **Estimate recovery confidence and file integrity**
9. **Classify and prioritize recovered evidence**
10. **Present investigators with clear, actionable recovery information**

The system should ultimately answer the investigator's most important questions:

> **What is this file?**

> **What part of it is damaged?**

> **Can it be recovered?**

> **Which fragments belong together?**

> **What can realistically be reconstructed?**

> **How confident are we in the recovered result?**

> **Which recovered artifacts should be investigated first?**

---

# 🧠 Core System Pipeline

```text
                    ┌─────────────────────┐
                    │   Damaged Evidence  │
                    │  Files / Fragments  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   File Analysis     │
                    │ • File Type         │
                    │ • Binary Structure  │
                    │ • Headers           │
                    │ • Entropy           │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  ML Classification  │
                    │ • File Type         │
                    │ • Corruption        │
                    │ • Recovery          │
                    │   Confidence        │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
       ┌──────────────────┐        ┌──────────────────┐
       │ Fragment Analysis│        │ Corruption       │
       │                  │        │ Assessment       │
       │ • Matching       │        │ • Intact         │
       │ • Similarity     │        │ • Partial        │
       │ • Ordering       │        │ • Severe         │
       └────────┬─────────┘        └────────┬─────────┘
                │                           │
                └─────────────┬─────────────┘
                              ▼
                    ┌─────────────────────┐
                    │    Reconstruction   │
                    │                     │
                    │ Reassemble usable   │
                    │ fragments and repair │
                    │ recoverable data     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Integrity Validation │
                    │                     │
                    │ • Structure         │
                    │ • File readability  │
                    │ • Recovery quality  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Evidence            │
                    │ Prioritization      │
                    │                     │
                    │ HIGH / MEDIUM / LOW │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Results Dashboard   │
                    └─────────────────────┘
```

---

# 🔬 Core AI/ML Components

## 1. File Classification

The system extracts binary, entropy, header, and structural features and predicts the likely file type.

Supported categories can include:

* PDF
* JPEG
* PNG
* ZIP
* DOC
* Binary files
* Other supported formats

---

## 2. Corruption Detection

The corruption model analyzes the extracted features and determines whether the file appears:

* Intact
* Corrupted
* Partially damaged
* Potentially unrecoverable

This allows the recovery system to determine whether reconstruction should be attempted.

---

## 3. Fragment Matching

RecoverAI analyzes file fragments and estimates whether two fragments belong to the same original file or occur consecutively.

The system considers characteristics such as:

* Byte patterns
* Entropy
* Structural similarity
* File signatures
* Fragment size
* Offset relationships
* Structural continuity

The objective is to reconstruct the original fragment sequence as accurately as possible.

---

## 4. Image Purification Model

RecoverAI now includes a trained **masked-pixel image purification model**.

Training uses clean reference images plus synthetic zeroed, impulse, noise, and small masked-pixel corruption. The model receives an 11×11 RGB neighborhood and predicts the clean RGB value of the damaged center pixel. During recovery it is applied **only inside a forensic damage mask**, so untouched decoded pixels are preserved. Multiple passes allow local information to propagate across a damaged block.

The trained artifact is stored at:

```text
api/ml/models/image_purification/image_purifier.joblib
```

Retraining is reproducible with:

```bash
cd api
python ml/training/train_image_purifier.py
```

The current validation run achieved about **93.7% lower RGB prediction RMSE than the deliberately corrupted-center baseline** on its held-out synthetic validation patches (40,800 training/validation patches in the bundled run). This is a model-quality metric, not a guarantee of perfect restoration for arbitrary real-world files.

Forensic recovery remains format-aware: the ML purifier handles localized decoded image damage, while PDF/DOCX/ZIP recovery continues to use structural reconstruction and validation.

## 4. Recovery Confidence

The recovery model estimates how much usable information can potentially be recovered.

The result is presented as a recovery-confidence indicator rather than claiming that recovery is guaranteed.

Example:

```text
Recovery Confidence: 82%
```

This allows investigators to distinguish between files that are highly recoverable and files requiring further forensic analysis.

---

# 🧩 Reconstruction Engine

After fragment analysis, RecoverAI attempts to reconstruct the original file.

```text
Fragment A
    ↓
Fragment B
    ↓
Fragment C
    ↓
Fragment D
    ↓
Reconstructed File
```

The reconstructed file is then validated.

Validation may include:

* File signature validation
* Structural validation
* Readability checks
* Format-specific checks
* Recovered-content verification

A reconstruction should never be presented as valid merely because fragments were concatenated successfully.

---

# 🚨 Evidence Prioritization

The final system should help investigators focus on the most useful recovered artifacts.

Evidence priority can be calculated from factors such as:

```text
Recovery Confidence
        +
Integrity
        +
File Importance
        +
Successful Reconstruction
        ↓
Evidence Priority
```

The dashboard can organize artifacts into:

```text
HIGH PRIORITY
Files with strong recovery potential and useful evidence

MEDIUM PRIORITY
Partially recoverable or uncertain artifacts

LOW PRIORITY
Severely damaged or low-confidence artifacts
```

This prioritization is intended as **decision support**, not as a replacement for forensic judgment.

---

# 🖥️ Investigator Workflow

The final user workflow should be:

```text
1. Upload Evidence
        ↓
2. Analyze File
        ↓
3. Detect File Type
        ↓
4. Detect Corruption
        ↓
5. Analyze Fragments
        ↓
6. Match & Order Fragments
        ↓
7. Attempt Reconstruction
        ↓
8. Validate Recovered File
        ↓
9. Calculate Recovery Confidence
        ↓
10. Prioritize Evidence
        ↓
11. Investigator Reviews Results
```

---

# 🏆 Final Product Objective

RecoverAI should ultimately transform this:

```text
Damaged / Fragmented / Corrupted Evidence
```

into this:

```text
┌─────────────────────────────────────────┐
│           RECOVERAI RESULT              │
├─────────────────────────────────────────┤
│ File Type: PDF                          │
│ Integrity: Partially Corrupted          │
│ Recovery Confidence: 82%                │
│ Fragments Detected: 7                   │
│ Fragments Matched: 6                    │
│ Reconstruction: Successful               │
│ Validation: Passed                      │
│ Evidence Priority: HIGH                 │
├─────────────────────────────────────────┤
│ Investigator Recommendation:            │
│ Review reconstructed artifact and        │
│ validate recovered content.              │
└─────────────────────────────────────────┘
```

The final goal is therefore **not simply to recover a file**.

The goal is to build an intelligent forensic assistant that helps investigators understand:

**what survived, what was damaged, what can be reconstructed, how reliable the reconstruction is, and which recovered evidence deserves attention first.**

---

# 🚀 Hackathon Goal

RecoverAI addresses the four major requirements of the challenge:

### 1. Intelligent Fragment Reconstruction

Use machine learning and structural analysis to identify, match, order, and reconstruct fragmented data.

### 2. Data Integrity & Corruption Assessment

Determine which portions of evidence remain intact, which are damaged, and which may be recoverable.

### 3. Classification & Prioritization

Classify recovered artifacts and prioritize them according to recoverability, integrity, and forensic relevance.

### 4. Investigative Decision Support

Provide investigators with understandable results and actionable information about what can realistically be recovered.

---

# 🔐 Forensic Principle

RecoverAI is designed as an **AI-assisted decision-support system**.

It should not silently modify evidence or claim certainty where the underlying evidence does not support it.

Original evidence should remain preserved, while recovered or reconstructed artifacts should be clearly identified as such.

All recovery decisions should remain reviewable by the investigator.

---

# 🎯 Final Vision

```text
                 RECOVERAI

        "From damaged evidence
          to actionable insight."

                         │
                         ▼

        Analyze → Understand → Reconstruct
                         │
                         ▼
              Validate → Prioritize
                         │
                         ▼
              Investigator Decision
```

RecoverAI's final vision is to make digital evidence recovery **faster, more systematic, explainable, and useful to investigators**, while clearly communicating uncertainty and preserving the distinction between original evidence and reconstructed data.

---

# 🧪 Current Implementation Status

The repository now contains an end-to-end implementation of the core RecoverAI workflow rather than only a UI prototype.

## Implemented

- File upload and byte-level SHA-256 identification
- Format-aware integrity analysis for images, PDF, DOCX and ZIP
- Image structure / CRC / decode checks and localized visual anomaly detection
- PDF strict + lenient parsing and XRef reconstruction recovery path
- ZIP/DOCX package and CRC/XML validation
- Non-destructive single-file recovery with post-recovery validation
- Trained ML artifacts for file classification, corruption detection, recovery confidence and fragment matching
- Runtime ML inference exposed as **advisory signals** alongside deterministic parser evidence
- Explainable evidence-priority score based on recovery potential, integrity and validation outcome
- Multi-fragment matching, ordering and reconstruction endpoint
- Reconstruction evidence report containing proposed order, pair scores, output SHA-256 and validation result
- React investigator dashboard with Analysis, Recovery, Fragment Lab, Results
- Express API gateway between the React client and Python forensic engine
- 50 MB upload protection and bounded 32-fragment reconstruction requests
- Automated Python regression tests for API routes, detectors and recovery strategies

## Important forensic limitation

The ML models are trained on the repository's synthetic fragment dataset. They are therefore presented as supporting evidence, not as authoritative proof of corruption, authenticity, or recoverability. Structural parsers and validation checks remain the primary evidence source.

A reconstructed file is always a **candidate artifact**. The original bytes are never modified, and a successful concatenation does not by itself prove that the original file has been recovered exactly.

## Runtime architecture

```text
React / Vite
    │
    ▼
Express API :5000
    │
    ├── /api/analysis/analyze
    ├── /api/recovery/recover
    └── /api/fragments/reconstruct
    │
    ▼
Flask forensic engine :5001
    │
    ├── recoverai_core/analyzer.py
    ├── recoverai_core/detectors/*
    ├── recoverai_core/recovery/engine.py
    ├── recoverai_core/recovery/fragments.py
    └── ml/inference/service.py
```

## Local startup

### 1. Python engine

```bash
cd api
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Flask runs on `http://127.0.0.1:5001`.

### 2. Express gateway

```bash
cd server
npm install
npm run dev
```

Express runs on `http://localhost:5000`.

### 3. React client

```bash
cd client
npm install
npm run dev
```

The client defaults to `http://localhost:5000/api`. Set `VITE_API_BASE_URL` only if the Express gateway is hosted elsewhere.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Express health check |
| `POST /api/analysis/analyze` | Analyze one evidence file |
| `POST /api/recovery/recover` | Repair and validate one supported file |
| `POST /api/fragments/reconstruct` | Match/order/concatenate multiple fragments and validate the candidate |
| `GET /api/health` on Flask | Python engine health check |

## Validation command

The Python test suite can be run with:

```bash
cd api
python -m unittest discover -s tests -v
```

The suite covers the implemented parser/recovery paths. Some tests intentionally skip when optional external corruption samples are not present.

---

# Current completion notes

The current implementation treats the trained ML models as an advisory forensic layer and the format-aware parsers/recovery engines as the authoritative validation layer.

### Recovery reporting

A recovery candidate can now be reported as:

- `completed` — the candidate changed the bytes and passed post-recovery validation without detected content-loss warnings.
- `completed_partial` — the candidate passed structural validation, but the repair engine explicitly reports content that could not be carried forward (for example, an unreadable PDF page or an unreadable ZIP member).
- `failed` — no validated candidate was produced; the original bytes are preserved.
- `not_needed` — the input did not show confirmed damage.

Recovery reports include original/repaired SHA-256 fingerprints, before/after analysis, applied methods, warnings, AI advisory signals, and quality information such as PDF page retention when measurable.

### Fragment ordering safeguards

Runtime fragment uploads normally do not contain ground-truth offsets. RecoverAI therefore does not use the browser upload order as a fake training feature. The fragment matcher uses neutral runtime position/offset values and combines its prediction with deterministic byte-continuity and file-signature evidence.

When fragment filenames expose a complete, unambiguous sequence such as `fragment_0000.bin`, `fragment_0001.bin`, etc., that filename sequence is treated as explicit evidence and is used to reconstruct the order. The report records the ordering method so the investigator can see why the order was chosen.

### Important ML limitation

The bundled models were trained on the project's synthetic fragment dataset. Their predictions are useful for triage, ranking, compatibility scoring, and recovery-confidence estimation, but they are not proof that bytes are corrupt or that a reconstruction is byte-exact. Structural parsers and post-recovery validation remain authoritative.

### Verification performed

The final source has been syntax-checked with Python `compileall`. Core recovery/image tests and the added runtime completion tests pass in the available environment. Full Flask API test collection and TypeScript compilation require the project's declared Node/Python dependencies to be installed locally; the validation environment used for this build does not have network access to install missing packages.

---

# Current Product Scope

The web application contains five primary workspaces:

1. **Dashboard** — system status and workflow entry points.
2. **Analyze** — upload evidence and inspect format-aware + ML findings.
3. **Recover** — generate, validate, and download a repaired/purified candidate.
4. **Fragments** — upload fragments, infer ordering, reconstruct, and validate.
5. **Results** — review integrity, recovery potential, findings, AI advisory signals, and evidence priority.

The previous standalone **AI Investigator** page has intentionally been removed. Its useful information is now surfaced directly in Analyze, Recover, Fragments, and Results so the workflow stays focused.

## Recovery Semantics

RecoverAI never treats a changed file as automatically recovered. A candidate is accepted only after re-analysis. PDF and archive repairs may be reported as `completed_partial` when some content cannot be carried forward. Image purification reports the trained model, number of pixels purified, number of passes, and the post-repair validation result.

Original input bytes are preserved conceptually by the service: recovery produces a separate candidate artifact and records SHA-256 hashes for before/after comparison.

## Deep-learning image restoration

RecoverAI now supports an optional LaMa ONNX inpainting backend for localized
image damage. The model is deliberately not committed to GitHub because the
weight file is approximately 88 MB. After cloning the repository, run:

```bash
cd api
python ml/download_models.py
```

If the model is unavailable, RecoverAI automatically falls back to its bundled
trained masked-pixel purifier and then deterministic OpenCV/NumPy methods.

This deep-learning path is intentionally limited to image restoration. PDFs,
DOCX files, and ZIP archives still use format-aware structural recovery: a
vision model cannot reliably reconstruct arbitrary binary/container bytes.

## Stronger recovery backends

For better structural recovery, RecoverAI can use two optional forensic command-line tools when they are available on `PATH`:

- **qpdf** for damaged PDF cross-reference/object structures.
- **7-Zip** for damaged ZIP/DOCX containers whose central directory cannot be read by Python's standard library.

The application never requires these tools to analyze a file. If they are missing, it falls back to the bundled Python recovery strategies and reports that fallback explicitly.

### GitHub model policy

The small RecoverAI `.joblib` models are included in the repository. The optional LaMa ONNX weights are intentionally excluded because the model is large; download them locally with `python api/ml/download_models.py` after cloning.

## AI / ML architecture

RecoverAI deliberately uses different techniques for different problems:

- **Custom ML models:** file classification, corruption detection, recovery-confidence estimation, fragment matching, and masked image purification.
- **Deep-learning image restoration:** optional OpenCV LaMa ONNX inpainting for localized image damage. The OpenCV model is Apache licensed and is downloaded separately rather than committed to GitHub. The official model card documents the ONNX model and Apache license. See https://huggingface.co/opencv/inpainting_lama.
- **Format-aware recovery:** PDFs, ZIPs and DOCX files are repaired using structural/container-aware algorithms rather than unconstrained generative models. This avoids inventing arbitrary binary content.

The AI Investigator page has been removed. AI evidence is shown directly in Analysis and Recovery results.
