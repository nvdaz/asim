import { useState, useCallback } from "react";

import Header from "../components/header.js";
import InputAndMessages from "../components/InputAndMessages/index.js";
import "../App.css";

const Lesson = ({}) => {
  const [headerHeight, setHeaderHeight] = useState(null);

  const header = useCallback((node) => {
    if (node !== null) {
      setHeaderHeight(node.getBoundingClientRect().height);
    }
  }, []);

  return (
    <div className="wrapper">
      <div ref={header}>
        <Header />
      </div>
      <InputAndMessages headerHeight={headerHeight} />
    </div>
  );
};

export default Lesson;
