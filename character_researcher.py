import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from googlesearch import search

load_dotenv()
try:
    client = OpenAI()
except Exception as e:
    print(f"Error al inicializar OpenAI: {e}")
    client = None

def search_internet_for(query: str, num_results: int = 5) -> list:
    """Busca en Google y devuelve una lista de URLs."""
    print(f"Buscando en internet: '{query}'...")
    try:
        urls = [url for url in search(query, num_results=num_results)]
        print(f"Se encontraron {len(urls)} URLs.")
        return urls
    except Exception as e:
        print(f"Error durante la búsqueda en internet: {e}")
        return []

def get_text_from_url(url: str) -> str:
    """
    (Versión Simplificada) Esta es la parte más compleja en un proyecto real.
    Para este prototipo, simularemos que obtenemos el texto, pero en realidad
    le pasaremos la URL a la IA si tiene capacidad de navegación, o
    simplemente usaremos el snippet de la búsqueda.
    Para una implementación real, se usarían librerías como `BeautifulSoup` o `requests-html`.
    Por ahora, vamos a devolver la URL para que la IA la procese si puede.
    """
    return url 

def analyze_and_extract_character_info(character_name: str, search_results: list) -> dict:
    """
    Usa GPT-4o para analizar los resultados de búsqueda y rellenar una ficha de personaje.
    """
    if not client:
        raise Exception("Cliente de OpenAI no inicializado.")

    print("Analizando resultados con IA para extraer información del personaje...")
    
    system_prompt = f"""
    Eres un analista de investigación de personajes de ficción. Tu tarea es analizar
    las siguientes URLs y fragmentos de texto sobre el personaje "{character_name}".
    Debes extraer y sintetizar la información para rellenar una ficha de personaje
    en formato JSON.

    La estructura del JSON debe ser exactamente la siguiente:
    {{
        "name": "Nombre completo del personaje",
        "series": "Serie a la que pertenece",
        "description": "Un párrafo breve que describe quién es.",
        "visual_description_for_ai": "Una descripción visual extremadamente detallada optimizada para un generador de imágenes de IA. Enfócate en colores, formas, patrones y estilo artístico. No uses el nombre del personaje aquí.",
        "personality_traits": ["lista", "de", "adjetivos", "clave"],
        "catchphrases": ["lista", "de", "frases", "típicas"]
    }}

    Analiza el contenido de las URLs proporcionadas y genera únicamente el objeto JSON como respuesta, sin ningún texto adicional.
    """

 
    context = "\n".join(search_results)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Aquí están los resultados de la búsqueda para '{character_name}':\n\n{context}"}
            ],
            response_format={"type": "json_object"}
        )
        
        extracted_json_str = response.choices[0].message.content
        character_data = json.loads(extracted_json_str)
        print("Análisis completado. Ficha de personaje extraída.")
        return character_data
        
    except Exception as e:
        print(f"Error durante el análisis de la IA: {e}")
        return {}

def main():
    """
    Flujo principal del script de investigación.
    """
    character_name = input("¿Sobre qué personaje quieres investigar? (Ej: Gary the Snail): ")
    if not character_name:
        print("No se ha introducido un nombre. Abortando.")
        return

    queries = [
        f"{character_name} personality traits",
        f"{character_name} physical appearance description",
        f"{character_name} Fandom wiki"
    ]
    all_urls = []
    for q in queries:
        all_urls.extend(search_internet_for(q, num_results=2))
    
    unique_urls = list(set(all_urls))

    if not unique_urls:
        print("No se encontraron resultados en internet. No se puede continuar.")
        return

    character_info = analyze_and_extract_character_info(character_name, unique_urls)

    if not character_info:
        print("La IA no pudo generar la ficha de personaje.")
        return

    safe_filename = character_name.lower().replace(" ", "_") + ".json"
    output_path = os.path.join("data", "ficha", safe_filename)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(character_info, f, indent=2, ensure_ascii=False)
    
    print("\n¡Éxito!")
    print(f"La nueva ficha de personaje ha sido guardada en: {output_path}")

if __name__ == "__main__":
    main()