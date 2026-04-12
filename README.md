# Kelime Asistanı Web MVP

Bu paket, masaüstü sürümünü gerçek internet sitesine dönüştürmek için hazırlanmış ilk yayınlanabilir sürümdür.

## Neler var?
- React + Vite ön yüz
- FastAPI arka uç
- 9x9 ve 15x15 tahta desteği
- Türkçe harf destekli temel solver API'si
- Vercel + Render deploy dosyaları

## Klasör yapısı
- `frontend/` → site arayüzü
- `backend/` → API ve solver

## Yerelde çalıştırma

### Backend
```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API varsayılan olarak `http://localhost:8000` üzerinde açılır.

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Site varsayılan olarak `http://localhost:3000` üzerinde açılır.

## Gerçek internet sitesine yayınlama

### 1) Backend → Render
- GitHub'a yükle
- Render'da yeni Web Service oluştur
- Root Directory: `backend`
- Render otomatik olarak `render.yaml` içindeki ayarları kullanabilir
- Yayın sonrası URL örneği: `https://kelime-asistani-api.onrender.com`

### 2) Frontend → Vercel
- GitHub repo bağla
- Project Root: `frontend`
- Environment Variable ekle:
  - `VITE_API_BASE=https://kelime-asistani-api.onrender.com`
- Deploy et

### 3) Domain bağlama
- Vercel üzerinden `kelimeasistani.com` veya istediğin alan adını bağlayabilirsin

## Sonraki adım
Bu MVP'den sonra yapılacak en mantıklı geliştirmeler:
1. Masaüstündeki solver'ın birebir davranışını web API'ye taşıma
2. Çoklu tahta sekmeleri
3. Kayıt / yükleme
4. Kullanıcı hesabı
5. Mobil kullanım için daha güçlü tahta etkileşimi
