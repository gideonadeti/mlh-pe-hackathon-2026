// Scalability Bronze — k6. See docs/scalability-bronze.md

import http from "k6/http";
import { check, sleep } from "k6";

http.setResponseCallback(http.expectedStatuses(302, 404));

const baseUrl = (__ENV.BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const shortCodes = (__ENV.K6_SHORT_CODES || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const parsedFrac = parseFloat(__ENV.K6_SEEDED_FRACTION || "0.5");
const seededFraction = Math.min(
  1,
  Math.max(0, Number.isFinite(parsedFrac) ? parsedFrac : 0.5),
);

const CODE_ALPHABET =
  "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

function randomShortCode() {
  let out = "";
  for (let i = 0; i < 6; i++) {
    out += CODE_ALPHABET[Math.floor(Math.random() * CODE_ALPHABET.length)];
  }
  return out;
}

function pickCode() {
  if (shortCodes.length > 0 && Math.random() < seededFraction) {
    return shortCodes[Math.floor(Math.random() * shortCodes.length)];
  }
  return randomShortCode();
}

export const options = {
  vus: 50,
  duration: "2m",
};

export default function () {
  const code = pickCode();
  const res = http.get(`${baseUrl}/${code}`, { redirects: 0 });
  check(res, {
    "redirect or not found": (r) => r.status === 302 || r.status === 404,
  });
  sleep(0.1 + Math.random() * 0.4);
}
