# Face Recognition Attendance System

## Requirements
- Windows 10/11 recommended
- Python 3.10 or 3.11 recommended
- Webcam
- VS Code

## Installation
Open the project folder in VS Code, then Terminal:

```bash
python -m venv venv
```

Windows PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```

Windows CMD:
```cmd
venv\Scripts\activate
```

Then:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open:
http://127.0.0.1:5000

## Default admin
Username: admin
Password: admin123

Change these credentials before real deployment.

## How to use
1. Open Students.
2. Add student details and upload a clear photo containing one face.
3. Open Scan Attendance.
4. Allow camera access.
5. Point the camera at a registered student's face.
6. Attendance is recorded once per student per day.
7. Use Attendance and Reports to view records.

## Troubleshooting
If `face_recognition`/`dlib` fails to install on Windows, use Python 3.10 or 3.11 and a compatible wheel/build environment. The rest of the Flask application is already prepared.

This project is intended for legitimate attendance use with appropriate notice/consent and secure handling of biometric data.
