from memory_cortex import store_blueprint

print("Seeding long-term memory with elite automation blueprints...")

# Blueprint 1: Secure CAN-bus and OBD2 Subprocess Isolation
store_blueprint(
    category="hardware_isolation",
    intent="Initialize CAN-bus socket monitoring loop and parse raw OBD2 execution streams",
    rules="Always force strict read-only bitmasks on the CAN interface socket. Implement non-blocking polling loops using select() to guarantee the core Python agent loop never stalls on physical hardware timeouts.",
    title="canbus_obd2_monitoring"
)

# Blueprint 2: AWS IAM & Privilege Escalation Boundary Enforcement
store_blueprint(
    category="aws_security",
    intent="Generate an isolated IAM Role policy string with maximum permission boundary enforcement",
    rules="Never hardcode access keys. Enforce strict dynamic assume-role mappings. Explicitly block wildcard (*) administrative actions on production resource segments by default.",
    title="aws_iam_boundary_enforcement"
)

# Blueprint 3: Auto-Trading API Failure Strategy
store_blueprint(
    category="trading_automation",
    intent="Execute automated algorithmic options order execution via live broker API layers",
    rules="Implement strict token rotation hooks and immediate circuit-breakers for HTTP 429 rate blocks. Always parse incoming Telegram signal payloads into clean JSON structures before parsing variables to Angel One or Dhan endpoints.",
    title="trading_api_circuit_breaker"
)

print("🎉 Seeding complete! HNSW graph layers are loaded.")
