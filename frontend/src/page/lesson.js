import { useState, useCallback, useEffect } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";

import Header from "../components/header/index.js";
import InputAndMessages from "../components/InputAndMessages/index.js";
import { Post, Get } from "../utils/request";

import styles from "./landing.module.css";

const Lesson = () => {
  const [headerHeight, setHeaderHeight] = useState(null);
  const [data, setData] = useState(null);
  const [nextConversation, setNextConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alertMessage, setAlertMessage] = useState("");
  const currentLevel = window.location.href.split("/")[4] - 1;

  const errr = async (conversationID, condition) => {
    const next = await Post(`conversations/${conversationID}/next`);
    if (!next.ok) {
      setAlertMessage("Error occurred fetching data");
      return;
    }

    if (condition || next.data.type === "ap") {
      const userOptions = await Post(`conversations/${conversationID}/next`);
      if (!userOptions.ok) {
        setAlertMessage("Error occurred fetching data");
        return;
      }

      setNextConversation({
        options: userOptions.data.options,
        ap_message: next.data.content,
      });
    } else {
      setNextConversation(next.data);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      if (typeof currentLevel !== "number") {
        setAlertMessage("Wrong url parameter");
      }

      const listConversations = await Get(
        `conversations/?level=${currentLevel}`
      );

      // when there were no previous conversatioins
      if (listConversations.data.length === 0) {
        const initConversation = await Post("conversations/", {
          level: currentLevel,
        });
        if (!initConversation.ok) {
          setAlertMessage("Error occurred fetching data");
          return;
        }
        setData(initConversation.data);

        //
        const next = await Post(
          `conversations/${initConversation.data.id}/next`
        );
        if (!next.ok) {
          setAlertMessage("Error occurred fetching data");
          return;
        }

        if (!initConversation.data.scenario.is_user_initiated) {
          const userOptions = await Post(
            `conversations/${initConversation.data.id}/next`
          );
          if (!userOptions.ok) {
            setAlertMessage("Error occurred fetching data");
            return;
          }

          setNextConversation({
            options: userOptions.data.options,
            ap_message: next.data.content,
          });
        } else {
          setNextConversation(next.data);
        }
        //
        // when there are many conversations
      } else {
        const length = listConversations.data.length;
        const conversationID = listConversations.data[length - 1].id;
        const history = await Get(`conversations/${conversationID}`);
        const historyData = history.data;

        setData({
          id: conversationID,
          subject_name: historyData.subject_name,
          scenario: historyData.scenario,
          messages: historyData.messages,
        });

        if (historyData.state.waiting) {
          setNextConversation({
            options: historyData.state.options,
            ap_message: null,
          });
        } else {
          const next = await Post(`conversations/${conversationID}/next`);
          if (next.data.type === "ap") {
            const userOptions = await Post(
              `conversations/${conversationID}/next`
            );
            setNextConversation({
              options: userOptions.data.options,
              ap_message: next.data.content,
            });
          } else {
            setNextConversation(next);
          }
        }
      }

      setLoading(false);
    };

    fetchData();
  }, [currentLevel]);

  const header = useCallback((node) => {
    if (node !== null) {
      setHeaderHeight(node.getBoundingClientRect().height);
    }
  }, []);

  return (
    <div className={styles.wrapper}>
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
        <div style={{ width: "100%", height: "100%" }}>
          <div ref={header}>
            <Header
              name={data["subject_name"]}
              initData={{
                scenario: data["scenario"]["user_scenario"],
                goal: data["scenario"]["user_goal"],
              }}
            />
          </div>
          <InputAndMessages
            headerHeight={headerHeight}
            initData={{
              id: data.id,
              options: nextConversation.options,
              is_user_initiated: data.scenario.is_user_initiated,
              ap_message: nextConversation?.ap_message,
              messages: data.messages,
            }}
          />
        </div>
      )}
    </div>
  );
};

export default Lesson;
