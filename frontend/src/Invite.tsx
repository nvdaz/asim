import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Loading } from "./components/ui/loading";

function Invite() {
  const { magic } = useParams();
  const navigate = useNavigate();
  const [userMagic, setUserMagic] = useState(null);
  const [state, setState] = useState<"loading" | "error" | "done">("loading");

  useEffect(() => {
    const abortController = new AbortController();

    fetch(`${import.meta.env.VITE_API_URL}/auth/redeem-invite`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ cohort_secret: magic }),
      signal: abortController.signal,
    })
      .then((res) => {
        if (res.ok) {
          return res.json();
        }
        throw new Error("Could not log in");
      })
      .then((data) => {
        setUserMagic(data.magic_link);
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
        navigate(`/auth/${userMagic}`);
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
                Sorry, we couldn't log you in. Your invite link may be invalid.
              </motion.h1>
            )}
            {state === "done" && (
              <motion.h1
                key="welcome"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="text-2xl font-semibold tracking-tight"
              >
                Just a moment while we create your account...
              </motion.h1>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  );
}

export default Invite;
