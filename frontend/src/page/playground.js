import { useState, useCallback, useEffect } from "react";
import { useParams } from "react-router-dom";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import LockIcon from "@mui/icons-material/Lock";

import Header from "../components/header/index.js";
import InputAndMessages from "../components/InputAndMessages/index.js";
import { Post, Get } from "../utils/request.js";

import styles from "./page.module.css";

const Playground = () => {
  const { conversationIDFromParam } = useParams();
  const [headerHeight, setHeaderHeight] = useState(null);
  const [data, setData] = useState(null);
  const [conversationList, setConversationList] = useState(null);
  const [nextConversation, setNextConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alertMessage, setAlertMessage] = useState("");
  const currentLevel = window.location.href.split("/")[4] - 1;
  const max_unlocked_stage = localStorage.getItem("max_unlocked_stage");

  useEffect(() => {
    if (max_unlocked_stage !== 'playground') {
      setTimeout(() => {
        window.location.href = `/`;
      }, 2000);
    }
  }, [max_unlocked_stage]);

  const fetchNextSteps = async (conversationID) => {
    const next = await Post(`conversations/${conversationID}/next`, {
      option: "none",
    });
    if (!next.ok) {
      setAlertMessage("Error occurred fetching data");
      return;
    }

    console.log("fetchNextSteps 2", next.data);
    setNextConversation(next.data);
  };

  const fetchNewConversation = useCallback(async () => {
    const initConversation = await Post("conversations/", {
      type: "playground",
      level: 0,
    });
    if (!initConversation.ok) {
      setAlertMessage("Error occurred fetching data");
      return;
    }
    const initData = initConversation.data;
    setData({
      id: initData.id,
      subject_name: initData.agent,
      topic: initData.info.topic,
      messages: initData.elements,
    });

    await fetchNextSteps(initConversation.data.id);
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      if (typeof currentLevel !== "number") {
        setAlertMessage("Invalid url parameter");
      }

      const listConversations = await Get(
        `conversations/?type=playground&level=0`
      );
      if (!listConversations.ok) {
        setAlertMessage("Error occurred fetching data");
        return;
      }

      setConversationList(listConversations.data);

      if (listConversations.data.length === 0) {
        await fetchNewConversation();
      } else {
        const conversationID =
          conversationIDFromParam ||
          listConversations.data[listConversations.data.length - 1].id;

        console.log(conversationIDFromParam, conversationID);
        const history = await Get(`conversations/${conversationID}`);
        if (!history.ok) {
          setAlertMessage("Error occurred fetching data");
          return;
        }
        const historyData = history.data;

        setData({
          id: conversationID,
          subject_name: historyData.agent,
          scenario: historyData.info.scenario,
          topic: historyData.info.topic,
          messages: historyData.elements,
        });

        if (historyData.state === null) {
          await fetchNextSteps(conversationID);
        } else if (historyData.state.waiting) {
          console.log("historyData.state.waiting", historyData.state.waiting);

          if (historyData.elements.length === 0) {
            setNextConversation({
              options: historyData.state.options,
            });
          } else {
            setNextConversation({
              options:
                historyData.elements[historyData.elements.length - 1].type !==
                "feedback"
                  ? historyData.state.options
                  : [],
            });
          }
        } else {
          await fetchNextSteps(conversationID);
        }
      }

      setLoading(false);
    };

    fetchData();
  }, [conversationIDFromParam, currentLevel, fetchNewConversation]);

  const header = useCallback((node) => {
    if (node !== null) {
      setHeaderHeight(node.getBoundingClientRect().height);
    }
  }, []);

  const playground = () => {
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
            <div style={{ color: "white" }}>Building Playground</div>
          </div>
        ) : (
          <div style={{ width: "100%", height: "100%" }}>
            <div ref={header}>
              <Header
                name={data?.["subject_name"]}
                initData={{
                  topic: data?.["topic"],
                }}
                fetchNewConversation={fetchNewConversation}
                conversationList={conversationList}
                currentLevel={currentLevel}
              />
            </div>
            <InputAndMessages
              allowCustomInput={true}
              subjectName={data?.["subject_name"]}
              inputPlaceholder={
                "Write your own response or choose an option to send"
              }
              explanationText={
                "Write your own response\n or choose an option to send"
              }
              headerHeight={headerHeight}
              initData={{
                id: data?.id,
                options: nextConversation?.options,
                is_user_initiated: data?.scenario?.is_user_initiated,
                ap_message: nextConversation?.ap_message,
                messages: data?.messages || [],
              }}
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      {max_unlocked_stage !== "playground" ? (
        <div className={styles.unavailableWrapper}>
          <div className={styles.unavailableTitle}>
            Playground Locked <LockIcon />
          </div>
          <div>Send 8 messages in each lessons to unlock</div>
          <div>Going back to main page...</div>
          <div>
            Click{" "}
            <a
              href="/"
              style={{ color: "turquoise", textDecoration: "underline" }}
            >
              here
            </a>{" "}
            if nothing is happening
          </div>
        </div>
      ) : (
        playground()
      )}
    </div>
  );
};

export default Playground;
