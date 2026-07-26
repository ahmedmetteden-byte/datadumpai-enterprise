import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { UI_COPY } from '@/constants/ui';

export type RequestFeedbackKind = 'loading' | 'success' | 'error';

export interface RequestFeedbackItem {
  id: string;
  kind: RequestFeedbackKind;
  message: string;
  onRetry?: () => void;
}

interface RunOptions {
  loading?: string;
  success?: string;
  error?: string;
  /** Keep the loading toast until success/error replaces it */
  stickyLoading?: boolean;
}

interface RequestFeedbackContextValue {
  items: RequestFeedbackItem[];
  notifyLoading: (message?: string) => string;
  notifySuccess: (message?: string) => string;
  notifyError: (message?: string, onRetry?: () => void) => string;
  dismiss: (id: string) => void;
  clear: () => void;
  /** Run an async action with Loading → Success / Error (+ Retry) feedback */
  run: <T>(action: () => Promise<T>, options?: RunOptions) => Promise<T>;
}

const RequestFeedbackContext =
  createContext<RequestFeedbackContextValue | null>(null);

let feedbackSeq = 0;
function nextId(): string {
  feedbackSeq += 1;
  return `rf-${feedbackSeq}`;
}

const AUTO_DISMISS_MS: Record<RequestFeedbackKind, number | null> = {
  loading: null,
  success: 4000,
  error: 8000,
};

export function RequestFeedbackProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<RequestFeedbackItem[]>([]);
  const timers = useRef<Map<string, number>>(new Map());

  const clearTimer = useCallback((id: string) => {
    const existing = timers.current.get(id);
    if (existing !== undefined) {
      window.clearTimeout(existing);
      timers.current.delete(id);
    }
  }, []);

  const scheduleDismiss = useCallback(
    (id: string, kind: RequestFeedbackKind) => {
      clearTimer(id);
      const ms = AUTO_DISMISS_MS[kind];
      if (ms == null) return;
      const timer = window.setTimeout(() => {
        setItems((current) => current.filter((item) => item.id !== id));
        timers.current.delete(id);
      }, ms);
      timers.current.set(id, timer);
    },
    [clearTimer],
  );

  const upsert = useCallback(
    (item: RequestFeedbackItem) => {
      setItems((current) => {
        const without = current.filter((entry) => entry.id !== item.id);
        return [...without, item];
      });
      scheduleDismiss(item.id, item.kind);
      return item.id;
    },
    [scheduleDismiss],
  );

  const dismiss = useCallback(
    (id: string) => {
      clearTimer(id);
      setItems((current) => current.filter((item) => item.id !== id));
    },
    [clearTimer],
  );

  const clear = useCallback(() => {
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current.clear();
    setItems([]);
  }, []);

  const notifyLoading = useCallback(
    (message: string = UI_COPY.requestLoading) =>
      upsert({ id: nextId(), kind: 'loading', message }),
    [upsert],
  );

  const notifySuccess = useCallback(
    (message: string = UI_COPY.requestSuccess) =>
      upsert({ id: nextId(), kind: 'success', message }),
    [upsert],
  );

  const notifyError = useCallback(
    (message: string = UI_COPY.requestError, onRetry?: () => void) =>
      upsert({ id: nextId(), kind: 'error', message, onRetry }),
    [upsert],
  );

  const run = useCallback(
    async <T,>(action: () => Promise<T>, options: RunOptions = {}) => {
      const loadingId = nextId();
      upsert({
        id: loadingId,
        kind: 'loading',
        message: options.loading ?? UI_COPY.requestLoading,
      });
      try {
        const result = await action();
        upsert({
          id: loadingId,
          kind: 'success',
          message: options.success ?? UI_COPY.requestSuccess,
        });
        return result;
      } catch (err) {
        const message =
          options.error ??
          (err instanceof Error ? err.message : UI_COPY.requestError);
        upsert({
          id: loadingId,
          kind: 'error',
          message,
          onRetry: () => {
            void run(action, options);
          },
        });
        throw err;
      }
    },
    [upsert],
  );

  const value = useMemo(
    () => ({
      items,
      notifyLoading,
      notifySuccess,
      notifyError,
      dismiss,
      clear,
      run,
    }),
    [
      items,
      notifyLoading,
      notifySuccess,
      notifyError,
      dismiss,
      clear,
      run,
    ],
  );

  return (
    <RequestFeedbackContext.Provider value={value}>
      {children}
    </RequestFeedbackContext.Provider>
  );
}

export function useRequestFeedback(): RequestFeedbackContextValue {
  const ctx = useContext(RequestFeedbackContext);
  if (!ctx) {
    throw new Error(
      'useRequestFeedback must be used within RequestFeedbackProvider',
    );
  }
  return ctx;
}
