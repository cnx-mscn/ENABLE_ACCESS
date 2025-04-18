import streamlit as st
import pandas as pd
import folium
import datetime
import googlemaps
from fpdf import FPDF
from geopy.geocoders import Nominatim
from sklearn.cluster import KMeans  # Yapay Zeka ile rota önerisi için
from geopy.distance import geodesic

# Google Maps API anahtarı (örnek)
gmaps = googlemaps.Client(key="AIzaSyDwQVuPcON3rGSibcBrwhxQvz4HLTpF9Ws")

# Kullanıcı girişi
def user_login():
    login_type = st.selectbox("Kullanıcı Tipi Seçin:", ["Yönetici", "İşçi"])
    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if login_type == "Yönetici" and username == "admin" and password == "admin123":
            st.session_state.logged_in = True
            st.session_state.user_type = login_type
        elif login_type == "İşçi" and username == "worker" and password == "worker123":
            st.session_state.logged_in = True
            st.session_state.user_type = login_type
        else:
            st.error("Geçersiz giriş bilgileri.")

# Kullanıcı Girişi Kontrolü
if 'logged_in' not in st.session_state:
    user_login()
else:
    if st.session_state.logged_in:
        st.write(f"Hoş geldiniz, {st.session_state.user_type}!")
        # Şehir ekleme ve görev atama (Yönetici)
        if st.session_state.user_type == "Yönetici":
            city = st.text_input("Şehir Ekle")
            task_duration = st.number_input("Görev Süresi (saat)", min_value=1)
            task_description = st.text_area("Görev Açıklaması")
            if st.button("Görev Atama"):
                st.success(f"Şehire {city} görev atandı. Süre: {task_duration} saat.")
       
        # Görev Durumu (İşçi)
        if st.session_state.user_type == "İşçi":
            task_status = st.selectbox("Görev Durumunu Seçin:", ["Yapılacak", "Tamamlandı", "Onay Bekliyor"])
            if task_status == "Tamamlandı":
                photo = st.file_uploader("Fotoğraf Yükle", type=["jpg", "png"])
                if photo:
                    st.success("Görev fotoğrafı yüklendi. Yöneticinin onayı bekleniyor.")
       
        # Harita Gösterimi
        geolocator = Nominatim(user_agent="montaj_planner")
        location = geolocator.geocode("Istanbul, Turkey")
        map = folium.Map(location=[location.latitude, location.longitude], zoom_start=12)
        folium.Marker([location.latitude, location.longitude], popup="Başlangıç Noktası").add_to(map)
        st.write("Harita:")
        st_map = st_folium(map, width=700)

        # Takvimli İş Planı
        date = st.date_input("İş Planı İçin Tarih Seçin:", min_value=datetime.date.today())
        if st.button("İş Planını Kaydet"):
            st.success(f"İş planı {date} tarihine kaydedildi.")

        # PDF ve Excel Çıktısı
        if st.button("PDF Çıktısı Al"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Montaj Rota Planlama Raporu", ln=True, align="C")
            pdf.output("planlama_raporu.pdf")
            st.success("PDF çıktısı oluşturuldu.")
       
        if st.button("Excel Çıktısı Al"):
            df = pd.DataFrame({
                "Şehir": ["Istanbul", "Ankara", "Izmir"],
                "Süre (Saat)": [5, 4, 3],
                "Durum": ["Tamamlandı", "Yapılacak", "Onay Bekliyor"]
            })
            df.to_excel("planlama_raporu.xlsx", index=False)
            st.success("Excel çıktısı oluşturuldu.")
   
    else:
        st.error("Lütfen giriş yapın.")

# Rota Hesaplama ve Google Maps Linki
if st.session_state.logged_in:
    if st.button("Rota Hesapla"):
        origin = "Istanbul"
        destination = "Ankara"
        directions = gmaps.directions(origin, destination, mode="driving")
        distance = directions[0]['legs'][0]['distance']['text']
        duration = directions[0]['legs'][0]['duration']['text']
        google_maps_link = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}"

        st.write(f"Mesafe: {distance}, Süre: {duration}")
        st.write(f"Rota için Google Maps Linki: [Tıklayın]({google_maps_link})")

# Yapay Zeka Destekli Rota Önerisi (KMeans ile kümelenmiş rota önerisi)
def kmeans_route_optimization(cities, locations):
    kmeans = KMeans(n_clusters=2)  # Örnek olarak 2 kümeye ayırıyoruz
    kmeans.fit(locations)
    clusters = kmeans.predict(locations)
   
    optimized_route = []
    for i in range(max(clusters)+1):
        cluster_cities = [cities[j] for j in range(len(cities)) if clusters[j] == i]
        optimized_route.append(cluster_cities)
    return optimized_route

cities = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya"]
locations = [(41.0082, 28.9784), (39.9334, 32.8597), (38.4237, 27.1428), (40.1950, 29.0604), (36.8841, 30.7056)]
optimized_route = kmeans_route_optimization(cities, locations)

st.write("Yapay Zeka Destekli Rota Önerisi:")
st.write(f"Optimum Rota: {optimized_route}")

# Renkli Görev Durumu
def task_status_color(status):
    if status == "Yapılacak":
        return "gray"
    elif status == "Tamamlandı":
        return "green"
    elif status == "Onay Bekliyor":
        return "orange"

# Görev Durumunu Renkli Gösterme
task_status = st.selectbox("Görev Durumu Seçin:", ["Yapılacak", "Tamamlandı", "Onay Bekliyor"])
status_color = task_status_color(task_status)
st.markdown(f"<span style='color:{status_color}; font-weight:bold'>{task_status}</span>", unsafe_allow_html=True)

# Mobil Uyumlu Arayüz
st.markdown("""
    <style>
        @media (max-width: 600px) {
            .streamlit-expanderHeader {
                font-size: 16px;
            }
            .streamlit-expanderContent {
                font-size: 14px;
            }
        }
    </style>
""", unsafe_allow_html=True)

# Gerçek Zamanlı Konum Takibi (Örnek kullanım)
if st.button("Gerçek Zamanlı Konum Takibi Başlat"):
    # Gerçek zamanlı veriyi burada alabilirsiniz (örneğin, işçi telefonundan veya GPS cihazından)
    real_time_location = [41.0082, 28.9784]  # Örnek olarak Istanbul koordinatları
    map = folium.Map(location=real_time_location, zoom_start=12)
    folium.Marker(real_time_location, popup="İşçi Konumu").add_to(map)
    st.write("Gerçek zamanlı konum takibi başlatıldı.")
    st_map = st_folium(map, width=700)

# Detaylı Veri Analizi ve Raporlama
if st.button("Detaylı Rapor Al"):
    report_data = {
        "Şehir": ["Istanbul", "Ankara", "Izmir"],
        "Mesafe (km)": [400, 450, 500],
        "Süre (Saat)": [6, 5, 7],
        "Yakıt Maliyeti (TL)": [100, 120, 140],
        "İşçilik Maliyeti (TL)": [250, 200, 300]
    }
    df = pd.DataFrame(report_data)
    st.write(df)

    # PDF Raporu
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Detaylı Montaj Raporu", ln=True, align="C")
    pdf.ln(10)

    for index, row in df.iterrows():
        pdf.cell(200, 10, txt=f"{row['Şehir']} - Mesafe: {row['Mesafe (km)']} km, Süre: {row['Süre (Saat)']} saat", ln=True)

    pdf.output("detayli_rapor.pdf")
    st.success("Detaylı PDF raporu oluşturuldu.")
