import { useEffect } from 'react';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

export interface RealtimeEventPayload {
  type: string;
  payload: any;
}

/**
 * React hook connecting to Server-Sent Events (SSE) backed by Redis Pub/Sub.
 * Automatically triggers callback or refetches when background workers complete tasks.
 */
export function useRealtimeEvents(onEventReceived: (event: RealtimeEventPayload) => void) {
  useEffect(() => {
    const token = localStorage.getItem('promisecheck_access_token');
    const streamUrl = `${API_BASE_URL}/events/stream${token ? `?token=${encodeURIComponent(token)}` : ''}`;

    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(streamUrl);

      eventSource.onopen = () => {
        console.log('[SSE] Connected to PromiseCheck real-time event stream via Redis Pub/Sub');
      };

      // Listen for custom Redis Pub/Sub events
      const eventTypes = [
        'connected',
        'INGESTION_COMPLETED',
        'INGESTION_FAILED',
        'COMMITMENT_CONFIRMED',
        'RISK_EVALUATION_COMPLETED',
        'TEST_EVENT',
      ];

      eventTypes.forEach((type) => {
        eventSource?.addEventListener(type, (e: MessageEvent) => {
          try {
            const parsed = JSON.parse(e.data);
            onEventReceived({ type, payload: parsed });
          } catch {
            onEventReceived({ type, payload: e.data });
          }
        });
      });

      eventSource.onerror = () => {
        // EventSource automatically attempts reconnection
      };
    } catch (err) {
      console.warn('[SSE] Could not establish event stream connection:', err);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [onEventReceived]);
}
