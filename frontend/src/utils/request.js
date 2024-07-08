export async function Post(path, data) {
  const styles = new Promise(async (resolve, reject) => {
    const token = localStorage.getItem("token");

    const options = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "http://localhost:3000",
      },
    };

    if (token) {
      options.headers["Authorization"] = `Bearer ${token}`;
    }

    if (data) {
      options.body = JSON.stringify(data);
    }

    let result;

    fetch(`http://127.0.0.1:8000/${path}`, options)
      .then(async (response) => {
        const ok = response.ok;

        try {
          const data = await response.json();
          result = { ok, data };
        } catch (error) {
          const errorText = await response.text();
          result = { ok, error: errorText || "Unknown error" };
        }

        resolve(result);
      })
      .catch((error) => {
        result = { ok: false, error: error || "Unknown error" };
      });
  })

  return styles;
}
