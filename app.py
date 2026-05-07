from flask import Flask, render_template, request, redirect, session, flash
from flask import jsonify
import os
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import mysql.connector

app = Flask(__name__)
app.secret_key = "secret"

UPLOAD_FOLDER = "static/uploads/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Charger le modèle
try:
    model = load_model("model/vgg16_skin_cancer.h5")
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"⚠️ Error loading model: {e}")
    model = None

# Connexion MySQL
try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="skin_cancer_db"
    )
    cursor = db.cursor(dictionary=True)
    print("✅ MySQL connection successful!")
except Exception as e:
    print(f"⚠️ MySQL error: {e}")
    cursor = None

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        
        try:
            if cursor:
                cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (user, pwd))
                result = cursor.fetchone()
            else:
                result = True if user == "doctor" and pwd == "123" else None
            
            if result:
                session["user"] = user
                flash("Login successful ✓", "success")
                return redirect("/dashboard")
            else:
                flash("Login error ✗", "danger")
        except Exception as e:
            if user == "doctor" and pwd == "123":
                session["user"] = user
                flash("Login successful ✓ (fallback mode)", "success")
                return redirect("/dashboard")
            else:
                flash(f"Error: {e}", "danger")
    
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    
    patients_data = []
    benign_count = 0
    malignant_count = 0
    
    if cursor:
        try:
            cursor.execute("SELECT * FROM patients ORDER BY id DESC")
            patients_data = cursor.fetchall()
            
            for p in patients_data:
                if p['result'] == 'Benign':
                    benign_count += 1
                elif p['result'] == 'Malignant':
                    malignant_count += 1
                    
        except Exception as e:
            print(f"Erreur: {e}")
    
    return render_template("dashboard.html", 
                         patients=patients_data,
                         benign_count=benign_count,
                         malignant_count=malignant_count)
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if "user" not in session:
        return redirect("/")
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            age = request.form.get('age')
            file = request.files.get('image')
            
            if not file or file.filename == '':
                flash('Aucune image sélectionnée', "danger")
                return redirect('/predict')
            
            # Sauvegarder l'image
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            
            if model:
                # Prédiction
                img = image.load_img(path, target_size=(224, 224))
                img_array = image.img_to_array(img) / 255.0
                img_array = np.expand_dims(img_array, axis=0)
                
                pred = model.predict(img_array)[0][0]
                
                if pred > 0.5:
                    result = "Malignant"
                    prob = round(pred * 100, 2)
                else:
                    result = "Benign"
                    prob = round((1 - pred) * 100, 2)
                
                # ✅ ENREGISTREMENT DANS LA BASE DE DONNÉES
                if cursor:
                    try:
                        sql = """INSERT INTO patients (nom, age, result, probability, image_path) 
                                 VALUES (%s, %s, %s, %s, %s)"""
                        valeurs = (name, age, result, float(pred), path)
                        cursor.execute(sql, valeurs)
                        db.commit()
                        print(f"✅ Patient enregistré: {name} - {result}")
                        flash("Analyse enregistrée avec succès !", "success")
                    except Exception as db_error:
                        print(f"❌ Erreur DB: {db_error}")
                        flash(f"Erreur sauvegarde: {db_error}", "danger")
                else:
                    flash("Base de données non disponible", "warning")
                
                return render_template("result.html",
                                     result=result,
                                     prob=prob,
                                     img=path)
            else:
                flash("Modèle non disponible", "danger")
                return redirect('/predict')
                
        except Exception as e:
            flash(f"Erreur: {e}", "danger")
            return redirect('/predict')
    
    return render_template("predict.html")
@app.route('/patients')
def patients_list():
    if "user" not in session:
        return redirect("/")
    
    patients_data = []
    if cursor:
        try:
            cursor.execute("SELECT * FROM patients ORDER BY id DESC")
            patients_data = cursor.fetchall()
            print(f"✅ {len(patients_data)} patients chargés")
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    return render_template("patients.html", patients=patients_data)
@app.route('/logout')
def logout():
    session.clear()
    flash("Disconnected", "info")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, port=5000)