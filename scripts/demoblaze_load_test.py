from locust import HttpUser, task, between


class DemoBlazeLoadTest(HttpUser):
    """Load test for DemoBlaze - E-commerce Demo Site"""
    wait_time = between(2, 5)
    
    def on_start(self):
        """Execute on user start"""
        pass
    
    @task(3)
    def browse_products(self):
        """Browse product categories"""
        categories = [1, 2, 3, 4]  # Electronics, Laptops, Monitors, Phones
        self.client.get(f"/product/{categories[0]}")
    
    @task(2)
    def view_product_detail(self):
        """View individual product details"""
        self.client.get("/prod?idp_=1")
    
    @task(1)
    def add_to_cart(self):
        """Simulate adding to cart"""
        self.client.post("/", {"cart_product": "1"})
    
    @task(1)
    def view_cart(self):
        """View shopping cart"""
        self.client.get("/cart.html")
    
    @task(2)
    def homepage(self):
        """Visit homepage"""
        self.client.get("/")
