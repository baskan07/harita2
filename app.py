from flask import Flask, jsonify ,request, redirect, render_template ,url_for ,flash
import os
import psycopg2

app = Flask(__name__)
app.secret_key = "gizli_anahtar"
# MySQL bağlantısı
db = psycopg2.connect(
    host="dpg-cv501saj1k6c73beessg-a.frankfurt-postgres.render.com",
    database="sensor_data_db",
    user="sensor_user",
    password="s7lCV9If5p67V7WkxgktD3n6JaO3bc7Y"
)
cursor = db.cursor()

@app.route('/')
def home():
    return redirect("/harita", code=301)

@app.route('/sms', methods=['POST'])
def receive_sms():
    try:

        incoming_msg = request.values.get('Body', '').lower()
        sender = request.values.get('From', '')

        print(f"Message from {sender}: {incoming_msg}")  # Debug için
        # Twilio'dan gelen SMS içeriğini al

        # SMS içeriğini ayrıştır
        data = dict(item.split("=") for item in incoming_msg.split("&"))
        latitude = float(data.get("latitude", 0))
        longitude = float(data.get("longitude", 0))
        temperature = float(data.get("temperature", 0))
        humidity = float(data.get("humidity", 0))

        # Veriyi PostgreSQL'e kaydet
        cursor.execute("""
            INSERT INTO sensor_okuma (latitude, longitude, temperature, humidity)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (latitude, longitude) 
            DO UPDATE SET 
                temperature = EXCLUDED.temperature,
                humidity = EXCLUDED.humidity,
                timestamp = CURRENT_TIMESTAMP
        """, (latitude, longitude, temperature, humidity))

        db.commit()
        return "Veri başarıyla kaydedildi!", 200

    except Exception as e:
        return f"Hata: {str(e)}", 400


@app.route('/veri', methods=['GET', 'POST'])
def veri_ekle():
    if request.method == 'POST':
        try:
            latitude = float(request.form['latitude'])
            longitude = float(request.form['longitude'])
            temperature = float(request.form['temperature'])
            humidity = float(request.form['humidity'])

            # Veriyi veritabanına ekle
            query = "INSERT INTO sensor_okuma (latitude, longitude, temperature, humidity) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (latitude, longitude, temperature, humidity))
            db.commit()

            flash("Veri başarıyla eklendi!", "success")
            return redirect(url_for('veri_ekle'))
        
        except Exception as e:
            flash(f"Hata: {e}", "danger")

    return render_template("veri_form.html")

@app.route('/data', methods=['GET'])
def get_data():
    cursor.execute("SELECT latitude, longitude, temperature, humidity, timestamp FROM sensor_okuma")
    data = cursor.fetchall()
    return jsonify([{"latitude": row[0], "longitude": row[1], "temperature": row[2], "humidity": row[3], "timestamp": row[4]} for row in data])

@app.route('/data2', methods=['GET'])
def get_data2():
    cursor.execute("SELECT latitude, longitude, timestamp, servername FROM sunucu_okuma")
    data = cursor.fetchall()
    return jsonify([{"latitude": row[0], "longitude": row[1], "timestamp": row[2], "servername": row[3]} for row in data])

@app.route("/harita", methods=["GET"])
def olustur():
    return render_template("data.html")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
