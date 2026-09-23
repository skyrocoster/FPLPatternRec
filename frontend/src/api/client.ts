import { client } from "./generated/client.gen";
import { getHealthOptions } from "./generated/@tanstack/react-query.gen";

/** Central handwritten configuration for the generated health API client. */
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5677";
client.setConfig({ baseUrl });

export { getHealthOptions };
export { getHealth } from "./generated/index";
export type {
  GetHealthData,
  GetHealthResponse,
  GetHealthResponses,
  HealthResponse,
} from "./generated/index";
