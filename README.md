# Configuracion de Git y `.gitignore`

Guia para evitar subir datasets, videos, imagenes, resultados de entrenamiento y otros archivos locales a GitHub.

## 1. Crear el archivo `.gitignore`

El archivo `.gitignore` debe estar en la carpeta raiz del proyecto, al mismo nivel que los archivos principales de codigo.

Ejemplo para proyectos Python con YOLO:

```gitignore
# Datasets y datos locales
dataset/
dataset_puerta*/
Images/
Videos/

# Resultados generados
runs/

# Pesos de modelos
*.pt
*.onnx

# Archivos generados por Python
__pycache__/
*.py[cod]

# Entornos virtuales
.venv/
venv/
env/

# Variables y configuracion local
.env
```

## 2. Comprobar las reglas

Desde la raiz del proyecto, ejecuta:

```powershell
git check-ignore -v dataset/ Images/ runs/ Videos/ modelo.pt
```

La salida indica que regla del `.gitignore` esta ignorando cada archivo o carpeta.

## 3. Dejar de rastrear archivos ya subidos

`.gitignore` solo evita que se agreguen archivos nuevos. Si ya estaban en Git, hay que retirarlos del indice:

```powershell
git rm -r --cached --ignore-unmatch -- dataset Images runs Videos
git rm --cached --ignore-unmatch -- "*.pt" "*.onnx"
```

El parametro `--cached` los quita del repositorio, pero conserva los archivos en la computadora.

## 4. Revisar los cambios

```powershell
git status
git diff --cached --stat
```

Confirma que los archivos grandes aparecen como eliminados del indice y que los archivos de codigo importantes siguen presentes.

## 5. Guardar y subir la limpieza

```powershell
git add .gitignore README.md
git commit -m "Limpia archivos locales y generados"
git push origin main
```

## 6. Reutilizarlo en otro proyecto

1. Copia las reglas necesarias al `.gitignore` del nuevo proyecto.
2. Cambia los nombres de las carpetas segun la estructura del proyecto.
3. Ejecuta `git check-ignore -v` para comprobarlas.
4. Si los archivos ya estaban versionados, usa `git rm --cached`.
5. Haz commit y push.

## Importante

- No uses `git rm -r` sin `--cached` si quieres conservar los archivos localmente.
- `.gitignore` no elimina archivos que ya quedaron guardados en el historial de Git.
- Para quitar archivos grandes del historial anterior se necesita una limpieza adicional del historial, por ejemplo con `git filter-repo`.
- No ignores archivos necesarios para ejecutar el proyecto, como `data.yaml`, scripts `.py` o archivos de configuracion que deban compartirse.
