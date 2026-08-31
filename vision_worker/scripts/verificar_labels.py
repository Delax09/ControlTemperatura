from pathlib import Path


DATASET = Path("dataset")

CARPETAS = [
    DATASET / "train" / "labels",
    DATASET / "valid" / "labels",
]


def verificar_archivo(archivo):

    problemas = []

    with open(
        archivo,
        "r",
        encoding="utf-8"
    ) as f:

        lineas = f.readlines()

    for numero, linea in enumerate(
        lineas,
        start=1
    ):

        partes = linea.strip().split()

        if not partes:
            continue

        # Clase
        clase = int(partes[0])

        if clase not in [0, 1, 2]:

            problemas.append(
                f"Línea {numero}: clase {clase}"
            )

        # Debe ser segmentación
        if len(partes) < 7:

            problemas.append(
                f"Línea {numero}: "
                f"formato detección "
                f"({len(partes)} valores)"
            )

    return problemas


def main():

    total = 0

    errores = 0

    for carpeta in CARPETAS:

        print("\n====================")
        print(carpeta)
        print("====================")

        for archivo in carpeta.glob("*.txt"):

            total += 1

            problemas = verificar_archivo(
                archivo
            )

            if problemas:

                errores += 1

                print(
                    f"\n❌ {archivo.name}"
                )

                for problema in problemas:

                    print(
                        f"   {problema}"
                    )

            else:

                print(
                    f"✅ {archivo.name}"
                )

    print("\n====================")
    print("RESUMEN")
    print("====================")

    print(
        f"Archivos: {total}"
    )

    print(
        f"Con errores: {errores}"
    )

    if errores == 0:

        print(
            "\n✅ Dataset de etiquetas correcto."
        )

    else:

        print(
            "\n❌ Todavía hay etiquetas que corregir."
        )


if __name__ == "__main__":

    main()