import { useCallback, useEffect, useMemo, useState } from "react";
import { useChats } from "./use-chats";

const ZERO_OID = "000000000000000000000000";

export function useCurrentChat() {
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);

    const onChatCreated = useCallback((id: string) => {
        if (!currentChatId) {
            setCurrentChatId(id);
        }
    }, [currentChatId, setCurrentChatId]);

    const {
        isConnected,
        isError,
        chats,
        sendChatMessage: sendChatMessageRaw,
        createChat: createChatRaw,
        loadChat,
        suggestMessages: suggestMessagesRaw,
        sendViewSuggestion: sendViewSuggestionRaw,
        markRead,
        handleRate: handleRateRaw,
        handleCheckpointRate: handleCheckpointRateRaw
    } = useChats({ onChatCreated });


    const currentChat = currentChatId ?
        currentChatId === ZERO_OID ? { id: ZERO_OID, last_updated: new Date().toISOString() } : chats[currentChatId]
        : null;

    const contacts = useMemo(
        () =>
            Object.values(chats).sort(
                (a, b) => Date.parse(b.last_updated) - Date.parse(a.last_updated)
            ),
        [chats]
    );

    // set current chat on load and when creating a new chat
    useEffect(() => {
        if (!currentChatId && contacts.length) {
            setCurrentChatId(contacts[0].id);
        }
    }, [contacts, setCurrentChatId]);

    // load messges for current chat
    useEffect(() => {
        if (currentChat && currentChat.id !== ZERO_OID && !("messages" in currentChat)) {
            loadChat(currentChatId!);
        }
    }, [currentChat, loadChat]);

    // mark opened chat as read
    useEffect(() => {
        if (currentChat && currentChat.unread) {
            markRead(currentChat.id);
        }
    }, [currentChat, chats]);

    const sendChatMessage = useCallback((index: number) => {
        if (currentChat) {
            sendChatMessageRaw(currentChat.id, index);
        }
    }, [currentChat, sendChatMessageRaw]);

    const suggestMessages = useCallback((message: string) => {
        if (currentChat) {
            suggestMessagesRaw(currentChat.id, message);
        }
    }, [currentChat, suggestMessagesRaw]);

    const createChat = useCallback(() => {
        createChatRaw();
        setCurrentChatId(ZERO_OID);
    }, [createChatRaw, setCurrentChatId]);

    const sendViewSuggestion = useCallback((index: number) => {
        if (currentChat) {
            sendViewSuggestionRaw(currentChat.id, index);
        }
    }, [currentChat, sendViewSuggestionRaw]);

    const handleRate = useCallback((index: number, rating: number) => {
        if (currentChat) {
            handleRateRaw(currentChat.id, index, rating);
        }
    }, [currentChat, handleRateRaw]);

    const handleCheckpointRate = useCallback((ratings: { [key: string]: number }) => {
        if (currentChat) {
            handleCheckpointRateRaw(currentChat.id, ratings);
        }
    }, [currentChat, handleCheckpointRateRaw]);

    return {
        isConnected,
        isError,
        contacts,
        currentChat,
        suggestMessages,
        sendChatMessage,
        createChat,
        sendViewSuggestion,
        setCurrentChatId,
        handleRate,
        handleCheckpointRate
    };
}
