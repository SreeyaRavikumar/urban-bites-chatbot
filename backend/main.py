from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import db_helper
from db_helper import get_combo_suggestions, update_order_statuses
import generic_helper
import logging
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# Set up logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler('app.log', maxBytes=1024*1024, backupCount=3)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
db_logger = logging.getLogger('db_helper')
db_logger.setLevel(logging.INFO)
db_logger.addHandler(file_handler)
db_logger.addHandler(console_handler)

# Set up scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=db_helper.update_order_statuses,
    trigger=IntervalTrigger(minutes=1),
    id='update_order_statuses',
    name='Update order statuses every minute',
    replace_existing=True
)
scheduler.start()
logger.info("Started scheduler for order status updates")

# Shutdown scheduler on exit
atexit.register(lambda: scheduler.shutdown())

app = FastAPI()
inprogress_orders = {}


@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()
    logger.info(f"Received payload: {payload}")

    intent = payload['queryResult']['intent']['displayName']
    parameters = {
        "parameters": payload["queryResult"]["parameters"],
        "outputContexts": payload["queryResult"]["outputContexts"]
    }
    output_contexts = payload["queryResult"]["outputContexts"]
    if not output_contexts:
        logger.error("No output contexts found in payload")
        return JSONResponse(content={"fulfillmentText": "Sorry, something went wrong. Please try again."})

    session_id = generic_helper.extract_session_id(output_contexts[0]["name"])
    if not session_id or session_id == "ongoing-order":
        logger.error(f"Invalid session ID extracted: {session_id}")
        return JSONResponse(content={"fulfillmentText": "Error processing your request. Please start a new session."})

    logger.info(f"Session ID: {session_id}, Intent: {intent}")

    intent_handler_dict = {
        'order.add-context:ongoing-order': add_to_order,
        'order.remove-context:ongoing-order': remove_from_order,
        'order.complete-context:ongoing-order': complete_order,
        'new.order': new_order,
        'suggest.combo': suggest_combo,
        'reorder.last': reorder_last,
        'confirm.reorder': confirm_reorder,
        'cancel.reorder': cancel_reorder,
        'order.status': track_order_status
    }

    return intent_handler_dict[intent](parameters, session_id)

@app.get("/check_last_orders")
async def check_last_orders():
    try:
        cursor = db_helper.cnx.cursor(dictionary=True)
        cursor.execute("SELECT * FROM last_orders ORDER BY created_at DESC LIMIT 10")
        results = cursor.fetchall()
        cursor.close()
        return {"status": "success", "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def add_to_order(parameters: dict, session_id: str):
    try:
        food_items = parameters["parameters"]["food-item"]
        quantities = parameters["parameters"]["number"]

        if len(food_items) != len(quantities):
            fulfillment_text = "Sorry, I didn't understand. Can you please specify food items and quantities clearly?"
        else:
            if session_id not in inprogress_orders:
                inprogress_orders[session_id] = {}
            current_food_dict = inprogress_orders[session_id]
            for food_item, quantity in zip(food_items, quantities):
                quantity = int(quantity)
                if food_item in current_food_dict:
                    current_food_dict[food_item] += quantity
                else:
                    current_food_dict[food_item] = quantity
            inprogress_orders[session_id] = current_food_dict

            order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
            ordered_items = list(inprogress_orders[session_id].keys())
            suggestions = db_helper.get_combo_suggestions(ordered_items)

            if suggestions:
                suggestion_text = "You might also like: " + ", ".join(
                    suggestions) + " since you have ordered " + ", ".join(ordered_items)
            else:
                suggestion_text = "No combos found, but we've got more delicious items!"

            fulfillment_text = f"So far you have: {order_str}. {suggestion_text} Do you need anything else?"

        return JSONResponse(content={"fulfillmentText": fulfillment_text})
    except Exception as e:
        logger.error(f"Error in add_to_order: {e}")
        return JSONResponse(content={"fulfillmentText": "Sorry, I encountered an error. Please try again."})

def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having trouble finding your order. Sorry! Can you place a new order please?"
        })

    food_items = parameters["parameters"]["food-item"]
    quantities = parameters["parameters"].get("number", [])
    if not quantities:
        quantities = [1] * len(food_items)

    if len(food_items) != len(quantities):
        return JSONResponse(content={
            "fulfillmentText": "Sorry, I didn't understand. Please specify food items and quantities clearly."
        })

    current_order = inprogress_orders[session_id]
    removed_items, no_such_items, partial_removals = [], [], []

    for item, qty in zip(food_items, quantities):
        qty = int(qty)
        if item not in current_order:
            no_such_items.append(item)
        else:
            current_qty = current_order[item]
            if qty >= current_qty:
                removed_items.append(item)
                del current_order[item]
            else:
                current_order[item] -= qty
                partial_removals.append(f"{qty} {item}")

    fulfillment_text = ""
    if removed_items:
        fulfillment_text += f"Removed {', '.join(removed_items)} from your order! "
    if partial_removals:
        fulfillment_text += f"Reduced {', '.join(partial_removals)} from your order! "
    if no_such_items:
        fulfillment_text += f"Your current order does not have {', '.join(no_such_items)}. "

    if not current_order:
        fulfillment_text += "Your order is empty!"
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f"Here is what is left in your order: {order_str}"

    ordered_items = list(current_order.keys())
    suggestions = get_combo_suggestions(ordered_items)

    if suggestions:
        suggestion_text = "You might also like: " + ", ".join(suggestions) + " since you have ordered " + ", ".join(ordered_items)
    else:
        suggestion_text = "No combos found, but we’ve got more delicious items!"

    fulfillment_text += f" {suggestion_text}"

    return JSONResponse(content={"fulfillmentText": fulfillment_text.strip()})

def complete_order(parameters: dict, session_id: str):
    try:
        logger.info(f"Starting complete_order for session: {session_id}")
        if session_id not in inprogress_orders:
            logger.error(f"No in-progress order found for session: {session_id}")
            return JSONResponse(content={
                "fulfillmentText": "I'm having trouble finding your order. Sorry! Can you place a new order please?"
            })

        order = inprogress_orders[session_id]
        logger.info(f"Current order to complete: {order}")
        order_id = save_to_db(order)
        if order_id == -1:
            logger.error("Failed to save to orders table")
            return JSONResponse(content={
                "fulfillmentText": "Sorry, I couldn't process your order due to a backend error. Please place a new order again."
            })

        logger.info(f"Successfully saved order with ID: {order_id}")
        order_total = db_helper.get_total_order_price(order_id)
        logger.info(f"Order total calculated: {order_total}")

        logger.info(f"Attempting to save to last_orders table with session_id: {session_id}")
        save_result = db_helper.save_last_order(session_id, order)
        if not save_result:
            logger.error(f"Failed to save last order for session: {session_id}")
        else:
            logger.info(f"Successfully saved last order for session: {session_id}")

        del inprogress_orders[session_id]
        logger.info(f"Completed order {order_id} and cleared session {session_id}")

        return JSONResponse(content={
            "fulfillmentText": f"Awesome. We have placed your order. Here is your order id # {order_id}. Your order total is {order_total} which you can pay at the time of delivery!"
        })
    except Exception as e:
        logger.error(f"Critical error in complete_order: {str(e)}", exc_info=True)
        return JSONResponse(content={
            "fulfillmentText": "Sorry, we encountered a serious error processing your order. Please try again."
        })

def reorder_last(parameters: dict, session_id: str):
    try:
        logger.info(f"Starting reorder process for session: {session_id}")
        last_order = db_helper.get_last_order(session_id)
        if not last_order:
            logger.error(f"No last order found for session: {session_id}")
            return JSONResponse(content={
                "fulfillmentText": "Sorry, I couldn't find your last order! Would you like to place a new order?"
            })

        logger.info(f"Retrieved last order: {last_order}")
        inprogress_orders[session_id] = last_order
        order_str = generic_helper.get_str_from_food_dict(last_order)
        fulfillment_text = f"Found your last order: {order_str}. Would you like to reorder it?"

        logger.info(f"Prepared reorder response: {fulfillment_text}")
        project_id = "jennie-qfgl"
        context_name = f"projects/{project_id}/locations/global/agent/sessions/{session_id}/contexts/awaiting-reorder-confirmation"

        return JSONResponse(content={
            "fulfillmentText": fulfillment_text,
            "outputContexts": [{
                "name": context_name,
                "lifespanCount": 5,
                "parameters": {
                    "food-item": list(last_order.keys()),
                    "number": list(last_order.values())
                }
            }]
        })
    except Exception as e:
        logger.error(f"Error in reorder_last for session {session_id}: {str(e)}", exc_info=True)
        return JSONResponse(content={
            "fulfillmentText": "Sorry, something went wrong while processing your reorder. Please try again or start a new order."
        }, status_code=500)

def new_order(parameters: dict, session_id: str):
    if session_id in inprogress_orders:
        del inprogress_orders[session_id]
    return JSONResponse(content={"fulfillmentText": "Sure! Let's start a new order. What would you like to have?"})

def suggest_combo(parameters: dict, session_id: str):
    output_contexts = parameters.get("outputContexts", [])
    ordered_items = []
    for ctx in output_contexts:
        if "ongoing-order" in ctx["name"]:
            ordered_items = ctx["parameters"].get("food-item", [])
    suggestions = get_combo_suggestions(ordered_items)
    if suggestions:
        suggestion_text = "You might also like: " + ", ".join(suggestions) + " since you have ordered " + ", ".join(ordered_items)
    else:
        suggestion_text = "No combos found, but we’ve got more delicious items!"
    return {"fulfillmentText": suggestion_text}

def confirm_reorder(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={"fulfillmentText": "No order to confirm. Please try reordering again."})
    order = inprogress_orders[session_id]
    order_id = save_to_db(order)
    if order_id == -1:
        fulfillment_text = "Something went wrong while placing your reorder. Please try again!"
    else:
        order_total = db_helper.get_total_order_price(order_id)
        db_helper.save_last_order(session_id, order)
        fulfillment_text = f"Awesome! Your previous order has been placed again. Order ID: {order_id}. Total: ₹{order_total}."
    del inprogress_orders[session_id]
    return JSONResponse(content={"fulfillmentText": fulfillment_text})

def cancel_reorder(parameters: dict, session_id: str):
    if session_id in inprogress_orders:
        del inprogress_orders[session_id]
    return JSONResponse(content={
        "fulfillmentText": "Alright! I won’t place your last order again. Let me know if you want something else."
    })

def save_to_db(order: dict):
    try:
        next_order_id = db_helper.get_next_order_id()
        if next_order_id == -1:
            return -1
        for food_item, quantity in order.items():
            rcode = db_helper.insert_order_item(food_item, quantity, next_order_id)
            if rcode == -1:
                return -1
        if not db_helper.insert_order_tracking(next_order_id, "in progress"):
            return -1
        return next_order_id
    except Exception as e:
        logger.error(f"Error saving order to db: {e}")
        return -1

def track_order_status(parameters: dict, session_id: str):
    try:
        order_id = parameters["parameters"].get("order_id")
        if not order_id:
            logger.info(f"No order_id provided for session: {session_id}")
            order_id = db_helper.get_last_order_id(session_id)
            if not order_id:
                return JSONResponse(content={
                    "fulfillmentText": "Please provide your order ID to track your order, or place a new order."
                })

        try:
            order_id = int(order_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid order_id format for session: {session_id}")
            return JSONResponse(content={
                "fulfillmentText": "The order ID must be a valid number. Please try again."
            })

        order_status = db_helper.get_order_status(order_id)
        if order_status:
            status_messages = {
                "being prepared": f"Your order #{order_id} is being whipped up in the kitchen!",
                "out for delivery": f"Your order #{order_id} is on its way to you!",
                "delivered": f"Your order #{order_id} has been delivered. Enjoy!",
                "in progress": f"Your order #{order_id} is being processed!"
            }
            normalized_status = order_status.lower()
            fulfillment_text = status_messages.get(normalized_status, f"Your order #{order_id} is currently: {order_status.title()}.")
        else:
            fulfillment_text = f"Sorry, no order found with ID #{order_id}. It may have been delivered or please try the correct order ID."

        logger.info(f"Tracked order {order_id} for session {session_id}: {fulfillment_text}")
        return JSONResponse(content={"fulfillmentText": fulfillment_text})

    except Exception as e:
        logger.error(f"Error tracking order for session {session_id}: {str(e)}")
        return JSONResponse(content={
            "fulfillmentText": "Sorry, something went wrong while tracking your order. Please try again later."
        })

