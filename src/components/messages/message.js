import styles from "./index.module.css";

const message = ({ message, index }) => {
  const range = document.createRange();
  const div = document.getElementById(`lol${index}`);
  const text = div?.childNodes[0];
  if (text) {
    range.setStartBefore(text);
    range.setEndAfter(text);
    const clientRect = range.getBoundingClientRect();
    div.style.width = `${clientRect.width}px`;
  }

  return (
    <div
      id={`lol${index}`}
      className={`${styles.message} ${
        message.isMine ? styles.mine : styles.theirs
      } `}
    >
      {message.text}
    </div>
  );
};

export default message;
