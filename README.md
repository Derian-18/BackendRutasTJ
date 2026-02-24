## Proceso para hacer modificaciones
Para poder hacer modificaciones en este proyecto se necesita clonar el proyecto con git clone y el codigo del repositorio

Tienes que instalar los requerimientos con pip install -r requerements.txt

Una vez que ya lo hayas clonado vas a hacer migraciones con python manage.py makemigrations y despues python manage.py migrate

Para poder entrar al panel administrador, necesitas crear un superusuario con python manage.py createsuperuser e ingresar los datos que te pide.

Una vez que hayas hecho todo eso, ahora si, podras correr el proyecto localmente con python manage.py runserver.

## A tener en cuenta
Tienes que tener en cuenta que tienes que tener un entorno virtual y activarlo, despues, instalar las dependencias.
Una vez ya clonado el repositorio, para que puedas hacer cambios tienes que crearte una rama, como se hace? con git checkout -b nombre-rama, luego git push -u origin nombre-rama que creaste para subirlo a github
