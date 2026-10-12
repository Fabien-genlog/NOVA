
import os
import re
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from io import BytesIO

from flask import (
    Flask, request, redirect, url_for,
    session, render_template_string, flash, abort
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from PIL import Image, UnidentifiedImageError



# ==================================================
# 1. FANOMANANA NY APPLICATION NOVA
# ==================================================

app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.environ.get(
        "NOVA_SECRET_KEY",
        "nova-dev-key-change-this-before-production"
    ),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.environ.get("NOVA_HTTPS", "0") == "1"
    ),
    PERMANENT_SESSION_LIFETIME=3600,
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)

csrf = CSRFProtect(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nova.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

Image.MAX_IMAGE_PIXELS = 20_000_000


# ==================================================
# 2. DATABASE SQLITE
# ==================================================

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with db() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password TEXT NOT NULL,
                photo TEXT
            );

            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                image TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id)
                    REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS likes (
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                PRIMARY KEY(user_id, post_id),
                FOREIGN KEY(user_id)
                    REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(post_id)
                    REFERENCES posts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id)
                    REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(post_id)
                    REFERENCES posts(id) ON DELETE CASCADE
            );
        """)


init_db()


# ==================================================
# 3. MPAMPIASA SY FIAROVANA NY PEJY
# ==================================================

def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    with db() as con:
        return con.execute(
            "SELECT id, username, photo FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Midira amin'ny kaontinao aloha.")
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


# ==================================================
# 4. FITAHIRIANA SARY
# ==================================================

def save_image(file):
    if not file or not file.filename:
        return None

    raw = file.stream.read(5 * 1024 * 1024 + 1)

    if not raw:
        return None

    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("Tsy tokony hihoatra ny 5 MB ny sary.")

    try:
        with Image.open(BytesIO(raw)) as im:
            if im.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError(
                    "JPG, PNG na WEBP ihany no azo ampidirina."
                )
            im.verify()

        with Image.open(BytesIO(raw)) as im:
            im = im.convert("RGB")
            im.thumbnail((1200, 1200))

            name = secrets.token_hex(16) + ".jpg"
            path = os.path.join(UPLOAD_DIR, name)

            im.save(path, "JPEG", quality=85, optimize=True)

        return name

    except ValueError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError
    ):
        raise ValueError("Tsy sary mety io fichier io.")


def remove_image(name):
    if not name:
        return

    path = os.path.join(UPLOAD_DIR, name)

    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


# ==================================================
# 5. ENDREKY NY NOVA
# ==================================================

STYLE = """
* { box-sizing: border-box; }

body {
    margin: 0;
    background: #f0f2f5;
    color: #202133;
    font-family: Arial, Helvetica, sans-serif;
}

header {
    background: white;
    padding: 12px 5%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    box-shadow: 0 2px 12px #0000000b;
    position: sticky;
    top: 0;
    z-index: 5;
}

.logo {
    font-size: 30px;
    font-weight: 900;
    color: #6855e8;
    text-decoration: none;
}

.logo span { color: #25253a; }

a { color: #6855e8; text-decoration: none; }

button, .btn {
    border: 0;
    border-radius: 10px;
    padding: 11px 15px;
    background: #6855e8;
    color: white;
    font-weight: bold;
    cursor: pointer;
    display: inline-block;
    font-size: 14px;
}

button:hover, .btn:hover { opacity: .88; }

.secondary {
    background: #efedff;
    color: #6855e8;
}

.container {
    max-width: 720px;
    margin: 25px auto;
    padding: 0 14px;
}

.card {
    background: white;
    padding: 20px;
    margin-bottom: 18px;
    border-radius: 16px;
    box-shadow: 0 4px 20px #2020400a;
    overflow-wrap: anywhere;
}

input, textarea {
    width: 100%;
    padding: 12px;
    margin: 7px 0 14px;
    border: 1px solid #e0e2ed;
    border-radius: 10px;
    font: inherit;
    background: white;
}

textarea {
    min-height: 90px;
    resize: vertical;
}

label { font-size: 13px; font-weight: bold; }

.avatar {
    width: 48px;
    height: 48px;
    object-fit: cover;
    border-radius: 50%;
    background: #e9e5ff;
    flex-shrink: 0;
}

.profile-head {
    display: flex;
    align-items: center;
    gap: 12px;
}

.profile-head h3 { margin: 0 0 5px; }

.muted { color: #9295a8; font-size: 12px; }

.post-image {
    width: 100%;
    max-height: 520px;
    object-fit: contain;
    border-radius: 12px;
    margin-top: 10px;
    background: #f5f5f5;
}

.actions {
    display: flex;
    gap: 10px;
    margin-top: 12px;
}

.actions form { flex: 1; }
.actions button { width: 100%; }

.notice {
    padding: 12px;
    border-radius: 10px;
    background: #e7f7ed;
    color: #246b43;
    margin-bottom: 12px;
}

.auth {
    max-width: 440px;
    margin: 45px auto;
    padding: 0 14px;
}

.center { text-align: center; }

.row {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}

.comment {
    background: #f1f3f9;
    padding: 10px 12px;
    border-radius: 12px;
    margin: 10px 0;
}

.comment p {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.search-box { max-width: 280px; }

@media(max-width: 500px) {
    header { padding: 12px; }
    .logo { font-size: 25px; }
    .card { padding: 15px; }
    .container { margin-top: 15px; }
}
"""


SHELL = """
<!doctype html>
<html lang="mg">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} — NOVA</title>
    <style>""" + STYLE + """</style>
</head>
<body>
<header>
    <a class="logo" href="{{ url_for('home') }}">NOVA<span>.</span></a>

    {% if user %}
    <form method="get" action="{{ url_for('home') }}"
          class="search-box">
        <input name="q" placeholder="Mitady publication..."
               value="{{ search_query }}"
               style="margin:0">
    </form>

    <div class="row">
        <a href="{{ url_for('profile') }}">Profil</a>
        <a class="btn" href="{{ url_for('logout') }}">Hivoaka</a>
    </div>
    {% else %}
    <div class="row">
        <a href="{{ url_for('login') }}">Connexion</a>
        <a class="btn" href="{{ url_for('register') }}">Inscription</a>
    </div>
    {% endif %}
</header>

<main class="{{ page_class }}">
    {% for message in get_flashed_messages() %}
        <div class="notice">{{ message }}</div>
    {% endfor %}

    {{ content|safe }}
</main>
</body>
</html>
"""


def page(title, content, user=None, page_class="container",
         search_query=""):
    return render_template_string(
        SHELL,
        title=title,
        content=content,
        user=user,
        page_class=page_class,
        search_query=search_query
    )


# ==================================================
# 6. FORMULAIRE INSCRIPTION SY CONNEXION
# ==================================================

AUTH_FORM = """
<section class="card">
    <h2>{{ heading }}</h2>
    <p class="muted">{{ description }}</p>

    <form method="post">
    <input type="hidden" name="csrf_token"
           value="{{ csrf_token() }}">
        <label>Anarana mpampiasa</label>
        <input name="username" minlength="3" maxlength="30"
               autocomplete="username" required>

        <label>Tenimiafina</label>
        <input type="password" name="password" minlength="8"
               autocomplete="{{ autocomplete }}" required>

        <button type="submit">{{ button }}</button>
    </form>

    <p>{{ other_text }}
       <a href="{{ other_url }}">{{ other_link }}</a>
    </p>
</section>
"""


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not re.fullmatch(r"[\w-]{3,30}", username, re.UNICODE):
            flash("Anarana 3–30 litera, isa, _ na - ihany.")
        elif len(password) < 8:
            flash("Tokony hanana litera 8 farafahakeliny ny tenimiafina.")
        else:
            try:
                with db() as con:
                    cur = con.execute(
                        "INSERT INTO users(username, password) VALUES (?, ?)",
                        (username, generate_password_hash(password))
                    )
                    session.clear()
                    session["user_id"] = cur.lastrowid

                return redirect(url_for("home"))

            except sqlite3.IntegrityError:
                flash("Efa misy mampiasa io anarana io.")

    content = render_template_string(
        AUTH_FORM,
        heading="Mamorona kaonty NOVA",
        description="Midira ao amin'ny vondrom-piarahamonina NOVA.",
        button="Hisoratra anarana",
        autocomplete="new-password",
        other_text="Efa manana kaonty?",
        other_url=url_for("login"),
        other_link="Hiditra"
    )

    return page("Inscription", content, page_class="auth")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with db() as con:
            user = con.execute(
                "SELECT id, username, password FROM users "
                "WHERE username = ? COLLATE NOCASE",
                (username,)
            ).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("home"))

        flash("Tsy marina ny anarana na ny tenimiafina.")

    content = render_template_string(
        AUTH_FORM,
        heading="Connexion NOVA",
        description="Ampidiro ny mombamomba ny kaontinao.",
        button="Hiditra",
        autocomplete="current-password",
        other_text="Mbola tsy manana kaonty?",
        other_url=url_for("register"),
        other_link="Hisoratra anarana"
    )

    return page("Connexion", content, page_class="auth")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==================================================
# 7. PEJY FANDRAISANA SY FIL D'ACTUALITE
# ==================================================

@app.route("/")
@login_required
def home():
    user = current_user()
    search_query = request.args.get("q", "").strip()

    with db() as con:
        if search_query:
            posts = con.execute("""
                SELECT posts.*, users.username, users.photo,
                    (SELECT COUNT(*) FROM likes
                     WHERE likes.post_id = posts.id) AS like_count,
                    (SELECT COUNT(*) FROM likes
                     WHERE likes.post_id = posts.id
                     AND likes.user_id = ?) AS liked,
                    (SELECT COUNT(*) FROM comments
                     WHERE comments.post_id = posts.id) AS comment_count
                FROM posts
                JOIN users ON users.id = posts.user_id
                WHERE posts.content LIKE ?
                   OR users.username LIKE ?
                ORDER BY posts.id DESC
            """, (
                user["id"],
                "%" + search_query + "%",
                "%" + search_query + "%"
            )).fetchall()
        else:
            posts = con.execute("""
                SELECT posts.*, users.username, users.photo,
                    (SELECT COUNT(*) FROM likes
                     WHERE likes.post_id = posts.id) AS like_count,
                    (SELECT COUNT(*) FROM likes
                     WHERE likes.post_id = posts.id
                     AND likes.user_id = ?) AS liked,
                    (SELECT COUNT(*) FROM comments
                     WHERE comments.post_id = posts.id) AS comment_count
                FROM posts
                JOIN users ON users.id = posts.user_id
                ORDER BY posts.id DESC
            """, (user["id"],)).fetchall()

        all_comments = con.execute("""
            SELECT comments.id, comments.post_id,
                   comments.content, comments.created_at,
                   users.username
            FROM comments
            JOIN users ON users.id = comments.user_id
            ORDER BY comments.id ASC
        """).fetchall()

    comments_by_post = {}
    for comment in all_comments:
        comments_by_post.setdefault(
            comment["post_id"], []
        ).append(comment)

    content = render_template_string("""
    <section class="card">
        <div class="profile-head">
            {% if user.photo %}
                <img class="avatar"
                     src="{{ url_for('static', filename='uploads/' + user.photo) }}">
            {% else %}
                <div class="avatar center"
                     style="display:grid;place-items:center">
                    {{ user.username[0]|upper }}
                </div>
            {% endif %}

            <div>
                <h3>Tongasoa, {{ user.username }}!</h3>
                <span class="muted">Inona no vaovao androany?</span>
            </div>
        </div>

        <form method="post" action="{{ url_for('publish') }}"
              enctype="multipart/form-data">
            <textarea name="content" maxlength="2000"
                      placeholder="Zarao amin'ny NOVA..."
                      ></textarea>

            <label>Sary (JPG, PNG na WEBP, 5 MB farafahabetsany)</label>
            <input type="file" name="image"
                   accept="image/jpeg,image/png,image/webp">

            <button type="submit">＋ Publier</button>
        </form>
    </section>

    <h2>📰 Fil d'actualité</h2>

    {% for post in posts %}
    <article class="card">
        <div class="profile-head">
            {% if post.photo %}
                <img class="avatar"
                     src="{{ url_for('static', filename='uploads/' + post.photo) }}">
            {% else %}
                <div class="avatar center"
                     style="display:grid;place-items:center">
                    {{ post.username[0]|upper }}
                </div>
            {% endif %}

            <div>
                <h3>{{ post.username }}</h3>
                <span class="muted">{{ post.created_at }}</span>
            </div>
        </div>

        {% if post.content %}
            <p style="white-space:pre-wrap;line-height:1.6">
                {{ post.content }}
            </p>
        {% endif %}

        {% if post.image %}
            <img class="post-image"
                 src="{{ url_for('static', filename='uploads/' + post.image) }}">
        {% endif %}

        <div class="actions">
            <form method="post"
                  action="{{ url_for('like', post_id=post.id) }}">
                <button class="secondary" type="submit">
                    {{ "💜 Efa tia" if post.liked else "❤️ J'aime" }}
                    ({{ post.like_count }})
                </button>
            </form>
        </div>

        <section style="margin-top:18px">
            <h4>💬 Commentaires ({{ post.comment_count }})</h4>

            {% for comment in comments_by_post.get(post.id, []) %}
                <div class="comment">
                    <strong>{{ comment.username }}</strong>
                    <p>{{ comment.content }}</p>
                    <small class="muted">{{ comment.created_at }}</small>
                </div>
            {% endfor %}

            <form method="post"
                  action="{{ url_for('add_comment', post_id=post.id) }}">
                <textarea name="content" maxlength="500"
                          placeholder="Manorata commentaire..."
                          required style="min-height:65px"></textarea>
                <button type="submit">Handefa commentaire</button>
            </form>
        </section>
    </article>
    {% else %}
        <section class="card center">
            <h3>✨ Mbola tsy misy publication</h3>
            <p>Atombohy amin'ny publication voalohany!</p>
        </section>
    {% endfor %}
    """, user=user, posts=posts,
       comments_by_post=comments_by_post)

    return page(
        "Fandraisana", content, user,
        search_query=search_query
    )


# ==================================================
# 8. MAMOAKA PUBLICATION
# ==================================================

@app.route("/publish", methods=["POST"])
@login_required
def publish():
    user = current_user()
    content = request.form.get("content", "").strip()
    image = None

    if len(content) > 2000:
        flash("Tsy tokony hihoatra ny 2000 litera ny publication.")
        return redirect(url_for("home"))

    try:
        image = save_image(request.files.get("image"))

        if not content and not image:
            flash("Manorata zavatra na mifidiana sary aloha.")
            return redirect(url_for("home"))

        with db() as con:
            con.execute(
                """
                INSERT INTO posts(user_id, content, image, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user["id"],
                    content,
                    image,
                    datetime.now().strftime("%d/%m/%Y %H:%M")
                )
            )

        flash("Voapublish ny hafatrao!")

    except ValueError as error:
        remove_image(image)
        flash(str(error))

    return redirect(url_for("home"))


# ==================================================
# 9. J'AIME
# ==================================================

@app.route("/like/<int:post_id>", methods=["POST"])
@login_required
def like(post_id):
    user = current_user()

    with db() as con:
        exists = con.execute(
            "SELECT id FROM posts WHERE id = ?", (post_id,)
        ).fetchone()

        if not exists:
            abort(404)

        liked = con.execute(
            "SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?",
            (user["id"], post_id)
        ).fetchone()

        if liked:
            con.execute(
                "DELETE FROM likes WHERE user_id = ? AND post_id = ?",
                (user["id"], post_id)
            )
        else:
            con.execute(
                "INSERT INTO likes(user_id, post_id) VALUES (?, ?)",
                (user["id"], post_id)
            )

    return redirect(url_for("home"))


# ==================================================
# 10. COMMENTAIRES
# ==================================================

@app.route("/comment/<int:post_id>", methods=["POST"])
@login_required
def add_comment(post_id):
    user = current_user()
    content = request.form.get("content", "").strip()

    if not content:
        flash("Tsy maintsy manoratra commentaire ianao.")
        return redirect(url_for("home"))

    if len(content) > 500:
        flash("Tsy tokony hihoatra ny 500 litera ny commentaire.")
        return redirect(url_for("home"))

    with db() as con:
        post = con.execute(
            "SELECT id FROM posts WHERE id = ?", (post_id,)
        ).fetchone()

        if not post:
            abort(404)

        con.execute(
            """
            INSERT INTO comments
                (user_id, post_id, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user["id"],
                post_id,
                content,
                datetime.now().strftime("%d/%m/%Y %H:%M")
            )
        )

    flash("Voaray ny commentaire-nao!")
    return redirect(url_for("home"))


# ==================================================
# 11. PROFIL SY FANOVANA SARY
# ==================================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()

    if request.method == "POST":
        new_photo = None

        try:
            new_photo = save_image(request.files.get("photo"))

            if not new_photo:
                flash("Misafidiana sary aloha.")
                return redirect(url_for("profile"))

            with db() as con:
                con.execute(
                    "UPDATE users SET photo = ? WHERE id = ?",
                    (new_photo, user["id"])
                )

            remove_image(user["photo"])
            flash("Niova ny sary profil-nao!")

        except ValueError as error:
            remove_image(new_photo)
            flash(str(error))

        return redirect(url_for("profile"))

    with db() as con:
        my_posts = con.execute("""
            SELECT posts.*,
                (SELECT COUNT(*) FROM likes
                 WHERE likes.post_id = posts.id) AS like_count,
                (SELECT COUNT(*) FROM comments
                 WHERE comments.post_id = posts.id) AS comment_count
            FROM posts
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user["id"],)).fetchall()

    content = render_template_string("""
    <section class="card center">
        {% if user.photo %}
            <img class="avatar"
                 style="width:110px;height:110px"
                 src="{{ url_for('static', filename='uploads/' + user.photo) }}">
        {% else %}
            <div class="avatar center"
                 style="width:110px;height:110px;margin:auto;
                        display:grid;place-items:center;font-size:35px">
                {{ user.username[0]|upper }}
            </div>
        {% endif %}

        <h2>{{ user.username }}</h2>
        <p class="muted">Ny profil NOVA</p>

        <form method="post" enctype="multipart/form-data">
            <label>Safidio ny sary profil</label>
            <input type="file" name="photo"
                   accept="image/jpeg,image/png,image/webp" required>
            <button type="submit">Ovay ny sary profil</button>
        </form>

        <p><a href="{{ url_for('home') }}">← Miverina any amin'ny fandraisana</a></p>
    </section>

    <h2>Ny publications-ko ({{ my_posts|length }})</h2>

    {% for post in my_posts %}
        <article class="card">
            <span class="muted">{{ post.created_at }}</span>

            {% if post.content %}
                <p style="white-space:pre-wrap">{{ post.content }}</p>
            {% endif %}

            {% if post.image %}
                <img class="post-image"
                     src="{{ url_for('static', filename='uploads/' + post.image) }}">
            {% endif %}

            <p>❤️ {{ post.like_count }} J'aime
               · 💬 {{ post.comment_count }} commentaires</p>
        </article>
    {% else %}
        <section class="card center">
            Mbola tsy manana publication ianao.
        </section>
    {% endfor %}
    """, user=user, my_posts=my_posts)

    return page("Profil", content, user)
    return page("Profil", content, user)


# ==================================================
# 12. FITANTANANA ERREUR
# ==================================================

@app.errorhandler(413)
def too_large(error):
    return "Lehibe loatra ny fichier. 5 MB no fetra.", 413


# ==================================================
# 13. FANDEFASANA NY APPLICATION
# ==================================================

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
