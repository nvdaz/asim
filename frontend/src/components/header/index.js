import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import Avatar from "@mui/material/Avatar";
import Dialog from "./dialog";
import { Link } from "react-router-dom";

import pic from "../../assets/jimmy.png";

export default function header({ name, initData }) {
  return (
    <div
      style={{
        width: "100%",
        backgroundColor: "#292929",
        borderBottom: "#333333 1px solid",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px",
          color: "white",
          fontSize: "12px",
        }}
      >
        <Link style={{ color: "white" }} to="/">
          <ArrowBackIosNewIcon style={{ cursor: "pointer" }} />
        </Link>
        <div
          style={{
            display: "flex",
            gap: "10px",
            alignItems: "center",
          }}
        >
          <Avatar alt="Jimmy" sx={{ width: 35, height: 35 }} src={pic} />
          <div>{name}</div>
        </div>
        <Dialog initData={initData} />
      </div>
    </div>
  );
}
