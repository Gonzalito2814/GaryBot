import os
import re
import psycopg2
from psycopg2.extras import DictCursor
import pandas as pd
from typing import List, Dict, Any, Set

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://garyuser:garypass@localhost:5432/garybotdb")
STOP_WORDS: Set[str] = { "a", "al", "ante", "con", "contra", "de", "del", "desde", "en", "entre", "hacia", "hasta", "para", "por", "segun", "sin", "sobre", "tras", "durante", "mediante", "etc", "y", "o", "u", "e", "ni", "que", "si", "porque", "como", "cuando", "donde", "quien", "cual", "cuyo", "el", "la", "lo", "los", "las", "un", "una", "unos", "unas", "algun", "alguna", "algunos", "algunas", "mucho", "mucha", "muchos", "muchas", "poco", "poca", "pocos", "pocas", "todo", "toda", "todos", "todas", "otro", "otra", "otros", "otras", "mismo", "misma", "mismos", "mismas", "ese", "esa", "esos", "esas", "este", "esta", "estos", "estas", "aquel", "aquella", "aquellos", "aquellas", "su", "sus", "mi", "mis", "tu", "tus", "nuestro", "nuestra", "nuestros", "nuestras", "vuestro", "vuestra", "vuestros", "vuestras", "me", "te", "se", "nos", "os", "le", "les", "lo", "la", "los", "las", "yo", "tu", "el", "ella", "ello", "nosotros", "nosotras", "vosotros", "vosotras", "ellos", "ellas", "usted", "ustedes"}

def _connect():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        print("Error al conectar con PostgreSQL.")
        raise e

def _extract_keywords(query: str) -> List[str]:
    clean_query = re.sub(r'[^\w\s]', '', query.lower())
    keywords = [
        word for word in clean_query.split() 
        if word not in STOP_WORDS and len(word) > 2
    ]
    return keywords


def init_db():
    """Crea y/o actualiza las tablas de la base de datos."""
    with _connect() as conn:
        with conn.cursor() as cur:
        
            cur.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id SERIAL PRIMARY KEY, season INTEGER, episode INTEGER, code TEXT,
                title TEXT, summary TEXT, quotes TEXT, characters TEXT
            );
            """)
            
            cur.execute("""
            DO $$ BEGIN
                ALTER TABLE episodes ADD COLUMN IF NOT EXISTS visual_summary TEXT;
                ALTER TABLE episodes ADD COLUMN IF NOT EXISTS key_characters TEXT;
                ALTER TABLE episodes ADD COLUMN IF NOT EXISTS key_objects_locations TEXT;
            EXCEPTION
                WHEN duplicate_column THEN RAISE NOTICE 'columnas ya existen.';
            END $$;
            """)
            
            cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL,
                content TEXT NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """)
        conn.commit()
        print("Bases de datos inicializadas y/o actualizadas.")

def search_episodes(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    keywords = _extract_keywords(query)
    if not keywords: return []
    sql_where_parts = []
    sql_params = []
    search_columns = ["title", "summary", "quotes", "characters", "key_objects_locations"]
    for keyword in keywords:
        keyword_part = " OR ".join([f"{col} ILIKE %s" for col in search_columns])
        sql_where_parts.append(f"({keyword_part})")
        for _ in search_columns:
            sql_params.append(f"%{keyword}%")
    full_where_clause = " OR ".join(sql_where_parts)
    
    sql_query = f"""
        SELECT id, season, episode, code, title, summary, quotes, characters,
               visual_summary, key_characters, key_objects_locations
        FROM episodes WHERE {full_where_clause} LIMIT %s;
    """
    sql_params.append(limit)
    with _connect() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql_query, sql_params)
            results = [dict(row) for row in cur.fetchall()]
    return results

def ingest_csv(csv_path: str):
    df = pd.read_csv(csv_path)
    df = df.fillna("")
    for col in ['visual_summary', 'key_characters', 'key_objects_locations']:
        if col not in df.columns:
            df[col] = ""

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE episodes RESTART IDENTITY;")
            for _, row in df.iterrows():
                cur.execute(
                    """
                    INSERT INTO episodes (season, episode, code, title, summary, quotes, characters, visual_summary, key_characters, key_objects_locations)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (row['season'], row['episode'], row['code'], row['title'], row['summary'], row['quotes'], row['characters'], row['visual_summary'], row['key_characters'], row['key_objects_locations'])
                )
        conn.commit()

def format_citation(ep: Dict[str, Any]) -> str:
    code = ep.get("code") or f"S{ep.get('season'):02d}E{ep.get('episode'):02d}"
    title = ep.get("title", "Sin título")
    summary = ep.get("summary", "")
    short = (summary[:140] + "…") if len(summary) > 140 else summary
    return f"[{code}] {title} — {short}"

def save_message_to_history(session_id: str, role: str, content: str):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute( "INSERT INTO chat_history (session_id, role, content) VALUES (%s, %s, %s)", (session_id, role, content))
        conn.commit()

def get_history_by_session(session_id: str, limit: int = 20) -> List[Dict[str, str]]:
    with _connect() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute( "SELECT role, content FROM chat_history WHERE session_id = %s ORDER BY created_at ASC LIMIT %s", (session_id, limit))
            history = [dict(row) for row in cur.fetchall()]
    return history

def delete_history_by_session(session_id: str):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_history WHERE session_id = %s", (session_id,))
        conn.commit()
        print(f"Historial de la sesión {session_id} ha sido borrado.")