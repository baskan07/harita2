from flask import Flask, render_template, request, jsonify
import psycopg2
import math

app = Flask(__name__)

# Veritabanı bağlantısı
DB_URL = os.getenv("postgresql://sensor_user:amLdGfRtXTtpye0zB6kHVBkZvmiQ0fyO@dpg-d2vjqu8dl3ps73992d3g-a.frankfurt-postgres.render.com:5432/sensor_data_db_x3lm")

def get_conn():
    return psycopg2.connect(DB_URL, sslmode="require")

# --- Tablo yoksa oluştur (uygulama başlarken bir kez) ---
with get_conn() as c:
    with c.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_verileri (
            id SERIAL PRIMARY KEY,
            sicaklik FLOAT NOT NULL,
            nem FLOAT NOT NULL,
            enlem FLOAT NOT NULL,
            boylam FLOAT NOT NULL,
            isi_indeksi FLOAT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        c.commit()

# --- Isı indeksi ---
def calculate_heat_index(T, RH):
    return (-8.78469475556 + 1.61139411*T + 2.33854883889*RH - 0.14611605*T*RH
            - 0.012308094*T**2 - 0.0164248277778*RH**2 + 0.002211732*T**2*RH
            + 0.00072546*T*RH**2 - 0.000003582*T**2*RH**2)

# --- Sayfalar ---
@app.route("/")
def index():
    return render_template("data.html")

@app.route("/veri_form")
def veri_form():
    return render_template("veri_form.html")

# --- JSON ile veri ekleme (Arduino/telefon köprüsünden de bunu çağıracağız) ---
@app.route("/veri", methods=["POST"])
def veri():
    try:
        d = request.get_json(force=True)
        sicaklik = float(d["sicaklik"])
        nem      = float(d["nem"])
        enlem    = float(d["enlem"])
        boylam   = float(d["boylam"])

        isi = calculate_heat_index(sicaklik, nem)

        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO sensor_verileri (sicaklik, nem, enlem, boylam, isi_indeksi) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (sicaklik, nem, enlem, boylam, isi)
                )
                c.commit()

        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# --- Verileri listeleme ---
@app.route("/data", methods=["GET"])
def data():
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT sicaklik, nem, enlem, boylam, isi_indeksi, timestamp FROM sensor_verileri")
            rows = cur.fetchall()

    return jsonify([
        {
            "sicaklik": r[0],
            "nem": r[1],
            "enlem": r[2],
            "boylam": r[3],
            "isi_indeksi": r[4],
            "timestamp": r[5].isoformat() if r[5] else None
        } for r in rows
    ])

# (İstersen Tasker/Twilio için SMS webhook'u da ekleyebilirim: /sms)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
