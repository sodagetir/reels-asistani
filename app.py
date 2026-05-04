import streamlit as st
import google.generativeai as genai
import yt_dlp
import os
import time
import random

# --- 1. KİMLİK KARTLARI ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

st.set_page_config(page_title="Reels Çoklu Analiz Asistanı", page_icon="📝", layout="centered")
st.title("📝 Reels Çoklu Analiz Asistanı")

# --- 2. HAFIZA ---
if "sonuclar" not in st.session_state:
    st.session_state.sonuclar = []

# --- 3. VİDEO İNDİRİCİ FONKSİYON (NİNJA MODU) ---
def videoyu_indir(link, index):
    dosya_adi = f"gecici_reel_{index}.mp4"
    if os.path.exists(dosya_adi):
        os.remove(dosya_adi)
        
    # Meta'yı kandırmak için kendimizi iPhone Safari gibi gösteriyoruz
    ayarlar = {
        'outtmpl': dosya_adi,
        'format': 'best',
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    }
    
    # 3 kere indirmeyi deneme mekanizması (Hata alırsak pes etmesin)
    max_deneme = 3
    for deneme in range(max_deneme):
        try:
            with yt_dlp.YoutubeDL(ayarlar) as ydl:
                ydl.download([link])
            return dosya_adi # Başarılı olursa dosyayı ver
        except Exception as e:
            if deneme < max_deneme - 1:
                time.sleep(random.uniform(3, 6)) # Hata verirse 3-6 saniye bekle tekrar dene
            else:
                return None # 3 denemede de olmadıysa vazgeç

# --- 4. ARAYÜZ VE AKIŞ ---
st.write("Instagram Reel linklerini her satıra BİR TANE gelecek şekilde alt alta yapıştır. Asistan sırayla hepsini analiz etsin.")
linkler_metni = st.text_area("Linkleri Buraya Yapıştır (Alt alta):", height=150)

if st.button("🎙️ Toplu Analizi Başlat", use_container_width=True, type="primary"):
    if linkler_metni.strip():
        linkler = [link.strip() for link in linkler_metni.split('\n') if link.strip()]
        st.session_state.sonuclar = [] 
        
        ilerleme_cubugu = st.progress(0)
        durum_metni = st.empty()
        
        for index, link in enumerate(linkler):
            # Arka arkaya hızlı istek atıp ban yememek için her video öncesi rastgele bekleme (İlk video hariç)
            if index > 0:
                bekleme_suresi = random.uniform(4, 8)
                durum_metni.warning(f"🕵️ Meta radarına yakalanmamak için {int(bekleme_suresi)} saniye bekleniyor...")
                time.sleep(bekleme_suresi)
                
            durum_metni.info(f"⏳ Video {index + 1} / {len(linkler)} işleniyor...")
            
            video_yolu = videoyu_indir(link, index)
            
            if video_yolu:
                yuklenen_video = genai.upload_file(path=video_yolu)
                
                while yuklenen_video.state.name == "PROCESSING":
                    time.sleep(2)
                    yuklenen_video = genai.get_file(yuklenen_video.name)
                    
                transkript_prompt = "Lütfen bu videodaki konuşmaların kelimesi kelimesine tam dökümünü (transkriptini) çıkar. Başında, sonunda veya içinde hiçbir yorum, özet, merhaba veya ekstra açıklama ekleme. SADECE konuşulanları yaz."
                ilk_cevap = model.generate_content([yuklenen_video, transkript_prompt])
                transkript_metni = ilk_cevap.text
                
                ceviri_prompt = f"""
                Sen usta bir çevirmen ve dilbilimcisin. Aşağıdaki metni, bağlamını, duygusunu ve tonunu koruyarak çok doğal bir Türkçeye çevir. 
                Kelimesi kelimesine robotik bir çeviri KESİNLİKLE YAPMA. 
                Eğer deyimler, metaforlar veya kültürel vurgular varsa, bunları Türkçedeki en doğal karşılıklarıyla uyarla. Metin akıcı ve anlaşılır olmalı.
                
                ÇEVRİLECEK METİN:
                {transkript_metni}
                """
                ikinci_cevap = model.generate_content(ceviri_prompt)
                ceviri_metni = ikinci_cevap.text
                
                st.session_state.sonuclar.append({
                    "video_no": index + 1,
                    "link": link,
                    "transkript": transkript_metni,
                    "ceviri": ceviri_metni,
                    "hata": False
                })
            else:
                st.session_state.sonuclar.append({
                    "video_no": index + 1,
                    "link": link,
                    "hata": True
                })
            
            ilerleme_cubugu.progress((index + 1) / len(linkler))
            
        durum_metni.success(f"✅ İşlem tamam! {len(linkler)} videonun analizine aşağıdan bakabilirsin.")
    else:
        st.warning("Lütfen en az bir link yapıştır.")

# --- 5. SONUÇLARI EKRANA BASMA ---
if st.session_state.sonuclar:
    st.divider()
    st.subheader("📊 Analiz Sonuçları")
    
    for sonuc in st.session_state.sonuclar:
        with st.expander(f"🎬 Video {sonuc['video_no']} (Tıklayıp açın)", expanded=False):
            st.caption(f"Kaynak Link: {sonuc['link']}")
            
            if sonuc["hata"]:
                st.error("❌ Bu video defalarca denenmesine rağmen indirilemedi. Gizli hesap veya katı Meta engeli.")
            else:
                st.markdown("**🇹🇷 Çeviri:**")
                st.info(sonuc["ceviri"])
                st.markdown("**🌐 Orijinal Transkript:**")
                st.write(sonuc["transkript"])
