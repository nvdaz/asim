import { useAuth } from "@/components/auth-provider";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Loading } from "./components/ui/loading";

function Auth() {
  const { magic } = useParams();
  const { user, setAuth } = useAuth();
  const [state, setState] = useState<"loading" | "error" | "done">("loading");
  const navigate = useNavigate();

  useEffect(() => {
    const abortController = new AbortController();

    fetch(`${import.meta.env.VITE_API_URL}/auth/exchange`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ magic_link: magic }),
      signal: abortController.signal,
    })
      .then((res) => {
        if (res.ok) {
          return res.json();
        }
        throw new Error("Could not log in");
      })
      .then((data) => {
        setAuth(data);
        setState("done");
      })
      .catch((err) => {
        if (err.name === "AbortError") {
          return;
        }
        setState("error");
      });

    return () => {
      abortController.abort();
    };
  }, [magic]);

  useEffect(() => {
    let timeout: number;

    if (state === "done") {
      timeout = window.setTimeout(() => {
        if (user!.name) {
          navigate("/chat");
        } else {
          navigate("/register");
        }
      }, 2500);
    }

    return () => {
      window.clearTimeout(timeout);
    };
  }, [state]);

  return (
    <>
      {state === "loading" && <Loading />}

      <div className="container relative h-full flex-col items-center justify-center grid lg:max-w-none lg:grid-cols-2 px-8">
        <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
          <AnimatePresence mode="wait">
            {state === "loading" && (
              <motion.h1
                key="loading"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="text-2xl font-semibold tracking-tight"
              >
                Logging you in...
              </motion.h1>
            )}
            {state === "error" && (
              <motion.h1
                key="error"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="text-2xl font-semibold tracking-tight"
              >
                Sorry, we couldn't log you in. Your magic link may be invalid.
              </motion.h1>
            )}
            {state === "done" &&
              (user!.name ? (
                <motion.h1
                  key="welcome-back"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="text-2xl font-semibold tracking-tight"
                >
                  Welcome back, {user!.name}!
                </motion.h1>
              ) : (
                <motion.h1
                  key="welcome"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="text-2xl font-semibold tracking-tight"
                >
                  Welcome! Please complete your registration.
                </motion.h1>
              ))}
          </AnimatePresence>
        </div>
      </div>
    </>
  );
}

export default Auth;
