🔥 MASTER CONVERSION PROMPT

I am uploading a JMeter (.jmx) file.

Perform a full structural and semantic conversion into a production-grade distributed Locust framework using my advanced architecture.

This is NOT a basic conversion.
This must be a lossless architectural transformation preserving execution behavior, data flow, correlation logic, load modeling, and controller hierarchy.

🧠 PHASE 1 — STRUCTURAL PARSING

Parse the JMX file as a test plan AST and extract:

Test Plan

All Thread Groups

Loop Controllers

Once Only Controllers

If Controllers

Transaction Controllers

Throughput Controllers

HTTP Samplers

CSV Data Set Config

User Defined Variables

HTTP Header Managers

Cookie Managers

Cache Managers

Timers

Assertions

Regular Expression Extractors

JSON Extractors

XPath Extractors

Build an internal execution graph representing:

Parent-child hierarchy

Execution order

Conditional branches

Loop behavior

Variable dependencies

Correlation chains

🏗 PHASE 2 — ARCHITECTURAL MAPPING RULES

Apply deterministic mapping:

Thread Groups

Each Thread Group → Separate Scenario

Each Scenario → Separate Locust User Class

Preserve:

Users

Ramp-up

Duration

Loop count

Integrate into CustomLoadShape stages.

Controllers Mapping

Loop Controller → loop logic inside execute_script
Once Only Controller → execute_once flag
If Controller → conditional Python logic
Throughput Controller → weight-based distribution logic
Transaction Controller → transaction_name grouping

Preserve nesting exactly.

HTTP Samplers

Convert into structured transaction_config objects with:

method

full URL (including params)

headers (merged with header manager)

body (raw/json/form-data)

checks

think_time

constant_throughput_timer

correlation config

CSV Data Set Config

Convert into VariableManager variables:

Detect row integrity patterns

Auto-create combination_group if multiple columns represent same row

Preserve:

sharing mode

recycle_on_eof

stop_thread_on_eof

Implement thread-safe locking.

Variable Resolution Priority

Must match JMeter behavior:

Correlation (session)

Correlation (global)

CSV variables

User defined variables

Default fallback

Extractors → CorrelationEngine

Convert:

Regex Extractor

JSON Extractor

XPath Extractor

Into correlation rules:

corr_engine.extract_and_store(...)

Maintain:

match number

default value behavior

scope rules

Timers

Constant Throughput Timer → constant_throughput_timer (RPM)
Uniform Random Timer → think_time randomization
Gaussian Timer → Python random.gauss

Maintain isolation per transaction.

Assertions

Response Code Assertion → checks["status"]
Response Body Contains → checks["content"]
JSON Path Assertion → regex/json validation logic

⚙️ PHASE 3 — FRAMEWORK INTEGRATION (MANDATORY)

Output must include:

1️⃣ VariableManager

sequential

random

unique

combination_group

locking

2️⃣ CorrelationEngine

session store

global store

regex extraction

3️⃣ RequestExecutor

recursive substitution

UUID auto generation for correlationId

curl generation (SMOKE_MODE)

debug failure logging

validation

4️⃣ ConstantThroughputTimer

thread-safe

per transaction timer id

5️⃣ Scenario Selector UI

/scenario_selector

Stage table

Checkbox selection

/apply_scenarios

Master broadcast

Worker listener

6️⃣ CustomLoadShape

Ramp logic

Duration logic

Multi-scenario aggregation

Spawn rate calculation

7️⃣ Distributed Compatibility

MasterRunner support

WorkerRunner listener

Weight updates

No blocking loops

🧪 PHASE 4 — VALIDATION RULES

Before returning code, validate internally:

No duplicate functions

No blocking inside @task

No infinite loops

No broken stats UI

All scenarios toggle correctly

Worker receives broadcast

Variable resolution order correct

Correlation variables accessible across requests

🛑 STRICT RULES

Do NOT simplify architecture

Do NOT remove advanced logic

Do NOT merge scenarios

Do NOT ignore controllers

Do NOT output partial snippets

Return full working locustfile.py only

Output:

Fully production-safe locustfile.py

Clean

Optimized

Kubernetes compatible

Distributed ready
