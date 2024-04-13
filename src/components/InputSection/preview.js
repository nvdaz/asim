import { useState } from "react";
import CloseIcon from "@mui/icons-material/Close";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import ContentCopyTwoToneIcon from "@mui/icons-material/ContentCopyTwoTone";
import copy from "copy-to-clipboard";

import styles from "./index.module.css";

const Preview = ({ setShowPreview }) => {
  const copyIcon = (
    <ContentCopyOutlinedIcon
      onClick={() => copy("Do you think it could work for your budget?")}
      style={{
        marginRight: "10px",
        cursor: "pointer",
        color: "#387D21",
      }}
    />
  );
  const [icon, setIcon] = useState(copyIcon);
  const [justCopied, setJustCopied] = useState(false);

  const handleClick = () => {
    setJustCopied(true);
    setIcon(
      <ContentCopyTwoToneIcon
        style={{
          marginRight: "10px",
          cursor: "pointer",
          color: "#387D21",
        }}
      />,
    );
    setTimeout(() => {
      setJustCopied(false);
      setIcon(copyIcon);
    }, 1500);
  };

  return (
    <div>
      <div className={styles.copyHeader}>
        <div style={{ flex: 1 }}>
          The other user might feel slightly uncomfortable due to the directness
          regarding affordability. Instead, you might want to say:
        </div>
        <CloseIcon
          onClick={() => setShowPreview(false)}
          style={{ cursor: "pointer", transform: "translate(2px, -2px)" }}
        />
      </div>
      <div
        className={styles.copyWrapper}
        style={{
          border: justCopied ? "rgb(56, 125, 33) 2px solid" : "none",
        }}
      >
        <div className={styles.copyText}>
          Do you think it could work for your budget?
        </div>
        <div onClick={() => handleClick()}>{icon}</div>
      </div>
      <hr className={styles.hr} />
    </div>
  );
};

export default Preview;
