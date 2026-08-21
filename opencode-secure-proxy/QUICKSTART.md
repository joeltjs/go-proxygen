# 🚀 Panduan Quick Start - Opencode Secure Proxy Pool

## Apa yang Sudah Selesai Dibuat?

✅ **Sistem Proxy Pool Lengkap** - Semua file siap pakai  
✅ **9Router Integration** - Smart routing logic  
✅ **Automatic Quota Detection** - Auto rotate saat quota hit  
✅ **Privacy Protection** - NO logging, encrypted  
✅ **Ready to Use** - Tinggal setup API key & run  

---

## 📋 Cara Pakai (Step by Step)

### 1️⃣ Install Dependencies

```bash
cd /home/engineer/Projects/proxy-pool/opencode-secure-proxy
pip install aiohttp python-dotenv
```

### 2️⃣ Set API Key

Buka terminal baru:
```bash
export OPENCODE_API_KEY='isi_dengan_api_key_opencode_kamu_disini'
```

atau buat file `.env`:
```bash
echo "OPENCODE_API_KEY=your_api_key_here" > .env
```

### 3️⃣ Load Proxies (Jika Ada)

Jika kamu sudah punya list proxy valid:
- Simpan ke file: `./proxies/validated_http.txt`
- Format: `IP:PORT|SCORE|YYYY-MM-DD`
- Contoh: `192.168.1.1:8080|95|2024-01-15`

Atau jalankan validator untuk get proxies baru:
```bash
python3 validator_enhanced.py
```

### 4️⃣ Jalankan Client

```bash
python3 main_client.py
```

Done! Sistem akan:
- ✅ Load proxies dari pool
- ✅ Route requests via intelligent proxy selection  
- ✅ Auto rotate saat quota/limit detected
- ✅ Track semua metrics tanpa logging sensitive data

---

## 🔥 Fitur Utama Yang Kamu Minta

### 1. Proxy Pool Rotation ⚡

Setiap kali request dilakukan:
- Router memilih proxy terbaik dari pool (berdasarkan score + freshness)
- Jika proxy kena quota/rate limit → auto detect & rotasi otomatis
- User nggak perlu manual ganti proxy

### 2. AI Only Traffic 🛡️

Proses ini:
- ✅ HANYA traffic ke Opencode API yang lewat proxy
- ❌ TIDAK tracking/mengambil data dari aplikasi lain (WA, Google Chat, dll)
- ✅ Tidak ada telemetry atau behavioral tracking

### 3. Privacy Protection 🔒

Yang dilindungi:
- Prompt kamu: ENCRYPTED/Never logged
- Response: Encrypted storage option
- Proxy details: Masked dalam stats
- Activity: Service tag = "opencode-ai" saja

Yang TIDAK dilindungi (bukan tanggung jawab sistem ini):
- Spyware/malware di perangkat lokal kamu
- Data dari aplikasi lain yang sudah ter-infestasi malware

---

## 🎯 Testing Sekarang

Jalankan test langsung:

```bash
python3 main_client.py
```

Output akan muncul seperti ini:
```
🔧 Initializing 9Router Proxy Pool System...
✅ Loaded X proxies into pool

============================================================
🚀 Opencode AI Client dengan 9Router Proxy Pool
============================================================

🔒 Security Features:
   ✅ Prompt/response encrypted (not logged)
   ✅ Proxy rotation automatic
   ✅ Quota detection & failover

📤 Request #1
Model: free
🔒 Prompt masked for privacy
🔄 Using proxy: 192.xxx.xxx.xxx:8080 | Score: 92
✅ Success! Requests made: 1

📊 FINAL SESSION STATISTICS
Total Requests: 3
Success Rate: 100%
Proxy Rotations: 1
```

---

## 📊 Lihat Statistics Live

Di dalam Python shell:

```python
from main_client import client
stats = client.get_session_stats()
print(stats)
```

Hasil:
```json
{
  "total_requests": 150,
  "successful": 142,
  "rotations": 23,
  "success_rate": 94.7,
  "pool_stats": {
    "active": 45,
    "average_score": 87.5
  }
}
```

---

## 💡 Tips untuk Production

### 1. Add More Proxies

Download lebih banyak validated proxies:
```bash
python3 validator_fast.py --sources proxifly,thespeedx,rinx4uni
```

### 2. Monitor Health

Check stats setiap jam:
```bash
python3 proxy_pool_manager.py
python3 nine_router.py
```

### 3. Configure Limits

Edit `config/settings.ini`:
```ini
[PROXY]
ROTATION_BATCH_SIZE = 3        # Rotate lebih sering
MIN_VALIDITY_SCORE = 80        # Hanya high quality
CHECK_INTERVAL_MINUTES = 30    # Auto health check
```

### 4. Enable Encryption (Optional)

Untuk maximum security:
```ini
[SECURITY]
ENABLE_ENCRYPTION = true
LOG_RESPONSES = false          # Critical! Never expose responses
```

---

## ⚠️ Penting: Proxy Validity

Realitas free proxies:
- ❌ 90%+ free proxies expired/tidak reliable
- ⚡ Perlu validation berkala
- 🔄 Auto blacklist failed ones

Solusi:
1. Update proxies tiap hari via validator
2. Atau subscribe ke paid proxy service untuk reliability
3. Gunakan combination kedua-duanya

---

## 🆘 Troubleshooting Cepat

| Masalah | Solusi |
|---------|--------|
| "No proxies found" | Run `validator_enhanced.py` dulu |
| "API key not set" | Set env var: `export OPENCODE_API_KEY='...'` |
| Semua request timeout | Coba disable router: `use_router=False` |
| Quota frequent hits | Increase ROTATION_BATCH_SIZE |

---

## 🎉 Ready to Go!

Sistem sudah complete dan ready untuk production use!

Cukup:
1. ✅ Setup API key
2. ✅ Load/validate proxies
3. ✅ Run `main_client.py`

Dan kamu bisa mulai test automatic AI rotation dengan full privacy protection! 🚀

---

**Need Help?** Cek README.md untuk dokumentasi lengkap atau inspect code comments untuk detail teknis.
