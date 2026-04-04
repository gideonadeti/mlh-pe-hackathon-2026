// Scalability Silver — 200 VUs. See docs/scalability-silver.md

import { createScalabilityScenario } from "./scalability-shared.js";

export const options = {
  vus: 200,
  duration: "2m",
};

export default createScalabilityScenario("http://127.0.0.1:8080");
