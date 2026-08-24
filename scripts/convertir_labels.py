from pathlib import Path


DATASET = Path("dataset")

CARPETAS = [
    DATASET / "train" / "labels",
    DATASET / "valid" / "labels",
]

def bbox_a_poligono(partes):
    """
    Convierte:
    class x_center y_center width height
    a:
    class x1 y1 x2 y2 x3 y3 x4 y4
    """

    clase = partes[0]
    x = float(partes[1])
    y = float(partes[2])
    w = float(partes[3])
    h = float(partes[4])
    x1 = x - w / 2
    y1 = y - h / 2
    x2 = x + w / 2
    y2 = y - h / 2
    x3 = x + w / 2
    y3 = y + h / 2
    x4 = x - w / 2
    y4 = y + h / 2

    return (
        f"{clase} "
        f"{x1:.6f} {y1:.6f} "
        f"{x2:.6f} {y2:.6f} "
        f"{x3:.6f} {y3:.6f} "
        f"{x4:.6f} {y4:.6f}"
    )


def procesar_archivo(archivo):

    lineas_nuevas = []
    with open(archivo,"r",encoding="utf-8") as f:
        lineas = f.readlines()
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        partes = linea.split()

        # --------------------------------
        # CLASE
        # --------------------------------
        clase = int(partes[0])
        if clase < 0 or clase > 2:
            print(
                f"ERROR clase fuera de rango: "
                f"{archivo}")
            continue

        # --------------------------------
        # DETECCIÓN -> SEGMENTACIÓN
        # --------------------------------

        if len(partes) == 5:
            nueva_linea = bbox_a_poligono(partes)
            lineas_nuevas.append(nueva_linea)
            print(f"Convertido: {archivo.name}")
        # --------------------------------
        # SEGMENTACIÓN
        # --------------------------------

        elif len(partes) >= 7:lineas_nuevas.append(linea)
        else:
            print(f"Etiqueta inválida: {archivo}")

    with open(
        archivo,
        "w",
        encoding="utf-8"
    ) as f:

        for linea in lineas_nuevas:
            f.write(linea + "\n")


def main():
    for carpeta in CARPETAS:
        if not carpeta.exists():
            print(f"No existe: {carpeta}")
            continue
        archivos = list(carpeta.glob("*.txt"))

        print(f"\nProcesando {carpeta}")
        for archivo in archivos:
            procesar_archivo(archivo)
    print("\nConversión terminada.")

if __name__ == "__main__":
    main()