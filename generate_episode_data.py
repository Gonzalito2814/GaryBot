import os
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
from googlesearch import search
import pandas as pd
from tqdm import tqdm

load_dotenv()
try:
    client = OpenAI()
except Exception as e:
    print(f"Error al inicializar OpenAI: {e}")
    client = None

def find_episode_list_url() -> str:
    """Busca en Google la URL de la lista de episodios de la Fandom Wiki."""
    query = "spongebob squarepants list of episodes fandom wiki"
    print(f"Buscando la lista principal de episodios con: '{query}'")
    try:
        urls = list(search(query, num_results=1))
        if urls:
            print(f"URL de la lista encontrada: {urls[0]}")
            return urls[0]
    except Exception as e:
        print(f"Error buscando la URL principal: {e}")
    return None

def scrape_episode_links(list_url: str) -> list:
    """Extrae los enlaces a las páginas de cada episodio."""
    print("Extrayendo enlaces a cada episodio...")
    try:
        response = requests.get(list_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        episode_links = []
        tables = soup.find_all('table', class_='wikitable')
        for table in tables:
            for link in table.find_all('a'):
                if link.has_attr('title') and 'Episode' not in link['href']:
                    full_url = "https://spongebob.fandom.com" + link['href']
                    if full_url not in episode_links:
                        episode_links.append(full_url)
        print(f"Se encontraron {len(episode_links)} enlaces a episodios.")
        return episode_links
    except Exception as e:
        print(f"Error al extraer los enlaces de los episodios: {e}")
        return []

def scrape_page_content(url: str) -> str:
    """Extrae el texto principal de la página de un episodio."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_div = soup.find('div', class_='mw-parser-output')
        if content_div:
            return ' '.join(content_div.get_text().split()) 
    except Exception as e:
        print(f"  -> Error al scrapear {url}: {e}")
    return ""

def extract_structured_data_with_ai(page_content: str, episode_url: str) -> dict:
    """Usa GPT-4o para rellenar nuestra ficha de episodio a partir de texto en bruto."""
    if not client: return {}

    system_prompt = """
    Eres un archivista de datos. Tu tarea es leer el texto extraído de una página de la Fandom Wiki
    y rellenar una ficha de episodio en formato JSON.

    La estructura del JSON debe ser:
    {
        "season": "Número de la temporada (como integer)",
        "episode": "Número del episodio en la temporada (como integer)",
        "code": "El código de producción (ej: S01E01a)",
        "title": "El título del episodio",
        "summary": "Un resumen detallado de la trama en 2-4 frases.",
        "quotes": "Una o dos citas famosas del episodio.",
        "characters": "Una lista de los personajes principales que aparecen."
    }

    Si no puedes encontrar un dato, déjalo como un string vacío "" o 0 para los números.
    Analiza el siguiente texto y genera únicamente el objeto JSON como respuesta.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"URL de referencia: {episode_url}\n\nContenido de la página:\n{page_content[:15000]}"} # Limitamos el contenido para no exceder el límite de tokens
            ],
            response_format={"type": "json_object"}
        )
        data_str = response.choices[0].message.content
        return json.loads(data_str)
    except Exception as e:
        print(f"  -> Error durante el análisis de IA: {e}")
        return {}

def main():
    print("--- Iniciando Agente Archivista para la Base de Datos de Episodios ---")
    
    list_url = find_episode_list_url()
    if not list_url:
        print("No se pudo encontrar la lista de episodios. Abortando.")
        return

    episode_links = scrape_episode_links(list_url)
    if not episode_links:
        print("No se pudieron extraer los enlaces de los episodios. Abortando.")
        return
        
    all_episodes_data = []
    
    print("\nProcesando cada episodio (esto puede tardar mucho)...")
    for link in tqdm(episode_links, desc="Episodios"):
        content = scrape_page_content(link)
        if content:
            structured_data = extract_structured_data_with_ai(content, link)
            if structured_data and structured_data.get('title'):
                all_episodes_data.append(structured_data)

    if not all_episodes_data:
        print("No se pudo extraer información estructurada de ningún episodio.")
        return

    df = pd.DataFrame(all_episodes_data)
    
    column_order = ["season", "episode", "code", "title", "summary", "quotes", "characters"]
    df = df.reindex(columns=column_order)
    
    output_path = os.path.join("data", "episodios", "episodios_completos.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print("\n--- ¡Proceso Completado! ---")
    print(f"Se ha generado un nuevo archivo con {len(df)} episodios.")
    print(f"Archivo guardado en: {output_path}")
    print("Ahora puedes reemplazar tu 'episodios.csv' con este nuevo archivo y ejecutar la ingesta de datos.")

if __name__ == "__main__":
    main()