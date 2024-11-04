import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { formatDistanceToNow } from "date-fns";
import { SquarePen } from "lucide-react";
import { ReactNode } from "react";
import { Button } from "./components/ui/button";
import { Skeleton } from "./components/ui/skeleton";

export type ChatInfo = {
  id: string;
  agent?: string;
  last_updated: string;
  unread?: boolean;
};

function ContactsContainer({
  handleNewChat,
  children,
}: {
  handleNewChat: () => void;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-row items-center justify-between p-4 h-16">
        <span className="font-semibold">Contacts</span>
        <Button variant="link" className="ml-4" onClick={handleNewChat}>
          <SquarePen className="w-[20px]" />
        </Button>
      </div>
      {children}
    </div>
  );
}

function Contacts({
  chats,
  selectedChatId,
  handleSelect,
  handleNewChat,
}: {
  chats: ChatInfo[] | null;
  selectedChatId: string | null;
  handleSelect: (id: string) => void;
  handleNewChat: () => void;
}) {
  if (chats === null) {
    return (
      <ContactsContainer handleNewChat={handleNewChat}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i}>
            <Separator />
            <div className="flex flex-row p-4 rounded-md">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="space-y-2 ml-8">
                <Skeleton className="h-4 w-[150px]" />
                <Skeleton className="h-4 w-[100px]" />
              </div>
            </div>
          </div>
        ))}
      </ContactsContainer>
    );
  }

  return (
    <ContactsContainer handleNewChat={handleNewChat}>
      {chats.map((chat) => (
        <div key={chat.id}>
          <Separator />
          <div
            className={`flex flex-row p-4 ${
              chat.id === selectedChatId
                ? "bg-blue-500 text-white"
                : "hover:bg-blue-100 dark:hover:bg-blue-800"
            }`}
            onClick={() => handleSelect(chat.id)}
          >
            <Avatar className="text-black dark:text-white">
              {chat.agent ? (
                <AvatarFallback>{chat.agent[0]}</AvatarFallback>
              ) : (
                <Skeleton className="h-10 w-10 rounded-full" />
              )}
            </Avatar>
            <div className="flex flex-col w-full ml-4">
              <div className="flex flex-row justify-between">
                {chat.agent ? (
                  <h2 className="ml-4">{chat.agent}</h2>
                ) : (
                  <Skeleton className="h-4 w-[150px]" />
                )}
                {chat.unread && (
                  <div className="w-2 h-2 bg-red-500 rounded-full ml-4" />
                )}
              </div>
              <p className="ml-4">
                {formatDistanceToNow(new Date(chat.last_updated), {
                  addSuffix: true,
                })}
              </p>
            </div>
          </div>
        </div>
      ))}
    </ContactsContainer>
  );
}

export default Contacts;
