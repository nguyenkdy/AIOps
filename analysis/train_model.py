"""Train Isolation Forest tren khoi du lieu sach, luu model + nguong + schema."""
import json
from pathlib import Path

import joblib
import numpy as np

from detect import make_features
from label import load

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "detector" / "models"

TRAIN_BLOCK = 1
FEATURE_COLS = [
    "latency_p95__backend",
    "cpu__backend",
    "memory__backend",
    "error_rate__frontend",
]
PERCENTILE = 99


def main():
    df, _ = load()
    train = df[df.block == TRAIN_BLOCK]
    print(f"Train tren {len(train)} diem, tu {train.index.min()} den {train.index.max()}")

    X = make_features(train, FEATURE_COLS)
    print(f"So dac trung: {X.shape[1]}")

    from sklearn.ensemble import IsolationForest
    model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
    model.fit(X)

    scores = -model.score_samples(X)
    threshold = float(np.percentile(scores, PERCENTILE))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT_DIR / "isolation_forest.joblib")

    meta = {
        "feature_cols": FEATURE_COLS,
        "feature_names": list(X.columns),   # dung thu tu, detector phai khop
        "threshold": threshold,
        "percentile": PERCENTILE,
        "train_block": TRAIN_BLOCK,
        "train_start": str(train.index.min()),
        "train_end": str(train.index.max()),
        "train_points": len(train),
        "sklearn_version": __import__("sklearn").__version__,
    }
    (OUT_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))

    print(f"\nNguong (percentile {PERCENTILE}): {threshold:.4f}")
    print(f"Diem bat thuong tren tap train: min {scores.min():.4f}, "
          f"max {scores.max():.4f}, trung binh {scores.mean():.4f}")
    print(f"\nDa luu vao {OUT_DIR}")


if __name__ == "__main__":
    main()
