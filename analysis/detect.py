"""So sanh Isolation Forest (1 metric vs nhieu metric) va STL residual."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_fscore_support
from statsmodels.tsa.seasonal import STL

from label import load

TRAIN_BLOCK = 1     # khoi sach, chu ky 1h
TEST_BLOCK = 2      # khoi chua su co
PERIOD = 120        # 120 diem x 30s = chu ky 1 gio


def make_features(df, cols):
    """Tao dac trung: gia tri, trung binh truot, do lech chuan truot, sai phan."""
    parts = {}
    for col in cols:
        s = df[col]
        parts[col] = s
        parts[col + "_mean15"] = s.rolling(15, min_periods=1).mean()
        parts[col + "_std15"] = s.rolling(15, min_periods=1).std()
        parts[col + "_diff"] = s.diff()
    X = pd.DataFrame(parts, index=df.index)
    return X.bfill().fillna(0)


def sustained(y_pred, k=3):
    """Chi giu bao dong khi co it nhat k diem lien tiep vuot nguong.
    Tuong duong 'for: 90s' trong PrometheusRule."""
    s = pd.Series(y_pred)
    return (s.rolling(k, min_periods=k).sum() == k).fillna(False).astype(int).values


def evaluate(name, y_true, y_pred, fault_types):
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    print(f"\n=== {name} ===")
    print(f"precision {p:.3f}   recall {r:.3f}   f1 {f1:.3f}")
    print(f"so diem bao dong: {int(y_pred.sum())} / {len(y_pred)}")

    print("recall theo tung loai su co:")
    for ftype in sorted(set(fault_types) - {""}):
        mask = fault_types == ftype
        caught = y_pred[mask].sum()
        total = mask.sum()
        print(f"  {ftype:18s} {caught}/{total}  ({100*caught/total:.0f}%)")

    # duong tinh gia: bao dong khi khong co su co
    fp_mask = (y_pred == 1) & (y_true == 0)
    print(f"duong tinh gia: {int(fp_mask.sum())}")
    return p, r, f1


def run_isolation_forest(train, test, cols, label, filter_k=1):
    X_train = make_features(train, cols)
    X_test = make_features(test, cols)

    model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
    model.fit(X_train)

    # Nguong lay tu tap huan luyen (sach), khong nhin nhan cua tap test
    train_scores = -model.score_samples(X_train)
    threshold = np.percentile(train_scores, 99)

    test_scores = -model.score_samples(X_test)
    y_pred = (test_scores > threshold).astype(int)
    if filter_k > 1:
        y_pred = sustained(y_pred, filter_k)

    return evaluate(label, test["label"].values, y_pred, test["fault_type"].values)


def prepare_series(df, col):
    """STL yeu cau chuoi khong NaN va cac diem cach deu nhau."""
    s = df[col]
    # dua ve luoi 30s deu dan, noi suy cho cac diem thieu
    s = s.resample("30s").mean()
    s = s.interpolate(method="time", limit_direction="both")
    return s


def run_stl(train, test, col, label, filter_k=1):
    train_s = prepare_series(train, col)
    test_s = prepare_series(test, col)

    # Do lech chuan phan du tren tap sach -> lam nguong
    train_res = STL(train_s, period=PERIOD, robust=True).fit().resid
    threshold = 3 * train_res.std()

    test_res = STL(test_s, period=PERIOD, robust=True).fit().resid
    # dua ket qua ve dung chi muc cua test goc
    pred_series = (test_res.abs() > threshold).astype(int).reindex(test.index, method="nearest")
    y_pred = pred_series.values
    if filter_k > 1:
        y_pred = sustained(y_pred, filter_k)

    print(f"\n(nguong STL = {threshold:.4f})")
    return evaluate(label, test["label"].values, y_pred, test["fault_type"].values)


if __name__ == "__main__":
    df, _ = load()
    train = df[df.block == TRAIN_BLOCK]
    test = df[df.block == TEST_BLOCK]

    print(f"Train: {len(train)} diem (khoi {TRAIN_BLOCK}, sach)")
    print(f"Test:  {len(test)} diem (khoi {TEST_BLOCK}), "
          f"{int(test.label.sum())} diem bat thuong "
          f"({100*test.label.mean():.1f}%)")

    run_isolation_forest(
        train, test,
        ["latency_p95__backend"],
        "Isolation Forest - chi latency",
    )

    run_isolation_forest(
        train, test,
        ["latency_p95__backend", "cpu__backend",
         "memory__backend", "error_rate__frontend"],
        "Isolation Forest - 4 metric",
    )

    run_stl(train, test, "latency_p95__backend", "STL residual - latency")

    # --- Voi bo loc thoi luong ---
    print("\n" + "=" * 60)
    print("VOI BO LOC: chi bao dong khi 3 diem lien tiep vuot nguong")
    print("=" * 60)

    run_isolation_forest(
        train, test,
        ["latency_p95__backend", "cpu__backend",
         "memory__backend", "error_rate__frontend"],
        "Isolation Forest - 4 metric + loc 3 diem",
        filter_k=3,
    )

    run_stl(train, test, "latency_p95__backend",
            "STL residual - latency + loc 3 diem", filter_k=3)
