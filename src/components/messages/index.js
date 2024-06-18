import { useEffect } from "react";
import styles from "./index.module.css";
import Explanation from "./explaination";
import Choice from "../InputSection/choice";

export default function Messages({
  height,
  messages,
  setMessages,
  selectedButton,
  setSelectedButton,
}) {
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

    // const handleButtonClick = (index, message) => {
    //   setSelectedButton(index);
    //   setMessage(message);
    // };

  return (
    <div
      style={{
        height: height,
      }}
      className={styles.wrapper}
    >
      <Explanation />
      <div className={styles.messageWrapper}>
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
      {/* <div
        style={{
          background: "#42454E",
          color: "white",
          borderRadius: "22px",
          padding: "15px 20px",
          lineHeight: 1.5,
        }}
      >
        <div>
          Autistic people tend to think literally, so it is best to avoid idioms
          and slang.
        </div>
        <div>
          Try to avoid using metaphors or abstract expressions where the meaning
          could be taken literally. Instead of “When can we brainstorm for the
          poster?”, you can say:
        </div>
        <div
          style={{ display: "flex", justifyContent: "center", padding: "10px" }}
        >
          <Choice
            index={0}
            message={"When is a good time to think about ideas for the poster?"}
            func={() =>
              handleButtonClick(
                0,
                "When is a good time to think about ideas for the poster?"
              )
            }
            selectedButton={null}
          />
        </div>
      </div> */}
    </div>
  );
}
