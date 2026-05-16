# 🐦 Tweety - Django Twitter Clone

A full-featured Twitter-inspired social media application built with **Django** and **Bootstrap**.

![Python](https://img.shields.io/badge/Python-3.14-blue)
![Django](https://img.shields.io/badge/Django-6.0-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)
## Screenshots
<p align="center">
  <img src="https://github.com/user-attachments/assets/50f3b845-7262-4c93-b02b-9004f006b24f" width="62%" />
  &nbsp;&nbsp;
  <img src="https://github.com/user-attachments/assets/fc3a230c-9f7a-4544-867b-e3fb217ec00b" width="32%" />
</p>


## 🌐 Live Demo
https://tweetapptweety.com   Website <br>  

> Feel free to visit the site while it is up and running!

---

## 🚀 Installation & Setup

Follow these steps to get the project running on your local machine.

### Windows (PowerShell)
```powershell
# 1. Clone the repository from GitHub
git clone https://github.com/Ardakorkmaz0/Tweety.git

# 2. Navigate into the project directory
cd Tweety

# 3. Create a virtual environment named 'venv'
python -m venv venv

# 4. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 5. Install all required Python packages
pip install -r requirements.txt

# 6. Generate a secure .env file (SECRET_KEY etc.)
python create_env.py

# 7. Create migration files based on model changes
python manage.py makemigrations

# 8. Apply migrations to create database tables
python manage.py migrate

# 9. Create an administrative user
python manage.py createsuperuser

# 10. Start the Django development server
python manage.py runserver
```

### macOS / Linux (Bash)
```bash
# 1. Clone the repository from GitHub
git clone https://github.com/Ardakorkmaz0/Tweety.git

# 2. Navigate into the project directory
cd Tweety

# 3. Create a virtual environment named 'venv'
python3 -m venv venv

# 4. Activate the virtual environment
source venv/bin/activate

# 5. Install all required Python packages
pip install -r requirements.txt

# 6. Generate a secure .env file (SECRET_KEY etc.)
python create_env.py

# 7. Create migration files based on model changes
python manage.py makemigrations

# 8. Apply migrations to create database tables
python manage.py migrate

# 9. Create an administrative user
python manage.py createsuperuser

# 10. Start the Django development server
python manage.py runserver
```

Once started, visit **`http://127.0.0.1:8000/`** in your web browser.

> **Note:** The project defaults to **development mode** (DEBUG=True, localhost allowed).  
> On the production server, set `ENVIRONMENT=production` in your `.env` file.

---

## 🛠 Tech Stack
* **Backend:** Django 6.0
* **Frontend:** HTML5, CSS3, Bootstrap 5.3
* **Database:** SQLite (Development)

## 👨‍💻 Author

**Arda Korkmaz**
* 🎓 Computer Engineering Student
* 🐙 GitHub: [@Ardakorkmaz0](https://github.com/Ardakorkmaz0)
