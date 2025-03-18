import argparse

def main():
    parser = argparse.ArgumentParser(description="Procesador de archivos")
    parser.add_argument("-i", "--input", required=True, help="Archivo de entrada")
    parser.add_argument("-o", "--output", help="Archivo de salida")
    args = parser.parse_args()
    if args.output is None:
        print("⚠️ No especificaste un archivo de salida. Usando 'salida.txt' por defecto.")
        args.output = "salida.txt"


    print(f"📂 Archivo de entrada: {args.input}")
    print(f"📂 Archivo de salida: {args.output}")

if __name__ == "__main__":
    main()