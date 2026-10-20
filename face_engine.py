import os, pickle, cv2, numpy as np

try:
    import face_recognition
except ImportError:
    face_recognition=None

class FaceEngine:
    def __init__(self, face_dir):
        self.face_dir=face_dir
        self.known=[]
        self.reload()

    def validate_face(self,path):
        if face_recognition is None:
            return False,"face_recognition is not installed. Run: pip install -r requirements.txt"
        img=face_recognition.load_image_file(path)
        locations=face_recognition.face_locations(img,model="hog")
        if len(locations)!=1:
            return False, f"Photo must contain exactly one clear face. Found {len(locations)}."
        return True,"OK"

    def reload(self):
        self.known=[]
        if face_recognition is None or not os.path.isdir(self.face_dir): return
        for f in os.listdir(self.face_dir):
            if not f.lower().endswith((".jpg",".jpeg",".png")): continue
            p=os.path.join(self.face_dir,f)
            try:
                img=face_recognition.load_image_file(p)
                encs=face_recognition.face_encodings(img)
                if len(encs)==1:
                    self.known.append((os.path.splitext(f)[0],encs[0]))
            except Exception:
                pass

    def recognize(self, frame):
        if face_recognition is None:
            raise RuntimeError("face_recognition is not installed.")
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        locs=face_recognition.face_locations(rgb,model="hog")
        encs=face_recognition.face_encodings(rgb,locs)
        if not encs or not self.known:
            return {"matched":False}
        for enc in encs:
            distances=face_recognition.face_distance([x[1] for x in self.known],enc)
            i=int(np.argmin(distances))
            if distances[i] < 0.48:
                return {"matched":True,"reg_no":self.known[i][0],"distance":float(distances[i])}
        return {"matched":False}
