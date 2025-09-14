from flask import Flask, render_template, request, jsonify
import os
import psycopg2

app = Flask(__name__)

# Veritabanı bağlantısı
DB_URL = "postgresql://sensor_user:amLdGfRtXTtpye0zB6kHVBkZvmiQ0fyO@dpg-d2vjqu8dl3ps73992d3g-a.frankfurt-postgres.render.com:5432/sensor_data_db_x3lm"

def get_conn():
    return psycopg2.connect(DB_URL, sslmode="require")

# --- Tabloya toprak_nem sütunu ekle (yoksa) ---
with get_conn() as c:
    with c.cursor() as cur:
        cur.execute("""
        ALTER TABLE sensor_verileri 
        ADD COLUMN IF NOT EXISTS toprak_nem FLOAT;
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

# --- JSON ile veri ekleme ---
@app.route("/veri", methods=["POST"])
def veri():
    try:
        d = request.get_json(force=True)
        sicaklik   = float(d["sicaklik"])
        nem        = float(d["nem"])
        toprak_nem = float(d["toprak_nem"])
        enlem      = float(d["enlem"])
        boylam     = float(d["boylam"])

        isi = calculate_heat_index(sicaklik, nem)

        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO sensor_verileri (sicaklik, nem, toprak_nem, enlem, boylam, isi_indeksi) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (sicaklik, nem, toprak_nem, enlem, boylam, isi)
                )
                c.commit()

        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# --- SMS ile veri ekleme ---
@app.route("/sms", methods=["POST"])
def sms():
    try:
        # Tasker Body JSON ile: {"sms": "S:25.3,N:70,T:25.3,E:36.544,B:32.003"}
        body = request.get_json(force=True).get("sms", "").strip()

        # SMS'i parse et
        parts = dict(item.split(":") for item in body.split(","))
        sicaklik   = float(parts["S"])
        nem        = float(parts["N"])
        toprak_nem = float(parts["T"])
        enlem      = float(parts["E"])
        boylam     = float(parts["B"])

        isi = calculate_heat_index(sicaklik, nem)

        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO sensor_verileri (sicaklik, nem, toprak_nem, enlem, boylam, isi_indeksi) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (sicaklik, nem, toprak_nem, enlem, boylam, isi)
                )
                c.commit()

        return jsonify({"status": "success", "from": "sms"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# --- Verileri listeleme ---
@app.route("/data", methods=["GET"])
def data():
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute("""
                SELECT sicaklik, nem, toprak_nem, enlem, boylam, isi_indeksi, timestamp
                FROM sensor_verileri
            """)
            rows = cur.fetchall()

    return jsonify([
        {
            "temperature": r[0],
            "humidity": r[1],
            "soil_moisture": r[2],
            "latitude": r[3],
            "longitude": r[4],
            "heat_index": r[5],
            "timestamp": r[6].isoformat() if r[6] else None
        } for r in rows
    ])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
