"""Operations used by the command-line order desk."""

from supplydesk.storage import JsonStore

MIN_ORDER_QUANTITY = 1
MAX_ORDER_QUANTITY = 99

STUDENT_DISCOUNT_THRESHOLD = 5000 # In Cents
FREE_DELIVERY_THRESHOLD = 10000 # In Cents

DELIVERY_FEE = 600
EXPRESS_FEE = 1200
STUDENT_DISCOUNT = 10
ROUNDING_ADJUSTMENT = 50
PERCENTAGE_DIVISOR = 100

class OrderService:
    def __init__(self, state_path=".supplydesk/state.json"):
        self.store = JsonStore(state_path)

    def catalog(self):
        return self.store.load()["catalog"]

    def calculate_discount(self, subtotal, customer_type):
        if customer_type == "student" and subtotal > STUDENT_DISCOUNT_THRESHOLD:
            return (subtotal * STUDENT_DISCOUNT + ROUNDING_ADJUSTMENT) // PERCENTAGE_DIVISOR
        return 0

    def calculate_delivery_fee(self, fulfillment, subtotal, discount):
        if fulfillment == "delivery" and subtotal - discount < FREE_DELIVERY_THRESHOLD:
            return DELIVERY_FEE
        elif fulfillment == "express":
            return EXPRESS_FEE
        return 0

    def calculate_express_fee(self, fulfillment):
        if fulfillment == "express":
            return EXPRESS_FEE
        return 0

    def validate_quantity(self, min_quantity, max_quantity, quantity, product):
        if type(quantity) is not int or quantity < min_quantity or quantity > max_quantity:
            raise ValueError(f"Quantity must be an integer from { min_quantity } to { max_quantity }.")
        if quantity > product["stock"]:
            raise ValueError("Not enough stock for " + product["product_id"] + ".")

    def validate_customer_and_fulfillment(self, customer_type, items, fulfillment):
        if customer_type not in ("regular", "student"):
            raise ValueError("Customer type must be regular or student.")
        if fulfillment not in ("pickup", "delivery", "express"):
            raise ValueError("Fulfillment must be pickup, delivery or express.")
        if not isinstance(items, list) or not items:
            raise ValueError("An order must contain at least one item.")

    def calculate_and_return_order(self, customer_type, items, fulfillment="pickup"):
        state = self.store.load()

        self.validate_customer_and_fulfillment(customer_type, items, fulfillment)
       
        lines = []
        subtotal = 0
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each item must contain a product_id and quantity.")
            product = None
            for candidate in state["catalog"]:
                if candidate["product_id"] == item.get("product_id"):
                    product = candidate
                    break
            if product is None:
                raise ValueError("Unknown product.")
            quantity = item.get("quantity")

            self.validate_quantity(MIN_ORDER_QUANTITY, MAX_ORDER_QUANTITY, quantity, product)

            line_total = product["unit_price_cents"] * quantity
            subtotal += line_total
            lines.append({
                "product_id": product["product_id"],
                "name": product["name"],
                "unit_price_cents": product["unit_price_cents"],
                "quantity": quantity,
                "line_total_cents": line_total,
            })

        discount = self.calculate_discount(subtotal, customer_type)
        delivery = self.calculate_delivery_fee(fulfillment, subtotal, discount)

        return {
            "customer_type": customer_type,
            "fulfillment": fulfillment,
            "items": lines,
            "subtotal_cents": subtotal,
            "discount_cents": discount,
            "delivery_cents": delivery,
            "total_cents": subtotal - discount + delivery,
        }, state

    def quote(self, customer_type, items, fulfillment="pickup"):
        quote, state = self.calculate_and_return_order(customer_type, items, fulfillment)

        return quote

    def place_order(self, customer_type, items, fulfillment="pickup"):
        orderCustomer, state = self.calculate_and_return_order(customer_type, items, fulfillment)

        order = {
            "order_id": "ORD-" + str(state["next_order_number"]).zfill(4),
            "status": "placed",
            **orderCustomer
        }

        for line in order["items"]:
            for product in state["catalog"]:
                if product["product_id"] == line["product_id"]:
                    product["stock"] -= line["quantity"]
        state["next_order_number"] += 1
        state["orders"].append(order)
        self.store.save(state)
        return order

    def list_orders(self):
        return self.store.load()["orders"]

    def get_order(self, order_id):
        state = self.store.load()
        for order in state["orders"]:
            if order["order_id"] == order_id:
                return order
        raise ValueError("Unknown order: " + order_id)

    def cancel_order(self, order_id):
        state = self.store.load()
        order = None
        for candidate in state["orders"]:
            if candidate["order_id"] == order_id:
                order = candidate
                break
        if order is None:
            raise ValueError("Unknown order: " + order_id)

        if order["status"] == "cancelled":
            raise ValueError("Order Already Cancelled")
        
        for line in order["items"]:
            for product in state["catalog"]:
                if product["product_id"] == line["product_id"]:
                    product["stock"] += line["quantity"]
        order["status"] = "cancelled"
        self.store.save(state)
        return order
