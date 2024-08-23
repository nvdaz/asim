import styles from "./feedback.module.css";

const Feedback = ({
  body,
  title,
  explanation,
  choice,
  handleContinue,
  oldHistory,
  selectionResultContent,
  setShowProgress
}) => {
  return (
    <div className={styles.wrapper}>
      <div className={styles.title}>{title}</div>
      <div className={styles.body}>{body}</div>
      {choice && (
        <div className={styles.follow_up}>
          <div style={{ marginBottom: "15px" }}>Instead, say:</div>
          <div className={styles.choice}>{choice}</div>
          {explanation && (
            <div>
              <hr style={{ border: "1.3px solid #1e1e1e" }} />
              <div className={styles.title}> 🤔 Why This Phrasing</div>
              <div>{explanation}</div>
              <hr style={{ border: "1.3px solid #1e1e1e" }} />
            </div>
          )}
          <div style={{ marginBottom: "8px" }}>
            Click on Send button to continue the conversation
          </div>
        </div>
      )}
      {choice === null && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <div
            className={styles.btn}
            onClick={() =>
              handleContinue(
                oldHistory,
                selectionResultContent,
                setShowProgress
              )
            }
          >
            Continue
          </div>
        </div>
      )}
    </div>
  );
};

export default Feedback;
