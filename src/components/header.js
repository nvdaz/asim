import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import Avatar from "@mui/material/Avatar";
import pic from "../assets/jimmy.png";

export default function header({ setOpenDrawer }) {
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
        }}
      >
        <ArrowBackIosNewIcon style={{ cursor: "pointer" }} />
        <div
          style={{
            display: "flex",
            gap: "10px",
            alignItems: "center",
            cursor: "pointer",
          }}
        >
          <Avatar alt="Jimmy" src={pic} />
          <div>Jimmy</div>
        </div>
        <MoreHorizIcon
          onClick={() => setOpenDrawer(true)}
          style={{ cursor: "pointer" }}
        />
      </div>
    </div>
  );
}
