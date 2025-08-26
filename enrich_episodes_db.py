import json
from openai import OpenAI
from dotenv import load_dotenv
from episodes_db import _connect

load_dotenv()
try:
    client = OpenAI()
except Exception as e:
    print(f"Error al inicializar OpenAI: {e}")
    client = None

def fetch_episodes_to_enrich(target_character: str = "Gary"):
    """
    (VERSIÓN MODIFICADA) Busca en la BD episodios donde un personaje específico
    es importante y que aún no han sido enriquecidos.
    """
    print(f"Buscando episodios no enriquecidos donde '{target_character}' es un personaje clave...")
    with _connect() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT id, title, summary 
                FROM episodes 
                WHERE 
                    (visual_summary IS NULL OR visual_summary = '') 
                    AND characters ILIKE %s
            """
            cur.execute(query, (f'%{target_character}%',))
            episodes = cur.fetchall()
    return episodes

def enrich_episode_with_ai(title, summary) -> dict:
    """Usa GPT-4o para extraer información visual y estructurada de un resumen."""
    if not client:
        raise Exception("Cliente de OpenAI no inicializado.")

    system_prompt = """
    Eres un analista de guiones de animación. Tu tarea es leer el título y el resumen de un
    episodio y extraer información clave en formato JSON.

    La estructura del JSON debe ser exactamente la siguiente:
    {
        "visual_summary": "Describe la escena principal o más icónica del episodio con gran detalle visual. Enfócate en la apariencia de los personajes, el entorno, los colores y la atmósfera. Esta descripción se usará para generar arte.",
        "key_characters": ["Lista de los 3-4 personajes más importantes que aparecen."],
        "key_objects_locations": ["Lista de objetos o lugares cruciales para la trama del episodio."]
    }

    Analiza el siguiente texto y genera únicamente el objeto JSON como respuesta.
    """
    
    user_content = f"Título: {title}\nResumen: {summary}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        extracted_data_str = response.choices[0].message.content
        return json.loads(extracted_data_str)
    except Exception as e:
        print(f"  -> Error durante el análisis de IA: {e}")
        return {}

def update_episode_in_db(episode_id, enriched_data):
    """Actualiza un episodio en la BD con los nuevos datos."""
    visual_summary = enriched_data.get("visual_summary", "")
    key_characters = ", ".join(enriched_data.get("key_characters", []))
    key_objects_locations = ", ".join(enriched_data.get("key_objects_locations", []))

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE episodes
                SET visual_summary = %s, key_characters = %s, key_objects_locations = %s
                WHERE id = %s
                """,
                (visual_summary, key_characters, key_objects_locations, episode_id)
            )
        conn.commit()

def main():
    print("Iniciando proceso de ENRIQUECIMIENTO DIRIGIDO de la base de datos...")
    
    episodes_to_process = fetch_episodes_to_enrich(target_character="Gary")
    
    if not episodes_to_process:
        print("¡No hay episodios nuevos de Gary que enriquecer! La base de datos está al día para este personaje.")
        return
        
    print(f"Se encontraron {len(episodes_to_process)} episodios de Gary para enriquecer.")
    
    for i, (ep_id, title, summary) in enumerate(episodes_to_process, 1):
        print(f"\nProcesando episodio {i}/{len(episodes_to_process)}: '{title}' (ID: {ep_id})")
        
        
        enriched_data = enrich_episode_with_ai(title, summary)
        
        if enriched_data:
            update_episode_in_db(ep_id, enriched_data)
            print(f"  -> ¡Éxito! Episodio ID {ep_id} enriquecido y actualizado en la base de datos.")
        else:
            print(f"  -> Fallo. No se pudo enriquecer el episodio ID {ep_id}.")
            
    print("\nProceso de enriquecimiento finalizado.")

if __name__ == "__main__":
    main()