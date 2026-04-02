# agent/eyes.py
import logging
from ollama import AsyncClient

logger = logging.getLogger(__name__)

async def analyze_image(prompt: str, image_b64: str) -> str:
    """Sends a base64 image from the UI to the LLaVA vision model."""
    try:
        logger.info("Visual data received from UI. Sending to LLaVA Vision Core...")
        client = AsyncClient()
        
        # Give it a default prompt if the user just said "look"
        if prompt.lower().strip() in ["look", "look at this", "what do you see"]:
            safe_prompt = "Describe what you see in this image concisely."
        else:
            safe_prompt = prompt

        response = await client.chat(
            model='llava', # Must have LLaVA installed in Ollama!
            messages=[{
                'role': 'user',
                'content': safe_prompt,
                'images': [image_b64]
            }]
        )
        return response['message']['content']

    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return "Sir, my visual cortex encountered an error while processing the image."