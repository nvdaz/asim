# API

To install:

In this directory:

```bash
pip install .
```

You will also need a huggingface access token with access to [NV-Embed-v1](https://huggingface.co/nvidia/NV-Embed-v1)

The access token should be an environment variable called `HF_TOKEN`.

Finally, the LLM endpoint should be exported as an environment variable called `LLM_URI`.

To run:

```bash
python -m api
```

Also: llm generate + embed calls are cached and random calls are seeded in `__main__.py` for speed and reproducibility.
You can get different results by changing the seed.
