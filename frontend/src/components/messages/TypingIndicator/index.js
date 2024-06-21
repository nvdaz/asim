import React from "react";
import styles from "./typingIndicator.module.css"; // CSS for styling

const TypingIndicator = () => {
  return (
    <div className={styles.typingIndicator}>
      <div className={styles.dot}></div>
      <div className={styles.dot}></div>
      <div className={styles.dot}></div>
    </div>
  );
};

export default TypingIndicator;
