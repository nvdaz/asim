import { useAuth } from "@/components/auth-provider";
import { useCallback, useEffect, useRef, useState } from "react";
import invariant from 'tiny-invariant';

type Message = {
  sender: string;
  content: string;
  created_at: string;
};

type Feedback = {
  title: string;
  body: string;
};

type Suggestion = {
  message: string
  objective?: string
  feedback?: Feedback
  needs_improvement: boolean
};

type ChatLoading = {
  id: string;
  agent?: string;
  last_updated: string;
  agent_typing?: boolean;
  unread?: boolean;
}

type ChatLoaded = {
  id: string;
  agent: string;
  messages: Message[];
  last_updated: string;
  agent_typing: boolean;
  suggestions?: Suggestion[];
  unread: boolean;
}

export type Chat = ChatLoading | ChatLoaded;

export function chatIsLoaded(chat: Chat): chat is ChatLoaded {
  return "messages" in chat;
}

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
  index: number;
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
  message: string;
};

type SendMarkRead = {
  type: "mark-read";
  id: string;
};

type SendViewSuggestion = {
  type: "view-suggestion";
  id: string;
  index: number;
};

type Send =
  | SendChatMessage
  | SendCreateChat
  | SendLoadChat
  | SendSuggestMessages
  | SendMarkRead
  | SendViewSuggestion;

export function useChats({ onChatCreated }: { onChatCreated: (id: string) => void }) {
  const [chats, setChats] = useState<{ [key: string]: Chat }>({});
  const { user } = useAuth();

  const onMessage = useCallback((message: Recv) => {
    if (message.type === "sync-chats") {
      setChats(
        message.chats.reduce((acc: { [key: string]: Chat }, chat: Chat) => {
          acc[chat.id] = chat;
          return acc;
        }, {})
      );
    } else if (message.type === "sync-chat") {
      if (!(message.chat.id in chats)) {
        onChatCreated(message.chat.id);
      }
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
    (id: string, index: number) => {
      setChats((chats) => {
        const chat = chats[id];
        invariant(chatIsLoaded(chat));
        const content = chat.suggestions![index].message;
        if (!chat.messages) {
          chat.messages = [];
        }
        chat.messages = [
          ...chat.messages,
          { sender: user!.name, content, created_at: new Date().toISOString() },
        ];
        chat.suggestions = undefined;
        return { ...chats, [id]: chat };
      });

      sendMessage({ type: "send-message", id, index });
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
    (id: string, message: string) => {
      sendMessage({ type: "suggest-messages", id, message });
    },
    [sendMessage]
  );


  const markRead = useCallback(
    (id: string) => {
      setChats((chats) => {
        return { ...chats, [id]: { ...chats[id], unread: false } };
      });
      sendMessage({ type: "mark-read", id });
    },
    [sendMessage]
  );

  const sendViewSuggestion = useCallback(
    (id: string, index: number) => {
      sendMessage({ type: "view-suggestion", id, index });
    },
    [sendMessage]);


  return {
    isConnected,
    isError,
    chats,
    sendChatMessage,
    createChat,
    loadChat,
    suggestMessages,
    markRead,
    sendViewSuggestion,
  };
}
