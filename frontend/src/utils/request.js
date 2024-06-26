export async function Post(path) {
  const styles = new Promise(async (resolve, reject) => {
  try {
    const res = await fetch(`http://127.0.0.1:8000/${path}`, {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
    });

    if (!res.ok) {
      throw new Error(res.statusText);
    }

    const data = await res.json();
    resolve(data);
  } catch (error) {
    console.error("Error:", error);
    throw error;
  }
  })

  return styles;
}
