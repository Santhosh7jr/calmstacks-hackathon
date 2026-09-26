from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATASET_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "fragment_dataset.csv"
)

MODELS_DIR = BASE_DIR / "models"

METRICS_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "metrics"
)


# =========================================================
# FEATURES
# =========================================================

NON_FEATURE_COLUMNS = {
    "fragment_id",
    "source_file",
    "source_file_id",
    "previous_fragment",
    "next_fragment",
    "corruption_method",
    "corruption_level",
    "detected_file_type",
    "file_type",
    "is_corrupted",
    "target_corruption_ratio",
    "actual_corrupted_bytes",
}


def load_dataset():

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{DATASET_PATH}"
        )

    df = pd.read_csv(DATASET_PATH)

    if df.empty:
        raise RuntimeError(
            "Dataset is empty."
        )

    return df


def get_numeric_features(df):

    features = []

    for column in df.columns:

        if column in NON_FEATURE_COLUMNS:
            continue

        if pd.api.types.is_numeric_dtype(
            df[column]
        ):
            features.append(column)

    if not features:
        raise RuntimeError(
            "No numeric features available."
        )

    return features


# =========================================================
# SOURCE-LEVEL SPLIT
# =========================================================

def split_by_source(df):

    groups = (
        df["source_file"]
        .fillna("unknown")
        .astype(str)
    )

    unique_groups = groups.unique()

    print(
        f"\nUnique source files detected: "
        f"{len(unique_groups)}"
    )

    if len(unique_groups) < 2:

        raise RuntimeError(
            "At least two source files are required "
            "for source-level evaluation."
        )

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=42,
    )

    train_idx, test_idx = next(
        splitter.split(
            df,
            groups=groups,
        )
    )

    train_df = df.iloc[
        train_idx
    ].copy()

    test_df = df.iloc[
        test_idx
    ].copy()

    print(
        "Using source-level train/test split."
    )

    return train_df, test_df


# =========================================================
# SAVE HELPERS
# =========================================================

def save_model(model, path):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        path,
    )


def save_json(data, path):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
        )


# =========================================================
# FILE CLASSIFICATION
# =========================================================

def train_file_classifier(
    train_df,
    test_df,
    features,
):

    print(
        "\n[1/4] Training File Classification Model..."
    )

    X_train = train_df[
        features
    ].fillna(0)

    X_test = test_df[
        features
    ].fillna(0)

    y_train = train_df[
        "detected_file_type"
    ].fillna("unknown")

    y_test = test_df[
        "detected_file_type"
    ].fillna("unknown")

    encoder = LabelEncoder()

    combined = pd.concat(
        [y_train, y_test]
    )

    encoder.fit(
        combined
    )

    y_train_encoded = encoder.transform(
        y_train
    )

    y_test_encoded = encoder.transform(
        y_test
    )

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=20,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )

    model.fit(
        X_train,
        y_train_encoded,
    )

    predictions = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test_encoded,
        predictions,
    )

    f1 = f1_score(
        y_test_encoded,
        predictions,
        average="weighted",
        zero_division=0,
    )

    output_dir = (
        MODELS_DIR
        / "file_classification"
    )

    save_model(
        {
            "model": model,
            "label_encoder": encoder,
            "features": features,
        },
        output_dir
        / "file_classifier.joblib",
    )

    save_json(
        {
            "accuracy": float(accuracy),
            "f1_weighted": float(f1),
            "classes": encoder.classes_.tolist(),
        },
        METRICS_DIR
        / "file_classification.json",
    )

    print(
        f"    Accuracy : {accuracy:.4f}"
    )

    print(
        f"    F1       : {f1:.4f}"
    )


# =========================================================
# CORRUPTION DETECTION
# =========================================================

def train_corruption_detector(
    train_df,
    test_df,
    features,
):

    print(
        "\n[2/4] Training Corruption Detection Model..."
    )

    X_train = train_df[
        features
    ].fillna(0)

    X_test = test_df[
        features
    ].fillna(0)

    y_train = train_df[
        "is_corrupted"
    ].astype(int)

    y_test = test_df[
        "is_corrupted"
    ].astype(int)

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=20,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0,
    )

    output_dir = (
        MODELS_DIR
        / "corruption_detection"
    )

    save_model(
        {
            "model": model,
            "features": features,
        },
        output_dir
        / "corruption_detector.joblib",
    )

    save_json(
        {
            "accuracy": float(accuracy),
            "f1": float(f1),
        },
        METRICS_DIR
        / "corruption_detection.json",
    )

    print(
        f"    Accuracy : {accuracy:.4f}"
    )

    print(
        f"    F1       : {f1:.4f}"
    )


# =========================================================
# RECOVERY CONFIDENCE
# =========================================================

def create_recovery_target(df):

    """
    Build a deterministic recoverability target.

    Higher corruption -> lower recovery confidence.

    We also account for:
      - whether the fragment is truncated
      - whether it has zeroed bytes
      - how much of the fragment remains
    """

    ratio = (
        df["target_corruption_ratio"]
        .astype(float)
        .clip(0.0, 1.0)
    )

    size_ratio = (
        df["size"].astype(float)
        /
        df["original_size"]
        .replace(0, np.nan)
    ).fillna(1.0)

    size_ratio = size_ratio.clip(
        0.0,
        1.0,
    )

    # Base recoverability.
    target = 1.0 - ratio

    # Truncation / deletion lowers confidence.
    target *= (
        0.70
        + 0.30 * size_ratio
    )

    # Strong zero-byte damage gets an additional penalty.
    zero_penalty = (
        df["zero_ratio"]
        .astype(float)
        .clip(0.0, 1.0)
    )

    target *= (
        1.0 - 0.15 * zero_penalty
    )

    return target.clip(
        0.0,
        1.0,
    )


def train_recovery_model(
    train_df,
    test_df,
    features,
):

    print(
        "\n[3/4] Training Recovery Confidence Model..."
    )

    X_train = train_df[
        features
    ].fillna(0)

    X_test = test_df[
        features
    ].fillna(0)

    y_train = create_recovery_target(
        train_df
    )

    y_test = create_recovery_target(
        test_df
    )

    model = RandomForestRegressor(
        n_estimators=500,
        max_depth=25,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(
        X_test
    )

    predictions = np.clip(
        predictions,
        0.0,
        1.0,
    )

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions,
        )
    )

    r2 = r2_score(
        y_test,
        predictions,
    )

    output_dir = (
        MODELS_DIR
        / "recovery_confidence"
    )

    save_model(
        {
            "model": model,
            "features": features,
        },
        output_dir
        / "recovery_model.joblib",
    )

    save_json(
        {
            "mae": float(mae),
            "rmse": float(rmse),
            "r2": float(r2),
        },
        METRICS_DIR
        / "recovery_confidence.json",
    )

    print(
        f"    MAE  : {mae:.4f}"
    )

    print(
        f"    RMSE : {rmse:.4f}"
    )

    print(
        f"    R²   : {r2:.4f}"
    )


# =========================================================
# FRAGMENT PAIR CREATION
# =========================================================

def create_fragment_pairs(
    df,
    features,
):
    """
    Build genuine pair examples.

    Positive:
        actual consecutive fragments.

    Negative:
        fragments from the same source file that are
        NOT consecutive.

    Importantly, each pair is built from the original
    fragment identity/position, not from dataset row order.
    """

    pairs = []

    for source_file, group in df.groupby(
        "source_file"
    ):

        # Only use one representative row for each
        # original fragment.
        #
        # This prevents the 16 corruption variants of
        # the same fragment from becoming duplicate pairs.

        representatives = (
            group.sort_values(
                [
                    "fragment_id",
                    "is_corrupted",
                    "target_corruption_ratio",
                ]
            )
            .drop_duplicates(
                subset=["fragment_id"],
                keep="first",
            )
            .sort_values(
                "fragment_position"
            )
        )

        fragments = list(
            representatives.iterrows()
        )

        if len(fragments) < 2:
            continue

        # -------------------------------------------------
        # Positive pairs
        # -------------------------------------------------

        for i in range(
            len(fragments) - 1
        ):

            _, first = fragments[i]
            _, second = fragments[i + 1]

            if (
                first["fragment_position"] + 1
                != second["fragment_position"]
            ):
                continue

            pair = build_pair_features(
                first,
                second,
                features,
            )

            pair["label"] = 1

            pairs.append(pair)

        # -------------------------------------------------
        # Negative pairs
        # -------------------------------------------------

        for i in range(
            len(fragments)
        ):

            _, first = fragments[i]

            # Choose fragments that are not adjacent.
            for j in range(
                i + 2,
                len(fragments),
            ):

                _, second = fragments[j]

                pair = build_pair_features(
                    first,
                    second,
                    features,
                )

                pair["label"] = 0

                pairs.append(pair)

                # Keep dataset balanced.
                if len(
                    [
                        p
                        for p in pairs
                        if p["label"] == 0
                    ]
                ) >= len(
                    [
                        p
                        for p in pairs
                        if p["label"] == 1
                    ]
                ):

                    break

    return pd.DataFrame(
        pairs
    )


def build_pair_features(
    first,
    second,
    features,
):

    pair = {}

    for feature in features:

        a = float(
            first[feature]
        )

        b = float(
            second[feature]
        )

        pair[
            f"a_{feature}"
        ] = a

        pair[
            f"b_{feature}"
        ] = b

        pair[
            f"diff_{feature}"
        ] = abs(
            a - b
        )

    # Additional positional relationship.
    pair[
        "position_gap"
    ] = abs(
        float(
            second["fragment_position"]
        )
        -
        float(
            first["fragment_position"]
        )
    )

    pair[
        "offset_gap"
    ] = abs(
        float(
            second["offset"]
        )
        -
        (
            float(
                first["offset"]
            )
            +
            float(
                first["original_size"]
            )
        )
    )

    return pair


# =========================================================
# FRAGMENT MATCHING
# =========================================================

def train_fragment_matcher(
    train_df,
    test_df,
    features,
):

    print(
        "\n[4/4] Training Fragment Matching Model..."
    )

    train_pairs = create_fragment_pairs(
        train_df,
        features,
    )

    test_pairs = create_fragment_pairs(
        test_df,
        features,
    )

    if (
        train_pairs.empty
        or test_pairs.empty
    ):

        print(
            "    WARNING: Not enough fragment pairs."
        )

        return

    print(
        f"    Training pairs : "
        f"{len(train_pairs)}"
    )

    print(
        f"    Testing pairs  : "
        f"{len(test_pairs)}"
    )

    X_train = train_pairs.drop(
        columns=["label"]
    )

    y_train = train_pairs[
        "label"
    ]

    X_test = test_pairs.drop(
        columns=["label"]
    )

    y_test = test_pairs[
        "label"
    ]

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=25,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0,
    )

    output_dir = (
        MODELS_DIR
        / "fragment_matching"
    )

    save_model(
        {
            "model": model,
            "features": list(
                X_train.columns
            ),
        },
        output_dir
        / "fragment_matcher.joblib",
    )

    save_json(
        {
            "accuracy": float(
                accuracy
            ),
            "f1": float(
                f1
            ),
            "training_pairs": len(
                train_pairs
            ),
            "testing_pairs": len(
                test_pairs
            ),
        },
        METRICS_DIR
        / "fragment_matching.json",
    )

    print(
        f"    Accuracy : {accuracy:.4f}"
    )

    print(
        f"    F1       : {f1:.4f}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print("\n" + "=" * 60)
    print("RECOVERAI - ML TRAINING")
    print("=" * 60)

    df = load_dataset()

    print(
        f"\nDataset rows : {len(df)}"
    )

    print(
        f"Dataset columns : {len(df.columns)}"
    )

    features = get_numeric_features(
        df
    )

    print(
        f"Numeric features : {len(features)}"
    )

    print("\nFeatures:")

    for feature in features:
        print(
            f"  - {feature}"
        )

    train_df, test_df = split_by_source(
        df
    )

    print(
        "\nSource-level split:"
    )

    print(
        f"Training rows : {len(train_df)}"
    )

    print(
        f"Testing rows  : {len(test_df)}"
    )

    print(
        "\nTraining source files:"
    )

    for source in sorted(
        train_df["source_file"].unique()
    ):
        print(
            f"  - {source}"
        )

    print(
        "\nTesting source files:"
    )

    for source in sorted(
        test_df["source_file"].unique()
    ):
        print(
            f"  - {source}"
        )

    train_file_classifier(
        train_df,
        test_df,
        features,
    )

    train_corruption_detector(
        train_df,
        test_df,
        features,
    )

    train_recovery_model(
        train_df,
        test_df,
        features,
    )

    train_fragment_matcher(
        train_df,
        test_df,
        features,
    )

    print("\n" + "=" * 60)
    print("ALL TRAINING COMPLETE")
    print("=" * 60)

    print(
        f"\nModels saved in:\n{MODELS_DIR}"
    )

    print(
        f"\nMetrics saved in:\n{METRICS_DIR}"
    )


if __name__ == "__main__":
    main()