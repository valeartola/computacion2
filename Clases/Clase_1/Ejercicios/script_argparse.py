import argparse

def main():
    parser = argparse.ArgumentParser(description="Un script de saludo")
    parser.add_argument("-n", "--nombre", required=True, help="Tu nombre")
    args = parser.parse_args()

    print(f"¡Hola, {args.nombre}!")

if __name__ == "__main__":
    main()
