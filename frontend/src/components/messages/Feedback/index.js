import { Choice } from "../../InputSection/choice";
import styles from "./feedback.module.css";

const Feedback = ({
  handleButtonClick,
  body,
  title,
  choice,
  handleContinue,
  oldHistory,
  selectionResultContent
}) => {
  return (
    <div className={styles.wrapper}>
      <div style={{ fontWeight: 700, fontSize: "18px", marginBottom: "5px" }}>
        {title}
      </div>
      <div style={{ paddingBottom: "10px" }}>{body}</div>
      {choice && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            padding: "5px 0 5px",
          }}
        >
          <Choice
            index={0}
            message={choice}
            func={() => handleButtonClick(0, choice)}
          />
        </div>
      )}

      {!choice && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <div
            className={styles.btn}
            onClick={() => handleContinue(oldHistory, selectionResultContent)}
          >
            Continue
          </div>
        </div>
      )}
    </div>
  );
};

export default Feedback;
