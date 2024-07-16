import { Choice } from "../../InputSection/choice";
import styles from "./feedback.module.css";

const Feedback = ({
  handleButtonClick,
  body,
  title,
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
        <div>
          <div>Instead, say:</div>
          <div
            style={{
              margin: "5px 0",
              padding: "10px 15px",
              backgroundColor: "#2C2F39",
              borderRadius: "22px",
            }}
          >
            {choice}
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
