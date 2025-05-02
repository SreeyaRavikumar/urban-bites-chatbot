
# Urban Bites Chatbot

## Overview
The **Urban Bites Chatbot** is a restaurant assistant powered by **Dialogflow** and a **FastAPI** backend. It helps customers order food, track their orders, get combo suggestions, and reorder their last meal.

## Tech Stack
- **Dialogflow** for intent recognition and conversational flow.
- **FastAPI** for building the backend API.
- **MySQL** for managing order data and user information.

## Features
- **Combo Suggestions**: Recommends complementary food items based on customer choices.
- **Quick Reorder**: Allows users to reorder their last meal with a single command.
- **Order Tracking**: Users can track the status of their orders in real-time.
- **Add Items to Cart**: Customers can add new items to their cart while placing the order.
- **Remove Items from Order**: Users can remove items from their order if they change their mind.
- **New Orders**: Handles completely new orders and updates the cart accordingly.

## Setup Instructions
1. Clone this repository:
   ```bash
   git clone https://github.com/SreeyaRavikumar/urban-bites-chatbot.git
````

2. Install dependencies:

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

## Evaluation Results

* **Accuracy**: 95% on test set (for intent recognition).
* **Latency**: 500ms average response time for order processing.

## Future Improvements

* Adding voice recognition for a more interactive experience.
* Expanding the range of UPI payment gateways supported.
* Integrating advanced AI models for better food recommendations.

````

---