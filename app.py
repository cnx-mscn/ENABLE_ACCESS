# app.py
import streamlit as st
import googlemaps
import json
from datetime import date, datetime
from haversine import haversine
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
from reportlab.pdfgen import canvas
from sklearn.cluster import KMeans

# ============ AYARLAR ============ #
API_KEY = "AIzaSyDwQVuPcON3rGSibcBrwhxQvz4HLTpF9Ws"  # Google API key
JSON_FILE = "veriler.json"

gmaps = googlemaps.Client(key=API_KEY)
st.set_page_config(page_title="Montaj Yönetim Sistemi", layout="wide")

# ============ JSON VERİ YÜKLEME ============ #
def veri_yukle():
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"ekipler": {}, "baslangic_konum": None}

def veri_kaydet(veri):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

veri = veri_yukle()

# ============ GİRİŞ ============ #
import bcrypt

# Kullanıcıları JSON'dan yükle
def kullanicilari_yukle():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

kullanicilar = kullanicilari_yukle()

# === GİRİŞ === #
if "giris" not in st.session_state:
    st.session_state.giris = None
    st.session_state.kullanici = None

if not st.session_state.giris:
    st.title("🔐 Giriş Yap")

    kullanici_adi = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    
    if st.button("✅ Giriş"):
        if kullanici_adi in kullanicilar:
            hashed = kullanicilar[kullanici_adi]["password"].encode("utf-8")
            if bcrypt.checkpw(sifre.encode("utf-8"), hashed):
                st.session_state.giris = kullanicilar[kullanici_adi]["role"]
                st.session_state.kullanici = kullanici_adi
                st.success("Giriş başarılı")
                st.experimental_rerun()
            else:
                st.error("Hatalı şifre")
        else:
            st.error("Kullanıcı bulunamadı")
    
    st.stop()



# ============ YÖNETİCİ ============ #
if st.session_state.giris == "Yönetici":
    st.title("🛠️ Yönetici Paneli")

    st.sidebar.header("👷 Ekip Yönetimi")
    yeni_ekip = st.sidebar.text_input("Yeni Ekip Adı")
    if st.sidebar.button("➕ Ekip Oluştur") and yeni_ekip:
        if yeni_ekip not in veri["ekipler"]:
            veri["ekipler"][yeni_ekip] = {"members": [], "visited_cities": []}
            veri_kaydet(veri)

    secilen_ekip = st.sidebar.selectbox("Ekip Seç", list(veri["ekipler"].keys()) if veri["ekipler"] else [])

    st.sidebar.header("📍 Başlangıç Konumu")
    if not veri["baslangic_konum"]:
        adres = st.sidebar.text_input("Adres")
        if st.sidebar.button("✅ Onayla") and adres:
            sonuc = gmaps.geocode(adres)
            if sonuc:
                veri["baslangic_konum"] = sonuc[0]["geometry"]["location"]
                st.sidebar.success("Başlangıç kaydedildi.")
                veri_kaydet(veri)

    st.subheader("📌 Görev Ekle")
    with st.form("form_gorev"):
        sehir = st.text_input("Şehir / Bayi")
        onem = st.slider("Önem", 1, 5, 3)
        sure = st.number_input("Süre (saat)", 1, 24, 2)
        tarih = st.date_input("Tarih", date.today())
        ekle = st.form_submit_button("➕ Ekle")
        if ekle and secilen_ekip:
            sonuc = gmaps.geocode(sehir)
            if sonuc:
                konum = sonuc[0]["geometry"]["location"]
                gorev = {
                    "sehir": sehir,
                    "konum": konum,
                    "onem": onem,
                    "is_suresi": sure,
                    "tarih": str(tarih),
                    "foto": None,
                    "onay": None
                }
                veri["ekipler"][secilen_ekip]["visited_cities"].append(gorev)
                veri_kaydet(veri)
                st.success("Görev eklendi.")

    # Rota Haritası
    if veri["baslangic_konum"] and secilen_ekip:
        st.subheader("🗺️ Rota Haritası")
        bas = veri["baslangic_konum"]
        harita = folium.Map(location=[bas["lat"], bas["lng"]], zoom_start=6)
        folium.Marker([bas["lat"], bas["lng"]], popup="Başlangıç", icon=folium.Icon(color="blue")).add_to(harita)

        sehirler = veri["ekipler"][secilen_ekip]["visited_cities"]
        for i, s in enumerate(sehirler):
            lat, lng = s["konum"]["lat"], s["konum"]["lng"]
            renk = "red"
            if s["onay"] == True: renk = "green"
            elif s["foto"]: renk = "orange"
            folium.Marker([lat, lng], popup=s["sehir"], icon=folium.Icon(color=renk)).add_to(harita)

        st_folium(harita, width=700)

    # Onay Paneli
    st.subheader("✅ Görev Onay")
    for i, s in enumerate(veri["ekipler"][secilen_ekip]["visited_cities"]):
        if s["foto"] and s["onay"] is None:
            st.info(f"{s['sehir']} → Onay Bekliyor")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✔️ Onayla", key=f"onay_{i}"):
                    s["onay"] = True
                    veri_kaydet(veri)
            with col2:
                if st.button("❌ Reddet", key=f"red_{i}"):
                    s["onay"] = False
                    veri_kaydet(veri)

    # PDF ve Excel
    st.subheader("📄 Rapor Çıktıları")
    df = pd.DataFrame(veri["ekipler"][secilen_ekip]["visited_cities"])
    if not df.empty:
        st.dataframe(df[["sehir", "tarih", "is_suresi", "onay"]])
        if st.button("📥 Excel İndir"):
            df.to_excel("rapor.xlsx", index=False)
            with open("rapor.xlsx", "rb") as f:
                st.download_button("Raporu İndir (Excel)", f, file_name="rapor.xlsx")

        if st.button("📥 PDF İndir"):
            c = canvas.Canvas("rapor.pdf")
            c.drawString(100, 800, f"{secilen_ekip} - Montaj Raporu")
            for i, row in df.iterrows():
                c.drawString(100, 770 - i*20, f"{row['sehir']} - {row['tarih']} - {row['is_suresi']} saat - Onay: {row['onay']}")
            c.save()
            with open("rapor.pdf", "rb") as f:
                st.download_button("Raporu İndir (PDF)", f, file_name="rapor.pdf")

    # Takvim Görünümü
    st.subheader("📅 Takvim")
    if not df.empty:
        df["tarih"] = pd.to_datetime(df["tarih"])
        fig = px.timeline(df, x_start="tarih", x_end="tarih", y="sehir", color="onay", title="Görev Takvimi")
        st.plotly_chart(fig)

    # Yapay Zekâ ile Önerilen Rota
    st.subheader("🤖 Yapay Zekâ Rota Önerisi")
    if len(df) >= 2:
        df["lat"] = df["konum"].apply(lambda x: x["lat"])
        df["lng"] = df["konum"].apply(lambda x: x["lng"])
        coords = df[["lat", "lng"]].values
        kmeans = KMeans(n_clusters=min(3, len(coords)), n_init="auto").fit(coords)
        df["grup"] = kmeans.labels_
        st.write("AI Önerili Gruplar (Rotalar):")
        st.dataframe(df[["sehir", "grup"]])

# ============ İŞÇİ ============ #
elif st.session_state.giris == "İşçi":
    st.title("👷 İşçi Paneli")
    secim = st.selectbox("Ekip Seç", list(veri["ekipler"].keys()) if veri["ekipler"] else [])
    if secim:
        for i, s in enumerate(veri["ekipler"][secim]["visited_cities"]):
            if not s["foto"]:
                st.write(f"📍 {s['sehir']} - {s['tarih']} - Süre: {s['is_suresi']} saat")
                f = st.file_uploader(f"{s['sehir']} Fotoğraf", type=["jpg", "png"], key=f"foto_{i}")
                if f:
                    s["foto"] = f.name
                    veri_kaydet(veri)
                    st.success("Fotoğraf yüklendi.")
            else:
                if s["onay"] == True:
                    st.success(f"{s['sehir']} ✅ Onaylandı")
                elif s["onay"] == False:
                    st.error(f"{s['sehir']} ❌ Reddedildi, tekrar yükleyin")
                    s["foto"] = None
                    veri_kaydet(veri)
                else:
                    st.info(f"{s['sehir']} ⏳ Onay bekleniyor")
