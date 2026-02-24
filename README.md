# Rutas Tijuana 🚍

### Que hace el proyecto?
Guarda y gestiona todas las rutas del transporte público en Tijuana, ofreciendo un mapa interactivo y confiable para los ciudadanos que residen en la ciudad.

### Que problema resuelve?
Elimina la incertidumbre de no saber qué transporte elegir para llegar a un destino específico en una ciudad con un sistema de rutas complejo.

### Tecnologias principales

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

## Instalacion y configuracion local
Sigue estos pasos para mmontar el entorno de desarrollo

1. **Clona el repositorio:**
   ```bash
   # HTTPS
   git clone https://github.com/Derian-18/BackendRutasTJ.git
   ```
   ```bash
   # SSH
   git clone git@github.com:Derian-18/BackendRutasTJ.git
   ```

2. **Crea y activa el entorno virtual**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate

  3. **Instala las dependencias**
     ```bash
     pip install -r requirements.txt

  4. **Configura la base de datos**
     ```bash
     python manage.py makemigrations
     python manage.py migrate

  5. **Crea un administrador**
     ```bash
     python manage.py createsuperuser

  6. **Inicia el servidor**
     ```bash
     python manage.py runserver

## Como contribuir
Para mantener orden en el proyecto, sigue este flujo: <br>
**Crea una rama para tu mejora:**
```bash
git checkout -b nombre-de-tu-rama
```

Realiza tus cambios y haz commit.

**Sube tu rama:**
```bash
git push -u origin nombre-de-tu-rama
```

Abre un Pull Request en github.
