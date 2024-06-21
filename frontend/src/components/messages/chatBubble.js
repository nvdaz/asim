import styles from "./index.module.css";

const ChatBubble = ({ message, index, length }) => {

  return (
    <div
      key={index}
      id={`message-${index}`}
      data-role="message"
      style={{
        marginBottom: "10px",
        borderRadius: message.isSentByUser
              ? "13px 13px 3px 13px"
              : "13px 13px 13px 3px",
      }}
      className={`${styles.message} ${
        message.isSentByUser ? styles.sendedText : styles.receivedText
      } `}
    >
      {message.content}
    </div>
  );
};

export default ChatBubble;
