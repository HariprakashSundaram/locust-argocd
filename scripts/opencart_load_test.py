from locust import HttpUser, task, between


class OpenCartLoadTest(HttpUser):
    """Load test for OpenCart - Open Source E-commerce Platform"""
    wait_time = between(1, 4)
    
    def on_start(self):
        """Execute on user start"""
        pass
    
    @task(3)
    def browse_categories(self):
        """Browse product categories"""
        self.client.get("/index.php?route=product/category&path=20")
    
    @task(2)
    def search_products(self):
        """Search for products"""
        self.client.get("/index.php?route=product/search&search=laptop")
    
    @task(2)
    def product_details(self):
        """View product detail page"""
        self.client.get("/index.php?route=product/product&product_id=28")
    
    @task(1)
    def add_to_cart(self):
        """Add product to shopping cart"""
        self.client.post("/index.php?route=checkout/cart/add", 
                        {"product_id": 28, "quantity": 1})
    
    @task(1)
    def view_cart(self):
        """View shopping cart"""
        self.client.get("/index.php?route=checkout/cart")
    
    @task(1)
    def checkout(self):
        """Proceed to checkout"""
        self.client.get("/index.php?route=checkout/checkout")
    
    @task(2)
    def homepage(self):
        """Visit store homepage"""
        self.client.get("/")
