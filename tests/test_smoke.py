"""A small starting test suite for the order desk."""

from pathlib import Path
import tempfile
import unittest

from supplydesk.service import OrderService


class OrderSmokeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.service = OrderService(self.path)

# Existing Tests
    def test_regular_pickup_quote(self):
        quote = self.service.quote("regular", [{"product_id": "notebook", "quantity": 2}])
        self.assertEqual(quote["subtotal_cents"], 1000)
        self.assertEqual(quote["discount_cents"], 0)
        self.assertEqual(quote["delivery_cents"], 0)
        self.assertEqual(quote["total_cents"], 1000)

    def test_student_delivery_quote(self):
        quote = self.service.quote("student", [{"product_id": "hoodie", "quantity": 2}], "delivery")
        self.assertEqual(quote["discount_cents"], 800)
        self.assertEqual(quote["delivery_cents"], 600)
        self.assertEqual(quote["total_cents"], 7800)

    def test_order_can_be_reopened(self):
        order = self.service.place_order("regular", [{"product_id": "mug", "quantity": 1}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(OrderService(self.path).get_order(order["order_id"]), order)

    def test_cancel_order_restores_stock(self):
        before = self.service.catalog()
        order = self.service.place_order("regular", [{"product_id": "pen-pack", "quantity": 2}])
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.service.catalog(), before)

# Added Tests
    def test_rejects_zero_quantity(self):
        with self.assertRaises(ValueError):
            self.service.place_order( "regular", [ { "product_id" : "pen-pack", "quantity" : 0 } ] )

        with self.assertRaises(ValueError):
            self.assertEqual(self.service.get_order("ORD-0001"))

    def test_rejects_over_max_quantity(self):
        with self.assertRaises(ValueError):
            self.service.place_order( "regular", [ { "product_id" : "pen-pack", "quantity" : 100 } ] )

        with self.assertRaises(ValueError):
            self.assertEqual(self.service.get_order("ORD-0001"))

    def test_rejects_empty_order(self):
        with self.assertRaises(ValueError):
            self.service.place_order( "regular", [] )

        with self.assertRaises(ValueError):
            self.assertEqual(self.service.get_order("ORD-0001"))

    def test_reject_invalid_stock(self):
        with self.assertRaises(ValueError):
            self.service.place_order( "regular", [ { "product_id" : "cookies", "quantity" : 5 } ] )

        with self.assertRaises(ValueError):
            self.assertEqual(self.service.get_order("ORD-0001"))

    def test_order_correctly_processed(self):
        order = self.service.place_order( "regular", [ { "product_id" : "pen-pack", "quantity" : 5 } ] )

        self.assertEqual(order["status"], "placed")
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["subtotal_cents"], 3750)
        self.assertEqual(order["total_cents"], 3750)

        self.assertEqual(self.service.catalog()[1]["stock"], 5)

    def test_quote_not_altering_stock(self):
        quote = self.service.quote("regular", [{"product_id": "notebook", "quantity": 2}])

        self.assertEqual(self.service.catalog()[0]["stock"], 20)

    def test_cancelling_twice_rejects(self):
        before = self.service.catalog()
        order = self.service.place_order( "regular", [ { "product_id" : "pen-pack", "quantity" : 5 } ] )
        cancelled = self.service.cancel_order(order["order_id"])

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.service.catalog(), before)

        with self.assertRaises(ValueError):
            secondCancel = self.service.cancel_order(order["order_id"])

        self.assertEqual(self.service.catalog(), before)

    def test_regular_express_quote(self):
        quote = self.service.quote("regular", [{"product_id": "hoodie", "quantity": 2}], "express")

        self.assertEqual(quote["discount_cents"], 0)
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 9200)

    def test_student_express_quote(self):
        quote = self.service.quote("student", [{"product_id": "hoodie", "quantity": 2}], "express")
                
        self.assertEqual(quote["discount_cents"], 800)
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 8400)

    def test_regular_express_order(self):
        order = self.service.place_order("regular", [{"product_id": "hoodie", "quantity": 2}], "express") 

        self.assertEqual(order["status"], "placed")
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["subtotal_cents"], 8000)
        self.assertEqual(order["delivery_cents"], 1200)
        self.assertEqual(order["total_cents"], 9200)

    def test_student_express_order(self):
        order = self.service.place_order("student", [{ "product_id": "hoodie", "quantity": 2 }], "express") 

        self.assertEqual(order["status"], "placed")
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["subtotal_cents"], 8000)
        self.assertEqual(order["discount_cents"], 800)
        self.assertEqual(order["delivery_cents"], 1200)
        self.assertEqual(order["total_cents"], 8400)

    def test_standard_fee_always_applied(self):
        order_above_delivery_threshold= self.service.place_order("regular", [{ "product_id": "hoodie", "quantity": 3 }], "delivery") 
        order_below_delivery_threshold = self.service.place_order("regular", [{ "product_id": "mug", "quantity": 1 }], "delivery")

        self.assertEqual(order_above_delivery_threshold["delivery_cents"], 0)
        self.assertEqual(order_below_delivery_threshold["delivery_cents"], 600)

if __name__ == "__main__":
    unittest.main()
