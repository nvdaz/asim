import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import useMediaQuery from "@mui/material/useMediaQuery";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Button from "@mui/material/Button";

import TextareaAutosize from "../components/InputSection/textareaAutosize";
import { Post } from "../utils/request";

import styles from "./landing.module.css";

const Landing = () => {
  const { uniqueString } = useParams();
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(true);
  const [enteredName, setEnteredName] = useState("");
  const [alertMessage, setAlertMessage] = useState("");
  const [mode, selectedMode] = useState("Learn");
  const isMobile = useMediaQuery("(max-width:600px)");

  useEffect(() => {
    const fetchData = async () => {
      const link = localStorage.getItem("link") || uniqueString;
      if (uniqueString) {
        localStorage.setItem("link", uniqueString);
      }

      const res2 = await Post("auth/exchange", {
        magic_link: link,
      });
      if (!res2.ok) {
        setAlertMessage("Error occurred");
        return;
      }
      localStorage.setItem("token", res2.data.token);

      if (!res2.data.user.init) {
        setFetching(false);
      } else {
        setLoading(false);
      }
    };

    fetchData();
  }, [uniqueString]);

  const handleMessageChange = (e) => {
    setEnteredName(e.target.value);
  };

  const handleSend = async (e) => {
    const setupName = await Post("auth/setup", {
      name: enteredName,
    });

    localStorage.setItem("name", enteredName);

    if (!setupName.ok) {
      setAlertMessage(
        "Submission failed. Please make sure your signup link is correct."
      );
      return;
    }

    setLoading(false);
  };

  const loginAndInitSetUp = () => {
    return fetching ? (
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
        <div style={{ color: "white" }}>Loading</div>
      </div>
    ) : (
      <div className={styles.setUpWrapper}>
        <div>Welcome! What is your name?</div>
        <div>
          It will be how you are addressed during conversations and when given
          feedback.
        </div>
        <div className={styles.textAreaWrapper}>
          <div style={{ width: "40%" }}>
            {Boolean(enteredName) && (
              <div style={{ padding: "15px 0 20px 0" }}>Hi {enteredName}!</div>
            )}
            <TextareaAutosize
              value={enteredName}
              onChange={handleMessageChange}
            />
          </div>
        </div>
        <div className={styles.btnWrapper}>
          <div
            style={{
              backgroundColor: Boolean(enteredName) ? "#FFB930" : "#3C3C43",
              color: Boolean(enteredName) ? "#282828" : "#ACACAC",
              cursor: Boolean(enteredName) ? "pointer" : "default",
            }}
            onClick={handleSend}
          >
            Send
          </div>
        </div>
      </div>
    );
  };

  const lessonsSection = () => {
    return (
      <div className={styles.columnRight}>
        <Button
          sx={{
            backgroundColor: "#FFB930",
            textTransform: "none",
            borderRadius: "50%",
            padding: 0,
            "&:hover": {
              backgroundColor: "#FF9430",
            },
            "& .MuiTouchRipple-child": {
              backgroundColor: "#FFCC69",
            },
          }}
        >
          <div
            className={styles.lessonsBtn}
            onClick={() =>
              setTimeout(() => {
                window.location.href = "/lesson/1";
              }, "250")
            }
          >
            <div>Start</div>
          </div>
        </Button>
        <Button
          sx={{
            backgroundColor: "#797979",
            borderRadius: "50%",
            padding: 0,
            marginLeft: "100px",
            "&:hover": {
              backgroundColor: "#A3A3A3",
            },
            "& .MuiTouchRipple-child": {
              backgroundColor: "#637BC4",
            },
          }}
        >
          <div
            className={styles.lessonsBtn}
            onClick={() =>
              setTimeout(() => {
                window.location.href = "/lesson/2";
              }, "250")
            }
          ></div>
        </Button>
      </div>
    );
  }

  const btn = (name) => {
    return (
      <div
        className={mode === name ? styles.btnSelected : styles.btn}
        onClick={() =>{
          selectedMode(name)
          name === "Playground" &&
            setTimeout(() => {
              window.location.href = "/playground";
            }, "250");
        }}
      >
        {name}
      </div>
    );
  }

  const landingPage = () => {
    return isMobile ? (
      <div style={{ width: "100%", margin: "16px" }}>
        {lessonsSection()}
        <div className={styles.mobileBtnWrapper}>
          {btn("Learn")}
          {btn("Playground")}
        </div>
      </div>
    ) : (
      <div className={styles.wrapper}>
        <div className={styles.column}>
          <div style={{ padding: "3rem 0" }}>
            {btn("Learn")}
            {btn("Playground")}
          </div>
        </div>
        {lessonsSection()}
      </div>
    );
  };

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
      {loading ? loginAndInitSetUp() : landingPage()}
    </div>
  );
};

export default Landing;
