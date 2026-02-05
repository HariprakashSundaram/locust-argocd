from locust import HttpUser, task, between


class GoogleLoadTest(HttpUser):
    """Load test for Google Search"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Execute on user start"""
        pass
    
    @task(2)
    def search_query(self):
        """Simulate Google search queries"""
        self.client.get("/search?q=locust+performance+testing")
    
    @task(1)
    def homepage(self):
        """Visit Google homepage"""
        self.client.get("/")
    
    @task(1)
    def images_search(self):
        """Search images on Google"""
        self.client.get("/search?q=python&tbm=isch")
