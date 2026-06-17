import os
import time
import json
import re
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

PERFORMANCE_FILE = "cluster_logs/performance_ledger.json"
ENV_MANIFEST = "config/environments.json"

def load_active_environment(env_name="dev"):
    try:
        with open(ENV_MANIFEST, "r") as f:
            manifest = json.load(f)
        return env_name, manifest.get("environments", {}).get(env_name, {})
    except FileNotFoundError:
        return env_name, { "mode": "sandbox", "debug": True }

def load_prompt_from_file(file_path="input_prompt.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"❌ Error: '{file_path}' not found.")
        exit(1)

def save_model_output(model_id, content):
    os.makedirs("cluster_logs/responses", exist_ok=True)
    safe_filename = model_id.replace("/", "_").replace(":", "_") + ".txt"
    path = os.path.join("cluster_logs/responses", safe_filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def deploy_to_environment(target_env, filename, code_content):
    env_dir = f"environments/{target_env}"
    os.makedirs(env_dir, exist_ok=True)
    if "```python" in code_content:
        code_content = re.search(r"```python(.*?)```", code_content, re.DOTALL).group(1).strip()
    elif "```" in code_content:
        code_content = re.search(r"```(.*?)```", code_content, re.DOTALL).group(1).strip()
    dest_path = os.path.join(env_dir, filename)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(code_content)
    print(f"🚀 [Module A Deployment]: Automated source snapshot pushed to -> {dest_path}")

def load_performance_history():
    if os.path.exists(PERFORMANCE_FILE) and os.path.getsize(PERFORMANCE_FILE) > 0:
        try:
            with open(PERFORMANCE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def update_performance_ledger(winner_id, reasoning, cluster_metrics):
    """Saves wins along with real generation speed records."""
    ledger = load_performance_history()
    
    for model, metrics in cluster_metrics.items():
        if model not in ledger:
            ledger[model] = {"wins": 0, "total_runs": 0, "tokens_per_sec": 0.0, "last_reasoning": ""}
        
        ledger[model]["total_runs"] += 1
        # Update running average of generation hardware speed
        if metrics["tokens_per_sec"] > 0:
            current_avg = ledger[model].get("tokens_per_sec", 0.0)
            if current_avg == 0:
                ledger[model]["tokens_per_sec"] = metrics["tokens_per_sec"]
            else:
                ledger[model]["tokens_per_sec"] = round((current_avg + metrics["tokens_per_sec"]) / 2, 2)
                
    if winner_id in ledger:
        ledger[winner_id]["wins"] += 1
        ledger[winner_id]["last_reasoning"] = reasoning
        
    with open(PERFORMANCE_FILE, "w") as f:
        json.dump(ledger, f, indent=4)

def get_all_ui_free_models():
    return [
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "google/gemma-4-26b-a4b-it:free",
        "google/gemma-4-31b-it:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
        "liquid/lfm-2.5-1.2b-thinking:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "nex-agi/nex-n2-pro:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "nvidia/nemotron-3.5-content-safety:free",
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "nvidia/nemotron-nano-9b-v2:free",
        "openai/gpt-oss-120b:free",
        "openai/gpt-oss-20b:free",
        "poolside/laguna-m.1:free",
        "poolside/laguna-xs.2:free",
        "qwen/qwen3-coder:free",
        "qwen/qwen3-next-80b-a3b-instruct:free"
    ]

def ask_model(model_id, user_prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": user_prompt}]
    }
    start = time.time()
    try:
        res = requests.post(url, headers=HEADERS, json=data, timeout=30)
        duration = time.time() - start
        
        if res.status_code == 429:
            return "Error: Rate Limit", 0.0
            
        res_json = res.json()
        if 'choices' in res_json and len(res_json['choices']) > 0:
            output = res_json['choices'][0]['message']['content'] or ""
            
            # Extract actual hardware usage parameters from OpenRouter
            usage = res_json.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            
            # Compute real token throughput speed
            tps = round(completion_tokens / duration, 2) if completion_tokens > 0 else 0.0
            
            if output and "Error:" not in output:
                save_model_output(model_id, output)
            return output, tps
            
        return f"Error: Format -> {res_json}", 0.0
    except Exception as e:
        return f"Error: Request failed ({str(e)})", 0.0

def evaluate_with_direct_gemini(user_prompt, model_outputs, active_env_meta):
    if not GEMINI_API_KEY:
        return {"best_model": list(model_outputs.keys())[0], "reasoning": "Missing key."}

    client = genai.Client(api_key=GEMINI_API_KEY)
    valid_outputs = {k: v for k, v in model_outputs.items() if v is not None and "Error:" not in str(v)}
    
    if not valid_outputs:
        return {"best_model": None, "reasoning": "All checked endpoints failed."}
        
    history = load_performance_history()
    formatted_outputs = ""
    for model, output in valid_outputs.items():
        formatted_outputs += f"--- MODEL: {model} ---\n{output}\n\n"
        
    evaluation_prompt = f"""
    You are the head of the G-Stack Matrix.
    Target Environment Metadata: {json.dumps(active_env_meta)}
    Task: \"\"\"{user_prompt}\"\"\"
    History: {json.dumps(history)}
    Outputs: {formatted_outputs}
    
    Instructions: Choose the winning model string based on code quality and depth. Return JSON only:
    {{
        "best_model": "exact_winning_model_id",
        "reasoning": "Engineering code rationale breakdown."
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=evaluation_prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text)
    except Exception as e:
        return {"best_model": list(valid_outputs.keys())[0], "reasoning": f"Error: {e}"}

if __name__ == "__main__":
    env_name, env_meta = load_active_environment("dev")
    print(f"🌍 Running Evaluation Matrix for layer target -> [{env_name.upper()}]")
    print("-" * 70)

    payload = load_prompt_from_file("input_prompt.txt")
    all_free_models = get_all_ui_free_models()
    
    cluster_results = {}
    cluster_metrics = {}
    
    print(f"🚀 Processing payload tasks across the grid...")
    for model in all_free_models:
        print(f"  -> {model}")
        output, tps = ask_model(model, payload)
        cluster_results[model] = output
        cluster_metrics[model] = {"tokens_per_sec": tps}
        time.sleep(1.5)
        
    print("\n🧠 Streaming outputs to Google Stack matrix judge...")
    decision = evaluate_with_direct_gemini(payload, cluster_results, env_meta)
    
    winning_model = decision.get('best_model')
    winning_reasoning = decision.get('reasoning')
    
    update_performance_ledger(winning_model, winning_reasoning, cluster_metrics)
    
    print("\n" + "="*24 + " MATRIX EVALUATION STATUS " + "="*24)
    print(f"🏆 Winning Model Set: {winning_model}")
    print(f"📝 Evaluation Logic: {winning_reasoning}")
    
    if winning_model and cluster_results.get(winning_model):
        deploy_to_environment(env_name, "verified_script.py", cluster_results[winning_model])
        
    print("="*65 + "\n")
