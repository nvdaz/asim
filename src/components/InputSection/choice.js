import styles from "./index.module.css";

const Choice = ({ index, message, func, selectedButton }) => {
  return (
    <div
      className={
        selectedButton === index ? styles.selectedBtn : styles.selectableBtn
      }
      onClick={func}
    >
      {message}
    </div>
  );
};

export default Choice;
