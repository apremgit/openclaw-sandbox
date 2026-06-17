import os
import subprocess
import sys
import time
from memory_cortex import recall_relevant_blueprints, store_blueprint

def execute_local_sandbox(script_path: str) -> Dict[str, Any]:
    """
    Executes code strictly within the local host workspace, capturing
    syntax issues and execution errors safely into an evaluation matrix.
    """
    print(f"⚙️ Running local syntax validation on {script_path}...")
    
    # Pre-validation check using python's compilation flag
    compile_check = subprocess.run([sys.executable, "-m", "py_compile", script_path], 
                                   capture_output=True, text=True)
    
    if compile_check.returncode != 0:
        return {"success": False, "error_log": compile_check.stderr, "phase": "COMPILATION"}
        
    # Run the script and collect stdout/stderr outputs
    print("🚀 Launching execution loop...")
    run_check = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    
    if run_check.returncode != 0:
        return {"success": False, "error_log": run_check.stderr, "phase": "RUNTIME"}
        
    return {"success": True, "output_log": run_check.stdout, "phase": "EXECUTION"}

def run_self_improvement_cycle(task_intent: str, filename: str):
    """
    Main autonomous reasoning loop. It pulls past blueprints, checks execution,
    and saves successful code patterns directly as local skills.
    """
    print(f"\n⚡ TARGET GOAL: {task_intent}")
    
    # 1. Look up past memories to find existing constraints
    memories = recall_relevant_blueprints(task_intent, limit=1)
    constraints = ""
    if memories:
        constraints = f"Incorporate past successful constraints: {memories[0]['rules']}"
        print(f"💡 Extracted matching local context pattern: {memories[0]['category']}")

    # 2. Simulated Local Reasoning Mock Generation (This maps to your orchestrator loop)
    # For testing, we create a script that tracks infrastructure metrics locally
    test_code = """
import os
print("Analyzing local cluster logs matrix...")
# Dynamic token check simulation
if 'GEMINI_API_KEY' in os.environ:
    print("Token handler: SECURE [Masked Status]")
else:
    print("Token handler: UNSET")
"""
    
    filepath = os.path.join(os.getcwd(), filename)
    with open(filepath, "w") as f:
        f.write(test_code.strip())
        
    # 3. Local Evaluation Loop
    result = execute_local_sandbox(filepath)
    
    if result["success"]:
        print("✅ Local Execution Evaluation Passed perfectly.")
        # Automatically store the pattern as an active local skill!
        store_blueprint(
            category="validated_local_skill",
            intent=task_intent,
            rules=f"Code verified cleanly on local host. Verified metrics logic output: {result['output_log'].strip()}",
            title=filename.replace(".py", "")
        )
    else:
        print(f"❌ Auto-Correction Triggered! Failed at phase [{result['phase']}]")
        print(f"Error Logs Extracted:\n{result['error_log']}")
        print("Routing error logs back to OpenRouter reasoning models for structural fine-tuning adjustments...")

if __name__ == "__main__":
    # Seed a self-improving trial task
    run_self_improvement_cycle(
        task_intent="Analyze infrastructure cluster memory usage and verify local API token safety masks",
        filename="local_infra_monitor.py"
    )
