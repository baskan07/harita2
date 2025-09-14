from flask import Flask, render_template, request, jsonify
import os
import psycopg2

app = Flask(__name__)

# Veritabanı bağlantısı
DB_URL = "postgresql://sensor_user:amLdGfRtXTtpye0zB6kHVBkZvmiQ0fyO@dpg-d2vjqu8dl3ps73992d3g-a.frankfurt-postgres.render.com:5432/sensor_data_db_x3lm"

def get_conn():
    return psycopg2.connect(DB_URL, sslmode="require")

# --- Şema güncellemeleri: toprak_nem sütunu + sensor_latest tablosu/indeksi ---
with get_conn() as c:
    with c.cursor() as cur:
        # Eski tabloda toprak_nem yoksa ekle
        cur.execute("""
        ALTER TABLE sensor_verileri 
        ADD COLUMN IF NOT EXISTS toprak_nem FLOAT;
        """)
        # Son değerleri tutacak tablo
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_latest (
            id SERIAL PRIMARY KEY,
            lat_r NUMERIC(9,5),
            lon_r NUMERIC(9,5),
            enlem FLOAT,
            boylam FLOAT,
            sicaklik FLOAT,
            nem FLOAT,
            toprak_nem FLOAT,
            isi_indeksi FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # Aynı konum için tek kayıt
        cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_sensor_latest_loc
        ON sensor_latest (lat_r, lon_r);
        """)
        c.commit()

# --- Isı indeksi ---
def calculate_heat_index(T, RH):
    return (-8.78469475556 + 1.61139411*T + 2.33854883889*RH - 0.14611605*T*RH
            - 0.012308094*T**2 - 0.0164248277778*RH**2 + 0.002211732*T**2*RH
            + 0.00072546*T*RH**2 - 0.000003582*T**2*RH**2)

def round5(x: float) -> float:
    return round(x, 5)

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
        lat_r = round5(enlem)
        lon_r = round5(boylam)

        with get_conn() as c:
            with c.cursor() as cur:
                # 1) Tarihçeye ekle
                cur.execute(
                    "INSERT INTO sensor_verileri (sicaklik, nem, toprak_nem, enlem, boylam, isi_indeksi) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (sicaklik, nem, toprak_nem, enlem, boylam, isi)
                )
                # 2) Son değeri upsert et
                cur.execute("""
                    INSERT INTO sensor_latest (lat_r, lon_r, enlem, boylam, sicaklik, nem, toprak_nem, isi_indeksi, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (lat_r, lon_r) DO UPDATE SET
                        enlem = EXCLUDED.enlem,
                        boylam = EXCLUDED.boylam,
                        sicaklik = EXCLUDED.sicaklik,
                        nem = EXCLUDED.nem,
                        toprak_nem = EXCLUDED.toprak_nem,
                        isi_indeksi = EXCLUDED.isi_indeksi,
                        timestamp = EXCLUDED.timestamp;
                """, (lat_r, lon_r, enlem, boylam, sicaklik, nem, toprak_nem, isi))
                c.commit()

        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# --- SMS ile veri ekleme ---
@app.route("/sms", methods=["POST"])
def sms():
    try:
        # Tasker Body JSON: {"sms": "S:25.3,N:70,T:25.3,E:36.544,B:32.003"}
        body = request.get_json(force=True).get("sms", "").strip()
        parts = dict(item.split(":") for item in body.split(","))

        sicaklik   = float(parts["S"])
        nem        = float(parts["N"])
        toprak_nem = float(parts["T"])
        enlem      = float(parts["E"])
        boylam     = float(parts["B"])

        isi = calculate_heat_index(sicaklik, nem)
        lat_r = round5(enlem)
        lon_r = round5(boylam)

        with get_conn() as c:
            with c.cursor() as cur:
                # 1) Tarihçeye ekle
                cur.execute(
                    "INSERT INTO sensor_verileri (sicaklik, nem, toprak_nem, enlem, boylam, isi_indeksi) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (sicaklik, nem, toprak_nem, enlem, boylam, isi)
                )
                # 2) Son değeri upsert et
                cur.execute("""
                    INSERT INTO sensor_latest (lat_r, lon_r, enlem, boylam, sicaklik, nem, toprak_nem, isi_indeksi, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (lat_r, lon_r) DO UPDATE SET
                        enlem = EXCLUDED.enlem,
                        boylam = EXCLUDED.boylam,
                        sicaklik = EXCLUDED.sicaklik,
                        nem = EXCLUDED.nem,
                        toprak_nem = EXCLUDED.toprak_nem,
                        isi_indeksi = EXCLUDED.isi_indeksi,
                        timestamp = EXCLUDED.timestamp;
                """, (lat_r, lon_r, enlem, boylam, sicaklik, nem, toprak_nem, isi))
                c.commit()

        return jsonify({"status": "success", "from": "sms"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# --- Güncel tekil marker'lar ---
@app.route("/data", methods=["GET"])
def data():
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute("""
                SELECT enlem, boylam, sicaklik, nem, toprak_nem, isi_indeksi, timestamp
                FROM sensor_latest
            """)
            rows = cur.fetchall()

    return jsonify([
        {
            "latitude": r[0],
            "longitude": r[1],
            "temperature": r[2],
            "humidity": r[3],
            "soil_moisture": r[4],
            "heat_index": r[5],
            "timestamp": r[6].isoformat() if r[6] else None
        } for r in rows
    ])

# --- Belirli konum için geçmiş (varsayılan: 1 gün) ---
@app.route("/history", methods=["GET"])
def history():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
        days = request.args.get("days")
        hours = request.args.get("hours")

        lat_r = round5(lat)
        lon_r = round5(lon)

        interval = "1 day"
        if hours:
            interval = f"{int(hours)} hours"
        elif days:
            interval = f"{int(days)} days"

        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(f"""
                    SELECT sicaklik, nem, toprak_nem, isi_indeksi, timestamp
                    FROM sensor_verileri
                    WHERE ROUND(enlem::numeric, 5) = %s
                      AND ROUND(boylam::numeric, 5) = %s
                      AND timestamp >= NOW() - interval %s
                    ORDER BY timestamp ASC
                """, (lat_r, lon_r, interval))
                rows = cur.fetchall()

        return jsonify([
            {
                "temperature": r[0],
                "humidity": r[1],
                "soil_moisture": r[2],
                "heat_index": r[3],
                "timestamp": r[4].isoformat() if r[4] else None
            } for r in rows
        ])
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
