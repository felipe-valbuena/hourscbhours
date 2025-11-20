from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datetime import datetime
import re
import os 

app = Flask(__name__)

def obtener_horas(modelo, fecha_inicio, fecha_fin):
    
    # --- RUTAS FIJAS PARA IMAGEN SELENIUM ---
    # La imagen 'selenium/standalone-chrome' usa estas rutas.
    CHROMIUM_PATH = '/usr/bin/google-chrome' 
    CHROME_DRIVER_PATH = '/usr/bin/chromedriver'

    url = f"https://www.cbhours.com/user/{modelo}.html"

    # Configuración de Selenium
    chrome_options = Options()
    
    # CRÍTICO: Especificar la ubicación del binario de Chrome
    chrome_options.binary_location = CHROMIUM_PATH 
    
    # --- OPCIONES ESENCIALES PARA DOCKER/LINUX ---
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox") # CRÍTICO para ejecución en Docker/Root user
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-notifications")
    
    # Otros argumentos de simulación de navegador
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080") 
    
    driver = None 
    try:
        # Inicialización del driver usando la RUTA FIJA de Docker
        service = Service(CHROME_DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        
        # Mantenemos 30 segundos de espera
        wait = WebDriverWait(driver, 30) 

        # --- ESPERA CRÍTICA: Asegurar la Carga y Presencia del Contenedor ---
        CONTAINER_SELECTOR = "div.activity_logs_container"
        try:
            # 1. Esperar que el estado de la página sea 'complete'
            wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # 2. Esperar que el contenedor principal esté presente
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, CONTAINER_SELECTOR)))
            
        except TimeoutException:
            driver.quit()
            return None, "Error de carga: La página no cargó completamente o no se encontró el contenedor principal después de 30 segundos. Verifique la URL."


        # --- PASO CLAVE: ACTIVAR LA PESTAÑA FORZANDO LA VISIBILIDAD CON JAVASCRIPT ---
        try:
            # 1. Encontrar el contenedor de la actividad
            activity_container = driver.find_element(By.CSS_SELECTOR, CONTAINER_SELECTOR)
            
            # 2. Inyectar JavaScript para añadir la clase 'visible' 
            driver.execute_script(
                "arguments[0].classList.add('visible');", activity_container
            )
            
            # 3. Esperar que el contenido de los registros sea visible 
            wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.activity_logs_content p"))
            )
            
        except TimeoutException:
            driver.quit()
            return None, "Fallo de renderizado: Se forzó la visibilidad, pero los registros de actividad no aparecieron."
        except Exception as e:
            if driver: driver.quit()
            return None, f"Fallo al forzar la pestaña: Error al inyectar JavaScript o al buscar el contenedor. ({e})"
            
        # 2. Obtener TODOS los elementos que coincidan con el selector
        registros_html = driver.find_elements(By.CSS_SELECTOR, "div.activity_logs_content p")
        
        # --- DEBUG (Se mantendrán impresos en los logs del servidor) ---
        print("-" * 50)
        print(f"DEBUG CRÍTICO: Registros encontrados (Count): {len(registros_html)}")
        if len(registros_html) > 0:
            print(f"DEBUG CRÍTICO: Primer registro: '{registros_html[0].text}'") 
        print("-" * 50)
        # ------------------------------------

        registros = []
        total_horas = 0
        total_minutos = 0

        fecha_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d")

        # 3. Bucle de parseo con la REGEX ROBUSTA
        for r in registros_html:
            texto = r.text.strip()
            match = re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d{1,2}) Hours (\d{1,2}) Minutes", texto)
            
            if match:
                fecha_str = match.group(1)
                horas_str = match.group(2)
                minutos_str = match.group(3)
                
                try:
                    fecha_registro = datetime.strptime(fecha_str, "%Y-%m-%d")
                    
                    if fecha_ini <= fecha_registro <= fecha_fin:
                        horas = int(horas_str)
                        minutos = int(minutos_str)
                        
                        total_horas += horas
                        total_minutos += minutos
                        
                        registros.append((fecha_str, f"{horas} horas {minutos} minutos"))
                except ValueError:
                    continue
        
        total_horas += total_minutos // 60
        total_minutos = total_minutos % 60

        driver.quit()

        return {
            "modelo": modelo,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "total_horas": total_horas,
            "total_minutos": total_minutos,
            "registros": registros
        }, None

    except WebDriverException as wde:
        if driver:
            driver.quit()
        # El error de WebDriver (Unable to obtain driver) debería desaparecer
        return None, f"Error del WebDriver. Error: {str(wde)}"

    except Exception as e:
        if driver:
            driver.quit()
        return None, f"Fallo inesperado al procesar la solicitud. Error: {str(e)}"


@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    error = None
    context = {"resultado": resultado, "error": error, "request": request} 

    if request.method == "POST":
        modelo = request.form.get("modelo")
        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")
        
        if not (modelo and fecha_inicio and fecha_fin):
            error = "Por favor, completa todos los campos del formulario."
        else:
            try:
                ini = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                fin = datetime.strptime(fecha_fin, "%Y-%m-%d")

                if ini > fin:
                    error = "La fecha de inicio no puede ser posterior a la fecha de fin."
                else:
                    # Llama a la función principal
                    resultado, error = obtener_horas(modelo, fecha_inicio, fecha_fin)
            except ValueError:
                error = "El formato de fecha no es válido (debe ser YYYY-MM-DD)."
        
        context["resultado"] = resultado
        context["error"] = error

    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(debug=True)
