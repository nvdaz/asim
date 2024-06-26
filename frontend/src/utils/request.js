export async function Post(path) {
  const styles = new Promise(async (resolve, reject) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/${path}`, {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
      });

      if (res.ok) {
        const data = await res.json();
        resolve(data);
      } else {
        console.error("Unexpected response status:", res.status);
      }
    } catch (error) {
      console.error("Error:", error);
    }
  }).catch((error) => {
    console.error("Error reading file:", error);
  });

  return styles;
}
