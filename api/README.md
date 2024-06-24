# API

To install:

In this directory:

```bash
pip install .
```

To run:

The LLM endpoint should be exported as an environment variable called `LLM_URI`. Then,

```bash
uvicorn api.main:app --reload
```

Also: llm generate + embed calls are cached and random calls are seeded for speed and reproducibility.
You can get different results by changing the seed.
