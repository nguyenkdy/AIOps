"""Doc metrics.csv + fault-log.csv -> gan nhan va cat cac khoi lien tuc."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def load(metrics_path=None, faults_path=None):
    metrics_path = metrics_path or ROOT / "data" / "metrics.csv"
    faults_path = faults_path or ROOT / "docs" / "fault-log.csv"
    df = pd.read_csv(metrics_path, index_col="time", parse_dates=["time"])
    df = df.sort_index()

    faults = pd.read_csv(faults_path)
    faults["start_utc"] = pd.to_datetime(faults["start_utc"], utc=True)
    faults["end_utc"] = pd.to_datetime(faults["end_utc"], utc=True)

    # Cot nhan: 1 neu diem nam trong khoang mot su co
    df["label"] = 0
    df["fault_type"] = ""
    for _, row in faults.iterrows():
        # noi rong 60s moi ben: metric phan ung tre hon thoi diem inject
        mask = (df.index >= row.start_utc - pd.Timedelta(seconds=60)) & \
               (df.index <= row.end_utc + pd.Timedelta(seconds=60))
        df.loc[mask, "label"] = 1
        df.loc[mask, "fault_type"] = row.type

    # Danh so khoi lien tuc: khoang cach > 5 phut nghia la VM da tat
    gap = df.index.to_series().diff() > pd.Timedelta(minutes=5)
    df["block"] = gap.cumsum()

    return df, faults


if __name__ == "__main__":
    df, faults = load()

    print("Tong so diem:", len(df))
    print("So diem bat thuong:", int(df.label.sum()),
          f"({100 * df.label.mean():.2f}%)")
    print()

    print("Cac khoi du lieu lien tuc:")
    for block_id, block in df.groupby("block"):
        hours = len(block) * 30 / 3600
        n_faults = block[block.label == 1].fault_type.nunique()
        print(f"  khoi {block_id}: {len(block):5d} diem "
              f"({hours:5.2f} gio)  {block.index.min()} -> {block.index.max()}  "
              f"{n_faults} loai su co")
    print()

    print("So diem theo loai su co:")
    print(df[df.label == 1].fault_type.value_counts().to_string())
    print()

    print("Gia tri trung binh khi binh thuong vs bat thuong:")
    cols = ["latency_p95__backend", "cpu__backend", "memory__backend",
            "error_rate__frontend"]
    summary = df.groupby("label")[cols].mean().T
    print(summary.to_string())
