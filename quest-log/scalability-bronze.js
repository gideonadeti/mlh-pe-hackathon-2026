// Scalability Bronze — k6. See docs/scalability-bronze.md

import { createScalabilityScenario } from "./scalability-shared.js";

export const options = {
  vus: 50,
  duration: "2m",
};

export default createScalabilityScenario("http://127.0.0.1:5000");
