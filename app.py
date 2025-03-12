import os
import random

#from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
import json
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import requests
from helpers import apology, login_required


from flask_dance.contrib.google import make_google_blueprint, google
from flask_sqlalchemy import SQLAlchemy

import sqlite3
# Configure application
app = Flask(__name__)
app.secret_key = '123'

# Configuración de la base de datos
DATABASE = 'dunder.db'

def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            google_id TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Llama a init_db al iniciar la aplicación
@app.before_request
def initialized():
    global initialized
    if not initialized:
        init_db()
        initialized = True


# Configuración de las credenciales de OAuth 2.0
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "46387988998-n11pfgthpv2ak755bhbe23qg1ij6clt3.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "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")
REDIRECT_URI = "https://d39b-2803-2d60-1118-f82-e8a6-7437-bb55-49c9.ngrok-free.app/login/google/authorized"


# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configura la autenticación de Google
google_bp = make_google_blueprint(client_id=GOOGLE_CLIENT_ID,
                                  client_secret=GOOGLE_CLIENT_SECRET,
                                  redirect_to="login")
app.register_blueprint(google_bp, url_prefix="/login")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(50), unique=True, nullable=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/diet')
def diet_types():
    return render_template('diet_types.html')

@app.route('/simple_diet', methods=['GET', 'POST'])
def simple_diet():
    if request.method == 'POST':
        gender = request.form['gender']
        age = int(request.form['age'])
        weight = float(request.form['weight'])
        height = float(request.form['height'])
        goal = request.form['goal']

        # Lógica para generar el plan de dieta
        diet_plan = generate_diet_plan(gender, age, weight, height, goal, "simple")
        
        return render_template('diet_results.html', diet_plan=diet_plan)

    return render_template('simple_diet.html')

@app.route('/fitness_diet', methods=['GET', 'POST'])
def fitness_diet():
    if request.method == 'POST':
        gender = request.form['gender']
        age = int(request.form['age'])
        weight = float(request.form['weight'])
        height = float(request.form['height'])
        goal = request.form['goal']

        # Lógica para generar el plan de dieta
        diet_plan = generate_diet_plan(gender, age, weight, height, goal, "fitness")
        
        return render_template('diet_results.html', diet_plan=diet_plan)

    return render_template('fitness_diet.html')

def generate_diet_plan(gender, age, weight, height, goal, diet_type):
    # Calcular la TMB (Tasa Metabólica Basal) usando la ecuación de Mifflin-St Jeor
    if gender == 'male':
        tmb = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        tmb = 10 * weight + 6.25 * height - 5 * age - 161
    
    # Ajustar la TMB según el objetivo de la dieta
    if goal == 'lose':
        calories = tmb - 500
    elif goal == 'maintain':
        calories = tmb
    elif goal == 'gain':
        calories = tmb + 300
    elif goal == 'definicion':
        calories = tmb - 750
    elif goal == 'volumen':
        calories = tmb + 750
    else:
        raise ValueError("Objetivo de dieta no válido")  # Manejo de error para objetivo no válido

    # Ajustar macronutrientes según el tipo de dieta
    if diet_type == 'simple':
        protein = 1.5 * weight
        fat = 0.8 * weight
        carbs = (calories - (protein * 4 + fat * 9)) / 4
    elif diet_type == 'fitness':
        protein = 2.0 * weight
        fat = 1.0 * weight
        carbs = (calories - (protein * 4 + fat * 9)) / 4
    else:
        raise ValueError("Tipo de dieta no válido")  # Manejo de error para tipo de dieta no válido

    # Crear el plan de comidas
    meal_plan = create_meal_plan(diet_type, goal)
    
    diet_plan = {
        'calories': round(calories),
        'protein': round(protein),
        'carbs': round(carbs),
        'fat': round(fat),
        'breakfast': meal_plan['breakfast'],
        'lunch': meal_plan['lunch'],
        'snack': meal_plan['snack'],
        'dinner': meal_plan['dinner']
    }
    
    return diet_plan

def create_meal_plan(diet_type, goal):
    meals = {
        'simple': {
            'lose': {
                'breakfast': [
                    'Avena con frutas y nueces', 
                    'Batido verde con espinacas y frutas', 
                    'Yogur con granola y frutas',
                    'Tostadas integrales con aguacate', 
                    'Claras de huevo revueltas con espinacas',
                    'Smoothie de proteínas con bayas', 
                    'Frutas frescas con queso cottage', 
                    'Batido de espinacas y plátano', 
                    'Tostadas de pan integral con tomate', 
                    'Porridge de avena con canela'
                ],
                'lunch': [
                    'Ensalada de pollo con aguacate y aderezo ligero', 
                    'Tacos de lechuga con pavo', 
                    'Sopa de verduras con pollo',
                    'Ensalada de quinoa con verduras asadas', 
                    'Pechuga de pollo a la parrilla con espárragos',
                    'Ensalada de atún con espinacas', 
                    'Salmón a la parrilla con ensalada de espinacas', 
                    'Pavo a la plancha con brócoli', 
                    'Wrap de pollo con vegetales', 
                    'Ensalada César con camarones'
                ],
                'snack': [
                    'Batido de proteína con almendras', 
                    'Hummus con vegetales', 
                    'Manzana con mantequilla de maní',
                    'Zanahorias baby con guacamole', 
                    'Rodajas de pepino con queso feta',
                    'Trozos de piña con yogur', 
                    'Moras con queso cottage', 
                    'Batido de proteínas con espinacas', 
                    'Pepino con hummus', 
                    'Palitos de apio con mantequilla de almendra'
                ],
                'dinner': [
                    'Pescado al horno con vegetales al vapor', 
                    'Pollo al curry con arroz de coliflor', 
                    'Tortilla de vegetales con ensalada',
                    'Salmón a la parrilla con brócoli', 
                    'Pavo a la plancha con espinacas',
                    'Gambas a la plancha con ensalada', 
                    'Pollo al horno con espárragos', 
                    'Filete de ternera con ensalada', 
                    'Ensalada de garbanzos con atún', 
                    'Sopa de tomate con albahaca'
                ]
            },
            'maintain': {
                'breakfast': [
                    'Tostadas integrales con aguacate y huevo', 
                    'Smoothie de frutas y proteínas', 
                    'Panqueques de avena con miel',
                    'Huevos revueltos con tomate y espinacas', 
                    'Tostadas de pan integral con mantequilla de almendra',
                    'Batido de proteínas con espinacas', 
                    'Omelette con champiñones y queso', 
                    'Yogur griego con nueces', 
                    'Avena con plátano y nueces', 
                    'Cereales integrales con leche'
                ],
                'lunch': [
                    'Pavo a la plancha con quinoa y brócoli', 
                    'Ensalada César con pollo', 
                    'Wrap de pavo con vegetales',
                    'Salmón a la parrilla con espinacas', 
                    'Ensalada de pollo con quinoa',
                    'Sandwich integral de atún', 
                    'Pechuga de pollo con arroz integral', 
                    'Bowl de quinoa con vegetales', 
                    'Pollo al horno con ensalada', 
                    'Pasta integral con salsa de tomate y pollo'
                ],
                'snack': [
                    'Yogur griego con frutas', 
                    'Barra de granola casera', 
                    'Batido de plátano y leche de almendras',
                    'Rodajas de zanahoria con hummus', 
                    'Tostadas de pan integral con aguacate',
                    'Manzana con queso', 
                    'Trozos de piña con yogur', 
                    'Frutas frescas con nueces', 
                    'Batido de proteínas con espinacas', 
                    'Palitos de apio con mantequilla de almendra'
                ],
                'dinner': [
                    'Pasta integral con salsa de tomate y pollo', 
                    'Pollo al horno con vegetales', 
                    'Salmón con ensalada de espinacas',
                    'Sopa de pollo con vegetales', 
                    'Pechuga de pollo con espárragos',
                    'Filete de ternera con ensalada', 
                    'Ensalada de garbanzos con atún', 
                    'Pollo al curry con arroz de coliflor', 
                    'Salmón a la parrilla con quinoa', 
                    'Pollo a la plancha con batata y brócoli'
                ]
            },
            'gain': {
                'breakfast': [
                    'Omelette con espinacas y queso, pan integral', 
                    'Batido de proteínas con avena', 
                    'Huevos revueltos con pavo y pan integral',
                    'Panqueques de avena con mantequilla de maní', 
                    'Tostadas de aguacate con huevo',
                    'Batido de proteínas con espinacas', 
                    'Tostadas de pan integral con queso', 
                    'Avena con plátano y nueces', 
                    'Smoothie de proteínas con frutas', 
                    'Yogur griego con frutas y miel'
                ],
                'lunch': [
                    'Sándwich de atún con ensalada y batata', 
                    'Pasta con albóndigas de pavo', 
                    'Bowl de quinoa con pollo y aguacate',
                    'Pechuga de pollo con arroz integral', 
                    'Wrap de pollo con vegetales',
                    'Ensalada César con pollo', 
                    'Sandwich integral de atún', 
                    'Pavo a la plancha con espinacas', 
                    'Salmón a la parrilla con ensalada de espinacas', 
                    'Ensalada de pollo con quinoa'
                ],
                'snack': [
                    'Frutos secos y plátano', 
                    'Batido de proteínas con mantequilla de maní', 
                    'Tostadas de aguacate con huevo',
                    'Rodajas de zanahoria con hummus', 
                    'Batido de proteínas con espinacas',
                    'Trozos de piña con yogur', 
                    'Manzana con queso', 
                    'Yogur griego con frutas y nueces', 
                    'Trozos de piña con yogur', 
                    'Batido de proteínas con espinacas'
                ],
                'dinner': [
                    'Ternera a la parrilla con arroz integral y espárragos', 
                    'Pollo al curry con arroz', 
                    'Pescado a la plancha con puré de papas',
                    'Salmón a la parrilla con espinacas', 
                    'Pollo al horno con vegetales',
                    'Filete de ternera con ensalada', 
                    'Ensalada de garbanzos con atún', 
                    'Sopa de pollo con vegetales', 
                    'Salmón a la parrilla con quinoa', 
                    'Pollo a la plancha con batata y brócoli'
                ]
            }
        },
        'fitness': {
            'definicion': {
                'breakfast': [
                    'Claras de huevo revueltas con espinacas y pimientos', 
                    'Avena con proteína en polvo', 
                    'Smoothie de espinacas y frutas',
                    'Batido de proteínas con espinacas', 
                    'Tostadas de aguacate con huevo',
                    'Batido de proteínas con avena', 
                    'Tostadas de pan integral con tomate', 
                    'Yogur griego con nueces', 
                    'Avena con plátano y nueces', 
                    'Smoothie de espinacas y plátano'
                ],
                'lunch': [
                    'Pollo a la parrilla con batata y brócoli', 
                    'Ensalada de atún con quinoa', 
                    'Tacos de lechuga con pollo',
                    'Salmón a la parrilla con espinacas', 
                    'Ensalada de pollo con quinoa',
                    'Wrap de pavo con vegetales', 
                    'Sandwich integral de atún', 
                    'Pavo a la plancha con espinacas', 
                    'Salmón a la parrilla con ensalada de espinacas', 
                    'Ensalada de pollo con quinoa'
                ],
                'snack': [
                    'Batido de proteína y una manzana', 
                    'Yogur griego con frutas y nueces', 
                    'Hummus con zanahorias',
                    'Rodajas de zanahoria con hummus', 
                    'Tostadas de pan integral con aguacate',
                    'Manzana con queso', 
                    'Batido de proteínas con espinacas', 
                    'Palitos de apio con mantequilla de almendra', 
                    'Frutas frescas con nueces', 
                    'Trozos de piña con yogur'
                ],
                'dinner': [
                    'Salmón a la plancha con quinoa y espárragos', 
                    'Pollo al horno con vegetales', 
                    'Carne de res magra con espárragos y batata',
                    'Pechuga de pollo con espárragos', 
                    'Pollo a la plancha con batata y brócoli',
                    'Filete de ternera con ensalada', 
                    'Ensalada de garbanzos con atún', 
                    'Pollo al curry con arroz de coliflor', 
                    'Salmón a la parrilla con quinoa', 
                    'Sopa de pollo con vegetales'
                ]
            },
            'volumen': {
                'breakfast': [
                    'Avena con proteína en polvo y bayas', 
                    'Tortilla de claras de huevo con espinacas', 
                    'Batido de proteínas con plátano',
                    'Batido de proteínas con avena', 
                    'Tostadas de aguacate con huevo',
                    'Yogur griego con frutas y miel', 
                    'Avena con plátano y nueces', 
                    'Tostadas de pan integral con mantequilla de almendra', 
                    'Smoothie de proteínas con frutas', 
                    'Omelette con champiñones y queso'
                ],
                'lunch': [
                    'Pechuga de pavo con arroz integral y espinacas', 
                    'Bowl de quinoa con pollo y vegetales', 
                    'Sándwich de pollo con aguacate y ensalada',
                    'Salmón a la parrilla con espinacas', 
                    'Ensalada de pollo con quinoa',
                    'Wrap de pollo con vegetales', 
                    'Sandwich integral de atún', 
                    'Pavo a la plancha con espinacas', 
                    'Salmón a la parrilla con ensalada de espinacas', 
                    'Ensalada de pollo con quinoa'
                ],
                'snack': [
                    'Yogur griego con miel y nueces', 
                    'Batido de proteínas con mantequilla de maní', 
                    'Frutos secos y pasas',
                    'Rodajas de zanahoria con hummus', 
                    'Tostadas de pan integral con aguacate',
                    'Manzana con queso', 
                    'Batido de proteínas con espinacas', 
                    'Palitos de apio con mantequilla de almendra', 
                    'Frutas frescas con nueces', 
                    'Trozos de piña con yogur'
                ],
                'dinner': [
                    'Pollo al horno con batata y brócoli', 
                    'Salmón a la parrilla con arroz integral', 
                    'Ternera a la parrilla con vegetales',
                    'Pechuga de pollo con espárragos', 
                    'Pollo a la plancha con batata y brócoli',
                    'Filete de ternera con ensalada', 
                    'Ensalada de garbanzos con atún', 
                    'Pollo al curry con arroz de coliflor', 
                    'Salmón a la parrilla con quinoa', 
                    'Sopa de pollo con vegetales'
                ]
            }
        }
    }

    selected_meals = {}
    for meal_time in ['breakfast', 'lunch', 'snack', 'dinner']:
        selected_meals[meal_time] = random.choice(meals[diet_type][goal][meal_time])
    
    return selected_meals
    
@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/login/google')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))

    resp = google.get("/plus/v1/people/me")
    assert resp.ok, resp.text
    google_info = resp.json()
    google_id = google_info["id"]
    username = google_info["displayName"]

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()
    if not user:
        conn.execute("INSERT INTO users (username, google_id) VALUES (?, ?)", (username, google_id))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()
    conn.close()

    session['user_id'] = user['id']
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not (password == confirmation):
            return render_template("apology.html", message="the passwords do not match"), 400

        if password == "" or confirmation == "" or username == "":
            return render_template("apology.html", message="input is blank"), 400

        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchall()

        if len(rows) == 1:
            conn.close()
            return render_template("apology.html", message="username already exist"), 400
        else:
            hashcode = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            conn.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hashcode))
            conn.commit()
            conn.close()
            return redirect("/")

    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user is None or not check_password_hash(user['hash'], password):
            return render_template("apology.html", message="invalid username and/or password"), 400

        session['user_id'] = user['id']
        return redirect('/')

    return render_template('login.html')

def apology(message, code=400):
    """Render message as an apology to user."""
    return render_template("apology.html", top=code, bottom=message), code

@app.route('/healthy_recipes')
def healthy_recipes():
    return render_template('healthy_recipes.html')

@app.route('/nutrition_tips')
def nutrition_tips():
    return render_template('nutrition_tips.html')


if __name__ == '__main__':
    app.run(debug=True)

