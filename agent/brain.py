import logging
from ollama import AsyncClient

logger = logging.getLogger(__name__)

async def ask_jarvis(user_message: str) -> str:
    logger.info(f"Sending to LLM: {user_message}")
    
    try:
        client = AsyncClient()
        response = await client.chat(
            model='llama3',
            messages=[
                # THE SYSTEM PROMPT: This overrides Llama 3's default training identity.
                {
                    'role': 'system', 
                    'content': 'You are Jarvis, a highly advanced personal assistant. You were built by Parth Chavan. Address the user respectfully and answer the questions asked in the best way possible, be precise and answers should not be of medium length.'
                },
                # THE USER PROMPT: The actual message you typed in the UI.
                {'role': 'user', 'content': user_message}
            ]
        )
        return response['message']['content']
    
    except Exception as e:
        logger.error(f"Brain Error: {e}")
        return "Sir, my AI core is currently offline."