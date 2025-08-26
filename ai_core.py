import os
import uuid
import requests
import base64
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

try:
    client = AsyncOpenAI()
except Exception as e:
    print(f"Error al inicializar OpenAI: {e}")
    client = None

ChatMessage = Dict[str, str]

async def create_prompt_from_image(user_text: str, image_bytes: bytes) -> str:
    """
    Usa GPT-4o para analizar una imagen y un texto, y crear un prompt detallado para DALL-E.
    """
    if not client:
        return "Error: Cliente de IA no configurado."

    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    system_prompt = """
    Eres un 'mejorador de prompts' para un generador de imágenes de IA. 
    Tu tarea es analizar la imagen y el texto del usuario. 
    Primero, describe la imagen que ves con el mayor detalle posible: el sujeto, los colores, el estilo artístico, la composición.
    Luego, integra la solicitud del usuario para modificar o añadir elementos a esa descripción.
    El resultado final debe ser un único párrafo, un prompt de texto muy detallado y optimizado para DALL-E 3.
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500 
        )
        detailed_prompt = response.choices[0].message.content.strip()
        print(f"Prompt mejorado por GPT-4o: {detailed_prompt}")
        return detailed_prompt
    except Exception as e:
        print(f"Error al analizar la imagen con GPT-4o: {e}")
        return f"Error al analizar la imagen: {e}"

async def classify_intent(user_question: str) -> str:
    if not client: return "chat"
    system_prompt = "Tu única tarea es clasificar la intención del usuario. Responde únicamente con 'chat' o 'image'."
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0, max_tokens=5
        )
        intent = response.choices[0].message.content.strip().lower()
        if intent in ["image", "chat"]:
            print(f"Intención clasificada como: '{intent}'")
            return intent
        return "chat"
    except Exception as e:
        print(f"Error al clasificar la intención: {e}")
        return "chat"

async def generate_character_response(
    persona_prompt: str, chat_history: List[ChatMessage],
    episode_context: str, user_question: str
) -> str:
    if not client: return "Miau... (Error: el cliente de IA no está configurado)."
    system_prompt = f"{persona_prompt}\nTu objetivo es responder como el personaje. Contexto: {episode_context if episode_context else 'N/A'}"
    messages = [{"role": "system", "content": system_prompt}, *chat_history, {"role": "user", "content": user_question}]
    try:
        response = await client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.7, max_tokens=200)
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error en la API de OpenAI (Chat): {e}")
        return "Miau... (Tuve un problema para pensar)."

async def generate_visual_image(prompt: str) -> str:
    if not client: raise Exception("El cliente de IA no está configurado.")
    print(f"Generando imagen para el prompt: {prompt}")
    try:
        response = await client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024", quality="standard")
        image_url = response.data[0].url
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        save_dir = "generated_images"
        os.makedirs(save_dir, exist_ok=True)
        file_name = f"{uuid.uuid4()}.png"
        file_path = os.path.join(save_dir, file_name)
        with open(file_path, "wb") as f: f.write(image_response.content)
        print(f"Imagen guardada en: {file_path}")
        return file_path
    except Exception as e:
        print(f"Error en DALL-E o al descargar: {e}")
        return "Miau... (Lo siento, no pude dibujar eso. Revisa el log para más detalles)."