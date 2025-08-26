from episodes_db import _connect

def get_database_status():
    """
    Se conecta a la base de datos y recupera un resumen del estado de los episodios.
    """
    status = {
        "total_episodes": 0,
        "enriched_episodes": 0,
        "connection_error": None
    }
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM episodes;")
                status["total_episodes"] = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM episodes WHERE visual_summary IS NOT NULL AND visual_summary != '';"
                )
                status["enriched_episodes"] = cur.fetchone()[0]
        return status
    except Exception as e:
        status["connection_error"] = str(e)
        return status

if __name__ == "__main__":
    print("🔍 Realizando auditoría de la base de datos de episodios...")
    
    status_report = get_database_status()

    if status_report["connection_error"]:
        print(f"Error de conexión: {status_report['connection_error']}")
    else:
        total = status_report["total_episodes"]
        enriched = status_report["enriched_episodes"]
        not_enriched = total - enriched
        
        percentage = (enriched / total * 100) if total > 0 else 0

        print("\n--- INFORME DE ESTADO DE LA BASE DE DATOS ---")
        print(f"Capítulos Totales en la Base de Datos: {total}")
        print(f"Capítulos Enriquecidos (con resumen visual): {enriched}")
        print(f"Capítulos Sin Enriquecer: {not_enriched}")
        print(f"Porcentaje de Enriquecimiento: {percentage:.2f}%")
        print("------------------------------------------")