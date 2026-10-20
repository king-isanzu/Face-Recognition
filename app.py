from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
import os, cv2, sqlite3, base64, re
from datetime import datetime
from werkzeug.utils import secure_filename
from face_engine import FaceEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "attendance.db")
FACE_DIR = os.path.join(BASE_DIR, "known_faces")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(FACE_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

engine = FaceEngine(FACE_DIR)

def db():
    con=sqlite3.connect(DB_PATH)
    con.row_factory=sqlite3.Row
    return con

def init_db():
    con=db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS students(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      reg_no TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      email TEXT,
      phone TEXT,
      face_file TEXT,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS attendance(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id INTEGER NOT NULL,
      date TEXT NOT NULL,
      time TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'Present',
      UNIQUE(student_id,date),
      FOREIGN KEY(student_id) REFERENCES students(id)
    );
    CREATE TABLE IF NOT EXISTS admins(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL
    );
    """)
    if not con.execute("SELECT 1 FROM admins LIMIT 1").fetchone():
        con.execute("INSERT INTO admins(username,password) VALUES(?,?)",("admin","admin123"))
    con.commit(); con.close()

init_db()

@app.route("/")
def index():
    con=db()
    students=con.execute("SELECT COUNT(*) c FROM students").fetchone()["c"]
    today=con.execute("SELECT COUNT(*) c FROM attendance WHERE date=?",(datetime.now().strftime("%Y-%m-%d"),)).fetchone()["c"]
    con.close()
    return render_template("dashboard.html", students=students, today=today)

@app.route("/students")
def students():
    con=db(); rows=con.execute("SELECT * FROM students ORDER BY id DESC").fetchall(); con.close()
    return render_template("students.html", students=rows)

@app.route("/students/add", methods=["GET","POST"])
def add_student():
    if request.method=="POST":
        reg=request.form["reg_no"].strip()
        name=request.form["name"].strip()
        email=request.form.get("email","").strip()
        phone=request.form.get("phone","").strip()
        photo=request.files.get("photo")
        if not reg or not name or not photo:
            flash("Registration number, name and face photo are required.","danger")
            return redirect(url_for("add_student"))
        if not photo.filename:
            flash("Choose a clear face photo.","danger"); return redirect(url_for("add_student"))
        ext=os.path.splitext(secure_filename(photo.filename))[1].lower()
        if ext not in [".jpg",".jpeg",".png"]:
            flash("Use JPG, JPEG or PNG.","danger"); return redirect(url_for("add_student"))
        filename=re.sub(r"[^A-Za-z0-9_-]","_",reg)+".jpg"
        path=os.path.join(FACE_DIR,filename)
        photo.save(path)
        ok,msg=engine.validate_face(path)
        if not ok:
            if os.path.exists(path): os.remove(path)
            flash(msg,"danger"); return redirect(url_for("add_student"))
        con=db()
        try:
            con.execute("INSERT INTO students(reg_no,name,email,phone,face_file,created_at) VALUES(?,?,?,?,?,?)",
                         (reg,name,email,phone,filename,datetime.now().isoformat(timespec="seconds")))
            con.commit()
            engine.reload()
            flash("Student registered successfully.","success")
        except sqlite3.IntegrityError:
            if os.path.exists(path): os.remove(path)
            flash("Registration number already exists.","danger")
        finally: con.close()
        return redirect(url_for("students"))
    return render_template("register.html")

@app.route("/students/delete/<int:sid>", methods=["POST"])
def delete_student(sid):
    con=db()
    row=con.execute("SELECT face_file FROM students WHERE id=?",(sid,)).fetchone()
    if row:
        con.execute("DELETE FROM attendance WHERE student_id=?",(sid,))
        con.execute("DELETE FROM students WHERE id=?",(sid,)); con.commit()
        if row["face_file"]:
            p=os.path.join(FACE_DIR,row["face_file"])
            if os.path.exists(p): os.remove(p)
        engine.reload()
        flash("Student deleted.","success")
    con.close()
    return redirect(url_for("students"))

@app.route("/attendance")
def attendance():
    con=db()
    rows=con.execute("""SELECT a.id,s.reg_no,s.name,a.date,a.time,a.status
                        FROM attendance a JOIN students s ON s.id=a.student_id
                        ORDER BY a.date DESC,a.time DESC""").fetchall()
    con.close()
    return render_template("attendance.html", rows=rows)

@app.route("/scan")
def scan():
    return render_template("scan.html")

@app.route("/api/recognize", methods=["POST"])
def recognize():
    data=request.get_json(silent=True) or {}
    image=data.get("image","")
    if "," in image: image=image.split(",",1)[1]
    try:
        raw=base64.b64decode(image)
        arr=cv2.imdecode(__import__("numpy").frombuffer(raw,dtype=__import__("numpy").uint8),cv2.IMREAD_COLOR)
        result=engine.recognize(arr)
        if not result["matched"]:
            return jsonify({"ok":True,"matched":False,"message":"Face not recognized."})
        reg=result["reg_no"]
        con=db()
        s=con.execute("SELECT * FROM students WHERE reg_no=?",(reg,)).fetchone()
        if not s:
            con.close(); return jsonify({"ok":False,"message":"Recognized face has no student record."})
        now=datetime.now()
        date,time=now.strftime("%Y-%m-%d"),now.strftime("%H:%M:%S")
        try:
            con.execute("INSERT INTO attendance(student_id,date,time,status) VALUES(?,?,?,?)",(s["id"],date,time,"Present"))
            con.commit()
            status="Attendance recorded"
        except sqlite3.IntegrityError:
            status="Already marked present today"
        con.close()
        return jsonify({"ok":True,"matched":True,"name":s["name"],"reg_no":s["reg_no"],"status":status})
    except Exception as e:
        return jsonify({"ok":False,"message":str(e)}),400

@app.route("/reports")
def reports():
    con=db()
    rows=con.execute("""SELECT s.reg_no,s.name,
                        COUNT(a.id) AS days_present
                        FROM students s LEFT JOIN attendance a ON a.student_id=s.id
                        GROUP BY s.id ORDER BY s.name""").fetchall()
    con.close()
    return render_template("reports.html", rows=rows)

@app.route("/health")
def health():
    return jsonify({"status":"ok","faces_loaded":len(engine.known)})

if __name__=="__main__":
    app.run(host="127.0.0.1",port=5000,debug=True)
