import Choice from "../../InputSection/choice";
import styles from "./explanation.module.css";

const Explanation = ({ selectedButton, handleButtonClick }) => {
  return (
    <div className={styles.wrapper}>
      <div className={styles.title}>
        Autistic people tend to think literally
      </div>
      <div style={{ paddingBottom: "10px" }}>
        Try to avoid using metaphors or abstract expressions where the meaning
        could be taken literally. Instead of “When can we brainstorm for the
        poster?”, you can say:
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          padding: "5px 0 5px",
        }}
      >
        <Choice
          index={0}
          message={
            "Sorry! I meant when is a good time to think about ideas for the poster?"
          }
          func={() =>
            handleButtonClick(
              0,
              "Sorry! I meant when is a good time to think about ideas for the poster?"
            )
          }
          selectedButton={selectedButton}
        />
      </div>
    </div>
  );
};

export default Explanation;
