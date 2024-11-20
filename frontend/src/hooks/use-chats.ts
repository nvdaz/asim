import { useAuth } from "@/components/auth-provider";
import { useCallback, useEffect, useRef, useState } from "react";
import useWebsocket, { ReadyState } from 'react-use-websocket';
import invariant from 'tiny-invariant';

type Message = {
  sender: string;
  content: string;
  created_at: string;
};

type Feedback = {
  title: string;
  body: string;
  alternative: string;
  alternative_feedback: string;
};

type InChatFeedback = {
  feedback: Feedback;
  created_at: string;
  rating: number | null;
}

type Suggestion = {
  message: string
  objective?: string
  feedback?: Feedback
  problem: string | null
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
  messages: (Message | InChatFeedback)[];
  last_updated: string;
  agent_typing: boolean;
  loading_feedback: boolean;
  generating_suggestions: number;
  suggestions?: Suggestion[];
  unread: boolean;
  checkpoint_rate: boolean;
}

export type Chat = ChatLoading | ChatLoaded;

export function chatIsLoaded(chat: Chat): chat is ChatLoaded {
  return "messages" in chat;
}

export function isContentInChatFeedback(content: Message | InChatFeedback): content is InChatFeedback {
  return "feedback" in content;
}

function useChatSocket<S, R>({
  onMessage,
}: {
  onMessage: (message: R) => void;
}) {
  const didUnmount = useRef(false);
  const { token } = useAuth();

  const {
    sendJsonMessage: sendSocketMessage, lastMessage: lastSocketMessage, readyState,
  } = useWebsocket(`${import.meta.env.VITE_API_URL}/conversations/ws`, {
    onOpen: () => {
      sendSocketMessage({ token });
    },
    retryOnError: true,
    reconnectInterval: (lastAttemptNumber) => Math.min(16000, 2 ** lastAttemptNumber * 1000),
    reconnectAttempts: 10,
    shouldReconnect: () => {
      return !didUnmount.current;
    }
  });


  useEffect(() => {
    didUnmount.current = false;
    return () => {
      didUnmount.current = true;
    };
  }, []);

  useEffect(() => {
    if (lastSocketMessage) {
      const message = JSON.parse(lastSocketMessage.data) as R;
      onMessage(message);
    }
  }, [lastSocketMessage, onMessage]);

  const sendMessage = (message: S) => {
    sendSocketMessage(message);
  };

  return {
    isConnected: readyState === ReadyState.OPEN,
    isError: false,
    sendMessage
  };
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

type SendRateFeedback = {
  type: "rate-feedback";
  id: string;
  index: number;
  rating: number;
}

type SendCheckpointRate = {
  type: "checkpoint-rating";
  id: string;
  ratings: { [key: string]: number };
}

type Send =
  | SendChatMessage
  | SendCreateChat
  | SendLoadChat
  | SendSuggestMessages
  | SendMarkRead
  | SendViewSuggestion
  | SendRateFeedback
  | SendCheckpointRate;

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
          { sender: user!.name!, content, created_at: new Date().toISOString() },
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
      setChats((chats) => {
        return {
          ...chats,
          [id]: {
            ...chats[id],
            generating_suggestions: 3,
          },
        };
      });
    }, [sendMessage]
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

  const handleRate = useCallback(
    (id: string, index: number, rating: number) => {
      setChats((chats) => {
        const chat = chats[id];
        invariant(chatIsLoaded(chat));
        const feedback = chat.messages![index] as InChatFeedback;
        feedback.rating = rating;
        return { ...chats, [id]: chat };
      })
      sendMessage({ type: "rate-feedback", id, index, rating });
    }, [sendMessage]);

  const handleCheckpointRate = useCallback((id: string, ratings: { [key: string]: number }) => {
    sendMessage({ type: "checkpoint-rating", id, ratings })

  }, [sendMessage])

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
    handleRate,
    handleCheckpointRate,
  };
}
