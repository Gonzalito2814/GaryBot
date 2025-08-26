import argparse
from episodes_db import init_db, ingest_csv, search_episodes, format_citation

def main():
    parser = argparse.ArgumentParser(description="Prueba de búsqueda de episodios.")
    parser.add_argument("--ingest", action="store_true", help="Ingerir CSV antes de buscar")
    parser.add_argument("--csv", default="data/episodios/episodios.csv", help="Ruta al CSV")
    parser.add_argument("query", nargs="?", default="Gary", help="Texto a buscar")
    args = parser.parse_args()

    init_db()
    if args.ingest:
        ingest_csv(args.csv)

    results = search_episodes(args.query, limit=5)
    if not results:
        print("Sin resultados.")
        return

    print(f"\nResultados para: '{args.query}'\n")
    for i, ep in enumerate(results, 1):
        print(f"{i}. {format_citation(ep)}")

if __name__ == "__main__":
    main()
