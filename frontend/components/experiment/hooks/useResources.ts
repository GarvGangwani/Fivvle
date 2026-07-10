"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createResource,
  deleteResource,
  listResources,
  patchResource,
} from "@/lib/experiment-api";
import type { ExperimentResource, ResourceType } from "@/lib/types";

export function useResources(experimentId: string) {
  const [resources, setResources] = useState<ExperimentResource[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const rows = await listResources(experimentId);
    setResources(rows);
  }, [experimentId]);

  useEffect(() => {
    let cancelled = false;
    void listResources(experimentId)
      .then((rows) => {
        if (!cancelled) setResources(rows);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  const addResource = useCallback(
    async (payload: {
      title: string;
      url?: string | null;
      note?: string | null;
      resource_type?: ResourceType;
    }) => {
      const row = await createResource(experimentId, payload);
      setResources((prev) => [row, ...prev]);
      return row;
    },
    [experimentId],
  );

  const updateResource = useCallback(
    async (
      resourceId: string,
      payload: Partial<{
        title: string;
        url: string | null;
        note: string | null;
        resource_type: ResourceType;
      }>,
    ) => {
      const row = await patchResource(experimentId, resourceId, payload);
      setResources((prev) => prev.map((p) => (p.id === resourceId ? row : p)));
      return row;
    },
    [experimentId],
  );

  const removeResource = useCallback(
    async (resourceId: string) => {
      await deleteResource(experimentId, resourceId);
      setResources((prev) => prev.filter((p) => p.id !== resourceId));
    },
    [experimentId],
  );

  return {
    resources,
    loading,
    refresh,
    addResource,
    updateResource,
    removeResource,
  };
}
