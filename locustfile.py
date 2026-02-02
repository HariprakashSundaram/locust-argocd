from locust import HttpUser, task, between

class SimpleUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def home(self):
        self.client.get("/")
