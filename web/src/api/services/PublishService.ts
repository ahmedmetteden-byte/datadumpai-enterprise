import { apiRequest } from '@/api/client';
import { mockLatency, type ServiceAuth } from '@/api/config';
import type { PublishJob, PublishService } from '@/api/services/contracts';
import { mockPublishJobs } from '@/api/mock/data';

export class MockPublishService implements PublishService {
  async listJobs(workspaceId: string) {
    await mockLatency(80);
    void workspaceId;
    return mockPublishJobs;
  }

  async enqueueExport(
    workspaceId: string,
    input: { reportId: string; format: PublishJob['format'] },
  ) {
    await mockLatency(120);
    void workspaceId;
    const job: PublishJob = {
      id: `pub_${Date.now()}`,
      title: input.reportId,
      format: input.format,
      status: 'queued',
      createdAt: new Date().toISOString(),
    };
    return job;
  }
}

export class HttpPublishService implements PublishService {
  async listJobs(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<PublishJob[]>(
      `/api/v1/workspaces/${workspaceId}/publish/jobs`,
      { token: auth?.accessToken },
    );
  }

  async enqueueExport(
    workspaceId: string,
    input: { reportId: string; format: PublishJob['format'] },
    auth?: ServiceAuth,
  ) {
    return apiRequest<PublishJob>(
      `/api/v1/workspaces/${workspaceId}/publish/exports`,
      {
        method: 'POST',
        body: input,
        token: auth?.accessToken,
      },
    );
  }
}
