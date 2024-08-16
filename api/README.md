# API

## Installation

In this directory:

```bash
pip install .
```

It is probably a good idea to do this in a virtual environment, but it is not required.

## Running

### Set environment variables

- `LLM_URI`: The URI of the LLM service.
- `CONVERSATIONS_URI`: The URI of the conversations service.
- `INTERNAL_API_KEY`: A random string to authorize requests to the internal endpoints.
- `MONGO_URI`: The URI of the MongoDB database.

### Run the server

```bash
uvicorn api.main:app --reload
```

### Access the API

- The API will then be available at <http://localhost:8000>.
- The API documentation will be available at <http://localhost:8000/docs>.

### Create an account

Accounts must be created using the internal endpoints.

1. Navigate to <http://localhost:8000/docs#/auth/internal_create_account_auth_internal_create_account_post>.
2. Click the padlock icon and enter the `INTERNAL_API_KEY` environment variable.
3. Click "Try it out".
4. Enter the Q&A service UUID into the `qa_id` field.
5. Click "Execute". The response will be the magic link (remove the quotes).

## How Conversations Work

There are two fundamental layers to each conversation:

1. A finite state machine that determines the flow of the conversation.
2. The LLM that combines the logical state with customizations to generate responses.

### The State Machine

This is a simple state machine that transitions between states based on which option the user selects. These provide the structure of the conversation and are defined in the `levels` folder. States contribute prompt data to the LLM.

Message states (user or agent messages) include instructions to generate messages. These instructions include the following:

- `description`: A description of the instructions (e.g. "I will ask a direct question.").
- `model`: The model to use for the message (by default, this is Claude 3 Sonnet).
- `examples`: Message-pair examples used in the prompt.

Feedback states include prompt instructions to generate feedback as well as instructions to generate a follow-up message for the user (technically optional, but as of now, all feedback states have follow-up messages). The follow-up message instructions are exactly the same as message states. The feedback prompt instructions include the following:

- `prompt`: A description of what the feedback should be about.
- `examples`: Messsages-feedback pairs used in the prompt.

There is also a final state (the `None` state) that is used to end the finite state machine's execution. Note that a transition to a `None` state internally does not necessarily mean the conversation is over (if the state machine is a sub-state machine). Though, it certainly does mean the conversation is over if the state machine that outputted the `None` state is the top-level state machine.

### The LLM

This layer calls the LLM to generate responses based on the state of the internal state machine, the context of the converstaion, and the user's persona. The calls for message and feedback generation in particular are made in `services/message_generation.py` and `services/feedback_generation.py`, respectively. These should hopefully be straightforward to follow.

## Development

A type checker (i.e. Pylance) would be extremely helpful, especially when working with the state machine since the syntax is a bit complex and hard to read. The code has also been formatted with Ruff.

## Deployment

The API is merely an ASGI application. It can be deployed as a container with uvicorn with the provided Dockerfile. It should also be possible to deploy it as a Lambda function using something like mangum.
