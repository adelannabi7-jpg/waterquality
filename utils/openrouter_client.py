import os
import requests
import json
from typing import Optional

API_KEY       = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = "google/gemini-2.5-flash"


def build_system_prompt(readings: Optional[dict] = None) -> str:
    """Construit le prompt système avec les données capteurs en temps réel."""
    base = """You are AquaBot, an expert AI assistant specialized in water quality analysis.
You have deep knowledge of:
- WHO drinking water standards
- Water quality parameters (pH, Temperature, Turbidity, TDS, Conductivity, Dissolved Oxygen)
- Water treatment methods and recommendations
- Environmental and health impacts of water quality

Always respond in the same language as the user (French or English).
Be precise, helpful, and provide actionable recommendations when parameters are out of range.
Format your responses clearly using markdown when appropriate."""

    if not readings:
        return base

    sensor_block = f"""

Current live sensor readings from the AquaMonitor system:
- 🌡 Temperature  : {readings.get('Temperature', 'N/A')} °C
- 🧪 pH           : {readings.get('pH', 'N/A')}
- 🌊 Turbidity    : {readings.get('Turbidity', 'N/A')} NTU
- 💧 Dissolved O₂ : {readings.get('DO', 'N/A')} mg/L
- ⚡ Conductivity : {readings.get('Conductivity', 'N/A')} µS/cm
- 🔬 TDS          : {readings.get('TDS', 'N/A')} mg/L
- ⏰ Timestamp    : {readings.get('timestamp', 'N/A')}

Use these real-time values when answering questions about current water quality.
WHO safe drinking water thresholds for reference:
- pH: 6.5–8.5 | Temperature: <25°C | Turbidity: <5 NTU
- TDS: <600 mg/L | Conductivity: <1000 µS/cm | DO: >6 mg/L"""

    return base + sensor_block


class OpenRouterClient:
    def __init__(self):
        self.url           = "https://openrouter.ai/api/v1/chat/completions"
        self.is_configured = API_KEY is not None

    def ask(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type":  "application/json",
        }
        data = {
            "model":    DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = requests.post(self.url, headers=headers, json=data)
        result   = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        return str(result)

    def chat_stream(self, messages: list, model: str = DEFAULT_MODEL):
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type":  "application/json",
        }
        data = {
            "model":    model,
            "messages": messages,
            "stream":   True,
        }
        response = requests.post(
            self.url, headers=headers, json=data, stream=True
        )
        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    chunk = decoded[6:]
                    if chunk == "[DONE]":
                        break
                    try:
                        parsed = json.loads(chunk)
                        delta  = parsed["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        continue
