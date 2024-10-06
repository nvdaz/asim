import { useAuth } from "@/components/auth-provider";
import { useCallback, useEffect, useRef, useState } from "react";

type Message = {
  sender: string;
  content: string;
  created_at: string;
};

type Chat = {
  id: string;
  agent: string;
  messages?: Message[];
  last_updated: string;
  agent_typing: boolean;
  suggestions?: string[];
  unread: boolean;
};

function useChatSocket<S, R>({
  onMessage,
}: {
  onMessage: (message: R) => void;
}) {
  const [isConnected, setIsConnected] = useState(false);
  const [isError, setIsError] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const { token } = useAuth();
  const connectDelayRef = useRef(1000);
  const [connectTimeout, setConnectTimeout] = useState<number | null>(null);
  const messageQueueRef = useRef<S[]>([]);

  const flushMessageQueue = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      while (messageQueueRef.current.length > 0) {
        const message = messageQueueRef.current.shift();
        wsRef.current.send(JSON.stringify(message));
      }
    }
  }, [wsRef.current]);

  const connect = useCallback(() => {
    const ws = new WebSocket(
      `${import.meta.env.VITE_API_URL}/conversations/ws`
    );

    ws.addEventListener("open", () => {
      setIsConnected(true);
      setIsError(false);
      ws.send(JSON.stringify({ token }));
      flushMessageQueue();
    });

    ws.addEventListener("error", () => {
      setIsError(true);
    });

    ws.addEventListener("close", () => {
      setIsConnected(false);
      setConnectTimeout(window.setTimeout(connect, connectDelayRef.current));
      connectDelayRef.current = Math.min(connectDelayRef.current * 2, 60000);
    });

    ws.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    });

    wsRef.current = ws;
  }, [connectDelayRef, token]);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }

      if (connectTimeout) {
        window.clearTimeout(connectTimeout);
      }
    };
  }, []);

  const sendMessage = (message: S) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      messageQueueRef.current.push(message);
    }
  };

  return { isConnected, isError, sendMessage };
}

type RecvSyncChats = {
  type: "sync-chats";
  chats: Chat[];
};

type RecvSynChat = {
  type: "sync-chat";
  chat: Chat;
};

type RecvSuggestedMessages = {
  type: "suggested-messages";
  id: string;
  messages: string[];
};

type Recv = RecvSyncChats | RecvSynChat | RecvSuggestedMessages;

type SendChatMessage = {
  type: "send-message";
  id: string;
  content: string;
};

type SendCreateChat = {
  type: "create-chat";
};

type SendLoadChat = {
  type: "load-chat";
  id: string;
};

type SendSuggestMessages = {
  type: "suggest-messages";
  id: string;
};

type SendMarkRead = {
  type: "mark-read";
  id: string;
};

type Send =
  | SendChatMessage
  | SendCreateChat
  | SendLoadChat
  | SendSuggestMessages
  | SendMarkRead;

export function useChats() {
  const [chats, setChats] = useState<{ [key: string]: Chat }>({});

  const onMessage = useCallback((message: Recv) => {
    if (message.type === "sync-chats") {
      setChats(
        message.chats.reduce((acc: { [key: string]: Chat }, chat: Chat) => {
          acc[chat.id] = chat;
          return acc;
        }, {})
      );
    } else if (message.type === "sync-chat") {
      setChats((chats) => {
        return { ...chats, [message.chat.id]: message.chat };
      });
    } else if (message.type === "suggested-messages") {
      setChats((chats) => {
        return {
          ...chats,
          [message.id]: { ...chats[message.id], suggestions: message.messages },
        };
      });
    }
  }, []);

  const { isConnected, isError, sendMessage } = useChatSocket<Send, Recv>({
    onMessage,
  });

  const sendChatMessage = useCallback(
    (id: string, content: string) => {
      sendMessage({ type: "send-message", id, content });
    },
    [sendMessage]
  );

  const createChat = useCallback(() => {
    sendMessage({ type: "create-chat" });
  }, [sendMessage]);

  const loadChat = useCallback(
    (id: string) => {
      sendMessage({ type: "load-chat", id });
    },
    [sendMessage]
  );

  const suggestMessages = useCallback(
    (id: string) => {
      sendMessage({ type: "suggest-messages", id });
    },
    [sendMessage]
  );

  const markRead = useCallback(
    (id: string) => {
      sendMessage({ type: "mark-read", id });
    },
    [sendMessage]
  );

  return {
    isConnected,
    isError,
    chats,
    sendChatMessage,
    createChat,
    loadChat,
    suggestMessages,
    markRead,
  };
}
