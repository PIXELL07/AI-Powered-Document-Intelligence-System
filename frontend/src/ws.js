import { useEffect, useRef } from "react";
import { WS_URL } from "./api";

export function useDocumentSocket(documentId, onMessage) {
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    if (!documentId) return;
    const socket = new WebSocket(`${WS_URL}/ws/documents/${documentId}`);
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handlerRef.current(data);
      } catch (e) {
        console.error("Bad WS payload", e);
      }
    };
    socket.onerror = () => {};
    return () => socket.close();
  }, [documentId]);
}
