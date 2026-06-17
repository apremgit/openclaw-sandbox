import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

PERFORMANCE_FILE = "cluster_logs/performance_ledger.json"

def boot_sequence():
    print("🤖 [Jarvis Subsystem]: Initializing Core Controllers...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ [Error]: OPENROUTER_API_KEY is missing from environment profiles.")
        return False
        
    print("🧠 [GBrain Status]: OpenRouter Cognitive Interface -> CONNECTED.")
    print("📊 [Metrics Matrix]: Historical Log Reader -> ACTIVE.")
    return True

def get_smart_route(metric_priority="accuracy"):
    """
    Evaluates real performance metrics from the ledger file.
    - 'accuracy': Targets the model with the highest win count from G-Stack.
    - 'speed': Targets the model with the highest historical tokens/second generation rate.
    """
    if os.path.exists(PERFORMANCE_FILE) and os.path.getsize(PERFORMANCE_FILE) > 0:
        try:
            with open(PERFORMANCE_FILE, "r") as f:
                ledger = json.load(f)
            
            best_model = None
            highest_score = -1
            
            for model_id, stats in ledger.items():
                if metric_priority == "accuracy":
                    # Rank based on direct G-Stack matrix evaluation wins
                    score = stats.get("wins", 0)
                elif metric_priority == "speed":
                    # Rank based on direct hardware throughput (tokens per second)
                    score = stats.get("tokens_per_sec", 0.0)
                else:
                    score = stats.get("wins", 0)

                if score > highest_score:
                    highest_score = score
                    best_model = model_id
            
            if best_model and highest_score > 0:
                print(f"🎯 [G-Stack Router]: Dynamic selection optimized for [{metric_priority.upper()}] -> {best_model}")
                return best_model
        except Exception as e:
            print(f"⚠️ Ledger read warning: {e}")
            
    # Premium hardware fallback if tracking metrics are initializing
    return "google/gemma-4-26b-a4b-it:free"

def query_brain(prompt, priority="accuracy"):
    api_key = os.getenv("OPENROUTER_API_KEY")
    api_base = os.getenv("GBRAIN_API_BASE", "https://openrouter.ai/api/v1")
    
    model = get_smart_route(metric_priority=priority)
    
    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://localhost:3000",
        "X-Title": "Jarvis Agent"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    start_time = time.time()
    try:
        response = requests.post(url, headers=headers, json=data)
        execution_time = time.time() - start_time
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            print(f"⚡ [Execution Metrics]: Request completed via {model} in {execution_time:.2f}s")
            return content
        else:
            return f"Error: API returned {response.status_code} - {response.text}"
    except Exception as e:
        return f"Connection Failed: {e}"

if __name__ == "__main__":
    if boot_sequence():
        print("\n⚡ Running Execution Test Task...")
        # Jarvis will now dynamically select based on speed or accuracy rules
        response = query_brain(
            prompt="Write a lightweight health check endpoint in Python using Flask.", 
            priority="accuracy"
        )
        print(f"\n📡 [Jarvis Executive Response]:\n{response}")
