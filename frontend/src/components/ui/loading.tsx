import { motion } from "framer-motion";

export function Loading() {
  return (
    <div className="fixed top-0 left-0 w-full h-1 bg-gray-200 dark:bg-gray-800 z-50 overflow-hidden">
      <motion.div
        className="absolute h-full bg-blue-500 w-[80px]"
        initial={{ left: "-80px" }}
        animate={{ left: ["-80px", `calc(100% + 80px)`] }}
        transition={{ ease: "linear", duration: 1.5, repeat: Infinity }}
      />
    </div>
  );
}
