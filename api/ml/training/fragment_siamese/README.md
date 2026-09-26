# RecoverAI Fragment Siamese 1D-CNN

This module is isolated from the existing RecoverAI implementation. It predicts whether fragment **B immediately follows fragment A**.

## Architecture

- Shared 1D CNN encoder for the last 512 bytes of A and first 512 bytes of B.
- 256-dimensional embeddings.
- Pair features: `A`, `B`, `abs(A-B)`, and `A*B`.
- MLP pair scorer with a single binary logit.
- `BCEWithLogitsLoss` with positive-class balancing.

## Files

```text
api/ml/models/fragment_siamese/
  config.py
  encoder.py
  scorer.py
  model.py

api/ml/training/fragment_siamese/
  dataset.py
  metrics.py
  train.py
  evaluate.py
  inference.py
  generate_dataset.py
```

## Install

From `api/`:

```bash
pip install -r fragment_siamese_requirements.txt
```

## Generate data

Put independent healthy source files under:

```text
api/ml/data/fragment_siamese/raw/
```

Then:

```bash
python ml/training/fragment_siamese/generate_dataset.py
```

For meaningful evaluation, use **many independent source files**. Do not use only the five sample files shipped with the project as evidence of generalization.

## Train

From `api/`:

```bash
python ml/training/fragment_siamese/train.py --epochs 30 --batch-size 64
```

The checkpoint is written to:

```text
api/ml/models/fragment_siamese/fragment_siamese.pt
```

## Evaluate

```bash
python ml/training/fragment_siamese/evaluate.py --checkpoint ml/models/fragment_siamese/fragment_siamese.pt
```

## Python inference

```python
from ml.training.fragment_siamese.inference import FragmentPairPredictor

predictor = FragmentPairPredictor(
    "ml/models/fragment_siamese/fragment_siamese.pt"
)
result = predictor.predict_bytes(fragment_a, fragment_b)
print(result)
```

The result has the form:

```json
{
  "probability": 0.93,
  "is_adjacent": true
}
```

## Important

This model scores **pairs**. Supporting 3, 10, or 100+ fragments comes from running the pair scorer across candidate pairs and then using a separate global ordering/reconstruction algorithm. That reconstruction layer will be built and tested after the pair model has a trustworthy held-out benchmark.

Do not replace the existing RecoverAI fragment URL yet. The new model must first pass the held-out benchmark and multi-fragment reconstruction tests.
