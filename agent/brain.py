import logging
from ollama import AsyncClient
import agent.state as state

logger = logging.getLogger(__name__)

async def ask_jarvis(user_message: str) -> str:
    logger.info(f"Sending to LLM: {user_message}")
    
    try:
        client = AsyncClient()
        response_stream = await client.chat(
            model='llama3',
            messages=[
                {
                    'role': 'system', 
                    'content': 'You are Jarvis, a highly advanced personal assistant. You were built by Parth Chavan. Address the user respectfully and answer the questions asked in the best way possible, be precise and answers should not be of medium length.'
                },
                {'role': 'user', 'content': user_message}
            ],
            stream=True 
        )
        
        full_reply = ""
        
        # Loop through the words as they arrive in real-time
        async for chunk in response_stream:
            # THE KILL SWITCH: Did the user hit the STOP button?
            if state.interrupt_llm:
                logger.info("🛑 LLM Generation violently interrupted by user.")
                full_reply += " ... [Interrupted]"
                break # Instantly kill the stream!
                
            content = chunk['message']['content']
            full_reply += content
            
        return full_reply
    
    except Exception as e:
        logger.error(f"Brain Error: {e}")
        return "Sir, my AI core is currently offline."