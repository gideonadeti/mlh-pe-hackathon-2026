// Scalability Gold — 500+ VUs, http_req_failed < 5%. See docs/scalability-gold.md

import { createScalabilityScenario } from "./scalability-shared.js";

export const options = {
  vus: 500,
  duration: "2m",
  thresholds: {
    http_req_failed: ["rate<0.05"],
  },
};

export default createScalabilityScenario("https://shurl.kdmarc.xyz");
