import { useCallback, useEffect, useMemo, useState } from 'react';
import { services } from '@/api/services';
import { useWorkspace } from '@/context/WorkspaceContext';
import type {
  IntelligenceConversation,
  IntelligenceConversationSummary,
  IntelligenceMessage,
  IntelligenceSource,
  ReasoningMode,
  StudioReadiness,
} from '@/types/intelligence';

interface StudioState {
  readiness: StudioReadiness | null;
  conversations: IntelligenceConversationSummary[];
  activeConversationId: string | null;
  conversation: IntelligenceConversation | null;
  suggestions: string[];
  mode: ReasoningMode;
  listLoading: boolean;
  conversationLoading: boolean;
  sending: boolean;
  streaming: boolean;
  error: string | null;
  listQuery: string;
  selectedSources: IntelligenceSource[];
  setMode: (mode: ReasoningMode) => void;
  setListQuery: (query: string) => void;
  setActiveConversationId: (id: string | null) => void;
  setSelectedSources: (sources: IntelligenceSource[]) => void;
  refreshList: () => Promise<void>;
  startNewConversation: () => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  togglePin: (id: string) => Promise<void>;
  filteredConversations: {
    pinned: IntelligenceConversationSummary[];
    recent: IntelligenceConversationSummary[];
  };
}

export function useIntelligenceStudio(): StudioState {
  const { activeWorkspaceId } = useWorkspace();
  const workspaceId = activeWorkspaceId;

  const [readiness, setReadiness] = useState<StudioReadiness | null>(null);
  const [conversations, setConversations] = useState<
    IntelligenceConversationSummary[]
  >([]);
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null);
  const [conversation, setConversation] =
    useState<IntelligenceConversation | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [mode, setMode] = useState<ReasoningMode>('ask');
  const [listLoading, setListLoading] = useState(true);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listQuery, setListQuery] = useState('');
  const [selectedSources, setSelectedSources] = useState<IntelligenceSource[]>(
    [],
  );

  const refreshList = useCallback(async () => {
    if (!workspaceId) {
      setConversations([]);
      setReadiness(null);
      setListLoading(false);
      return;
    }
    setListLoading(true);
    setError(null);
    try {
      const [ready, list, tips] = await Promise.all([
        services.intelligence.checkReadiness(workspaceId),
        services.intelligence.listConversations(workspaceId),
        services.intelligence.listSuggestions(workspaceId),
      ]);
      setReadiness(ready);
      setConversations(list);
      setSuggestions(tips);
      setActiveConversationId((current) => {
        if (current && list.some((item) => item.id === current)) return current;
        return list[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load Studio');
      setConversations([]);
    } finally {
      setListLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    setConversation(null);
    setActiveConversationId(null);
    setSelectedSources([]);
    setError(null);
    void refreshList();
  }, [workspaceId, refreshList]);

  useEffect(() => {
    if (!workspaceId || !activeConversationId) {
      setConversation(null);
      setSelectedSources([]);
      return;
    }

    let cancelled = false;
    async function load() {
      setConversationLoading(true);
      try {
        const detail = await services.intelligence.getConversation(
          workspaceId!,
          activeConversationId!,
        );
        if (!cancelled) {
          setConversation(detail);
          const lastAssistant = [...detail.messages]
            .reverse()
            .find((message) => message.role === 'assistant' && message.sources);
          setSelectedSources(lastAssistant?.sources ?? []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : 'Failed to load conversation',
          );
        }
      } finally {
        if (!cancelled) setConversationLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, activeConversationId]);

  const startNewConversation = useCallback(async () => {
    if (!workspaceId) return;
    setError(null);
    try {
      const created = await services.intelligence.startConversation(workspaceId);
      await refreshList();
      setActiveConversationId(created.id);
      setConversation(created);
      setSelectedSources([]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Could not start conversation',
      );
    }
  }, [workspaceId, refreshList]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!workspaceId || !content.trim()) return;
      if (readiness && !readiness.canAsk) {
        setError('Asking is not available for this workspace.');
        return;
      }

      setSending(true);
      setStreaming(true);
      setError(null);

      const optimisticUser: IntelligenceMessage = {
        id: `tmp_user_${Date.now()}`,
        conversationId: activeConversationId ?? 'tmp',
        role: 'user',
        content: content.trim(),
        status: 'complete',
        createdAt: new Date().toISOString(),
        mode,
      };
      const optimisticAssistant: IntelligenceMessage = {
        id: `tmp_assistant_${Date.now()}`,
        conversationId: activeConversationId ?? 'tmp',
        role: 'assistant',
        content: '',
        status: 'streaming',
        createdAt: new Date().toISOString(),
        mode,
      };

      setConversation((current) => {
        if (!current) {
          return {
            id: 'tmp',
            workspaceId,
            title: content.trim().slice(0, 48),
            pinned: false,
            updatedAt: new Date().toISOString(),
            messages: [optimisticUser, optimisticAssistant],
          };
        }
        return {
          ...current,
          messages: [...current.messages, optimisticUser, optimisticAssistant],
        };
      });

      try {
        let conversationId = activeConversationId;
        if (!conversationId) {
          const created = await services.intelligence.startConversation(
            workspaceId,
            { title: content.trim().slice(0, 48) },
          );
          conversationId = created.id;
          setActiveConversationId(created.id);
        }

        const updated = await services.intelligence.sendMessage(
          workspaceId,
          conversationId,
          { content: content.trim(), mode },
        );
        setConversation(updated);
        const lastAssistant = [...updated.messages]
          .reverse()
          .find((message) => message.role === 'assistant');
        setSelectedSources(lastAssistant?.sources ?? []);
        await refreshList();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send message');
        setConversation((current) => {
          if (!current) return current;
          return {
            ...current,
            messages: current.messages
              .filter((message) => message.status !== 'streaming')
              .concat({
                id: `err_${Date.now()}`,
                conversationId: current.id,
                role: 'assistant',
                content: '',
                answer: 'Something went wrong while analysing this workspace.',
                status: 'error',
                createdAt: new Date().toISOString(),
              }),
          };
        });
      } finally {
        setSending(false);
        setStreaming(false);
      }
    },
    [
      workspaceId,
      activeConversationId,
      mode,
      readiness,
      refreshList,
    ],
  );

  const renameConversation = useCallback(
    async (id: string, title: string) => {
      if (!workspaceId) return;
      await services.intelligence.renameConversation(workspaceId, id, title);
      await refreshList();
      if (conversation?.id === id) {
        setConversation({ ...conversation, title });
      }
    },
    [workspaceId, refreshList, conversation],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      if (!workspaceId) return;
      await services.intelligence.deleteConversation(workspaceId, id);
      if (activeConversationId === id) {
        setActiveConversationId(null);
        setConversation(null);
        setSelectedSources([]);
      }
      await refreshList();
    },
    [workspaceId, activeConversationId, refreshList],
  );

  const togglePin = useCallback(
    async (id: string) => {
      if (!workspaceId) return;
      await services.intelligence.togglePin(workspaceId, id);
      await refreshList();
    },
    [workspaceId, refreshList],
  );

  const filteredConversations = useMemo(() => {
    const normalized = listQuery.trim().toLowerCase();
    const filtered = conversations.filter((item) => {
      if (!normalized) return true;
      return (
        item.title.toLowerCase().includes(normalized) ||
        item.preview.toLowerCase().includes(normalized)
      );
    });
    return {
      pinned: filtered.filter((item) => item.pinned),
      recent: filtered.filter((item) => !item.pinned),
    };
  }, [conversations, listQuery]);

  return {
    readiness,
    conversations,
    activeConversationId,
    conversation,
    suggestions,
    mode,
    listLoading,
    conversationLoading,
    sending,
    streaming,
    error,
    listQuery,
    selectedSources,
    setMode,
    setListQuery,
    setActiveConversationId,
    setSelectedSources,
    refreshList,
    startNewConversation,
    sendMessage,
    renameConversation,
    deleteConversation,
    togglePin,
    filteredConversations,
  };
}
