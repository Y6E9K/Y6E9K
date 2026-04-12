Kelime Asistanı Web v4

Yenilikler:
- Sekmeli çoklu tahta sistemi eklendi (en fazla 7 sekme).
- Yeni Tahta butonundan 15x15 veya 9x9 seçerek yeni sekme açılır.
- Sekmelerde kapatma butonu var.
- Sekme adına çift tıklayarak yeniden ad verebilirsin; Enter veya odak kaybı ile tamamlanır.
- Öneri listesinde tek tık yeşil önizleme, çift tık tahtaya uygulama yapar.
- Tahtada başka yere tıklayınca yeşil önizleme söner.
- Sağdaki harf kutularında en fazla 2 joker (?) kullanılabilir.
- Harf kutuları sıralı ilerler; eksik kutu varken ileri bir kutuya tıklanırsa ilk boş kutuya döner.
- Özet alanı ve temizle düğmesi kaldırıldı.

Çalıştırma
1) Backend
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
python -m uvicorn app.main:app

2) Frontend
cd frontend
npm install
npm run dev

Tarayıcı
http://localhost:3000


V6 yenilikleri:
- Sadece boş kareler koyu tona çekildi.
- Öneri listesi sabit yükseklik + sağda scroll aldı.
- Limit 1000'e çıkarıldı; daha fazla kombinasyon listelenir.
