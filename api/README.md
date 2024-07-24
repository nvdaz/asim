# API

To install:

In this directory:

```bash
pip install .
```

To run:

The LLM endpoint should be exported as an environment variable called `LLM_URI`; conversations endpoint to `CONVERSATIONS_URI`; and an internal API key (some random string) to `INTERNAL_API_KEY`.

The internal API key is used to authorize requests _only_ to the `/internal-create-magic-link` endpoint.

A MongoDB URI is also read from `MONGO_URI` else `mongodb://localhost:27017` is used.

. Then,

```bash
uvicorn api.main:app --reload
```

The API will then be available at `http://localhost:8000`.

Magic links can be created with this form: `http://localhost:8000/docs#/auth/internal_create_magic_link_auth_internal_create_magic_link_post`.
