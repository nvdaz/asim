## Project Overview

NeuroBridge simulates an AI conversation partner that communicates in a direct and literal manner, a style common among some autistic individuals. The system delivers scenario-specific feedback that helps neurotypical users interpret this communication style and choose responses that are clearer and more appropriate

## Key Features

### Simulation of Scenarios
NeuroBridge centers the conversation around four common communication scenarios that may pose a challenge in mixed-neurotype settings:
- **Indirect speech acts** (implicit requests vs literal questions)
- **Figurative expressions** (idioms/metaphors interpreted literally vs interpreted figuratively)
- **Emojis with variable interpretations** (emojis with fluid meaning dependent on context)
- **Being misperceived as blunt** (direct statements read as rude vs honest)

### Scenario Generator
Users enter basic info (e.g., name/pronouns) and a topic they are interested in. Using this information, NeuroBridge generates a **personalized scenario** and context for the conversation.

### Message Options Generator
For each user-written message, NeuroBridge generates **three semantically similar options** that differ in tone/clarity/phrasing based on the given scenario. Users select which option to send.

### Feedback Panel (Positive + Constructive)
After the character responds, NeuroBridge provides **scenario-specific feedback**:
- **Constructive feedback** explains the intent mismatch, identifies the most appropriate option, and why it’s best—then provides an empathic follow-up message the user can send.
- **Positive feedback** reinforces good choices and explains why other options could cause misunderstanding.

### Co-designed and Evaluation
NeuroBridge was co-designed with an **advisory board of autistic individuals** and evaluated in an in-lab study with **12 neurotypical participants**.

## Installation

For frontend: 

``` sh
cd frontend
npm install
```

Create a .env file at the root of the frontend folder, and set the environment 
variable REACT_APP_API_HOST.

For backend, follow the instructions in [api/README.md ](./api/README.md).

#  Development

``` sh
cd frontend
npm start
```

## Publication
**NeuroBridge: Using Generative AI to Bridge Cross-neurotype Communication Differences with Neurotypical Perspective-taking**  
*Proceedings of the 27th International ACM SIGACCESS Conference on Computers and Accessibility (ASSETS 2025)*  
** Best Student Paper 🏆  
PDF: https://rukhshan23.github.io/assets-2025.pdf

### Citation
```bibtex
@inproceedings{haroon2025neurobridge,
  author    = {Haroon, Rukhshan and Wigdor, Kyle and Yang, Katie and Toumanios, Nicole and Crehan, Eileen T. and Dogar, Fahad},
  title     = {NeuroBridge: Using Generative AI to Bridge Cross-neurotype Communication Differences with Neurotypical Perspective-taking},
  booktitle = {Proceedings of the 27th International ACM SIGACCESS Conference on Computers and Accessibility (ASSETS 2025)},
  address   = {Denver, CO, USA},
  year      = {2025},
  url       = {https://rukhshan23.github.io/assets-2025.pdf}
}
```
