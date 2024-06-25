export async function Get(param) {
  const styles = new Promise(async (resolve, reject) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/${param}/`, {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
      });

      // Check if the response status is 201 Created
      if (res.status === 201) {
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
