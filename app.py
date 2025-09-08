from flask import Flask, render_template, request, jsonify
import psycopg2
import math

app = Flask(__name__)

# Veritabanı bağlantısı
conn = psycopg2.connect(
    host="render psql dpg-d2vjqu8dl3ps73992d3g-a",
    database="sensor_data_db_x3lm",
    user="sensor_user",
    password="amLdGfRtXTtpye0zB6kHVBkZvmi0Qfy0",
    port="5432"
)
cursor = conn.cursor()

# 🚀 Tablo yoksa oluştur
cursor.execute("""
CREATE TABLE IF NOT EXISTS sensor_verileri (
    id SERIAL PRIMARY KEY,
    sicaklik FLOAT,
    nem FLOAT,
    enlem FLOAT,
    boylam FLOAT,
    isi_indeksi FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()

# Isı indeksi hesaplama fonksiyonu
def calculate_heat_index(T, RH):
    return -8.78469475556 + 1.61139411*T + 2.33854883889*RH - 0.14611605*T*RH - 0.012308094*T**2 - 0.0164248277778*RH**2 + 0.002211732*T**2*RH + 0.00072546*T*RH**2 - 0.000003582*T**2*RH**2

@app.route('/')
def index():
    return render_template('data.html')

@app.route('/veri_form')
def veri_form():
    return render_template('veri_form.html')

@app.route('/veri', methods=['POST'])
def veri():
    try:
        data = request.json
        sicaklik = float(data.get('sicaklik'))
        nem = float(data.get('nem'))
        enlem = float(data.get('enlem'))
        boylam = float(data.get('boylam'))

        # Isı indeksi hesapla
        is_index = calculate_heat_index(sicaklik, nem)

        cursor.execute(
            "INSERT INTO sensor_verileri (sicaklik, nem, enlem, boylam, isi_indeksi) VALUES (%s, %s, %s, %s, %s)",
            (sicaklik, nem, enlem, boylam, is_index)
        )
        conn.commit()

        return jsonify({"status": "success", "message": "Veri eklendi!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/data', methods=['GET'])
def data():
    cursor.execute("SELECT sicaklik, nem, enlem, boylam, isi_indeksi, timestamp FROM sensor_verileri")
    rows = cursor.fetchall()
    return jsonify([{
        "sicaklik": row[0],
        "nem": row[1],
        "enlem": row[2],
        "boylam": row[3],
        "isi_indeksi": row[4],
        "timestamp": row[5].isoformat()
    } for row in rows])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
