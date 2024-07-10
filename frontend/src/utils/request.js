export async function Post(path, data) {
  const styles = new Promise(async (resolve, reject) => {
    const token = localStorage.getItem("token");

    const options = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    };

    if (token !== null) {
      options.headers["Authorization"] = `Bearer ${token}`;
    }

    if (data) {
      options.body = JSON.stringify(data);
    }

    let result;
    fetch(`${process.env.REACT_APP_API_HOST}/${path}`, options)
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
        resolve(result);
      });
  });

  return styles;
}
