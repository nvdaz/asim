import { useState, useCallback, useEffect } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";

import Header from "../components/header/index.js";
import InputAndMessages from "../components/InputAndMessages/index.js";
import { Post } from "../utils/request";
import "../App.css";

const Lesson = () => {
  const [headerHeight, setHeaderHeight] = useState(null);
  const [data, setData] = useState(null);
  const [nextConversation, setNextConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alertMessage, setAlertMessage] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await Post("conversations/");
        setData(res);
        console.log(res);
        const next = await Post(`conversations/${res.id}/next`);
        setNextConversation(next);
        setLoading(false);
        console.log('??');
      } catch (error) {
        setAlertMessage(error.message);
      }
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
      {alertMessage && (
        <Collapse in={alertMessage !== ""}>
          <Alert
            action={
              <IconButton
                aria-label="close"
                color="inherit"
                size="small"
                onClick={() => {
                  setAlertMessage(null);
                }}
              >
                <CloseIcon fontSize="inherit" />
              </IconButton>
            }
            sx={{ position: "absolute", top: "20px" }}
            variant="filled"
            severity="warning"
          >
            {alertMessage}
          </Alert>
        </Collapse>
      )}
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
        <div style={{width: '100%'}}>
          <div ref={header}>
            <Header
              name={data["info"]["subject_info"]["name"]}
              initData={{
                scenario: data["info"]["user_scenario"],
                goal: data["info"]["user_goal"],
              }}
            />
          </div>
          <InputAndMessages
            headerHeight={headerHeight}
            initData={{
              id: data.id,
              options: nextConversation.options,
            }}
          />
        </div>
      )}
    </div>
  );
};

export default Lesson;
