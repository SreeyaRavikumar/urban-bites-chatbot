
import mysql.connector
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    try:
        cnx = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="pandeyji_eatery",
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            autocommit=True
        )
        logger.info("Successfully connected to database")
        return cnx
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        return None


cnx = get_db_connection()


def check_db_connection():
    global cnx
    try:
        if cnx is None or not cnx.is_connected():
            cnx = get_db_connection()
        return cnx is not None
    except Exception as e:
        logger.error(f"Connection check failed: {e}")
        return False


def insert_order_item(food_item, quantity, order_id):
    try:
        if not check_db_connection():
            return -1
        cursor = cnx.cursor()
        query = "SELECT item_id, price FROM food_items WHERE name = %s"
        cursor.execute(query, (food_item,))
        result = cursor.fetchone()
        if not result:
            logger.error(f"Food item {food_item} not found")
            return -1
        item_id, price = result
        total_price = price * quantity
        insert_query = """
            INSERT INTO orders (order_id, item_id, quantity, total_price)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (order_id, item_id, quantity, total_price))
        cnx.commit()
        cursor.close()
        logger.info(f"Inserted order: {food_item} x {quantity} for order {order_id}")
        return 1
    except mysql.connector.Error as err:
        logger.error(f"Error inserting order: {err}")
        cnx.rollback()
        return -1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        cnx.rollback()
        return -1


def insert_order_tracking(order_id, status):
    try:
        if not check_db_connection():
            return False
        cursor = cnx.cursor()
        insert_query = """
            INSERT INTO order_tracking (order_id, status, status_updated_at)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE status = %s, status_updated_at = NOW()
        """
        cursor.execute(insert_query, (order_id, status, status))
        cnx.commit()
        cursor.close()
        logger.info(f"Inserted/Updated order tracking for order {order_id} with status {status}")
        return True
    except Exception as e:
        logger.error(f"Error inserting order tracking: {e}")
        cnx.rollback()
        return False


def get_total_order_price(order_id):
    try:
        if not check_db_connection():
            return 0.0
        cursor = cnx.cursor()
        query = "SELECT SUM(total_price) FROM orders WHERE order_id = %s"
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()[0]
        cursor.close()
        total = float(result) if result else 0.0
        logger.info(f"Retrieved total price {total} for order {order_id}")
        return total
    except Exception as e:
        logger.error(f"Error getting total order price: {e}")
        return 0.0


def get_next_order_id():
    try:
        if not check_db_connection():
            return -1
        cursor = cnx.cursor()
        query = "SELECT MAX(order_id) FROM orders"
        cursor.execute(query)
        result = cursor.fetchone()[0]
        cursor.close()
        next_id = 1 if result is None else result + 1
        logger.info(f"Next order ID will be {next_id}")
        return next_id
    except Exception as e:
        logger.error(f"Error getting next order ID: {e}")
        return -1


def get_order_status(order_id):
    try:
        if not check_db_connection():
            logger.error("No database connection available")
            return None
        cursor = cnx.cursor()
        cursor.callproc('get_order_status', (order_id,))
        result = None
        for res in cursor.stored_results():
            result = res.fetchone()
        cursor.close()
        status = result[0] if result else None
        logger.info(f"Retrieved status '{status}' for order {order_id}")
        return status
    except mysql.connector.Error as e:
        logger.error(f"MySQL error getting order status for order {order_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting order status for order {order_id}: {e}")
        return None


def update_order_statuses():
    try:
        if not check_db_connection():
            logger.error("No database connection available")
            return False
        cursor = cnx.cursor()

        # Update "in progress" to "out for delivery" after 15 minutes
        query_in_progress = """
            UPDATE order_tracking
            SET status = 'out for delivery', status_updated_at = NOW()
            WHERE status = 'in progress'
            AND status_updated_at <= %s
        """
        time_threshold = (datetime.now() - timedelta(seconds=20)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(query_in_progress, (time_threshold,))
        logger.info(f"Updated {cursor.rowcount} orders from 'in progress' to 'out for delivery'")

        # Update "out for delivery" to "delivered" after 30 minutes
        query_out_for_delivery = """
            UPDATE order_tracking
            SET status = 'delivered', status_updated_at = NOW()
            WHERE status = 'out for delivery'
            AND status_updated_at <= %s
        """
        time_threshold = (datetime.now() - timedelta(seconds=20)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(query_out_for_delivery, (time_threshold,))
        logger.info(f"Updated {cursor.rowcount} orders from 'out for delivery' to 'delivered'")

        # Delete "delivered" orders that have been delivered for at least 1 minute
        query_delete_delivered = """
            DELETE FROM order_tracking
            WHERE status = 'delivered'
            AND status_updated_at <= %s
        """
        time_threshold = (datetime.now() - timedelta(seconds=20)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(query_delete_delivered, (time_threshold,))
        deleted_count = cursor.rowcount
        logger.info(f"Deleted {deleted_count} delivered orders from order_tracking")

        cnx.commit()
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"Error updating order statuses: {e}")
        cnx.rollback()
        return False


combo_suggestions = {
    "Pav Bhaji": ["Mango Lassi", "Samosa"],
    "Pizza": ["Mango Lassi"],
    "Chole Bhature": ["Rava Dosa", "Masala Dosa"],
    "Vegetable Biryani": ["Raita", "Mango Lassi"],
    "Masala Dosa": ["Samosa"],
    "Vada Pav": ["Mango Lassi"],
}


def get_combo_suggestions(ordered_items):
    try:
        ordered_items = [item.title() for item in ordered_items]
        suggestions = set()
        for item in ordered_items:
            normalized_item = item.title()
            combos = combo_suggestions.get(normalized_item, [])
            suggestions.update(combos)
        suggestions = suggestions - set(ordered_items)
        logger.info(f"Generated combo suggestions: {suggestions} for items: {ordered_items}")
        return list(suggestions)
    except Exception as e:
        logger.error(f"Error generating combo suggestions: {e}")
        return []


def save_last_order(session_id, order):
    try:
        logger.info(f"Starting save_last_order for session: {session_id}, order: {order}")
        if not check_db_connection():
            logger.error("No database connection available")
            return False
        if not session_id or session_id == "ongoing-order":
            logger.error(f"Invalid session_id: {session_id}")
            return False

        cursor = None
        try:
            cursor = cnx.cursor()
            delete_query = "DELETE FROM last_orders WHERE session_id = %s"
            cursor.execute(delete_query, (session_id,))
            logger.info(f"Deleted {cursor.rowcount} previous orders for session: {session_id}")

            insert_query = "INSERT INTO last_orders (session_id, food_item, quantity) VALUES (%s, %s, %s)"
            for food_item, quantity in order.items():
                cursor.execute(insert_query, (session_id, food_item, quantity))
                logger.info(f"Inserted {food_item} x {quantity} for session: {session_id}")

            cnx.commit()
            logger.info("Transaction committed successfully")
            return True
        except mysql.connector.Error as err:
            logger.error(f"MySQL error in save_last_order for session {session_id}: {err}")
            cnx.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
                logger.info("Cursor closed")
    except Exception as e:
        logger.error(f"Unexpected error in save_last_order for session {session_id}: {str(e)}", exc_info=True)
        return False


def get_last_order(session_id):
    try:
        if not check_db_connection():
            logger.error("No database connection available")
            return None
        logger.info(f"Retrieving last order for session {session_id}")
        cursor = cnx.cursor(dictionary=True)
        query = "SELECT food_item, quantity FROM last_orders WHERE session_id = %s"
        cursor.execute(query, (session_id,))
        rows = cursor.fetchall()
        cursor.close()
        if not rows:
            logger.info(f"No last order found for session {session_id}")
            return None
        last_order = {row['food_item']: row['quantity'] for row in rows}
        logger.info(f"Successfully retrieved last order: {last_order}")
        return last_order
    except Exception as e:
        logger.error(f"Error retrieving last order: {e}")
        return None


def get_last_order_id(session_id):
    try:
        if not check_db_connection():
            logger.error("No database connection available")
            return None
        cursor = cnx.cursor()
        query = """
            SELECT DISTINCT o.order_id
            FROM orders o
            JOIN food_items fi ON o.item_id = fi.item_id
            WHERE fi.name IN (
                SELECT food_item
                FROM last_orders
                WHERE session_id = %s
            )
            ORDER BY o.order_id DESC
            LIMIT 1
        """
        cursor.execute(query, (session_id,))
        result = cursor.fetchone()
        cursor.close()
        order_id = result[0] if result else None
        logger.info(f"Retrieved last order_id {order_id} for session {session_id}")
        return order_id
    except Exception as e:
        logger.error(f"Error getting last order_id for session {session_id}: {e}")
        return None


def get_all_session_ids():
    try:
        if not check_db_connection():
            return []
        cursor = cnx.cursor()
        cursor.execute("SELECT DISTINCT session_id FROM last_orders")
        results = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return results
    except Exception as e:
        logger.error(f"Error getting session IDs: {str(e)}")
        return []