import { useEffect, useRef, useState } from 'react';
import { JobUpdate } from '../types';

interface WebSocketMessage {
  type: string;
  job_id?: string;
  status?: string;
  location?: any;
  message?: string;
  timestamp?: string;
}

export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [jobUpdates, setJobUpdates] = useState<Map<string, JobUpdate>>(new Map());
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      try {
        ws.current = new WebSocket(url);

        ws.current.onopen = () => {
          setIsConnected(true);
          console.log('WebSocket connected');
        };

        ws.current.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            setLastMessage(message);

            // Handle job updates
            if (message.type === 'job_update' && message.job_id) {
              const jobUpdate: JobUpdate = {
                job_id: message.job_id,
                status: message.status as any,
                location: message.location,
                message: message.message,
                timestamp: message.timestamp || new Date().toISOString(),
              };

              setJobUpdates(prev => new Map(prev.set(message.job_id!, jobUpdate)));
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.current.onclose = () => {
          setIsConnected(false);
          console.log('WebSocket disconnected');
          
          // Attempt to reconnect after 3 seconds
          setTimeout(connect, 3000);
        };

        ws.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnected(false);
        };
      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url]);

  const subscribeToJob = (jobId: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'subscribe_job',
        job_id: jobId,
      }));
    }
  };

  const sendMessage = (message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  };

  return {
    isConnected,
    lastMessage,
    jobUpdates,
    subscribeToJob,
    sendMessage,
  };
}