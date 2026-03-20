# 🐦 Tweety - Django Twitter Clone

A full-featured Twitter-inspired social media application built with **Django** and **Bootstrap**.

![Python](https://img.shields.io/badge/Python-3.14-blue)
![Django](https://img.shields.io/badge/Django-6.0-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)

## 🌐 Live Demo
[https://ardakorkmaz0.pythonanywhere.com](https://ardakorkmaz0.pythonanywhere.com)

> Feel free to visit the site while it is up and running!

---

## 🚀 Installation & Setup

Follow these steps to get the project running on your local machine.

**Terminal: PowerShell**
```powershell
# 1. Clone the repository from GitHub
git clone [https://github.com/Ardakorkmaz0/Tweety.git](https://github.com/Ardakorkmaz0/Tweety.git)

# 2. Navigate into the project directory
cd Tweety

# 3. Create a virtual environment named 'venv'
python -m venv venv

# 4. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 5. Install all required Python packages from requirements.txt
pip install -r requirements.txt

# 6. Create migration files based on model changes
python manage.py makemigrations

# 7. Apply migrations to create database tables
python manage.py migrate

# 8. Create an administrative user for the project
python manage.py createsuperuser

# 9. Start the Django development server
python manage.py runserver
```

Once started, visit **`http://127.0.0.1:8000/`** in your web browser.

---

## 🛠 Tech Stack
* **Backend:** Django 6.0
* **Frontend:** HTML5, CSS3, Bootstrap 5.3
* **Database:** SQLite (Development)

## 👨‍💻 Author

**Arda Korkmaz**
* 🎓 Computer Engineering Student
* 🐙 GitHub: [@Ardakorkmaz0](https://github.com/Ardakorkmaz0)
