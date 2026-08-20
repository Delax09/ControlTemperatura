import cv2
import os

# Nombre de tu archivo de video
video_path = "VideoEntrenar3.mp4"
# Carpeta donde se guardarán las imágenes
output_folder = "dataset_puerta3"

# Crea la carpeta si no existe
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Cargar el video
cap = cv2.VideoCapture(video_path)

frame_count = 0
saved_count = 0

# Frecuencia de extracción: guarda 1 de cada 15 fotogramas
frecuencia_extraccion = 15 

while cap.isOpened():
    ret, frame = cap.read()
    
    # Si ya no hay más fotogramas, termina el ciclo
    if not ret:
        break
        
    # Guarda el fotograma solo si coincide con la frecuencia
    if frame_count % frecuencia_extraccion == 0:
        nombre_archivo = os.path.join(output_folder, f"puerta_{saved_count:04d}.jpg")
        cv2.imwrite(nombre_archivo, frame)
        saved_count += 1
        
    frame_count += 1

cap.release()
print(f"¡Extracción completa! Se guardaron {saved_count} imágenes en la carpeta '{output_folder}'.")