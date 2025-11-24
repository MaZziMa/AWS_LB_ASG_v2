"""
Dedicated Locust test focused on exercising the /cpu-burn endpoint.
Usage:
    locust -f locust_cpu.py --host=http://your-alb-dns-name.amazonaws.com
Environment overrides:
    CPU_BURN_MIN_ITERATIONS (default: 50000000)
    CPU_BURN_MAX_ITERATIONS (default: 75000000)
    CPU_BURN_WEIGHT          (default: 1)
"""
from locust import HttpUser, task, between
import os
import random


class CpuBurnUser(HttpUser):
    """Continuously issues /cpu-burn requests to stress EC2 CPU"""

    wait_time = between(0.1, 0.3)

    min_iterations = int(os.getenv("CPU_BURN_MIN_ITERATIONS", 50_000_000))
    max_iterations = int(os.getenv("CPU_BURN_MAX_ITERATIONS", 75_000_000))
    task_weight = int(os.getenv("CPU_BURN_WEIGHT", 1)) or 1

    @task(task_weight)
    def burn_cpu(self):
        """Randomize iteration count to simulate variable CPU saturation"""
        iterations = random.randint(self.min_iterations, self.max_iterations)
        params = {"iterations": iterations}
        with self.client.get("/cpu-burn", params=params, name="/cpu-burn", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"CPU burn failed: {response.status_code}")
