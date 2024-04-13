import { useEffect } from "react";
import styles from "./index.module.css";

export default function Messages({ messages, headerHeight, inputHeight }) {
  useEffect(() => {
    const messageDivs = document.querySelectorAll('[data-role="message"]');
    messageDivs?.forEach((m, index) => {
      const range = document.createRange();
      const text = m?.childNodes[0];
      if (text) {
        range.setStartBefore(text);
        range.setEndAfter(text);
        const clientRect = range.getBoundingClientRect();
        m.style.width = `${clientRect.width}px`;
      }
    });
  }, []);

  return (
    <div
      style={{
        maxHeight: `calc(100vh - ${headerHeight}px - ${inputHeight}px)`,
      }}
      className={styles.messageWrapper}
    >
      {messages?.map((message, index) => (
        <div
          key={index}
          id={`message-${index}`}
          data-role="message"
          style={{
            marginBottom:
              index + 1 < messages.length &&
              message.isSendedText === messages[index + 1].isSendedText
                ? "5px"
                : "10px",
            borderRadius:
              index + 1 < messages.length &&
              message.isSendedText === messages[index + 1].isSendedText
                ? "20px"
                : message.isSendedText
                  ? "13px 13px 3px 13px"
                  : "13px 13px 13px 3px",
          }}
          className={`${styles.message} ${
            message.isSendedText ? styles.sendedText : styles.receivedText
          } `}
        >
          {message.text}
        </div>
      ))}
    </div>
  );
}
