import { useState, useRef, useEffect, forwardRef } from "react";
import styles from "./index.module.css";

const ChoicesSection = ({ options, handleButtonClick }) => {
  const [maxWidth, setMaxWidth] = useState(0);
  const elementsRef = useRef([]);

  useEffect(() => {
    const widths = elementsRef.current.map((el) => (el ? el.offsetWidth : 0));
    setMaxWidth(Math.max(...widths));
  }, [elementsRef.current]);

  return (
    <div className={styles.choicesWrapper}>
      <div>Choose an option:</div>
      <div className={styles.choices}>
        {Object.keys(options).map((index) => {
          return (
            <Choice
              width={maxWidth - 25}
              ref={(rel) => (elementsRef.current[index] = rel)}
              key={index}
              message={options[index]}
              func={() => handleButtonClick(index, options[index])}
            />
          );
        })}
      </div>
    </div>
  );
};

export const Choice = forwardRef(({ width, message, func }, ref) => {
  const style = width ? { width: width } : {};
  return (
    <div ref={ref} className={styles.choice} style={style} onClick={func}>
      {message}
    </div>
  );
});

export default ChoicesSection;
