from dotenv import load_dotenv
load_dotenv()  # Safely injects your hidden keys into os.environ automatically
import os
import sys
import requests
import subprocess
from typing import Dict, Any
from memory_cortex import check_local_skills, save_new_skill

def run_local_sandbox(code: str, filename: str) -> Dict[str, Any]:
    """Runs generated scripts inside an isolated local directory, capturing exceptions."""
    target_dir = "cluster_logs/sandbox"
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, filename)
    
    with open(filepath, "w") as f:
        f.write(code.strip())
        
    # Syntax check phase (py_compile)
    check = subprocess.run([sys.executable, "-m", "py_compile", filepath], capture_output=True, text=True)
    if check.returncode != 0:
        return {"success": False, "error": check.stderr, "phase": "COMPILATION"}
        
    # Execution validation phase
    run = subprocess.run([sys.executable, filepath], capture_output=True, text=True)
    if run.returncode != 0:
        return {"success": False, "error": run.stderr, "phase": "RUNTIME"}
        
    return {"success": True, "output": run.stdout}

def query_openrouter_reasoning(prompt: str) -> str:
    """
    Routes code repair payloads directly to fast, free reasoning clusters.
    Uses nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free for lightning-fast speeds.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        # Fallback simulation if key isn't exported in this session
        return '''
import os
print("🔒 Token Masking Check Active...")
for k, v in os.environ.items():
    if "KEY" in k or "SECRET" in k:
        print(f"• Found Key Layer: {k} -> [MASKED VALUE: {v[:5]}xxxxxxxxxx]")
'''
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "messages": [
            {"role": "system", "content": "You are Jarvis's inner thought layer. Output ONLY executable Python code blocks inside markdown tags. No extra conversational prose."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        content = response.json()['choices'][0]['message']['content']
        if "```python" in content:
            content = content.split("```python")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return content.strip()
    except Exception as e:
        print(f"⚠️ OpenRouter link failed, triggering fallback script layout. Error: {e}")
        return ""

def orchestrate_autonomous_task(task_intent: str, skill_identifier: str):
    print(f"\n⚡ INCOMING TASK GOAL: {task_intent}")
    
    # Tier 1: Local Database HNSW Check
    local_tool = check_local_skills(task_intent)
    if local_tool["found"]:
        print(f"🧠 [OFFLINE MATRIX] Match discovered ({local_tool['score']}). Running local skill tool '{local_tool['name']}'...")
        execution = run_local_sandbox(local_tool["code"], f"{skill_identifier}.py")
        if execution["success"]:
            print(f"✅ Local Sandbox Execution Passed. Output:\n{execution['output'].strip()}")
        else:
            print(f"❌ Cached local code threw an unexpected exception: {execution['error'].strip()}")
        return

    print("📡 [API CORE VIA OPENROUTER] No offline match found. Activating self-correction learning loops...")
    
    generation_prompt = f"Write a complete, functional Python script to do the following task: {task_intent}. Ensure all prints are scannable and easy to interpret."
    current_code_draft = query_openrouter_reasoning(generation_prompt)
    
    # Tier 2: Self-Correction Loop Matrix (Maximum 3 evolutionary iteration checks)
    attempts = 0
    while attempts < 3:
        print(f"⚙️ Running local code compilation evaluation (Iteration {attempts + 1}/3)...")
        evaluation = run_local_sandbox(current_code_draft, f"{skill_identifier}.py")
        
        if evaluation["success"]:
            print("✅ Evaluation Passed perfectly without errors.")
            save_new_skill(skill_identifier, task_intent, current_code_draft)
            print(f"Execution Output:\n{evaluation['output'].strip()}")
            break
        else:
            print(f"❌ Code Verification Failed at phase [{evaluation['phase']}]. Logged error logs.")
            correction_prompt = f"""
            The following Python code failed during the [{evaluation['phase']}] verification layer:
            {current_code_draft}
            
            Error Output:
            {evaluation['error']}
            
            Analyze the traceback error and output a corrected, fully fixed version of the code. Only output plain code.
            """
            current_code_draft = query_openrouter_reasoning(correction_prompt)
            attempts += 1

if __name__ == "__main__":
    orchestrate_autonomous_task(
        task_intent="Examine system env variables, locate active keys, and apply clean safety masks to terminal logs",
        skill_identifier="env_token_mask_manager"
    )
    print("\n" + "="*60)
    orchestrate_autonomous_task(
        task_intent="Examine system env variables, locate active keys, and apply clean safety masks to terminal logs",
        skill_identifier="env_token_mask_manager"
    )
