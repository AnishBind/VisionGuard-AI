# VisionGuard AI

# 🛡️ Real-Time Edge AI Surveillance Analytics System

VisionGuard AI is a full-stack AI-powered surveillance analytics platform designed for smart workplace monitoring, CCTV intelligence, and real-time safety analytics.

The system combines **Computer Vision**, **YOLOv8**, **MediaPipe Pose**, and **Flask** to monitor human activity, detect abnormal events, and generate real-time alerts from webcam or CCTV footage.

Inspired by enterprise Edge AI systems used in warehouses, logistics centers, factories, and smart monitoring environments, VisionGuard AI demonstrates how lightweight AI inference can power intelligent surveillance applications.

---

## ✨ Features

### 🎥 AI Surveillance Monitoring

* 👤 **Person Detection**
  Detect workers and human activity in real time using YOLOv8.

* 📱 **Mobile Phone Detection**
  Detect visible mobile phone usage during workplace monitoring.

* 🚨 **Fall Detection**
  Analyze body posture and detect possible fall events using pose estimation.

* 🧍 **Standing Posture Detection**
  Detect prolonged standing posture using body landmark analysis.

* ⏱️ **Inactivity Monitoring**
  Detect low-movement or inactive persons over long durations.

* 📸 **Screenshot Logging**
  Automatically save screenshots when alerts are triggered.

---

### 🖥️ Enterprise Dashboard

* 🎬 **Live Webcam Monitoring**
  Start real-time AI detection directly from webcam feed.

* 📂 **CCTV Video Upload**
  Upload and analyze CCTV surveillance footage.

* 📊 **System Status Monitoring**
  View FPS, detection status, and system information.

* 🚨 **Alert Management**
  View real-time alert logs with timestamps.

* ⏯️ **Video Playback Controls**
  Pause, resume, restart, and seek uploaded video streams.

* 🌙 **Modern Glassmorphism UI**
  Responsive dark-themed enterprise surveillance dashboard.

---

# 🎥 Demo Video

## 📹 Project Demonstration

Watch the complete VisionGuard AI demo here:

```md
https://github.com/yourusername/VisionGuardAI/assets/demo-video-link
```

OR

```md
uploads/VisionGuard AI.mp4
```

### 🚀 Demo Includes

* Real-time person detection
* Mobile phone detection
* Fall detection
* Standing posture analysis
* CCTV video upload testing
* Real-time alert generation

## 🧠 AI Pipeline

Video Input
→ OpenCV Frame Processing
→ YOLOv8 Object Detection
→ MediaPipe Pose Estimation
→ Posture & Activity Analysis
→ Alert Generation
→ Flask Dashboard Visualization

---

## 🛠 Tech Stack

### 🔹 Backend

* Python
* Flask

### 🔹 Computer Vision & AI

* OpenCV
* YOLOv8
* MediaPipe Pose
* NumPy

### 🔹 Frontend

* HTML
* CSS
* JavaScript

---

## 🚀 Installation

### 1️⃣ Clone Repository

```bash
git clone https://github.com/yourusername/VisionGuardAI.git
cd VisionGuardAI
```

### 2️⃣ Create Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install Requirements

```bash
pip install -r requirements.txt
```

### 4️⃣ Run the Application

```bash
python app.py
```

Open browser:

```bash
http://127.0.0.1:5000
```

---

## 🗂 Project Structure

```bash
VisionGuardAI/
│
├── app.py
├── detector.py
├── pose_estimator.py
├── posture_analyzer.py
├── vision_thread.py
├── alerts.py
├── utils.py
├── config.py
├── templates/
├── static/
├── uploads/
├── screenshots/
├── logs/
├── models/
├── requirements.txt
└── README.md
```

---

## 🧩 Detection Capabilities

| Detection Type       | Description                          |
| -------------------- | ------------------------------------ |
| Person Detection     | Detects workers and human activity   |
| Mobile Detection     | Detects visible mobile phone usage   |
| Fall Detection       | Detects abnormal fall posture events |
| Standing Detection   | Detects prolonged standing posture   |
| Inactivity Detection | Detects low movement activity        |

---

## 🏭 Enterprise Use Cases

* Smart warehouse monitoring
* Workplace safety analytics
* Logistics surveillance systems
* Retail monitoring systems
* Industrial safety monitoring
* CCTV analytics research
* Edge AI surveillance prototypes

---

## ⚡ Performance Optimizations

* Lightweight YOLOv8 models
* CPU-friendly inference
* Optimized OpenCV streaming
* Efficient MediaPipe pose analysis
* Reduced resolution processing
* Real-time FPS optimization

---

## 🔮 Future Improvements

* Multi-camera support
* Advanced pose classification
* Better fall detection accuracy
* Edge GPU optimization
* Real-time notification system
* Cloud deployment
* Database integration
* AI analytics dashboard

---

## 🎯 Goal

The goal of VisionGuard AI is to demonstrate how modern Computer Vision and Edge AI systems can be used to build practical real-time surveillance analytics platforms for enterprise environments.

The project focuses on:

* Real-time monitoring
* Human activity analysis
* Lightweight AI inference
* Enterprise surveillance workflows
* Edge AI concepts

---

## 👨‍💻 Author

Aashish Paramhans Bind

B.E. Electronics & Telecommunication Engineering
Honors Specialization in Artificial Intelligence & Machine Learning

---

## 📄 License

This project is created for educational, research, and portfolio purposes.
