import cv2

# Inisialisasi detektor HOG untuk deteksi tubuh
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

# Inisialisasi detektor wajah menggunakan Haar Cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Fungsi untuk deteksi orang dan wajah dalam video
def detect_people_and_faces(video_source=0):
    # Buka video atau webcam
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print("Tidak dapat membuka video atau webcam!")
        return

    while True:
        # Baca frame dari video
        ret, frame = cap.read()
        if not ret:
            print("Tidak dapat membaca frame (akhir video?).")
            break

        # Ubah frame ke skala abu-abu (untuk deteksi wajah)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Deteksi tubuh
        bodies, _ = hog.detectMultiScale(frame, winStride=(8, 8), padding=(8, 8), scale=1.05)

        # Gambar kotak di sekitar tubuh
        for (x, y, w, h) in bodies:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Warna hijau untuk tubuh

        # Deteksi wajah
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        # Gambar kotak di sekitar wajah
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)  # Warna biru untuk wajah

        # Tampilkan frame dengan hasil deteksi
        cv2.imshow("People and Face Detection", frame)

        # Berhenti jika pengguna menekan tombol 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Bersihkan resource
    cap.release()
    cv2.destroyAllWindows()

# Path video atau gunakan 0 untuk webcam
video_source = 0  # Ganti dengan path video Anda atau gunakan 0 untuk webcam
detect_people_and_faces(video_source)
