import { apiRequest } from '@/api/client';
import { mockLatency, type ServiceAuth } from '@/api/config';
import type { IntelligenceService } from '@/api/services/contracts';
import {
  mockCheckReadiness,
  mockDeleteConversation,
  mockGetConversation,
  mockListConversations,
  mockRenameConversation,
  mockSendMessage,
  mockStartConversation,
  mockSuggestedPrompts,
  mockTogglePin,
} from '@/api/mock/intelligenceStore';
import type {
  IntelligenceConversation,
  IntelligenceConversationSummary,
  IntelligenceMessage,
  SendMessageInput,
  StartConversationInput,
  StudioReadiness,
} from '@/types/intelligence';

export class MockIntelligenceService implements IntelligenceService {
  async checkReadiness(workspaceId: string) {
    await mockLatency(80);
    return mockCheckReadiness(workspaceId);
  }

  async listConversations(workspaceId: string) {
    await mockLatency(100);
    return mockListConversations(workspaceId);
  }

  async getConversation(workspaceId: string, conversationId: string) {
    await mockLatency(80);
    return mockGetConversation(workspaceId, conversationId);
  }

  async startConversation(
    workspaceId: string,
    input: StartConversationInput = {},
  ) {
    await mockLatency(120);
    return mockStartConversation(workspaceId, input);
  }

  async sendMessage(
    workspaceId: string,
    conversationId: string,
    input: SendMessageInput,
  ) {
    await mockLatency(700);
    return mockSendMessage(workspaceId, conversationId, input);
  }

  async renameConversation(
    workspaceId: string,
    conversationId: string,
    title: string,
  ) {
    await mockLatency(80);
    return mockRenameConversation(workspaceId, conversationId, title);
  }

  async deleteConversation(workspaceId: string, conversationId: string) {
    await mockLatency(80);
    mockDeleteConversation(workspaceId, conversationId);
  }

  async togglePin(workspaceId: string, conversationId: string) {
    await mockLatency(60);
    return mockTogglePin(workspaceId, conversationId);
  }

  async listSuggestions(workspaceId: string) {
    await mockLatency(40);
    void workspaceId;
    return mockSuggestedPrompts();
  }

  async askTemporary(workspaceId: string, input: SendMessageInput) {
    await mockLatency(500);
    const scratch = mockStartConversation(workspaceId, {});
    const conversation = mockSendMessage(workspaceId, scratch.id, input);
    return (
      conversation.messages[conversation.messages.length - 1] ?? conversation.messages[0]
    );
  }
}

export class HttpIntelligenceService implements IntelligenceService {
  async checkReadiness(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<StudioReadiness>(
      `/api/v1/workspaces/${workspaceId}/intelligence/readiness`,
      { token: auth?.accessToken },
    );
  }

  async listConversations(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<IntelligenceConversationSummary[]>(
      `/api/v1/workspaces/${workspaceId}/intelligence/conversations`,
      { token: auth?.accessToken },
    );
  }

  async getConversation(
    workspaceId: string,
    conversationId: string,
    auth?: ServiceAuth,
  ) {
    return apiRequest<IntelligenceConversation>(
      `/api/v1/workspaces/${workspaceId}/intelligence/conversations/${conversationId}`,
      { token: auth?.accessToken },
    );
  }

  async startConversation(
    workspaceId: string,
    input: StartConversationInput = {},
    auth?: ServiceAuth,
  ) {
    return apiRequest<IntelligenceConversation>(
      `/api/v1/workspaces/${workspaceId}/intelligence/conversations`,
      {
        method: 'POST',
        body: input,
        token: auth?.accessToken,
      },
    );
  }

  async sendMessage(
    workspaceId: string,
    conversationId: string,
    input: SendMessageInput,
    auth?: ServiceAuth,
  ) {
    return apiRequest<IntelligenceConversation>(
      `/api/v1/workspaces/${workspaceId}/intelligence/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        body: input,
        token: auth?.accessToken,
      },
    );
  }

  async renameConversation(
    workspaceId: string,
    conversationId: string,
    title: string,
    auth?: ServiceAuth,
  ) {
    return apiRequest<IntelligenceConversationSummary>(
      `/api/v1/workspaces/${workspaceId}/intelligence/conversations/${conversationId}`,
      {
        method: 'PATCH',
        body: { title },
        token: auth?.accessToken,
      },
    );
  }

  async deleteConversation(
    workspaceId: string,
    conversationId: string,
    auth?: ServiceAuth,
  ) {
    await apiRequest<void>(
      `/api/v1/workspaces/${workspaceId}/intelligence/conversations/${conversationId}`,
      {
        method: 'DELETE',
        token: auth?.accessToken,
      },
    );
  }

  async togglePin(
    workspaceId: string,
    conversationId: string,
    auth?: ServiceAuth,
  ) {
    return apiRequest<IntelligenceConversationSummary>(
      `/api/v1/workspaces/${workspaceId}/intelligence/conversations/${conversationId}/pin`,
      {
        method: 'POST',
        token: auth?.accessToken,
      },
    );
  }

  async listSuggestions(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<string[]>(
      `/api/v1/workspaces/${workspaceId}/intelligence/suggestions`,
      { token: auth?.accessToken },
    );
  }

  async askTemporary(
    workspaceId: string,
    input: SendMessageInput,
    auth?: ServiceAuth,
  ) {
    return apiRequest<IntelligenceMessage>(
      `/api/v1/workspaces/${workspaceId}/intelligence/ask`,
      {
        method: 'POST',
        body: input,
        token: auth?.accessToken,
      },
    );
  }
}
