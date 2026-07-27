"use client";

import type {
  ActivityItem,
  AttachmentType,
  AttachmentUploadUrl,
  CanvasLayout,
  CanvasNodeId,
  Experiment,
  ExperimentAttachment,
  ExperimentResource,
  NodePosition,
  ResourceType,
  SparkVersion,
} from "./types";
import { apiFetch } from "./api";
import { getFirebaseAuth } from "./firebase";
import { handleSessionExpired } from "./session-expired";

export type CanvasLayoutInput = {
  node_positions: Record<CanvasNodeId, NodePosition>;
  viewport_x?: number | null;
  viewport_y?: number | null;
  viewport_zoom?: number | null;
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

export async function saveSparkVersion(
  experimentId: string,
  payload: { raw_idea: string },
): Promise<SparkVersion> {
  return apiFetch<SparkVersion>(`/experiments/${experimentId}/spark/save`, {
    method: "POST",
    body: payload,
  });
}

export async function listSparkVersions(
  experimentId: string,
): Promise<SparkVersion[]> {
  return apiFetch<SparkVersion[]>(
    `/experiments/${experimentId}/spark/versions`,
  );
}

export async function rerunEvidence(
  experimentId: string,
): Promise<{ experiment_id: string; status: string; status_url: string }> {
  return apiFetch(`/experiments/${experimentId}/evidence/rerun`, {
    method: "POST",
  });
}

export async function listAttachments(
  experimentId: string,
): Promise<ExperimentAttachment[]> {
  return apiFetch<ExperimentAttachment[]>(
    `/experiments/${experimentId}/attachments`,
  );
}

export async function createAttachment(
  experimentId: string,
  payload: {
    attachment_type: AttachmentType;
    title: string;
    content_text?: string | null;
    file_url?: string | null;
    file_mime?: string | null;
    file_size_bytes?: number | null;
  },
): Promise<ExperimentAttachment> {
  return apiFetch<ExperimentAttachment>(
    `/experiments/${experimentId}/attachments`,
    { method: "POST", body: payload },
  );
}

export async function patchAttachment(
  experimentId: string,
  attachmentId: string,
  payload: Partial<{ title: string; content_text: string | null }>,
): Promise<ExperimentAttachment> {
  return apiFetch<ExperimentAttachment>(
    `/experiments/${experimentId}/attachments/${attachmentId}`,
    { method: "PATCH", body: payload },
  );
}

export async function deleteAttachment(
  experimentId: string,
  attachmentId: string,
): Promise<void> {
  await apiFetch<void>(
    `/experiments/${experimentId}/attachments/${attachmentId}`,
    { method: "DELETE" },
  );
}

export async function requestAttachmentUploadUrl(
  experimentId: string,
  payload: { filename: string; mime_type: string; size_bytes: number },
): Promise<AttachmentUploadUrl> {
  return apiFetch<AttachmentUploadUrl>(
    `/experiments/${experimentId}/attachments/upload-url`,
    { method: "POST", body: payload },
  );
}

export async function putAttachmentBytes(
  uploadUrl: string,
  file: File,
): Promise<void> {
  const headers: Record<string, string> = {
    "Content-Type": file.type || "application/octet-stream",
  };

  // Local upload URLs hit FastAPI and need Firebase auth.
  if (uploadUrl.includes("/attachments/local-upload/")) {
    const auth = getFirebaseAuth();
    const user = auth.currentUser;
    if (!user) {
      await handleSessionExpired();
      throw new Error("Not authenticated");
    }
    headers.Authorization = `Bearer ${await user.getIdToken()}`;
  }

  const res = await fetch(uploadUrl, {
    method: "PUT",
    headers,
    body: file,
  });
  if (!res.ok) {
    throw new Error(`Upload failed (${res.status})`);
  }
}
