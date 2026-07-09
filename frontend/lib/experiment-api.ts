"use client";

import { apiFetch } from "./api";
import type {
  ActivityItem,
  CanvasLayout,
  CanvasNodeId,
  ExperimentResource,
  NodePosition,
  ResourceType,
} from "./types";

export type CanvasLayoutInput = {
  node_positions: Record<CanvasNodeId, NodePosition>;
};

export async function getCanvasLayout(
  experimentId: string,
): Promise<CanvasLayout> {
  return apiFetch<CanvasLayout>(`/experiments/${experimentId}/canvas-layout`);
}

export async function upsertCanvasLayout(
  experimentId: string,
  payload: CanvasLayoutInput,
): Promise<CanvasLayout> {
  return apiFetch<CanvasLayout>(`/experiments/${experimentId}/canvas-layout`, {
    method: "PUT",
    body: payload,
  });
}

export async function listResources(
  experimentId: string,
): Promise<ExperimentResource[]> {
  return apiFetch<ExperimentResource[]>(`/experiments/${experimentId}/resources`);
}

export async function createResource(
  experimentId: string,
  payload: {
    title: string;
    url?: string | null;
    note?: string | null;
    resource_type?: ResourceType;
  },
): Promise<ExperimentResource> {
  return apiFetch<ExperimentResource>(`/experiments/${experimentId}/resources`, {
    method: "POST",
    body: payload,
  });
}

export async function patchResource(
  experimentId: string,
  resourceId: string,
  payload: Partial<{
    title: string;
    url: string | null;
    note: string | null;
    resource_type: ResourceType;
  }>,
): Promise<ExperimentResource> {
  return apiFetch<ExperimentResource>(
    `/experiments/${experimentId}/resources/${resourceId}`,
    {
      method: "PATCH",
      body: payload,
    },
  );
}

export async function deleteResource(
  experimentId: string,
  resourceId: string,
): Promise<void> {
  await apiFetch<void>(`/experiments/${experimentId}/resources/${resourceId}`, {
    method: "DELETE",
  });
}

export async function getActivity(
  experimentId: string,
  limit = 30,
): Promise<ActivityItem[]> {
  return apiFetch<ActivityItem[]>(
    `/experiments/${experimentId}/activity?limit=${limit}`,
  );
}

export async function createExperimentEvent(
  experimentId: string,
  payload: { event_type: string; payload: Record<string, unknown> },
): Promise<ActivityItem> {
  return apiFetch<ActivityItem>(`/experiments/${experimentId}/events`, {
    method: "POST",
    body: payload,
  });
}
