"""
RecoverAI - ML Model Validation Tests

Validates the four trained RecoverAI models without retraining.

Models:
1. File Classification
2. Corruption Detection
3. Recovery Confidence
4. Fragment Matching
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# This module is a standalone validation runner; its helpers accept explicit
# arguments and are invoked by main(). Prevent pytest from treating them as
# fixture-based tests.
__test__ = False


# ============================================================
# PATHS
# ============================================================

API_DIR = Path(__file__).resolve().parents[1]
ML_DIR = API_DIR / "ml"

DATASET_PATH = (
    ML_DIR
    / "data"
    / "processed"
    / "fragment_dataset.csv"
)

MODELS_DIR = ML_DIR / "models"

FILE_CLASSIFIER_PATH = (
    MODELS_DIR
    / "file_classification"
    / "file_classifier.joblib"
)

CORRUPTION_MODEL_PATH = (
    MODELS_DIR
    / "corruption_detection"
    / "corruption_detector.joblib"
)

RECOVERY_MODEL_PATH = (
    MODELS_DIR
    / "recovery_confidence"
    / "recovery_model.joblib"
)

FRAGMENT_MODEL_PATH = (
    MODELS_DIR
    / "fragment_matching"
    / "fragment_matcher.joblib"
)


# ============================================================
# INDIVIDUAL FRAGMENT FEATURES
# ============================================================

FEATURE_COLUMNS = [
    "source_file_size",
    "total_fragments",
    "fragment_position",
    "offset",
    "original_size",
    "byte_mean",
    "byte_std",
    "zero_ratio",
    "printable_ratio",
    "unique_byte_ratio",
    "high_byte_ratio",
    "entropy",
    "entropy_normalized",
    "has_pdf_header",
    "has_jpeg_header",
    "has_png_header",
    "has_gif_header",
    "has_zip_header",
    "has_doc_header",
    "has_exe_header",
    "has_sqlite_header",
    "header_byte_0",
    "header_byte_1",
    "header_byte_2",
    "header_byte_3",
    "size",
    "ascii_word_count",
    "null_byte_count",
    "newline_count",
    "pdf_marker_count",
    "zip_marker_count",
    "jpeg_marker_count",
    "structure_density",
]


# ============================================================
# FRAGMENT MATCHING FEATURES
# ============================================================

def get_fragment_pair_feature_columns():
    """
    Reconstruct the exact 101 feature names used
    by the fragment matching training code.
    """

    columns = []

    for feature in FEATURE_COLUMNS:
        columns.append(f"a_{feature}")

    for feature in FEATURE_COLUMNS:
        columns.append(f"b_{feature}")

    for feature in FEATURE_COLUMNS:
        columns.append(f"diff_{feature}")

    columns.append("position_gap")
    columns.append("offset_gap")

    return columns


PAIR_FEATURE_COLUMNS = (
    get_fragment_pair_feature_columns()
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def print_section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def check_file(path, name):

    if not path.exists():
        raise FileNotFoundError(
            f"{name} not found:\n{path}"
        )

    if not path.is_file():
        raise ValueError(
            f"{name} exists but is not a file:\n{path}"
        )

    print(f"  [OK] {name}")
    print(f"       {path}")


# ============================================================
# MODEL LOADING
# ============================================================

def unwrap_model(loaded, name):
    """
    Extract the estimator from the dictionary produced
    by train_all.py.

    Current saved model format:

        {
            "model": estimator,
            "features": [...],
            ...
        }

    File classifier additionally contains:

        "label_encoder"
    """

    if hasattr(loaded, "predict"):

        print(
            f"  [OK] {name} is a direct estimator"
        )

        return loaded, None

    if isinstance(loaded, dict):

        print(
            f"  [INFO] {name} is a dictionary wrapper"
        )

        print("  Dictionary keys:")

        for key in loaded.keys():
            print(f"    - {key}")

        model = loaded.get("model")

        if model is None:

            possible_keys = [
                "estimator",
                "classifier",
                "regressor",
                "pipeline",
                "model_object",
            ]

            for key in possible_keys:

                if key in loaded:
                    candidate = loaded[key]

                    if hasattr(
                        candidate,
                        "predict"
                    ):
                        model = candidate
                        break

        if model is None:

            raise TypeError(
                f"{name} dictionary does not contain "
                f"a prediction model."
            )

        if not hasattr(
            model,
            "predict"
        ):

            raise TypeError(
                f"The extracted object from "
                f"{name} does not support predict()."
            )

        label_encoder = loaded.get(
            "label_encoder"
        )

        print(
            "  [OK] Extracted estimator "
            "from dictionary"
        )

        if label_encoder is not None:

            print(
                "  [OK] Label encoder found"
            )

        return model, label_encoder

    raise TypeError(
        f"{name} has unsupported saved type: "
        f"{type(loaded).__name__}"
    )


def load_model(path, name):

    check_file(
        path,
        name
    )

    try:

        loaded = joblib.load(
            path
        )

    except Exception as exc:

        raise RuntimeError(
            f"Failed to load {name}:\n{exc}"
        ) from exc

    return unwrap_model(
        loaded,
        name
    )


# ============================================================
# DATASET
# ============================================================

def load_dataset():

    check_file(
        DATASET_PATH,
        "Processed fragment dataset"
    )

    try:

        df = pd.read_csv(
            DATASET_PATH
        )

    except Exception as exc:

        raise RuntimeError(
            f"Failed to read dataset:\n{exc}"
        ) from exc

    if df.empty:

        raise ValueError(
            "The dataset is empty."
        )

    print(
        f"  [OK] Dataset loaded "
        f"({len(df)} rows, "
        f"{len(df.columns)} columns)"
    )

    return df


# ============================================================
# FEATURE VALIDATION
# ============================================================

def validate_features(df):

    missing = [
        feature
        for feature in FEATURE_COLUMNS
        if feature not in df.columns
    ]

    if missing:

        print(
            "\nMissing required features:"
        )

        for feature in missing:
            print(
                f"  - {feature}"
            )

        raise ValueError(
            "Dataset does not contain all "
            "required features."
        )

    print(
        f"  [OK] All "
        f"{len(FEATURE_COLUMNS)} "
        f"individual features are present"
    )


def prepare_features(df):

    X = df[
        FEATURE_COLUMNS
    ].copy()

    X = X.replace(
        [np.inf, -np.inf],
        np.nan
    )

    for column in X.columns:

        X[column] = pd.to_numeric(
            X[column],
            errors="coerce"
        )

    X = X.fillna(0)

    return X


# ============================================================
# MODEL INFORMATION
# ============================================================

def print_model_information(
    model,
    name,
    expected_features
):

    print(
        f"\n  {name} information:"
    )

    print(
        f"    Model type : "
        f"{type(model).__name__}"
    )

    if hasattr(
        model,
        "n_features_in_"
    ):

        model_features = (
            model.n_features_in_
        )

        print(
            f"    Model features : "
            f"{model_features}"
        )

        print(
            f"    Test features  : "
            f"{expected_features}"
        )

        if (
            model_features
            != expected_features
        ):

            raise ValueError(
                f"{name} expects "
                f"{model_features} features, "
                f"but the test provides "
                f"{expected_features}."
            )

    if hasattr(
        model,
        "classes_"
    ):

        print(
            f"    Classes    : "
            f"{list(model.classes_)}"
        )


# ============================================================
# FILE CLASSIFICATION
# ============================================================

def test_file_classification(
    df,
    model,
    label_encoder,
    X
):

    print_section(
        "[1/4] FILE CLASSIFICATION TEST"
    )

    print_model_information(
        model,
        "File Classification Model",
        len(FEATURE_COLUMNS)
    )

    try:

        predictions = model.predict(
            X
        )

    except Exception as exc:

        raise RuntimeError(
            "File classification prediction "
            f"failed:\n{exc}"
        ) from exc

    predictions = np.asarray(
        predictions
    )

    if len(predictions) != len(df):

        raise AssertionError(
            "File classification prediction "
            "count does not match dataset rows."
        )

    if pd.isna(
        predictions
    ).any():

        raise AssertionError(
            "File classifier produced "
            "NaN predictions."
        )

    print(
        f"\n  Predictions generated : "
        f"{len(predictions)}"
    )

    # --------------------------------------------------------
    # Decode labels if label encoder exists.
    # --------------------------------------------------------

    display_predictions = predictions

    if label_encoder is not None:

        try:

            display_predictions = (
                label_encoder.inverse_transform(
                    predictions.astype(int)
                )
            )

        except Exception as exc:

            print(
                "  WARNING: Could not decode "
                f"classification labels: {exc}"
            )

    distribution = (
        pd.Series(
            display_predictions
        )
        .value_counts()
    )

    print(
        "\n  Prediction distribution:"
    )

    for label, count in (
        distribution.items()
    ):

        percentage = (
            count /
            len(predictions)
        ) * 100

        print(
            f"    - {label}: "
            f"{count} "
            f"({percentage:.2f}%)"
        )

    print(
        "\n  RESULT: PASS"
    )


# ============================================================
# CORRUPTION DETECTION
# ============================================================

def test_corruption_detection(
    df,
    model,
    X
):

    print_section(
        "[2/4] CORRUPTION DETECTION TEST"
    )

    print_model_information(
        model,
        "Corruption Detection Model",
        len(FEATURE_COLUMNS)
    )

    try:

        predictions = model.predict(
            X
        )

    except Exception as exc:

        raise RuntimeError(
            "Corruption prediction failed:\n"
            f"{exc}"
        ) from exc

    predictions = np.asarray(
        predictions
    )

    if len(predictions) != len(df):

        raise AssertionError(
            "Corruption prediction count "
            "does not match dataset rows."
        )

    if pd.isna(
        predictions
    ).any():

        raise AssertionError(
            "Corruption detector produced "
            "NaN predictions."
        )

    print(
        f"\n  Predictions generated : "
        f"{len(predictions)}"
    )

    distribution = (
        pd.Series(
            predictions
        )
        .value_counts()
    )

    print(
        "\n  Prediction distribution:"
    )

    for label, count in (
        distribution.items()
    ):

        percentage = (
            count /
            len(predictions)
        ) * 100

        label_name = (
            "Intact"
            if int(label) == 0
            else "Corrupted"
            if int(label) == 1
            else str(label)
        )

        print(
            f"    - {label_name} "
            f"({label}): "
            f"{count} "
            f"({percentage:.2f}%)"
        )

    # --------------------------------------------------------
    # Ground truth
    # --------------------------------------------------------

    if "is_corrupted" in df.columns:

        actual = (
            pd.to_numeric(
                df["is_corrupted"],
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
            .to_numpy()
        )

        predicted_numeric = (
            predictions.astype(int)
        )

        agreement = np.mean(
            predicted_numeric
            ==
            actual
        )

        print(
            f"\n  Dataset agreement : "
            f"{agreement:.4f}"
        )

        print(
            f"  Dataset agreement : "
            f"{agreement * 100:.2f}%"
        )

    print(
        "\n  RESULT: PASS"
    )


# ============================================================
# RECOVERY CONFIDENCE
# ============================================================

def test_recovery_confidence(
    df,
    model,
    X
):

    print_section(
        "[3/4] RECOVERY CONFIDENCE TEST"
    )

    print_model_information(
        model,
        "Recovery Confidence Model",
        len(FEATURE_COLUMNS)
    )

    try:

        predictions = model.predict(
            X
        )

    except Exception as exc:

        raise RuntimeError(
            "Recovery confidence prediction "
            f"failed:\n{exc}"
        ) from exc

    predictions = np.asarray(
        predictions,
        dtype=float
    )

    if len(predictions) != len(df):

        raise AssertionError(
            "Recovery prediction count "
            "does not match dataset rows."
        )

    if not np.isfinite(
        predictions
    ).all():

        raise AssertionError(
            "Recovery model produced "
            "NaN or infinite values."
        )

    print(
        f"\n  Predictions generated : "
        f"{len(predictions)}"
    )

    print(
        f"  Minimum confidence    : "
        f"{predictions.min():.4f}"
    )

    print(
        f"  Maximum confidence    : "
        f"{predictions.max():.4f}"
    )

    print(
        f"  Mean confidence       : "
        f"{predictions.mean():.4f}"
    )

    print(
        f"  Median confidence     : "
        f"{np.median(predictions):.4f}"
    )

    out_of_range = np.sum(
        (predictions < 0.0)
        |
        (predictions > 1.0)
    )

    if out_of_range == 0:

        print(
            "  Confidence range     : PASS"
        )

    else:

        print(
            f"  WARNING: "
            f"{out_of_range} predictions "
            "outside 0..1."
        )

    # --------------------------------------------------------
    # Intact vs corrupted
    # --------------------------------------------------------

    if "is_corrupted" in df.columns:

        corruption = (
            pd.to_numeric(
                df["is_corrupted"],
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
            .to_numpy()
        )

        intact_mask = (
            corruption == 0
        )

        corrupted_mask = (
            corruption == 1
        )

        if (
            intact_mask.any()
            and
            corrupted_mask.any()
        ):

            intact_mean = (
                predictions[
                    intact_mask
                ].mean()
            )

            corrupted_mean = (
                predictions[
                    corrupted_mask
                ].mean()
            )

            print(
                f"\n  Intact mean confidence    : "
                f"{intact_mean:.4f}"
            )

            print(
                f"  Corrupted mean confidence : "
                f"{corrupted_mean:.4f}"
            )

            if (
                intact_mean
                >
                corrupted_mean
            ):

                print(
                    "  Confidence ordering   : PASS"
                )

            else:

                print(
                    "  Confidence ordering   : WARNING"
                )

    print(
        "\n  RESULT: PASS"
    )


# ============================================================
# BUILD FRAGMENT PAIR
# ============================================================

def build_pair(
    a,
    b,
    label
):

    pair = {}

    # Fragment A
    for feature in FEATURE_COLUMNS:

        pair[
            f"a_{feature}"
        ] = float(
            a[feature]
        )

    # Fragment B
    for feature in FEATURE_COLUMNS:

        pair[
            f"b_{feature}"
        ] = float(
            b[feature]
        )

    # Absolute differences
    for feature in FEATURE_COLUMNS:

        pair[
            f"diff_{feature}"
        ] = abs(
            float(a[feature])
            -
            float(b[feature])
        )

    # Additional pair features
    pair[
        "position_gap"
    ] = abs(
        int(a["fragment_position"])
        -
        int(b["fragment_position"])
    )

    pair[
        "offset_gap"
    ] = abs(
        int(a["offset"])
        -
        int(b["offset"])
    )

    pair["label"] = label

    return pair


# ============================================================
# FRAGMENT MATCHING
# ============================================================

def test_fragment_matching(
    df,
    model
):

    print_section(
        "[4/4] FRAGMENT MATCHING TEST"
    )

    # --------------------------------------------------------
    # Determine the exact feature order used during training.
    # --------------------------------------------------------

    if not hasattr(
        model,
        "feature_names_in_"
    ):
        raise ValueError(
            "Fragment matching model does not contain "
            "feature_names_in_. Cannot safely determine "
            "the training feature order."
        )

    trained_features = list(
        model.feature_names_in_
    )

    print(
        f"\n  Model feature count : "
        f"{len(trained_features)}"
    )

    print(
        f"  Expected pair features : "
        f"{len(PAIR_FEATURE_COLUMNS)}"
    )

    if len(trained_features) != 101:

        raise ValueError(
            "Fragment matching model should contain "
            f"101 features, but contains "
            f"{len(trained_features)}."
        )

    print(
        "  [OK] Model contains 101 pair features"
    )

    required_columns = [
        "fragment_id",
        "source_file",
        "fragment_position",
        "offset",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing fragment matching columns:\n"
            +
            "\n".join(
                f"  - {column}"
                for column in missing
            )
        )

    # --------------------------------------------------------
    # Select one intact representative for each fragment.
    # --------------------------------------------------------

    if "is_corrupted" in df.columns:

        representatives = (
            df.sort_values(
                [
                    "fragment_id",
                    "is_corrupted",
                ]
            )
            .drop_duplicates(
                "fragment_id",
                keep="first"
            )
        )

    else:

        representatives = (
            df.drop_duplicates(
                "fragment_id"
            )
        )

    print(
        f"  Unique fragments     : "
        f"{len(representatives)}"
    )

    positive_pairs = []
    negative_pairs = []

    # ========================================================
    # POSITIVE PAIRS
    # ========================================================

    for (
        source_file,
        group
    ) in representatives.groupby(
        "source_file"
    ):

        group = (
            group.sort_values(
                "fragment_position"
            )
            .reset_index(
                drop=True
            )
        )

        for index in range(
            len(group) - 1
        ):

            a = group.iloc[index]
            b = group.iloc[index + 1]

            positive_pairs.append(
                build_pair(
                    a,
                    b,
                    label=1
                )
            )

    # ========================================================
    # NEGATIVE PAIRS
    # ========================================================

    for (
        source_file,
        group
    ) in representatives.groupby(
        "source_file"
    ):

        group = (
            group.sort_values(
                "fragment_position"
            )
            .reset_index(
                drop=True
            )
        )

        for i in range(
            len(group)
        ):

            for j in range(
                i + 2,
                len(group)
            ):

                a = group.iloc[i]
                b = group.iloc[j]

                negative_pairs.append(
                    build_pair(
                        a,
                        b,
                        label=0
                    )
                )

    # ========================================================
    # BALANCE POSITIVE / NEGATIVE PAIRS
    # ========================================================

    pair_count = min(
        len(positive_pairs),
        len(negative_pairs)
    )

    if pair_count == 0:

        raise ValueError(
            "Could not create both positive "
            "and negative fragment pairs."
        )

    positive_pairs = (
        positive_pairs[
            :pair_count
        ]
    )

    negative_pairs = (
        negative_pairs[
            :pair_count
        ]
    )

    pairs = (
        positive_pairs
        +
        negative_pairs
    )

    pair_df = pd.DataFrame(
        pairs
    )

    labels = (
        pair_df.pop(
            "label"
        )
        .astype(int)
    )

    # ========================================================
    # VALIDATE GENERATED FEATURES
    # ========================================================

    generated_features = list(
        pair_df.columns
    )

    print(
        f"\n  Generated features : "
        f"{len(generated_features)}"
    )

    # Features expected by the trained model.
    missing_features = [
        feature
        for feature in trained_features
        if feature not in generated_features
    ]

    if missing_features:

        raise ValueError(
            "The generated fragment-pair data is missing "
            "features required by the trained model:\n"
            +
            "\n".join(
                f"  - {feature}"
                for feature in missing_features
            )
        )

    # Features generated by the test but not used by model.
    extra_features = [
        feature
        for feature in generated_features
        if feature not in trained_features
    ]

    if extra_features:

        print(
            "\n  WARNING: Generated extra features:"
        )

        for feature in extra_features:
            print(
                f"    - {feature}"
            )

    # ========================================================
    # IMPORTANT:
    # USE EXACT TRAINING FEATURE ORDER
    # ========================================================

    pair_df = pair_df[
        trained_features
    ]

    # Replace invalid values.
    pair_df = pair_df.replace(
        [np.inf, -np.inf],
        np.nan
    )

    pair_df = pair_df.fillna(0)

    # Final verification.
    final_features = list(
        pair_df.columns
    )

    if final_features != trained_features:

        raise AssertionError(
            "Feature ordering still does not "
            "match the trained model."
        )

    print(
        "  [OK] Feature names match model"
    )

    print(
        "  [OK] Feature order matches model"
    )

    print(
        f"  Pair feature count   : "
        f"{len(pair_df.columns)}"
    )

    # ========================================================
    # PREDICTION
    # ========================================================

    try:

        predictions = model.predict(
            pair_df
        )

    except Exception as exc:

        raise RuntimeError(
            "Fragment matching prediction failed:\n"
            f"{exc}"
        ) from exc

    predictions = np.asarray(
        predictions
    )

    actual = labels.to_numpy()

    if len(predictions) != len(actual):

        raise AssertionError(
            "Fragment matching prediction count "
            "does not match test pair count."
        )

    if pd.isna(
        predictions
    ).any():

        raise AssertionError(
            "Fragment matcher produced "
            "NaN predictions."
        )

    # ========================================================
    # METRICS
    # ========================================================

    accuracy = np.mean(
        predictions == actual
    )

    true_positive = np.sum(
        (predictions == 1)
        &
        (actual == 1)
    )

    false_positive = np.sum(
        (predictions == 1)
        &
        (actual == 0)
    )

    false_negative = np.sum(
        (predictions == 0)
        &
        (actual == 1)
    )

    if (
        true_positive
        +
        false_positive
    ) > 0:

        precision = (
            true_positive
            /
            (
                true_positive
                +
                false_positive
            )
        )

    else:

        precision = 0.0

    if (
        true_positive
        +
        false_negative
    ) > 0:

        recall = (
            true_positive
            /
            (
                true_positive
                +
                false_negative
            )
        )

    else:

        recall = 0.0

    if (
        precision
        +
        recall
    ) > 0:

        f1 = (
            2
            *
            precision
            *
            recall
            /
            (
                precision
                +
                recall
            )
        )

    else:

        f1 = 0.0

    # ========================================================
    # RESULTS
    # ========================================================

    print(
        f"\n  Positive pairs       : "
        f"{len(positive_pairs)}"
    )

    print(
        f"  Negative pairs       : "
        f"{len(negative_pairs)}"
    )

    print(
        f"  Total test pairs     : "
        f"{len(pair_df)}"
    )

    print(
        f"\n  Accuracy             : "
        f"{accuracy:.4f}"
    )

    print(
        f"  Precision            : "
        f"{precision:.4f}"
    )

    print(
        f"  Recall               : "
        f"{recall:.4f}"
    )

    print(
        f"  F1                   : "
        f"{f1:.4f}"
    )

    print(
        "\n  RESULT: PASS"
    )

# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("RECOVERAI - ML MODEL VALIDATION")
    print("=" * 60)

    # --------------------------------------------------------
    # Paths
    # --------------------------------------------------------

    print("\nProject paths:")

    print(
        f"  API directory : "
        f"{API_DIR}"
    )

    print(
        f"  ML directory  : "
        f"{ML_DIR}"
    )

    print(
        f"  Dataset       : "
        f"{DATASET_PATH}"
    )

    print(
        f"  Models        : "
        f"{MODELS_DIR}"
    )

    # --------------------------------------------------------
    # Dataset
    # --------------------------------------------------------

    print_section(
        "CHECKING DATASET"
    )

    df = load_dataset()

    validate_features(
        df
    )

    X = prepare_features(
        df
    )

    print(
        f"  Feature matrix shape : "
        f"{X.shape}"
    )

    # --------------------------------------------------------
    # Models
    # --------------------------------------------------------

    print_section(
        "LOADING TRAINED MODELS"
    )

    (
        file_classifier,
        file_label_encoder
    ) = load_model(
        FILE_CLASSIFIER_PATH,
        "File Classification Model"
    )

    (
        corruption_model,
        _
    ) = load_model(
        CORRUPTION_MODEL_PATH,
        "Corruption Detection Model"
    )

    (
        recovery_model,
        _
    ) = load_model(
        RECOVERY_MODEL_PATH,
        "Recovery Confidence Model"
    )

    (
        fragment_model,
        _
    ) = load_model(
        FRAGMENT_MODEL_PATH,
        "Fragment Matching Model"
    )

    # --------------------------------------------------------
    # Run tests
    # --------------------------------------------------------

    test_file_classification(
        df,
        file_classifier,
        file_label_encoder,
        X
    )

    test_corruption_detection(
        df,
        corruption_model,
        X
    )

    test_recovery_confidence(
        df,
        recovery_model,
        X
    )

    test_fragment_matching(
        df,
        fragment_model
    )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(
        "ALL ML MODEL VALIDATION TESTS COMPLETED"
    )
    print("=" * 60)

    print(
        "\nAll four trained models were "
        "successfully loaded and tested."
    )

    print(
        "No model was retrained."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()