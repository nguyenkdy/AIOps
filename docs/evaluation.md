# Ket qua danh gia detector

## Dieu kien thi nghiem

- Train: khoi du lieu sach ngay 17/08/2026, 519 diem (4.33 gio), chu ky tai 1 gio
- Test: khoi ngay 18/08/2026, 423 diem (3.52 gio), 9 su co co nhan
- Scrape interval 30s; dac trung: gia tri, trung binh truot 15 diem, do lech chuan truot, sai phan
- Nguong lay o percentile 99 cua diem bat thuong tren tap train (khong nhin nhan tap test)

## Danh gia theo diem (point-wise)

| Phuong phap | Precision | Recall | F1 | Duong tinh gia |
|---|---|---|---|---|
| Isolation Forest - 1 metric (latency) | 0.453 | 0.289 | 0.353 | 29 |
| Isolation Forest - 4 metric | 0.432 | 0.771 | 0.554 | 84 |
| STL residual - latency | 0.828 | 0.289 | 0.429 | 5 |

Recall theo loai su co (Isolation Forest):

| Loai | 1 metric | 4 metric |
|---|---|---|
| latency | 79% | 82% |
| cpu | 0% | 80% |
| memory | 25% | 50% |
| memory_sustained | 0% | 100% |
| outage | 0% | 76% |
| podkill | 0% | 50% |

## Danh gia theo su co (event-based)

Isolation Forest 4 metric, gop cac diem bao dong cach nhau duoi 2 phut
thanh mot canh bao, cho phep lech 3 phut so voi moc inject:

- **Phat hien: 9/9 su co (100%)**
- **Canh bao rac: 4 trong 3.5 gio (1.1/gio)**

## Ket luan

1. **Mot metric la khong du.** Chi dung latency thi bo sot hoan toan cpu,
   outage, podkill va memory_sustained. Recall tang tu 0.29 len 0.77 khi
   dung 4 metric.

2. **STL chinh xac hon nhung hep hon.** Cung bat duoc dung tap su co nhu
   Isolation Forest 1 metric, nhung chi bao nham 5 lan thay vi 29 - nho
   tru bo thanh phan chu ky truoc khi so sanh. Hai phuong phap bo sung
   cho nhau chu khong thay the nhau.

3. **Bo loc thoi luong khong hieu qua o day.** Yeu cau 3 diem lien tiep
   lam recall giam tu 0.77 xuong 0.63 ma precision gan nhu khong doi
   (0.432 -> 0.419), vi cac duong tinh gia gom thanh cum chu khong roi rac.

4. **71% duong tinh gia nam trong vong 5 phut quanh mot su co that** -
   do do tre cua metric va cua so rate([2m]), khong phai mo hinh bao bua.
   Day la ly do danh gia theo su kien phan anh dung hon danh gia theo diem.

## Gioi han

- Chi 9 su co: mot su co bo sot lam ti le phat hien tut 11 diem phan tram.
  Con so 100% dinh huong thiet ke, chua du de ket luan.
- Train va test la hai khoi thoi gian khac nhau, khong phai hai moi truong
  doc lap.
- 6% diem trong tap train co gia tri NaN (do request rate thap khien
  histogram_quantile khong tinh duoc), da noi suy tuyen tinh truoc khi chay STL.
