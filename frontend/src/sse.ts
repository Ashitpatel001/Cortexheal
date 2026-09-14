import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getApiKey } from './api';


export function useSSE() {
  const queryClient = useQueryClient();

  useEffect(() => {
    let abortController = new AbortController();
    let reconnectTimeout: ReturnType<typeof setTimeout>;
    let connected = false;

    const connect = async () => {
      const apiKey = getApiKey();
      if (!apiKey) {
        queryClient.setQueryData(['sse_status'], 'disconnected');
        return;
      }

      try {
        queryClient.setQueryData(['sse_status'], 'connecting');
        
        // Workaround: Native EventSource doesn't support headers.
        // Since backend requires X-API-Key header, we use native fetch() + ReadableStream.
        const response = await fetch('/api/stream', {
          headers: { 'X-API-Key': apiKey },
          signal: abortController.signal
        });

        if (!response.ok) {
          throw new Error('SSE connection failed');
        }

        queryClient.setQueryData(['sse_status'], 'connected');
        connected = true;
        
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (reader) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep the incomplete line

          let currentEvent = 'message';
          
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            if (line.startsWith('event: ')) {
              currentEvent = line.substring(7).trim();
            } else if (line.startsWith('data: ')) {
              const dataStr = line.substring(6).trim();
              if (dataStr === 'ping' || dataStr === 'new_data_available') continue;

              try {
                const data = JSON.parse(dataStr);
                handleEvent(currentEvent, data);
              } catch (e) {
                console.error("Failed to parse SSE JSON", e);
              }
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== 'AbortError') {
          console.error("SSE Error:", err);
        } else if (!(err instanceof Error)) {
          console.error("SSE Error:", err);
        }
      } finally {
        if (connected) {
          queryClient.setQueryData(['sse_status'], 'reconnecting');
          reconnectTimeout = setTimeout(connect, 3000);
        }
      }
    };

    const handleEvent = (event: string, data: Record<string, unknown>) => {
      if (event === 'incident_created') {
        // Invalidate incidents list, or prepend optimistically
        queryClient.invalidateQueries({ queryKey: ['incidents'] });
        queryClient.invalidateQueries({ queryKey: ['fleet'] });
        queryClient.invalidateQueries({ queryKey: ['timeline', String(data.run_id)] });
      } else if (event === 'run_status_changed') {
        // Refetch specifically
        queryClient.invalidateQueries({ queryKey: ['runs'] });
        queryClient.invalidateQueries({ queryKey: ['fleet'] });
        queryClient.invalidateQueries({ queryKey: ['run', String(data.run_id)] });
        queryClient.invalidateQueries({ queryKey: ['timeline', String(data.run_id)] });
        
        // Gap requirement: If we are on incident detail for this run, we must refetch the incident
        // since run_status_changed doesn't contain incident_id.
        // We will just invalidate all incidents that might belong to this run.
        queryClient.invalidateQueries({ queryKey: ['incidents'] }); 
        queryClient.invalidateQueries({ queryKey: ['incident'] });
      } else if (event === 'run_resumed' || event === 'plan_approved' || event === 'plan_rejected') {
        queryClient.invalidateQueries({ queryKey: ['incidents'] });
        queryClient.invalidateQueries({ queryKey: ['incident'] });
        queryClient.invalidateQueries({ queryKey: ['plan'] });
        queryClient.invalidateQueries({ queryKey: ['timeline'] });
      }
    };

    connect();

    return () => {
      connected = false;
      abortController.abort();
      clearTimeout(reconnectTimeout);
    };
  }, [queryClient]);
}
