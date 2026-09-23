import { useQuery } from "@tanstack/react-query";

import { getHealthOptions } from "../../api/client";
import { StatusView } from "./StatusView";

export function StatusPage() {
  const healthQuery = useQuery({ ...getHealthOptions(), gcTime: 0 });

  if (healthQuery.isPending) {
    return <StatusView state={{ kind: "loading" }} />;
  }
  if (healthQuery.isError || healthQuery.data?.status !== "ok") {
    return <StatusView state={{ kind: "error" }} />;
  }
  return <StatusView state={{ kind: "success" }} />;
}
