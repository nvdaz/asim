import { useState, useCallback, useEffect } from "react";
import CircularProgress from "@mui/material/CircularProgress";

import Header from "../components/header.js";
import InputAndMessages from "../components/InputAndMessages/index.js";
import { Post } from "../utils/request";
import "../App.css";

const Lesson = ({}) => {
  const [headerHeight, setHeaderHeight] = useState(null);
  const [data, setData] = useState(null);
  const [nextConversation, setNextConversation] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      const data = await Post('conversations/');
      setData(data);
      const next = await Post(`conversations/${data["id"]}/next`);
      setNextConversation(next);
      setLoading(false);
    };

    fetchData();
  }, []);

  const header = useCallback((node) => {
    if (node !== null) {
      setHeaderHeight(node.getBoundingClientRect().height);
    }
  }, []);

  return (
    <div className="wrapper">
      {loading ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "20px",
            marginBottom: "10%",
          }}
        >
          <CircularProgress />
          <div style={{ color: "white" }}>Initializing Lesson</div>
        </div>
      ) : (
        <div>
          <div ref={header}>
            <Header name={data["info"]["subject_info"]["name"]} />
          </div>
          <InputAndMessages
            headerHeight={headerHeight}
            initData={{
              id: data["info"]["id'"],
              scenario: data["info"]["user_scenario"],
              goal: data["info"]["user_goal"],
              options: nextConversation.options
            }}
          />
        </div>
      )}
    </div>
  );
};

export default Lesson;
