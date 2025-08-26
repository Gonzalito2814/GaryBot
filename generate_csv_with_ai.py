import os
import json
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
try:
    client = OpenAI()
except Exception as e:
    print(f"Error al inicializar OpenAI: {e}")
    client = None

def find_list_in_json(data):
    """Busca recursivamente la primera lista que encuentre en un objeto JSON."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key, value in data.items():
            result = find_list_in_json(value)
            if result is not None:
                return result
    return None

def generate_episode_batch_with_ai(start_episode: int, end_episode: int) -> list:
    """Usa GPT-4o para generar un lote de datos de episodios."""
    if not client: return []

    system_prompt = f"""
    Eres un experto mundial y archivista de la serie animada "Bob Esponja Pantalones Cuadrados".
    Tu tarea es generar un objeto JSON. La clave raíz del objeto JSON debe ser "episodes", 
    y su valor debe ser una lista de objetos de episodio.
    
    Cada objeto en la lista "episodes" debe tener la siguiente estructura:
    {{
      "season": "Número de la temporada (como integer)",
      "episode": "Número del episodio en general, no por temporada (como integer)",
      "code": "El código de producción (ej: 1a, 1b, 2a, etc.)",
      "title": "El título oficial del episodio",
      "summary": "Un resumen conciso y bien escrito de la trama del episodio en una o dos frases.",
      "quotes": "Una o dos citas icónicas del episodio, separadas por un '|'.",
      "characters": "Una lista de los personajes principales que aparecen, separados por un ';'."
    }}
    
    Genera únicamente el objeto JSON como respuesta.
    """
    
    user_prompt = f"Por favor, genera los datos para los episodios de Bob Esponja desde el número {start_episode} hasta el {end_episode}."

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        response_data_str = response.choices[0].message.content
        response_data = json.loads(response_data_str)
        
        episode_list = find_list_in_json(response_data)
        
        if episode_list and isinstance(episode_list, list):
            return episode_list
        else:
            print(f"  -> La respuesta JSON no contenía una lista de episodios válida.")
            print(f"  -> Recibido: {response_data_str[:200]}...") 
            return []
        
    except Exception as e:
        print(f"  -> Error durante la generación de IA para el lote {start_episode}-{end_episode}: {e}")
        return []

def main():
    TOTAL_EPISODES_TO_GENERATE = 300
    BATCH_SIZE = 10
    
    print(f"--- Iniciando Agente Generador de Datos para {TOTAL_EPISODES_TO_GENERATE} episodios ---")
    
    all_episodes_data = []
    
    num_batches = (TOTAL_EPISODES_TO_GENERATE + BATCH_SIZE - 1) // BATCH_SIZE
    with tqdm(total=TOTAL_EPISODES_TO_GENERATE, desc="Episodios Generados") as pbar:
        for i in range(num_batches):
            start_ep = i * BATCH_SIZE + 1
            end_ep = start_ep + BATCH_SIZE - 1
            if end_ep > TOTAL_EPISODES_TO_GENERATE:
                end_ep = TOTAL_EPISODES_TO_GENERATE
            
            print(f"\nGenerando lote de episodios del {start_ep} al {end_ep}...")
            batch_data = generate_episode_batch_with_ai(start_ep, end_ep)
            
            if batch_data:
                valid_episodes = [ep for ep in batch_data if isinstance(ep, dict)]
                all_episodes_data.extend(valid_episodes)
                pbar.update(len(valid_episodes))
                print(f"  -> Lote recibido con {len(valid_episodes)} episodios válidos.")
            else:
                print(f"  -> Fallo al generar el lote. Saltando al siguiente.")

    if not all_episodes_data:
        print("No se pudo generar ningún dato de episodio.")
        return

    df = pd.DataFrame(all_episodes_data)
    
    column_order = ["season", "episode", "code", "title", "summary", "quotes", "characters"]
    df['episode'] = pd.to_numeric(df.get('episode'), errors='coerce')
    df = df.dropna(subset=['episode'])
    df['episode'] = df['episode'].astype(int)
    df = df.sort_values(by='episode')
    df = df.reindex(columns=column_order).fillna("")

    output_path = os.path.join("data", "episodios", "episodios_generados_por_ia.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    print("\n--- ¡Proceso Completado! ---")
    print(f"Se ha generado un nuevo archivo con {len(df)} episodios.")
    print(f"Archivo guardado en: {output_path}")

if __name__ == "__main__":
    main()