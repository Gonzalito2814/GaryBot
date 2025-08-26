import os
import random
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from character_models import CharacterSheet
from sheet_reader import load_character_sheet
from episodes_db import (
    search_episodes, 
    format_citation, 
    save_message_to_history, 
    get_history_by_session,
    delete_history_by_session
)
from ai_core import classify_intent, create_prompt_from_image, generate_character_response, generate_visual_image

app = FastAPI(title="GaryBot API", version="0.1.0")

app.mount("/images", StaticFiles(directory="generated_images"), name="images")

origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True, 
    allow_methods=["*"], allow_headers=["*"]
)

class UnifiedResponse(BaseModel):
    type: str
    content: str

class ResetRequest(BaseModel):
    session_id: str

#ENDPOINTS
@app.post("/ask", response_model=UnifiedResponse)
async def unified_ask_endpoint(
    question: str = Form(...),
    session_id: str = Form(...),
    image: Optional[UploadFile] = File(None),
    character_sheet_path: str = Form("data/ficha/gary.json")
):
    raw_sheet = load_character_sheet(character_sheet_path)
    sheet = CharacterSheet(**raw_sheet)
    detailed_prompt = ""

    def get_fallback_prompt():
        print("Fallback activado: Usando descripción visual del JSON.")
        visual_desc = getattr(sheet, 'visual_description_for_ai', 'Un caracol de dibujos animados.')
        return f"{visual_desc}. {question}."

    if image:
        image_bytes = await image.read()
        detailed_prompt = await create_prompt_from_image(question, image_bytes)
        if "VISION_REJECTED" in detailed_prompt or "VISION_ERROR" in detailed_prompt:
            detailed_prompt = get_fallback_prompt()
    else:
        intent = await classify_intent(question)
        if intent == "image":
            print("Intención de imagen detectada. Construyendo prompt...")
            
            episode_context = "No hay contexto de episodio específico."
            
            generic_phrases = ["de ti", "tuya", "una imagen de gary", "una foto tuya"]
            is_generic_request = any(phrase in question.lower() for phrase in generic_phrases)
            
            if len(question.split()) > 4 and not is_generic_request:
                print("Petición específica detectada. Buscando contexto de episodio...")
                hits = search_episodes(question, limit=1)
                if hits and hits[0].get('visual_summary'):
                    ep = hits[0]
                    episode_context = f"Título del Episodio: {ep.get('title')}\nDescripción Visual de la Escena: {ep.get('visual_summary')}\nPersonajes Clave: {ep.get('key_characters')}\nObjetos/Lugares Clave: {ep.get('key_objects_locations')}"
            else:
                print("Petición genérica o corta detectada. No se usará contexto de episodio.")

            visual_desc = getattr(sheet, 'visual_description_for_ai', 'Un caracol de dibujos animados.')
            synthesis_system_prompt = "Eres un director de escena para una serie de animación. Tu tarea es sintetizar la información proporcionada para crear un único y detallado prompt visual para un artista de IA (DALL-E). Combina la descripción base del personaje, el contexto del episodio y la acción solicitada por el usuario. El resultado debe ser un párrafo descriptivo que pinte una imagen vívida de la escena completa."
            synthesis_user_prompt = f"Descripción Base del Personaje: {visual_desc}\nContexto del Episodio: {episode_context}\nAcción Solicitada por el Usuario: {question}"
            
            detailed_prompt = await generate_character_response(
                persona_prompt=synthesis_system_prompt, 
                chat_history=[],
                episode_context="", 
                user_question=synthesis_user_prompt
            )
            
        else: 
            persona_prompt = sheet.persona_prompt()
            visual_desc = getattr(sheet, 'visual_description_for_ai', '')
            full_persona_prompt = f"{persona_prompt}\n\nDescripción física detallada de ti mismo para tu referencia interna:\n{visual_desc}"
            
            hits = search_episodes(question, limit=2)
            episode_context = "\n".join([format_citation(ep) for ep in hits])
            chat_history = get_history_by_session(session_id, limit=10)
            
            ai_answer = await generate_character_response(
                persona_prompt=full_persona_prompt,
                chat_history=chat_history,
                episode_context=episode_context,
                user_question=question
            )
            save_message_to_history(session_id, "user", question)
            save_message_to_history(session_id, "assistant", ai_answer)
            return {"type": "text", "content": ai_answer}

    if "Error" in detailed_prompt:
        return {"type": "text", "content": detailed_prompt}

    path_or_error = await generate_visual_image(detailed_prompt)
    save_message_to_history(session_id, "user", question)
    save_message_to_history(session_id, "assistant_image", path_or_error)
    
    if os.path.exists(path_or_error):
        content = f"/images/{os.path.basename(path_or_error)}"
        return {"type": "image", "content": content}
    else:
        return {"type": "text", "content": path_or_error}

@app.post("/reset")
def reset_chat(request: ResetRequest):
    """
    Recibe un session_id y borra todo el historial de chat asociado.
    """
    try:
        delete_history_by_session(request.session_id)
        return {"message": f"Historial para la sesión {request.session_id} ha sido reiniciado."}
    except Exception as e:
        print(f"Error al reiniciar el historial: {e}")
        return {"message": "Error al reiniciar el historial."}