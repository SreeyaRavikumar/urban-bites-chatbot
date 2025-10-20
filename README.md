
# Urban Bites Chatbot

![Python](https://img.shields.io/badge/Python-3.10-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![Dialogflow](https://img.shields.io/badge/Dialogflow-NLP-orange)

## Table of Contents
- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Features](#features)
- [Setup Instructions](#setup-instructions)
- [How to Run](#how-to-run)
- [Evaluation Results](#evaluation-results)
- [Future Improvements](#future-improvements)

## Overview
The **Urban Bites Chatbot** is a restaurant assistant powered by **Dialogflow** and a **FastAPI** backend. It helps customers order food, track their orders, get combo suggestions, and reorder their last meal.

## Tech Stack
- Frontend: Dialogflow (for chatbot AI)
- Backend: FastAPI
- Database: MySQL (for storing order data)

### Prerequisites:
- Python 3.x
- MySQL
- Dialogflow agent (exported ZIP)

## Features
- Natural Language Processing using Dialogflow
- Backend API with FastAPI
- Place new orders or reorder past items
- Session-based user interaction
- Structured results and analytics

## Setup Instructions
1. Clone this repository:
```bash
   git clone https://github.com/SreeyaRavikumar/urban-bites-chatbot.git
````

2. Install dependencies

```bash
   cd urban-bites-chatbot/backend
   pip install -r requirements.txt
```

3. Set up environment variables:

   * Create a `.env` file in the `backend/` directory.
   * Add your MySQL configuration and other necessary variables.

4. Run the FastAPI server:

```bash
   uvicorn main:app --reload
```

5. (Optional) To deploy to production, make sure database and environment configs are production-ready.

## How to Run

To run the chatbot locally:

1. Ensure your Dialogflow credentials are set up.
2. Start the FastAPI backend.
3. Open `website/index.html` in your browser to interact with the chatbot.

## 💬 Sample Interaction

**User**: I want a pizza
**Bot**: So far you have 1 pizza. You would like mango lassi since you have ordered a pizza. Would you like me to add that?
**User**: Yes
**Bot**: Mango lassi added to your cart. So far you have 1 pizza and 1 Mango lassi. Do you need anything else?

## Evaluation Results

* **Accuracy**: 95% on test set (for intent recognition).
* **Latency**: 500ms average response time for order processing.

## Future Improvements

* Adding voice recognition for a more interactive experience.
* Expanding the range of UPI payment gateways supported.
* Integrating advanced AI models for better food recommendations.

## Credits

* **[Varshini Chilakala](https://github.com/Varshini-chilakala)**.

* **[Killi Sreeya Ravikumar](https://github.com/SreeyaRavikumar)**.

* **[Aidupogula Hepsiba Grace](https://github.com/Hepsiba1803)**.

* **[Kokkiligadda Himabindhu](https://github.com/Himabindu-dot)**.

* **Special thanks to [Mrs. Mathe Jerusha Blessy](#)** for guidance and feedback.

---

