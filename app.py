import streamlit as st
import google.generativeai as genai
import yt_dlp
import os
import time

# --- 1. KİMLİK KARTLARI ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

st.set_page_config(page_title="Reels Çoklu Analiz Asistanı", page_icon="📝", layout="centered")
st.title("📝 Reels Çoklu Analiz Asistanı")

# --- 2. HAFIZA ---
if "sonuclar" not in st.session_state:
    st.session_state.sonuclar = []

# --- 3. VİDEO İNDİRİCİ FONKSİYON ---
def videoyu_indir(link, index):
    dosya_adi = f"gecici_reel_{index}.mp4"
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
st.write("Instagram Reel linklerini her satıra BİR TANE gelecek şekilde alt alta yapıştır. Asistan sırayla hepsini analiz etsin.")
linkler_metni = st.text_area("Linkleri Buraya Yapıştır (Alt alta):", height=150)

if st.button("🎙️ Toplu Analizi Başlat", use_container_width=True, type="primary"):
    if linkler_metni.strip():
        # Satır satır ayır ve boş olanları çöpe at
        linkler = [link.strip() for link in linkler_metni.split('\n') if link.strip()]
        st.session_state.sonuclar = [] # Önceki sonuçları temizle
        
        ilerleme_cubugu = st.progress(0)
        durum_metni = st.empty()
        
        for index, link in enumerate(linkler):
            durum_metni.info(f"⏳ Video {index + 1} / {len(linkler)} işleniyor...")
            
            video_yolu = videoyu_indir(link, index)
            
            if video_yolu:
                yuklenen_video = genai.upload_file(path=video_yolu)
                
                while yuklenen_video.state.name == "PROCESSING":
                    time.sleep(2)
                    yuklenen_video = genai.get_file(yuklenen_video.name)
                    
                # 1. Aşama: Transkript
                transkript_prompt = "Lütfen bu videodaki konuşmaların kelimesi kelimesine tam dökümünü (transkriptini) çıkar. Başında, sonunda veya içinde hiçbir yorum, özet, merhaba veya ekstra açıklama ekleme. SADECE konuşulanları yaz."
                ilk_cevap = model.generate_content([yuklenen_video, transkript_prompt])
                transkript_metni = ilk_cevap.text
                
                # 2. Aşama: Çeviri
                ceviri_prompt = f"""
                Sen usta bir çevirmen ve dilbilimcisin. Aşağıdaki metni, bağlamını, duygusunu ve tonunu koruyarak çok doğal bir Türkçeye çevir. 
                Kelimesi kelimesine robotik (Google Translate tarzı) bir çeviri KESİNLİKLE YAPMA. 
                Eğer deyimler, metaforlar veya kültürel vurgular varsa, bunları Türkçedeki en doğal karşılıklarıyla uyarla. Metin akıcı, tok ve anlaşılır olmalı.
                
                ÇOK ÖNEMLİ KURAL: Çevirinin başına veya sonuna HİÇBİR açıklama, giriş veya laga luga ekleme. SADECE VE SADECE çevrilmiş metni ver.
                
                ÇEVRİLECEK METİN:
                {transkript_metni}
                """
                ikinci_cevap = model.generate_content(ceviri_prompt)
                ceviri_metni = ikinci_cevap.text
                
                # Sonucu kaydet
                st.session_state.sonuclar.append({
                    "video_no": index + 1,
                    "link": link,
                    "transkript": transkript_metni,
                    "ceviri": ceviri_metni,
                    "hata": False
                })
            else:
                # Video inmezse hata kaydet
                st.session_state.sonuclar.append({
                    "video_no": index + 1,
                    "link": link,
                    "hata": True
                })
            
            # İlerlemeyi güncelle
            ilerleme_cubugu.progress((index + 1) / len(linkler))
            
        durum_metni.success(f"✅ {len(linkler)} videonun analizi tamamlandı!")
    else:
        st.warning("Lütfen en az bir link yapıştır.")

# --- 5. SONUÇLARI EKRANA BASMA (Açılır Kapanır Kutularla) ---
if st.session_state.sonuclar:
    st.divider()
    st.subheader("📊 Analiz Sonuçları")
    
    for sonuc in st.session_state.sonuclar:
        # Her video için bir açılır-kapanır kutu oluştur
        with st.expander(f"🎬 Video {sonuc['video_no']} (Tıklayıp açın)", expanded=False):
            st.caption(f"Kaynak Link: {sonuc['link']}")
            
            if sonuc["hata"]:
                st.error("❌ Bu video indirilemedi. Gizli hesap veya Meta engeli olabilir.")
            else:
                st.markdown("**🇹🇷 Çeviri:**")
                st.info(sonuc["ceviri"])
                st.markdown("**🌐 Orijinal Transkript:**")
                st.write(sonuc["transkript"])
