import os
import time
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

def get_all_ui_free_models():
    """Aggressively captures all free models visible on the OpenRouter UI."""
    url = "https://openrouter.ai/api/v1/models"
    try:
        response = requests.get(url).json()
        raw_models = response.get('data', [])
        free_models = set()
        
        for model in raw_models:
            model_id = model.get('id', '')
            model_name = model.get('name', '').lower()
            pricing = model.get('pricing', {})
            
            # Condition 1: ID explicitly ends with :free
            if model_id.endswith(':free'):
                free_models.add(model_id)
                continue
                
            # Condition 2: Name contains '(free)' like on the UI
            if 'free' in model_name:
                free_models.add(model_id)
                continue
                
            # Condition 3: Flat zero pricing architecture
            try:
                if float(pricing.get('prompt', 1)) == 0 and float(pricing.get('completion', 1)) == 0:
                    # If it's free but doesn't have the :free suffix, use the base ID
                    free_models.add(model_id)
            except (ValueError, TypeError):
                pass
                
        return sorted(list(free_models))
        
    except Exception as e:
        print(f"❌ Error fetching models from API: {e}")
        return []

def ask_model(model_id, user_prompt):
    """Sends your prompt to a target free model."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": user_prompt}]
    }
    try:
        res = requests.post(url, headers=HEADERS, json=data, timeout=15)
        if res.status_code == 429:
            return "Error: Rate Limit Exceeded"
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"

def evaluate_with_g_stack(user_prompt, model_outputs):
    """Uses Gemini 2.5 Pro as the central judging stack to evaluate options."""
    evaluator_model = "google/gemini-2.5-pro"
    
    # Filter out models that errored or got rate-limited
    valid_outputs = {k: v for k, v in model_outputs.items() if "Error:" not in v}
    
    if not valid_outputs:
        return {"best_model": None, "reasoning": "All free models failed or were rate-limited."}
        
    formatted_outputs = ""
    for model, output in valid_outputs.items():
        formatted_outputs += f"--- MODEL: {model} ---\n{output}\n\n"
        
    evaluation_prompt = f"""
    You are the head of the Google Stack AI Evaluation matrix. 
    Review the following responses to this task: "{user_prompt}"
    
    {formatted_outputs}
    
    Determine which model executed the task with the highest structural accuracy and optimization.
    Output your decision in a clean JSON block:
    {{
        "best_model": "exact_model_id_here",
        "reasoning": "Clear professional engineering justification."
    }}
    """
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    data = {
        "model": evaluator_model,
        "response_format": { "type": "json_object" },
        "messages": [{"role": "user", "content": evaluation_prompt}]
    }
    
    try:
        res = requests.post(url, headers=HEADERS, json=data).json()
        return json.loads(res['choices'][0]['message']['content'])
    except Exception as e:
        return {"best_model": list(valid_outputs.keys())[0], "reasoning": f"G-Stack evaluation fallback: {e}"}

# --- Execution Entry Point ---
if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        print("❌ Set your OPENROUTER_API_KEY in the .env file first.")
        exit(1)

    # 1. Gather all free options matching UI visibility
    print("🔄 Scanning OpenRouter for full free tier lineup...")
    all_free_models = get_all_ui_free_models()
    print(f"✅ Successfully captured {len(all_free_models)} free endpoints from the index.\n")
    
    # Print the models so you can verify Qwen 480B and GPT-OSS are present
    for idx, m in enumerate(all_free_models, 1):
        print(f"  [{idx}] {m}")

    print("\n---------------------------------------------------------")
    
    # 2. Set your custom prompt here
    my_prompt = "Write an optimized Python script to check AWS S3 bucket public access status using boto3."
    
    results = {}
    
    # 3. Loop and evaluate
    print(f"\n🚀 Dispatching task across the cluster...")
    for model in all_free_models:
        print(f"-> Querying: {model}")
        results[model] = ask_model(model, my_prompt)
        time.sleep(1.0) # Small spacing to minimize hitting the 429 wall
        
    # 4. G-Stack Processing
    print("\n🧠 Passing raw cluster outputs to Google Stack for evaluation...")
    decision = evaluate_with_g_stack(my_prompt, results)
    
    print("\n================ FINAL G-STACK DECISION ================")
    print(f"🏆 Selected Model: {decision.get('best_model')}")
    print(f"📝 Evaluation: {decision.get('reasoning')}")
    print("========================================================\n")