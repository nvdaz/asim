import styles from "./index.module.css";

const backStory = ({ initData }) => {
  return (
    <div className={styles.explanation}>
      <div>
        <div
          style={{
            fontSize: "17px",
            paddingBottom: "5px",
          }}
        >
          Senario:
        </div>
        {initData.scenario}
      </div>
      <div>
        <div
          style={{
            fontSize: "17px",
            paddingBottom: "5px",
          }}
        >
          Goal:
        </div>
        {initData.goal}
      </div>
    </div>
  );
};

export default backStory;
