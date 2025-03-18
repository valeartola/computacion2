import sys
import getopt

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "n:", ["nombre="])
    except getopt.GetoptError as err:
        print(err)
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-n", "--nombre"):
            print(f"¡Hola, {arg}!")

if __name__ == "__main__":
    main()
