import http from 'k6/http';
import { sleep } from 'k6';

// Chu ky 3 gio, mo phong nhip ngay/dem nen lai.
// Khai bao scenario tuong minh de startVUs co hieu luc:
// chu ky ket thuc o 4 VU va bat dau lai cung o 4 VU -> lien mach.
export const options = {
  discardResponseBodies: true,
  scenarios: {
    daily: {
      executor: 'ramping-vus',
      startVUs: 4,
      gracefulRampDown: '10s',
      stages: [
        { duration: '40m', target: 8 },
        { duration: '50m', target: 20 },
        { duration: '40m', target: 10 },
        { duration: '50m', target: 4 },
      ],
    },
  },
};

const TARGET = 'http://172.18.0.2:30080/api/data';

export default function () {
  http.get(TARGET);
  sleep(Math.random() * 2);
}
