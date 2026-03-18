# 🐦 Tweety - Django Twitter Clone

A full-featured Twitter-inspired social media application built with Django and Bootstrap.

![Python](https://img.shields.io/badge/Python-3.14-blue)
![Django](https://img.shields.io/badge/Django-6.0-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)

## 🌐 Live Demo
https://ardakorkmaz0.pythonanywhere.com

> Feel free to visit while the site is up and running.

---

## 📸 Screenshots

| Main Page | Profile | Post |
|-----------|---------|------|
| ![Main](https://github.com/user-attachments/assets/362dad22-19ca-4c60-9fd6-6c2c725e799e) | ![Profile](https://github.com/user-attachments/assets/534d8edc-408c-4341-a0f5-edc076c6f86f) | ![Post](https://github.com/user-attachments/assets/0ba4a5c9-0c27-421d-85f1-ca202c6b5924) |

---

## ✨ Features

### 🔐 Authentication
- User registration with first name, last name, and age
- Login / Logout system
- Age verification (min 18) (max 150)
- Username uniqueness validation

### 📝 Tweets
- Create tweets (max 280 characters)
- Upload multiple images per tweet
- Image carousel for multi-image tweets
- Delete your own tweets
- View full tweet in modal popup

### ❤️ Likes
- Like / unlike tweets
- Like count displayed on each tweet
- Real-time heart icon toggle (❤️ / 🤍)

### 💬 Comments
- Comment on any tweet
- View all comments in tweet modal
- Comment author links to profile
- Timestamp on each comment

### 👤 Profiles
- Custom profile photo
- Bio, first name, last name, age
- View all tweets by user
- Edit your own profile
- Visit other users' profiles by clicking their username

### 🔍 Search
- Search tweets by message content
- Search by username with `@` prefix (e.g. `@Arda`)
- Search bar integrated in navbar

### 🛡️ Moderation
- Staff users can delete any tweet
- Django admin panel for full management
- Inline image preview in admin

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 6.0 |
| Frontend | Bootstrap 5.3 |
| Database | SQLite3 |
| Language | Python 3.14 |
| Templating | Django Templates |
| Image Handling | Pillow |

---

## 📁 Project Structure

```
djangotweet/
├── djangotweet/          # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── tweetapp/             # Main application
│   ├── models.py         # Tweet, TweetImage, Profile, Like
│   ├── views.py          # All view functions
│   ├── forms.py          # AddTweetForm, ProfileForm, RegisterForm
│   ├── admin.py          # Admin configuration with inline images
│   ├── urls.py           # App URL routing
│   ├── static/tweetapp/
│   │   └── customform.css  # Dark theme styling
│   ├── templates/tweetapp/
│   │   ├── listtweet.html        # Main feed with card grid
│   │   ├── profile.html          # User profile page
│   │   ├── edit_profile.html     # Profile editor
│   │   ├── addtwetbyform.html    # Tweet creation form
│   │   └── addtweet.html         # Basic tweet form
│   └── templatetags/     # Custom template filters
├── templates/
│   ├── base.html          # Base template with navbar
│   └── registration/
│       ├── login.html
│       └── register.html
├── media/                 # Uploaded images (gitignored)
└── manage.py
```

---

## 🗄️ Database Models

```
Tweet          → user, nickname, message, created_at
TweetImage     → tweet (FK), image
Profile        → user (1-1), bio, profile_image, first_name, last_name, age
Like           → user (FK), tweet (FK), created_at  [unique_together]
Comment        → user (FK), tweet (FK), message, created_at
```

---

## 🚀 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Ardakorkmaz0/Tweety.git
cd Tweety
```

### 2. Install dependencies
```bash
pip install django pillow
```

### 3. Run migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create superuser
```bash
python manage.py createsuperuser
```

### 5. Run the server
```bash
python manage.py runserver
```

### 6. Open in browser
```
http://127.0.0.1:8000/tweetapp/
```

---

## 🎨 Design

The app features a custom dark theme with:
- Dark navy background (`#0f0f1a`)
- Card-based tweet layout with hover animations
- Gradient buttons and navbar
- Green accent color (`#10f28c`) for usernames
- Responsive grid (5 columns on desktop, 1 on mobile)
- Modal popups for full tweet view with image carousel
- Consistent styling across all pages

---

## 📌 Notes

- This is a learning project built for educational purposes
- Uses Django's built-in authentication system
- SQLite for development (not recommended for production)
- Media files are stored locally in the `media/` directory
- `DEBUG = True` — not configured for production deployment

---

## 👨‍💻 Author

**Arda Korkmaz**
- Computer Engineering Student 
- GitHub: [@Ardakorkmaz0](https://github.com/Ardakorkmaz0)
