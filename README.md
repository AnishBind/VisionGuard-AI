# HealthConnect

# 🏥 Hospital & NGO Management System

A full-stack **Node.js** application designed to streamline healthcare services, doctor–patient interactions, and NGO community support.  
The system implements **Role-Based Access Control (RBAC)** to provide customized dashboards for **Patients**, **Doctors**, and **NGOs**.

---

## ✨ Features

### 🧑‍⚕️ Patient Portal
- 🚑 **Emergency Services**  
  View available ambulances sorted by distance.
- 📅 **Doctor Appointments**  
  Browse doctors by specialization and book appointments with reason and preferred time slot.
- 🤝 **NGO Collaboration**  
  Request help, apply for NGO membership, or make donations.
- 📝 **Incident Reporting**  
  Submit medical or social incident reports for action.

---

### 🩺 Doctor Portal
- 📥 **Appointment Management**  
  Accept or reject patient appointment requests.
- 📖 **Consultation History**  
  View records of accepted consultations.
- 🌍 **NGO Directory**  
  Access registered NGOs for collaboration.

---

### 🤝 NGO Dashboard
- 👥 **Member Management**  
  Approve or reject membership requests.
- 💰 **Donation Tracking**  
  Monitor donor details, donation amounts, and purposes.
- 🆘 **Response Center**  
  Handle help requests and manage incident reports.

---

## 🛠 Tech Stack

- **Backend**: Node.js
- **Framework**: Express.js (v4.19.2)
- **Database**: MySQL (`mysql2`)
- **View Engine**: EJS (Embedded JavaScript)
- **Middleware**:
  - `body-parser`
  - `express-session`

---

## 🚀 Installation

### 1️⃣ Clone the Repository
```
git clone https://github.com/AnishBind/HealthConnect.git
```

### 2️⃣ Install Dependencies
```
npm install
```

### 3️⃣ Database Configuration
Create a MySQL database named:
```
CREATE DATABASE hospital;
```

MySQL credentials:
```
host: localhost
user: root
password: admin
```

### 4️⃣ Start the Server
The application runs on **port 4000**.
```
node index.js
```

---

## 🗄 Database Schema

| Table Name   | Description |
|-------------|-------------|
| users       | Stores Patients, Doctors, and NGOs |
| ambulance   | Ambulance services with distances |
| doctor      | Appointment records and statuses |
| member      | Pending NGO membership requests |
| ngoMembers  | Approved NGO members |
| help        | Help requests sent to NGOs |
| donations   | Donation transaction records |
| report      | Public incident reports |

---

## 👨‍💻 Author
Anish

---

## 📄 License
ISC License
