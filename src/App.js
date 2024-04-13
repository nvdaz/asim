import { useState, useCallback } from "react";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import Divider from "@mui/material/Divider";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";

import Header from "./components/header";
import Inputs from "./components/InputSection";
import Messages from "./components/messages";
import "./App.css";

function App() {
  const [inputHeight, setInputHeight] = useState(null);
  const [headerHeight, setHeaderHeight] = useState(null);
  const [openDrawer, setOpenDrawer] = useState(false);
  const [messages, setMessages] = useState([
    {
      text: "how is it going?",
      isSendedText: true,
    },
    { text: "Hey! I'm good, thanks.", isSendedText: false },
    { text: "What is going on?", isSendedText: false },
    {
      text: "Do you want to join me on a trip to gloucester this weekend?",
      isSendedText: true,
    },
    {
      text: "Gloucester, huh? Sounds like a blast! What's the plan, mate?",
      isSendedText: false,
    },
  ]);

  const input = useCallback((node) => {
    if (node !== null) {
      setInputHeight(node.getBoundingClientRect().height);
    }
  }, []);

  const header = useCallback((node) => {
    if (node !== null) {
      setHeaderHeight(node.getBoundingClientRect().height);
    }
  }, []);

  return (
    <div className="wrapper">
      <div ref={header}>
        <Header setOpenDrawer={setOpenDrawer} />
      </div>
      <Messages
        messages={messages}
        inputHeight={inputHeight}
        headerHeight={headerHeight}
      />
      <div ref={input}>
        <Inputs messages={messages} setMessages={setMessages} />
      </div>
      <Drawer
        anchor={"right"}
        open={openDrawer}
        onClose={() => setOpenDrawer(false)}
      >
        <Box
          sx={{
            width: 250,
            height: "100%",
            backgroundColor: "rgb(30, 30, 30)",
            color: "white",
          }}
          role="presentation"
        >
          <List
            sx={{
              paddingBottom: 0,
              width: "100%",
              position: "absolute",
              bottom: 0,
            }}
          >
            <Divider />
            <ListItem disablePadding>
              <ListItemButton
                sx={{
                  padding: "25px 15px",
                }}
              >
                <ListItemIcon sx={{ minWidth: "auto" }}>
                  <DeleteOutlineIcon
                    sx={{ marginRight: "15px", color: "#F55151" }}
                  />
                </ListItemIcon>
                <ListItemText primary={"CLEAR CHAT HISTORY"} />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>
      </Drawer>
    </div>
  );
}

export default App;
