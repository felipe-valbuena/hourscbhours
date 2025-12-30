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

app = Flask(__name__)

def obtener_horas(modelo, fecha_inicio, fecha_fin):

    # RUTAS CORRECTAS PARA RENDER + CHROMIUM
    CHROMIUM_PATH = "/usr/bin/chromium"
    CHROMEDRIVER_PATH = "/usr/bin/chromedriver"

    url = f"https://www.cbhours.com/user/{modelo}.html"

    chrome_options = Options()
    chrome_options.binary_location = CHROMIUM_PATH

    # OPCIONES OBLIGATORIAS EN SERVIDORES
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = None

    try:
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        wait = WebDriverWait(driver, 30)

        CONTAINER_SELECTOR = "div.activity_logs_container"

        # Esperar carga completa
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, CONTAINER_SELECTOR)))

        # Forzar visibilidad con JS
        activity_container = driver.find_element(By.CSS_SELECTOR, CONTAINER_SELECTOR)
        driver.execute_script(
            "arguments[0].classList.add('visible');", activity_container
        )

        wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div.activity_logs_content p")
            )
        )

        registros_html = driver.find_elements(
            By.CSS_SELECTOR, "div.activity_logs_content p"
        )

        registros = []
        total_horas = 0
        total_minutos = 0

        fecha_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d")

        for r in registros_html:
            texto = r.text.strip()
            match = re.search(
                r"(\d{4}-\d{2}-\d{2}).*?(\d{1,2}) Hours (\d{1,2}) Minutes",
                texto,
            )

            if match:
                fecha_str, horas_str, minutos_str = match.groups()
                fecha_registro = datetime.strptime(fecha_str, "%Y-%m-%d")

                if fecha_ini <= fecha_registro <= fecha_fin:
                    horas = int(horas_str)
                    minutos = int(minutos_str)

                    total_horas += horas
                    total_minutos += minutos
                    registros.append(
                        (fecha_str, f"{horas} horas {minutos} minutos")
                    )

        total_horas += total_minutos // 60
        total_minutos = total_minutos % 60

        driver.quit()

        return {
            "modelo": modelo,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "total_horas": total_horas,
            "total_minutos": total_minutos,
            "registros": registros,
        }, None

    except (TimeoutException, WebDriverException) as e:
        if driver:
            driver.quit()
        return None, f"Error al obtener datos: {str(e)}"

    except Exception as e:
        if driver:
            driver.quit()
        return None, f"Error inesperado: {str(e)}"


@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    error = None

    if request.method == "POST":
        modelo = request.form.get("modelo")
        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

        if not (modelo and fecha_inicio and fecha_fin):
            error = "Por favor, completa todos los campos."
        else:
            try:
                ini = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                fin = datetime.strptime(fecha_fin, "%Y-%m-%d")

                if ini > fin:
                    error = "La fecha de inicio no puede ser posterior a la fecha final."
                else:
                    resultado, error = obtener_horas(
                        modelo, fecha_inicio, fecha_fin
                    )
            except ValueError:
                error = "Formato de fecha inválido (YYYY-MM-DD)."

    return render_template(
        "index.html",
        resultado=resultado,
        error=error,
        request=request,
    )


if __name__ == "__main__":
    app.run()


