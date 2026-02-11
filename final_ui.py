#!/usr/bin/env python

"""
Production-Safe Locust Framework with Advanced Features
- Master/Worker Compatible
- Kubernetes & ArgoCD Safe
- Dynamic Scenario Selection (No File Rewrites)
- Variables, Correlations, Checks, Think Time, Pacing, Constant Throughput
"""

import time
import uuid
import logging
import re
import random
from threading import Lock
from flask import request, jsonify

from locust import HttpUser, task, between, events, LoadTestShape

# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure transaction logger for simplified logging
transaction_logger = logging.getLogger('transaction_log')
transaction_logger.setLevel(logging.INFO)
transaction_handler = logging.FileHandler('log.txt')
transaction_handler.setFormatter(logging.Formatter('%(message)s'))
transaction_logger.addHandler(transaction_handler)
transaction_logger.propagate = False  # Don't propagate to root logger

# ============================================================
# DEBUGGING MODE CONFIGURATION
# ============================================================

DEBUGGING_MODE = False  # Set to True to enable detailed logging for failures
SMOKE_MODE = False  # Set to True to run 2 users, 1 iteration, and print curl commands

# ============================================================
# UTILITY CLASSES - ADVANCED FEATURES
# ============================================================

class VariableManager:
    """Manages test data variables with different distribution patterns"""
    
    def __init__(self):
        self.variables = {}
        self.locks = {}
        self.indices = {}
        self.combination_groups = {}  # Store combination group indices
        
    def register_variable(self, name, config):
        """Register a variable with its configuration"""
        self.variables[name] = config
        self.locks[name] = Lock()
        self.indices[name] = 0
        
    def register_combination_group(self, group_name, variable_names):
        """Register a group of variables that should be used in combination"""
        self.combination_groups[group_name] = {
            "variables": variable_names,
            "index": 0,
            "lock": Lock()
        }
    
    def get_value(self, name, user_id=None):
        """Get variable value based on distribution type"""
        if name not in self.variables:
            return f"${{{name}}}"
            
        config = self.variables[name]
        var_type = config.get("type", "sequential")
        values = config.get("values", [])
        recycle = config.get("recycle_on_eof", True)
        combination_group = config.get("combination_group")  # Check if part of a combination
        
        if not values:
            return f"${{{name}}}"
        
        # Handle combination group variables
        if combination_group and combination_group in self.combination_groups:
            group = self.combination_groups[combination_group]
            with group["lock"]:
                idx = group["index"]
                if idx >= len(values):
                    if recycle:
                        idx = 0
                        group["index"] = 0
                    else:
                        raise StopIteration(f"All values for combination group {combination_group} have been used")
                value = values[idx]
                # Only increment the group index when the last variable in the group is accessed
                if name == group["variables"][-1]:
                    group["index"] += 1
                return value
        
        # Handle non-combination variables
        if var_type == "random":
            return random.choice(values)
        elif var_type == "sequential":
            with self.locks[name]:
                idx = self.indices[name]
                if idx >= len(values):
                    if recycle:
                        idx = 0
                        self.indices[name] = 0
                    else:
                        raise StopIteration(f"All values for {name} have been used")
                value = values[idx]
                self.indices[name] += 1
                return value
        elif var_type == "unique":
            with self.locks[name]:
                idx = self.indices[name]
                if idx >= len(values):
                    if not recycle:
                        raise StopIteration(f"All values for {name} have been used")
                    idx = 0
                    self.indices[name] = 0
                value = values[idx]
                self.indices[name] += 1
                return value
        
        return values[0] if values else f"${{{name}}}"


class CorrelationEngine:
    """Handles regex-based correlation for extracting and storing values"""
    
    def __init__(self):
        self.global_store = {}
        self.session_store = {}
        self.lock = Lock()
        
    def extract_and_store(self, response_text, pattern, var_name, scope="session", user_id=None):
        """Extract value using regex and store in session or global scope"""
        match = re.search(pattern, response_text)
        if match:
            value = match.group(1) if match.groups() else match.group(0)
            if scope == "global":
                with self.lock:
                    self.global_store[var_name] = value
            else:  # session scope
                if user_id not in self.session_store:
                    self.session_store[user_id] = {}
                self.session_store[user_id][var_name] = value
            return value
        return None
    
    def get_value(self, var_name, scope="session", user_id=None):
        """Retrieve stored correlation value"""
        if scope == "global":
            return self.global_store.get(var_name)
        else:
            if user_id in self.session_store:
                return self.session_store[user_id].get(var_name)
        return None


class ConstantThroughputTimer:
    """Controls request rate to achieve target requests per minute"""
    
    def __init__(self):
        self.timers = {}
        self.locks = {}
        
    def wait(self, requests_per_minute, timer_id="default"):
        """Wait to maintain constant throughput"""
        if timer_id not in self.timers:
            self.timers[timer_id] = {"last_request": 0, "count": 0}
            self.locks[timer_id] = Lock()
        
        with self.locks[timer_id]:
            target_interval = 60.0 / requests_per_minute
            current_time = time.time()
            
            if self.timers[timer_id]["last_request"] > 0:
                elapsed = current_time - self.timers[timer_id]["last_request"]
                sleep_time = max(0, target_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            self.timers[timer_id]["last_request"] = time.time()
            self.timers[timer_id]["count"] += 1

# ============================================================
# GLOBAL INSTANCES
# ============================================================

var_manager = VariableManager()
corr_engine = CorrelationEngine()
throughput_timer = ConstantThroughputTimer()

# ============================================================
# TEST DATA - VARIABLES CONFIGURATION
# ============================================================

variables = {
    # Address Read call data
    "OrderId1": {"type": "sequential", "values": ["121383715391", "122911311582", "122614965635", "122801343301", "121834134396"], "recycle_on_eof": True},
    
    # Address Create test data - All in combination to ensure row integrity
    "AddressLine1": {"type": "sequential", "combination_group": "address_data", "values": ["205 Pine Street", "607 Cherry Street", "308 Birch Street", "109 Maple Avenue", "3000 Birch Street"], "recycle_on_eof": True},
    "City": {"type": "sequential", "combination_group": "address_data", "values": ["Houston", "San Jose", "Chicago", "Phoenix", "Dallas"], "recycle_on_eof": True},
    "State": {"type": "sequential", "combination_group": "address_data", "values": ["TX", "CA", "IL", "AZ", "TX"], "recycle_on_eof": True},
    "ZIPCode": {"type": "sequential", "combination_group": "address_data", "values": ["75201", "95101", "60601", "85001", "78201"], "recycle_on_eof": True},
    "customerId": {"type": "sequential", "combination_group": "address_data", "values": ["CustId1", "CustId2", "CustId3", "CustId4", "CustId5"], "recycle_on_eof": True},
    "PhoneNumber": {"type": "sequential", "combination_group": "address_data", "values": ["721-890-9139", "597-367-2493", "293-659-1083", "813-721-3755", "933-136-6363"], "recycle_on_eof": True},
    "Email": {"type": "sequential", "combination_group": "address_data", "values": ["user1@example.com", "user2@example.com", "user3@example.com", "user4@example.com", "user5@example.com"], "recycle_on_eof": True},
    "FirstName": {"type": "sequential", "combination_group": "address_data", "values": ["John", "Jane", "Mike", "Sarah", "Tom"], "recycle_on_eof": True},
    "LastName": {"type": "sequential", "combination_group": "address_data", "values": ["Smith", "Johnson", "Williams", "Brown", "Jones"], "recycle_on_eof": True},
    
    # Random variables not part of combination
    "RandomString": {"type": "random", "values": ["A1B2", "C3D4", "E5F6", "G7H8", "I9J0"], "recycle_on_eof": True},

}

# Register all variables
for var_name, var_config in variables.items():
    var_manager.register_variable(var_name, var_config)

# Register the combination group for address data
var_manager.register_combination_group("address_data", [
    "AddressLine1", "City", "State", "ZIPCode", 
    "customerId", "PhoneNumber", "Email", "FirstName", "LastName"
])

# ============================================================

stages = [
    {"scenario": "Script_01", "script_name": "Address CRUD - READ", "duration": 1, "users": 2, "RampUp": 5},
    {"scenario": "Script_02", "script_name": "Address CRUD - CREATE", "duration": 1, "users": 2, "RampUp": 5},
]

# ============================================================
# GLOBAL SCENARIO STATE (MASTER ONLY)
# ============================================================

# Start with no scenarios active - user selects via web UI
ACTIVE_SCENARIOS = set()
SCENARIO_LOCK = Lock()

# ============================================================
# SCRIPT DEFINITIONS
# ============================================================

Script_01 = [
    {
        "transaction_name": "Address CRUD - READ",
        "method": "GET",
        "url": "http://localhost:8088/ordr/core/address-api/api/address?orderId=${OrderId1}",
        "headers": {
            "callerId": "OrderSourcing",
            "costco-env": "tst",
            "x-costco-gdx-deployment": "primary",
            "Content-Type": "application/json",
            "clientId": "OrderCreate",
            "correlationId": ""
        },
        "checks": {"status": 200},
        "constant_throughput_timer": 60
    }
]

Script_02 = [
    {
        "transaction_name": "Address CRUD - CREATE",
        "method": "POST",
        "url": "http://localhost:8088/ordr/core/address-api/api/address",
        "headers": {
            "clientId": "AddressCreate",
            "correlationId": "",
            "costco-env": "tst",
            "x-costco-gdx-deployment": "primary",
            "Content-Type": "application/json"
        },
        "body": {
            "type": "BILLING",
            "addressLine1": "${AddressLine1}",
            "city": "${City}",
            "state": "${State}",
            "zipCode": "${ZIPCode}",
            "customerId": "${customerId}",
            "dayPhone": "${PhoneNumber}",
            "emailAddress": "${Email}",
            "firstName": "${FirstName}",
            "lastName": "${LastName}",
            "country": "US",
            "countryCode": "840",
            "deliveryIndicator": "B",
            "action": "Create"
        },
        "checks": {"status": 200},
        "constant_throughput_timer": 30
    },
]

# ============================================================
# REQUEST EXECUTOR - ENHANCED WITH ALL FEATURES
# ============================================================

class RequestExecutor:
    """Executes HTTP requests with validation and correlation"""
    
    def __init__(self, client, var_manager, corr_engine, throughput_timer):
        self.client = client
        self.var_manager = var_manager
        self.corr_engine = corr_engine
        self.throughput_timer = throughput_timer
    
    def generate_curl_command(self, method, url, headers, body):
        """Generate curl command for the request in the exact format"""
        import json
        
        # Start with curl --location --request
        curl_parts = [f"curl --location --request {method} '{url}'"]
        
        # Add headers
        for key, value in headers.items():
            curl_parts.append(f"--header '{key}: {value}'")
        
        # Add body with beautified JSON
        if body:
            if isinstance(body, (dict, list)):
                # Beautify JSON with 4-space indentation
                body_str = json.dumps(body, indent=4)
                curl_parts.append(f"--data-raw '{body_str}'")
            else:
                body_str = str(body)
                curl_parts.append(f"--data-raw '{body_str}'")
        
        # Join with backslash and newline for readability
        return " \\\n".join(curl_parts)
        
    def substitute_variables(self, text, user_id):
        """Replace ${VarName} with actual values"""
        if not isinstance(text, str):
            return text
        
        pattern = r'\$\{(\w+)\}'
        
        def replacer(match):
            var_name = match.group(1)
            # Check correlation values first
            corr_value = self.corr_engine.get_value(var_name, scope="session", user_id=user_id)
            if corr_value:
                return str(corr_value)
            corr_value = self.corr_engine.get_value(var_name, scope="global")
            if corr_value:
                return str(corr_value)
            # Then check variable manager
            return str(self.var_manager.get_value(var_name, user_id))
        
        return re.sub(pattern, replacer, text)
    
    def substitute_variables_in_object(self, obj, user_id):
        """Recursively substitute variables in dict/list objects"""
        import json
        if isinstance(obj, dict):
            return {key: self.substitute_variables_in_object(value, user_id) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.substitute_variables_in_object(item, user_id) for item in obj]
        elif isinstance(obj, str):
            return self.substitute_variables(obj, user_id)
        else:
            return obj
    
    def execute_request(self, transaction_config, user_id, iteration, execute_once=False):
        """Execute a single HTTP request with all features"""
        if execute_once:
            # Once-only controller logic can be added here
            pass
        
        # Apply constant throughput timer if specified (skip in SMOKE_MODE)
        if not SMOKE_MODE and "constant_throughput_timer" in transaction_config:
            rpm = transaction_config["constant_throughput_timer"]
            timer_id = transaction_config.get("transaction_name", "default")
            self.throughput_timer.wait(rpm, timer_id)
        
        # Prepare request
        method = transaction_config.get("method", "GET").upper()
        url = self.substitute_variables(transaction_config["url"], user_id)
        headers = transaction_config.get("headers", {})
        
        # Substitute variables in headers
        processed_headers = {}
        for key, value in headers.items():
            processed_headers[key] = self.substitute_variables(str(value), user_id)
        
        # Generate unique correlationId for headers that contain correlationId
        if "correlationId" in processed_headers or "CorrelationId" in processed_headers:
            unique_correlation_id = str(uuid.uuid4())
            if "correlationId" in processed_headers:
                processed_headers["correlationId"] = unique_correlation_id
            if "CorrelationId" in processed_headers:
                processed_headers["CorrelationId"] = unique_correlation_id
        
        # Prepare body with proper variable substitution
        body = transaction_config.get("body")
        processed_body = None
        
        if body:
            if isinstance(body, (dict, list)):
                # Handle dict/list objects - substitute variables recursively
                processed_body = self.substitute_variables_in_object(body, user_id)
            else:
                # Handle string body
                processed_body = self.substitute_variables(str(body), user_id)
        
        # Print curl command in SMOKE_MODE
        if SMOKE_MODE:
            transaction_name = transaction_config.get("transaction_name", "Request")
            print("\n" + "="*80)
            print(f"SMOKE MODE - Transaction: {transaction_name}")
            print(f"User: {user_id} | Iteration: {iteration}")
            print("="*80)
            curl_cmd = self.generate_curl_command(method, url, processed_headers, processed_body)
            print("\nCURL Command:")
            print(curl_cmd)
            print("="*80 + "\n")
        
        # Extract OrderId from URL for logging
        order_id = "N/A"
        order_id_match = re.search(r'orderId=([^&\s]+)', url)
        if order_id_match:
            order_id = order_id_match.group(1)
        
        # Execute request
        transaction_name = transaction_config.get("transaction_name", "Request")
        
        with self.client.request(
            method=method,
            url=url,
            headers=processed_headers,
            json=processed_body if isinstance(processed_body, (dict, list)) else None,
            data=processed_body if isinstance(processed_body, str) else None,
            name=transaction_name,
            catch_response=True
        ) as response:
            # Log transaction details to log.txt
            # transaction_logger.info(f"Transaction: {transaction_name}, User: {user_id}, Iteration: {iteration}, OrderId: {order_id}, ResponseCode: {response.status_code}")
            
            # Perform checks
            checks = transaction_config.get("checks", {})
            
            if "status" in checks:
                expected_status = checks["status"]
                if response.status_code != expected_status:
                    response.failure(f"Status code {response.status_code} != {expected_status}")
                    
                    # Debug logging for failures
                    if DEBUGGING_MODE:
                        logger.error("="*80)
                        logger.error(f"FAILED REQUEST - {transaction_name}")
                        logger.error("="*80)
                        logger.error(f"URL: {url}")
                        logger.error(f"Method: {method}")
                        logger.error(f"Response Code: {response.status_code}")
                        logger.error(f"Expected Code: {expected_status}")
                        logger.error(f"Request Headers: {processed_headers}")
                        if body:
                            logger.error(f"Request Body: {body}")
                        logger.error(f"Response Body: {response.text[:2000]}")  # First 2000 chars
                        logger.error("="*80)
                else:
                    response.success()
            
            if "content" in checks:
                expected_content = checks["content"]
                if expected_content not in response.text:
                    response.failure(f"Content check failed: '{expected_content}' not found")
                    
                    # Debug logging for failures
                    if DEBUGGING_MODE:
                        logger.error("="*80)
                        logger.error(f"FAILED REQUEST (Content Check) - {transaction_name}")
                        logger.error("="*80)
                        logger.error(f"URL: {url}")
                        logger.error(f"Method: {method}")
                        logger.error(f"Response Code: {response.status_code}")
                        logger.error(f"Expected Content: {expected_content}")
                        logger.error(f"Request Headers: {processed_headers}")
                        if body:
                            logger.error(f"Request Body: {body}")
                        logger.error(f"Response Body: {response.text[:2000]}")
                        logger.error("="*80)
                else:
                    response.success()
            
            # Handle correlation
            if "correlations" in transaction_config:
                for corr in transaction_config["correlations"]:
                    pattern = corr.get("regex")
                    var_name = corr.get("variable")
                    scope = corr.get("scope", "session")
                    if pattern and var_name:
                        self.corr_engine.extract_and_store(
                            response.text, pattern, var_name, scope, user_id
                        )
        
        # Apply think time
        think_time = transaction_config.get("think_time", 0)
        if think_time > 0:
            time.sleep(think_time)


# ============================================================
# BASE USER CLASS
# ============================================================

class BaseAPIUser(HttpUser):
    abstract = True
    host = "http://localhost:8088"
    wait_time = between(0.1, 0.5)
    verify = False  # Disable SSL certificate verification

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable SSL verification
        self.client.verify = False
        
        # Disable SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.executor = RequestExecutor(self.client, var_manager, corr_engine, throughput_timer)
        self.user_id = id(self)
        self.script = []
        self.iteration = 0  # Track iteration count

    def on_start(self):
        self.executor = RequestExecutor(self.client, var_manager, corr_engine, throughput_timer)

    def execute_script(self):
        """Execute all transactions in the script"""
        self.iteration += 1  # Increment iteration counter
        
        # In SMOKE_MODE, stop after 1 iteration
        if SMOKE_MODE and self.iteration > 1:
            self.environment.runner.quit()
            return
        
        for transaction in self.script:
            try:
                self.executor.execute_request(transaction, self.user_id, self.iteration)
            except StopIteration:
                self.environment.runner.quit()
                break
        
        # In SMOKE_MODE, quit after completing 1 iteration
        if SMOKE_MODE:
            self.environment.runner.quit()


# ============================================================
# SCENARIO USERS
# ============================================================
class Script_01_User(BaseAPIUser):
    weight = 1

    def on_start(self):
        super().on_start()
        self.script = Script_01

    @task
    def run_script(self):
        with SCENARIO_LOCK:
            if "Script_01" not in ACTIVE_SCENARIOS:
                time.sleep(1)
                return
        self.execute_script()


class Script_02_User(BaseAPIUser):
    weight = 1

    def on_start(self):
        super().on_start()
        self.script = Script_02

    @task
    def run_script(self):
        with SCENARIO_LOCK:
            if "Script_02" not in ACTIVE_SCENARIOS:
                time.sleep(1)
                return
        self.execute_script()





# ============================================================
# CUSTOM LOAD SHAPE (STABLE VERSION)
# ============================================================
from locust import LoadTestShape
class CustomLoadShape(LoadTestShape):

    def tick(self):
        run_time = self.get_run_time()

        if SMOKE_MODE:
            if run_time < 10:
                return (2, 2)
            return None

        with SCENARIO_LOCK:
            active = ACTIVE_SCENARIOS.copy()

        if not active:
            return (0, 1)

        total_users = 0
        spawn_rate = 1

        for stage in stages:
            if stage["scenario"] in active:
                duration = stage["duration"] * 60
                ramp = stage["RampUp"]
                users = stage["users"]

                if run_time < ramp:
                    current = int((run_time / ramp) * users)
                elif run_time < duration:
                    current = users
                else:
                    continue

                total_users += current
                spawn_rate = max(spawn_rate, users / ramp if ramp > 0 else users)

        return total_users, spawn_rate

# ============================================================
# UI EXTENSION – SCENARIO SELECTOR
# ============================================================

@events.init.add_listener
def add_scenario_selector(environment, **kwargs):

    if not environment.web_ui:
        return

    @environment.web_ui.app.route("/scenario_selector")
    def scenario_selector():

        scenario_list = sorted(set(stage["script_name"] for stage in stages))

        with SCENARIO_LOCK:
            active = ACTIVE_SCENARIOS.copy()

        # Build Stage Table Rows
        table_rows = ""
        for stage in stages:
            table_rows += f"""
            <tr>
                <td>{stage.get("scenario")}</td>
                <td>{stage.get("script_name", "N/A")}</td>
                <td>{stage.get("duration")} min</td>
                <td>{stage.get("users")}</td>
                <td>{stage.get("RampUp")} sec</td>
            </tr>
            """

        # Build Checkbox Section - use scenario ID as value, script_name as display
        checkboxes = ""
        for stage in stages:
            scenario_id = stage["scenario"]
            script_name = stage["script_name"]
            checked = "checked" if scenario_id in active else ""
            checkboxes += f"""
                <label>
                    <input type="checkbox" value="{scenario_id}" {checked}> {script_name}
                </label><br>
            """

        return f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial;
                    padding: 40px;
                    background: #f4f6f9;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 30px;
                    background: white;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                    text-align: center;
                }}
                th {{
                    background-color: #2d8cff;
                    color: white;
                }}
                tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
                button {{
                    padding: 10px 20px;
                    background-color: #2d8cff;
                    color: white;
                    border: none;
                    cursor: pointer;
                    font-size: 14px;
                }}
                button:hover {{
                    background-color: #1a6fd9;
                }}
            </style>
        </head>
        <body>

        <h2>Stage Configuration</h2>

        <table>
            <thead>
                <tr>
                    <th>Scenario</th>
                    <th>Script Name</th>
                    <th>Duration</th>
                    <th>Users</th>
                    <th>RampUp</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>

        <h2>Select Scenarios to Run</h2>

        {checkboxes}

        <br><br>

        <button onclick="save()">Apply Selection</button>

        <script>
        async function save() {{
            let selected = Array.from(
                document.querySelectorAll("input[type=checkbox]:checked")
            ).map(x => x.value);

            let res = await fetch("/apply_scenarios", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ selected }})
            }});

            let data = await res.json();
            alert(JSON.stringify(data));
            
            // Redirect to home page after applying selection
            window.location = "http://localhost:8089/";
        }}
        </script>

        </body>
        </html>
        """

    @environment.web_ui.app.route("/apply_scenarios", methods=["POST"])
    def apply_scenarios():

        data = request.get_json()
        selected = set(data.get("selected", []))

        if not selected:
            return jsonify({"success": False, "error": "Select at least one scenario"})

        with SCENARIO_LOCK:
            ACTIVE_SCENARIOS.clear()
            ACTIVE_SCENARIOS.update(selected)

        logger.info(f"Active scenarios updated: {ACTIVE_SCENARIOS}")

        return jsonify({"success": True, "active": list(ACTIVE_SCENARIOS)})
