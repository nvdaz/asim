import Choice from "../../InputSection/choice";
import styles from "./feedback.module.css";

const Feedback = ({ selectedButton, handleButtonClick, body, choice }) => {
  return (
    <div className={styles.wrapper}>
      {/* <div className={styles.title}>
        Autistic people tend to think literally
      </div> */}
      <div style={{ paddingBottom: "10px" }}>{body}</div>
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
          selectedButton={selectedButton}
        />
      </div>
    </div>
  );
};

export default Feedback;
