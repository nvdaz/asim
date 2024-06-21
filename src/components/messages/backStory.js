import styles from "./index.module.css";

const backStory = ({}) => {
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
        It is a random Saturday and everything is slow. You and Jimmy are on the
        same team to make a poster about yourselves to present on the first day
        of class.
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
        Schedule a brainstorming session with Jimmy and talk about the project
        for a bit.
      </div>
    </div>
  );
};

export default backStory;
