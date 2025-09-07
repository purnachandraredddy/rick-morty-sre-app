"""Load testing with Locust."""
from locust import HttpUser, task, between


class RickMortyAPIUser(HttpUser):
    """Load test user for Rick and Morty API."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts."""
        # Verify the service is up
        response = self.client.get("/healthcheck")
        if response.status_code != 200:
            print(f"Health check failed: {response.status_code}")
    
    @task(3)
    def get_characters(self):
        """Get characters list - most common operation."""
        self.client.get("/characters")
    
    @task(2)
    def get_characters_paginated(self):
        """Get characters with pagination."""
        page = self.random_page()
        self.client.get(f"/characters?page={page}&per_page=10")
    
    @task(2)
    def get_characters_sorted(self):
        """Get characters with sorting."""
        sort_options = ["id", "name", "created_at"]
        order_options = ["asc", "desc"]
        
        sort = self.random_choice(sort_options)
        order = self.random_choice(order_options)
        
        self.client.get(f"/characters?sort={sort}&order={order}")
    
    @task(1)
    def get_character_by_id(self):
        """Get specific character by ID."""
        # Test with various character IDs
        character_id = self.random_character_id()
        response = self.client.get(f"/characters/{character_id}")
        
        # Log 404s for monitoring
        if response.status_code == 404:
            print(f"Character {character_id} not found")
    
    @task(1)
    def get_stats(self):
        """Get application statistics."""
        self.client.get("/stats")
    
    @task(1)
    def get_metrics(self):
        """Get Prometheus metrics."""
        self.client.get("/metrics")
    
    @task(1)
    def health_check(self):
        """Perform health check."""
        self.client.get("/healthcheck")
    
    def random_page(self):
        """Get random page number."""
        import random
        return random.randint(1, 5)
    
    def random_character_id(self):
        """Get random character ID."""
        import random
        return random.randint(1, 100)
    
    def random_choice(self, choices):
        """Make random choice from list."""
        import random
        return random.choice(choices)


class AdminUser(HttpUser):
    """Admin user for testing admin operations."""
    
    wait_time = between(5, 15)  # Longer wait times for admin operations
    weight = 1  # Lower weight - fewer admin users
    
    @task
    def trigger_sync(self):
        """Trigger manual synchronization."""
        response = self.client.post("/sync")
        if response.status_code == 200:
            print("Sync triggered successfully")
        else:
            print(f"Sync failed: {response.status_code}")


class HealthCheckUser(HttpUser):
    """User that only performs health checks."""
    
    wait_time = between(10, 30)  # Health checks every 10-30 seconds
    weight = 1  # Low weight
    
    @task
    def health_check(self):
        """Continuous health monitoring."""
        response = self.client.get("/healthcheck")
        if response.status_code != 200:
            print(f"Health check failed: {response.status_code}")


# Custom load test scenarios
class StressTestUser(HttpUser):
    """User for stress testing specific endpoints."""
    
    wait_time = between(0.1, 0.5)  # Very fast requests for stress testing
    
    @task
    def rapid_character_requests(self):
        """Rapid character requests to test rate limiting."""
        self.client.get("/characters?per_page=50")
    
    @task
    def rapid_health_checks(self):
        """Rapid health checks to test rate limiting."""
        self.client.get("/healthcheck")
