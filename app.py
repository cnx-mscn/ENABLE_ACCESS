import streamlit as st
import json
import os
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
from geopy.geocoders import Nominatim
from folium.plugins import MarkerCluster
from io import BytesIO
import base64
import uuid

# --- Kullanıcı verisi ve görev verisi dosyaları ---
USER_FILE = "users.json"
TASK_FILE = "tasks.json"

# --- Oturum durumu başlat ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_type = ""

# --- JSON dosya okuma/yazma ---
def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# --- Kullanıcı kayıt işlemi ---
def register_user(username, password, user_type):
    users = load_json(USER_FILE)
    if username in users:
        return False
    users[username] = {"password": password, "type": user_type}
    save_json(USER_FILE, users)
    return True

# --- Giriş işlemi ---
def login(username, password):
    users = load_json(USER_FILE)
    if username in users and users[username]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.user_type = users[username]["type"]
        return True
    return False
    # --- Görev ekleme ---
def add_task(city, ekip, tarih, onem, sure):
    tasks = load_json(TASK_FILE)
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "city": city,
        "ekip": ekip,
        "tarih": tarih,
        "onem": onem,
        "sure": sure,
        "status": "Beklemede",
        "photo": None,
        "onay": False
    }
    save_json(TASK_FILE, tasks)

# --- Görev güncelleme ---
def update_task_status(task_id, status=None, photo=None, onay=None):
    tasks = load_json(TASK_FILE)
    if task_id in tasks:
        if status: tasks[task_id]["status"] = status
        if photo: tasks[task_id]["photo"] = photo
        if onay is not None: tasks[task_id]["onay"] = onay
        save_json(TASK_FILE, tasks)

# --- Harita oluştur ---
def draw_map():
    tasks = load_json(TASK_FILE)
    m = folium.Map(location=[39.92, 32.85], zoom_start=6)
    marker_cluster = MarkerCluster().add_to(m)
    geolocator = Nominatim(user_agent="montaj_app")

    for tid, task in tasks.items():
        location = geolocator.geocode(f"{task['city']}, Turkey")
        if location:
            color = "green" if task["onay"] else "red"
            popup = f"""
                <b>Şehir:</b> {task['city']}<br>
                <b>Ekip:</b> {task['ekip']}<br>
                <b>Durum:</b> {task['status']}<br>
                <b>Tarih:</b> {task['tarih']}<br>
                <b>Harita:</b> <a href="https://www.google.com/maps/search/?api=1&query={location.latitude},{location.longitude}" target="_blank">Google Maps</a>
            """
            folium.Marker(
                location=[location.latitude, location.longitude],
                popup=popup,
                icon=folium.Icon(color=color)
            ).add_to(marker_cluster)
    return m

# --- PDF ve Excel çıktısı için yardımcı ---
def download_link(df, filename, filetype="csv"):
    buffer = BytesIO()
    if filetype == "excel":
        df.to_excel(buffer, index=False)
    elif filetype == "csv":
        df.to_csv(buffer, index=False)
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">Dosyayı indir</a>'

# --- Ana Uygulama Arayüzü ---
def main_app():
    st.sidebar.title("Menü")
    secim = st.sidebar.radio("Seçim", ["Görevlerim", "Harita", "Takvim", "Raporlama", "Çıkış"])

    if secim == "Görevlerim":
        tasks = load_json(TASK_FILE)
        if st.session_state.user_type == "işçi":
            for tid, task in tasks.items():
                if task["ekip"] == st.session_state.username:
                    st.subheader(task["city"])
                    st.write(f"Tarih: {task['tarih']}, Süre: {task['sure']} saat")
                    st.write(f"Durum: {task['status']}")
                    if not task["onay"]:
                        photo = st.file_uploader("Fotoğraf yükle", key=tid)
                        if photo and st.button("Görevi tamamla", key="btn"+tid):
                            update_task_status(tid, status="Tamamlandı", photo=photo.name)
                            st.success("Görev gönderildi. Yönetici onayı bekleniyor.")
        elif st.session_state.user_type == "yönetici":
            for tid, task in tasks.items():
                st.subheader(f"{task['city']} - {task['ekip']}")
                st.write(f"Tarih: {task['tarih']} - Durum: {task['status']}")
                if task["photo"]:
                    st.image(task["photo"], caption="Yüklenen Fotoğraf")
                    if not task["onay"] and st.button("Onayla", key="onay"+tid):
                        update_task_status(tid, onay=True)
                        st.success("Görev onaylandı.")

    elif secim == "Harita":
        map_object = draw_map()
        st_folium(map_object, width=700)

    elif secim == "Takvim":
        tasks = load_json(TASK_FILE)
        for tid, task in tasks.items():
            st.markdown(f"**{task['tarih']}** - {task['city']} - {task['ekip']}")

    elif secim == "Raporlama":
        tasks = load_json(TASK_FILE)
        df = pd.DataFrame.from_dict(tasks, orient="index")
        st.dataframe(df)
        st.markdown(download_link(df, "rapor.xlsx", "excel"), unsafe_allow_html=True)

    elif secim == "Çıkış":
        st.session_state.logged_in = False
        st.experimental_rerun()
        
        # --- Giriş ve Kayıt Sistemi ---
def login():
    st.title("Montaj Uygulaması Giriş")

    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])

    with tab1:
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            user = authenticate_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user["username"]
                st.session_state.user_type = user["type"]
                st.success(f"Hoş geldin, {username}!")
                st.experimental_rerun()
            else:
                st.error("Geçersiz kullanıcı adı veya şifre")

    with tab2:
        new_user = st.text_input("Yeni Kullanıcı Adı")
        new_pass = st.text_input("Yeni Şifre", type="password")
        user_type = st.selectbox("Kullanıcı Türü", ["işçi", "yönetici"])
        if st.button("Kayıt Ol"):
            if register_user(new_user, new_pass, user_type):
                st.success("Kayıt başarılı, şimdi giriş yapabilirsiniz.")
            else:
                st.warning("Bu kullanıcı adı zaten mevcut.")

# --- Oturum Başlatma ve Uygulama Akışı ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    main_app()
else:
    login()