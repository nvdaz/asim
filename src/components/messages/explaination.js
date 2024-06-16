const Explanation = ({}) => {
  return (
    <div
      style={{
        fontSize: "14px",
        border: "#42454E 2px solid",
        borderRadius: "22px",
        padding: "15px",
        color: "white",
        display: "flex",
        flexDirection: "row",
        gap: "10px",
        paddingBottom: "15px",
        marginBottom: '20px',
      }}
    >
      <div>
        <div
          style={{
            fontSize: "17px",
            paddingBottom: "5px",
          }}
        >
          Senario:
        </div>
        It is a random Saturday and everything is slow. You and Jimmy are on the
        same team to make a poster about yourselves to present on the first day
        of class.
      </div>
      <div>
        <div
          style={{
            fontSize: "17px",
            paddingBottom: "5px",
          }}
        >
          Goal:
        </div>
        Schedule a brainstorming session with Jimmy and talk about the project
        for a bit.
      </div>
    </div>
  );
};

export default Explanation;
