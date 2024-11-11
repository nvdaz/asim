import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./components/auth-provider";

function App() {
  const { token } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (token) {
      navigate("/chat");
    }
  });

  return (
    <div className="container relative h-full flex-col items-center justify-center grid lg:max-w-none lg:grid-cols-2 px-8">
      <div className="mx-auto flex w-full flex-col justify-center space-y-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          Hello! You are not logged in.
        </h1>
        <p className="text-lg">
          If you are seeing this page, you have not logged in yet. Please use
          the link that was provided to you to log in.
        </p>
      </div>
    </div>
  );
}

export default App;
