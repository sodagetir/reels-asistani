import streamlit as st
import google.generativeai as genai
import yt_dlp
import os
import time

# --- 1. KİMLİK KARTLARI ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

st.set_page_config(page_title="Reels Transkript & Çeviri Asistanı", page_icon="📝", layout="centered")
st.title("📝 Reels Transkript Asistanı")

# --- 2. HAFIZA ---
if "transkript" not in st.session_state:
    st.session_state.transkript = ""
if "ceviri" not in st.session_state:
    st.session_state.ceviri = ""

# --- 3. VİDEO İNDİRİCİ FONKSİYON ---
def videoyu_indir(link):
    dosya_adi = "gecici_reel.mp4"
    if os.path.exists(dosya_adi):
        os.remove(dosya_adi)
        
    ayarlar = {
        'outtmpl': dosya_adi,
        'format': 'best',
        'quiet': True 
    }
    try:
        with yt_dlp.YoutubeDL(ayarlar) as ydl:
            ydl.download([link])
        return dosya_adi
    except Exception as e:
        return None

# --- 4. ARAYÜZ VE AKIŞ ---
st.write("Instagram Reel linkini yapıştır, sistem videoyu Gemini'a dinletip sana hem orijinal dökümü hem de doğal Türkçe çevirisini tek seferde versin.")
reel_linki = st.text_input("Instagram Reel Linkini Buraya Yapıştır:")

if st.button("🎙️ Transkripti ve Çeviriyi Çıkar", use_container_width=True):
    if reel_linki:
        with st.spinner("1/3: Meta kalkanları aşılıyor, video indiriliyor..."):
            video_yolu = videoyu_indir(reel_linki)
            
        if video_yolu:
            with st.spinner("2/3: Gemini videoyu dinliyor ve orijinal deşifreyi çıkarıyor..."):
                yuklenen_video = genai.upload_file(path=video_yolu)
                
                while yuklenen_video.state.name == "PROCESSING":
                    time.sleep(2)
                    yuklenen_video = genai.get_file(yuklenen_video.name)
                    
                # 1. Aşama: Saf Transkript Çıkarımı
                transkript_prompt = "Lütfen bu videodaki konuşmaların kelimesi kelimesine tam dökümünü (transkriptini) çıkar. Hiçbir yorum, özet veya ekstra açıklama ekleme. Sadece konuşulanları yaz."
                ilk_cevap = model.generate_content([yuklenen_video, transkript_prompt])
                st.session_state.transkript = ilk_cevap.text
                
            with st.spinner("3/3: Metin analiz ediliyor ve doğal Türkçeye çevriliyor..."):
                # 2. Aşama: Doğrudan Çeviriye Geçiş (Buton beklemeden)
                ceviri_prompt = f"""
                Sen usta bir çevirmen ve dilbilimcisin. Aşağıdaki metni, bağlamını, duygusunu ve tonunu koruyarak çok doğal bir Türkçeye çevir. 
                Kelimesi kelimesine robotik (Google Translate tarzı) bir çeviri KESİNLİKLE YAPMA. 
                Eğer deyimler, metaforlar veya kültürel vurgular varsa, bunları Türkçedeki en doğal karşılıklarıyla uyarla. Metin akıcı, tok ve anlaşılır olmalı.
                
                ÇEVRİLECEK METİN:
                {st.session_state.transkript}
                """
                ikinci_cevap = model.generate_content(ceviri_prompt)
                st.session_state.ceviri = ikinci_cevap.text
                
            st.rerun() # Tüm işlemler bitince sayfayı yenile ve sonuçları göster
        else:
            st.error("HATA: Video indirilemedi. Gizli bir hesap olabilir veya Meta engelledi.")
    else:
        st.warning("Lütfen bir link yapıştır.")

# İşlemler bittiyse sonuçları ekrana bas
if st.session_state.transkript and st.session_state.ceviri:
    st.success("✅ İşlem Tamam! İşte sonuçlar:")
    
    st.info("🇹🇷 Doğal Türkçe Çeviri:")
    st.text_area("Kopyalamak için:", st.session_state.ceviri, height=250)
    
    st.divider()
    
    st.write("🌐 Orijinal Transkript:")
    st.text_area("Kaynak Metin:", st.session_state.transkript, height=150)
