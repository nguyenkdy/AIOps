"""Danh gia theo su co (event-based) thay vi theo tung diem."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from detect import make_features, TRAIN_BLOCK, TEST_BLOCK
from label import load

GRACE = pd.Timedelta(minutes=3)   # do tre cho phep sau khi su co ket thuc


def to_events(index, y_pred, max_gap=pd.Timedelta(minutes=2)):
    """Gop cac diem bao dong lien tiep thanh mot 'canh bao'."""
    times = index[y_pred == 1]
    if len(times) == 0:
        return []
    events = []
    start = prev = times[0]
    for t in times[1:]:
        if t - prev > max_gap:
            events.append((start, prev))
            start = t
        prev = t
    events.append((start, prev))
    return events


def main():
    df, faults = load()
    train = df[df.block == TRAIN_BLOCK]
    test = df[df.block == TEST_BLOCK]

    cols = ["latency_p95__backend", "cpu__backend",
            "memory__backend", "error_rate__frontend"]

    model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
    X_train = make_features(train, cols)
    model.fit(X_train)
    thr = np.percentile(-model.score_samples(X_train), 99)
    y_pred = (-model.score_samples(make_features(test, cols)) > thr).astype(int)

    alerts = to_events(test.index, y_pred)
    window_start = test.index.min()
    window_end = test.index.max()
    faults_in = faults[(faults.start_utc >= window_start) &
                       (faults.end_utc <= window_end)]

    print(f"Cua so danh gia: {window_start} -> {window_end}")
    print(f"So su co that: {len(faults_in)}")
    print(f"So canh bao sinh ra: {len(alerts)}\n")

    matched_alerts = set()
    print("Tung su co:")
    detected = 0
    for _, f in faults_in.iterrows():
        hit = None
        for i, (a_start, a_end) in enumerate(alerts):
            if a_start <= f.end_utc + GRACE and a_end >= f.start_utc - GRACE:
                hit = i
                matched_alerts.add(i)
                break
        status = "BAT DUOC" if hit is not None else "BO SOT  "
        detected += hit is not None
        print(f"  {status}  {f.type:18s} {f.start_utc:%H:%M:%S}")

    spurious = len(alerts) - len(matched_alerts)
    hours = (window_end - window_start).total_seconds() / 3600

    print(f"\nPhat hien: {detected}/{len(faults_in)} su co "
          f"({100*detected/len(faults_in):.0f}%)")
    print(f"Canh bao rac: {spurious} trong {hours:.1f} gio "
          f"({spurious/hours:.1f}/gio)")


if __name__ == "__main__":
    main()
