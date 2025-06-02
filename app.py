from flask import Flask, jsonify, request, redirect, render_template, url_for, flash
import psycopg2
import math

app = Flask(__name__)
app.secret_key = "gizli_anahtar"

# PostgreSQL bağlantısı
conn = psycopg2.connect(
    host="dpg-d0untvp5pdvs73a276e0-a.frankfurt-postgres.render.com",
    database="sensor_data_db_1mjp",
    user="sensor_data_db_1mjp_user",
    password="OKPCNZaDSyCp9tyyzOiEipYsjyQTb8NW"
)
cursor = conn.cursor()

# Hissedilen sıcaklığı hesaplayan fonksiyon
def calculate_heat_index(T, RH):
    HI = (-8.78469475556 + 1.61139411 * T + 2.33854883889 * RH
          - 0.14611605 * T * RH - 0.012308094 * (T ** 2)
          - 0.0164248277778 * (RH ** 2) + 0.002211732 * (T ** 2) * RH
          + 0.00072546 * T * (RH ** 2) - 0.000003582 * (T ** 2) * (RH ** 2))
    return round(HI, 2)

@app.route('/')
def home():
    return redirect("/harita", code=301)

@app.route('/data', methods=['GET'])
def get_data():
    cursor.execute("SELECT latitude, longitude, temperature, humidity FROM sensor_okuma")
    data = cursor.fetchall()
    
    result = []
    for row in data:
        latitude, longitude, temperature, humidity = row
        heat_index = calculate_heat_index(temperature, humidity)  # Hissedilen sıcaklık hesaplanıyor
        result.append({
            "latitude": latitude,
            "longitude": longitude,
            "temperature": temperature,
            "humidity": humidity,
            "heat_index": heat_index  # API'ye eklendi
        })
    
    return jsonify(result)

@app.route('/veri', methods=['GET', 'POST'])
def veri_ekle():
    if request.method == 'POST':
        try:
            latitude = float(request.form['latitude'])
            longitude = float(request.form['longitude'])
            temperature = float(request.form['temperature'])
            humidity = float(request.form['humidity'])

            query = "INSERT INTO sensor_okuma (latitude, longitude, temperature, humidity) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (latitude, longitude, temperature, humidity))
            db.commit()

            flash("Veri başarıyla eklendi!", "success")
            return redirect(url_for('veri_ekle'))
        
        except Exception as e:
            flash(f"Hata: {e}", "danger")

    return render_template("veri_form.html")

@app.route("/harita", methods=["GET"])
def olustur():
    return render_template("data.html")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
