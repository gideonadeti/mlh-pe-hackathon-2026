// Scalability Gold — 500+ VUs, http_req_failed < 5%. See docs/scalability-gold.md

import { createScalabilityScenario } from "./scalability-shared.js";

export const options = {
  vus: 500,
  duration: "2m",
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<2000"], // p95 < 2s as per Gold proposal
  },
};

export function handleSummary(data) {
  const { metrics } = data;
  const failRate = metrics.http_req_failed.values.rate;
  const p95Duration = metrics.http_req_duration.values["p(95)"];
  
  const success = failRate < 0.05 && p95Duration < 2000;
  
  const summary = {
    test_name: "Scalability Gold",
    timestamp: new Date().toISOString(),
    success: success,
    metrics: {
      http_req_failed: failRate,
      http_req_duration_p95: p95Duration,
      iterations: metrics.iterations.values.count,
      vus: metrics.vus.values.max || options.vus,
    },
    thresholds: {
      http_req_failed: "rate < 0.05",
      http_req_duration_p95: "p(95) < 2000",
    }
  };

  return {
    "stdout": JSON.stringify(summary, null, 2) + "\n",
    "quest-log/scalability-gold.json": JSON.stringify(summary, null, 2),
  };
}

export default createScalabilityScenario("https://shurl.kdmarc.xyz");
