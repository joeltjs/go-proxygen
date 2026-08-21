# 📌 COMPACT SUMMARY - Seluruh Percakapan Project Ini

> File ini adalah ringkasan inti dari seluruh diskusi. Untuk agent yang baru membaca project ini: mulai dari sini.

---

## 🎯 Tujuan Project (Kenapa Dibuat)

Memanfaatkan **OpenCode Free tier** secara maksimal dengan cara:
1. Import banyak proxy gratis ke **Proxy Pools** milik 9Router
2. Set rotation strategy **Round-robin** di provider OpenCode
3. Setiap request keluar lewat IP proxy berbeda → quota harian per-IP tidak pernah habis
4. Hasil: ribuan request gratis per hari tanpa bayar

**Alasan:** Subscription AI premium mahal ($500+/bulan). Free tier dibatasi per-IP (~40-60 req/IP/hari). Dengan rotasi 1500+ proxy, kapasitas jadi ~60K request/hari ≈ 1.6 miliar token/bulan, gratis.

---

## 🏗️ Arsitektur Sistem

```
Kilo Code / Agent
      ↓
9Router (localhost:20128) ← API key internal: sk-ebce437b01a1c7eb-6xbgmg-ac257ac8
      ↓ Round-robin rotation
Proxy Pool (1500+ proxies, format http://IP:PORT atau socks5://IP:PORT)
      ↓
OpenCode Free API (NO-AUTH provider, tidak butuh API key)
```

### Komponen:
- **9Router** — terinstall global via npm (`~/.nvm/versions/node/v24.11.1/lib/node_modules/9router/`), DB di `~/.9router/db/data.sqlite`, dashboard di `http://localhost:20128`
- **Proxy sources** — 3 repo GitHub terpercaya: [TheSpeedX/PROXY-List](https://github.com/TheSpeedX/PROXY-List), [proxifly/free-proxy-list](https://github.com/proxifly/free-proxy-list), [rix4uni/fresh-proxy-list](https://github.com/rix4uni/fresh-proxy-list)
- **Generator tool** — `generate_proxies.py <jumlah>` (0.1 detik untuk 1500 proxy), output overwrite ke `generated_proxy_result.txt`
- **Cloudflare Worker Relay** — opsional, lapisan anonimitas ekstra, free tier 100K req/hari

---

## ✅ Yang Sudah Dikerjakan & Terbukti Jalan

1. **Import proxy ke 9Router** via Batch Import — format WAJIB ada prefix protocol (`http://IP:PORT`), kalau polos `IP:PORT` akan error "Unsupported format"
2. **Set rotation Round-robin** untuk provider `opencode` — semua proxy aktif dipakai bergiliran otomatis, tidak perlu "bind" manual
3. **Test request sukses** — `opencode/big-pickle` merespons normal via endpoint `http://127.0.0.1:20128/v1/chat/completions` dengan cost "0"
4. **Fix config Kilo Code** (`~/.config/kilo/kilo.jsonc`) — nama model yang benar adalah prefix `opencode/...` (bukan `oc/...`): `opencode/big-pickle`, `opencode/mimo-v2.5-free`, dll.
5. **Generate 1500-2000 proxy** dari gabungan 3 sumber GitHub

---

## ⚠️ Temuan Penting Selama Proses

| Temuan | Detail |
|--------|--------|
| **DeepSeek V4 Flash free ENDED** | Promo gratis berakhir ([Reddit](https://www.reddit.com/r/opencode/comments/1vtzz5v/free_promotion_has_ended_for_deepseek_v4_flash/)) → kena `FreeUsageLimitError`. Model masih ada tapi quota free-nya habis/dibatasi |
| **Model free pengganti** | `opencode/mimo-v2.5-free`, `opencode/minimax-m3-free`, `opencode/qwen3.6-plus-free` — masih gratis |
| **Rekomendasi model** | Qwen 3.6 = terbaik untuk coding + privacy paling baik; MiniMax M3 = reasoning terkuat. Pakai keduanya via round-robin |
| **Rate limit = per-IP** | Rotasi proxy efektif bypass daily quota. Kemungkinan ada account-level cap tersembunyi (belum terkonfirmasi) — mulai dengan usage moderat lalu naikkan bertahap |
| **Free proxy unreliable** | ~85-90% work pada satu waktu; jalankan Health Check di 9Router secara berkala, regenerate list mingguan |
| **OpenCode Free = No-auth** | Tidak perlu API key sama sekali di 9Router |

---

## 🔒 Kesimpulan Keamanan (Jujur)

**Aman ✅:**
- Isi prompt/response **terenkripsi HTTPS** — proxy hanya lihat domain tujuan, tidak bisa baca isi
- IP asli **tersembunyi** di balik rotasi proxy (+ Cloudflare relay opsional)
- Data lokal/VPS **tidak bisa diakses** oleh AI service sama sekali (one-way API call)
- Malware/injection via traffic = **nol risiko** (TLS mencegah tampering)

**Risiko nyata ⚠️:**
- Melanggar ToS OpenCode (bypass rate limit) → akun bisa dibanned, tapi dampak minim (akun gratis)
- Free tier kemungkinan memakai data untuk training/pattern analysis → **jangan kirim credentials, secrets, .env, private key, atau data sensitif**
- Kalau dipakai dari laptop kantor → IT kantor bisa mendeteksi traffic anomali (risiko terbesar yang realistis)
- Agent dengan MCP bisa membaca file lokal jika dikonfigurasi ceroboh → batasi akses ke folder khusus saja

**VPS:** Oracle Always Free (2 core ARM, 12GB RAM) lebih dari cukup — bahkan 1 CPU/1GB pun memadai. 9Router pakai <300MB RAM, <15% CPU. Tidak perlu VPS gratisan lain (alternatifnya semua lebih buruk).

---

## 💰 Angka-Angka Penting

| Metrik | Nilai |
|--------|-------|
| Quota per IP | ~40-60 request/hari |
| Dengan 1500 proxy | ~60K request/hari |
| Token/bulan | ~1.6 miliar |
| Nilai jika dibayar | ~$500-2800/bulan |
| Biaya aktual | **$0** |
| Cloudflare Workers free | 100K req/hari (pakai ≤75% = aman) |

---

## 📂 Struktur Dokumentasi

```
markdowns/
├── summaries/
│   ├── README.md                      ← Penjelasan project untuk agent (APA & KENAPA)
│   └── CONVERSATION_COMPACT.md        ← File ini (ringkasan seluruh diskusi)
├── for-vps/
│   └── VPS_SETUP_COMPLETE_GUIDE.md    ← Panduan deploy lengkap di VPS
└── [file lainnya]                     ← Analisis detail (rate limit, privacy, dsb)
```

---

## 🚀 Quick Reference Perintah

```bash
# Generate proxy baru (overwrite generated_proxy_result.txt)
python3 generate_proxies.py 1500

# Lihat list proxy siap import
cat generated_proxy_result.txt

# Test request manual via 9Router
curl -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-ebce437b01a1c7eb-6xbgmg-ac257ac8" \
  -d '{"model": "opencode/mimo-v2.5-free", "messages": [{"role": "user", "content": "hi"}]}'

# Start 9Router (kalau belum jalan)
9router -H 127.0.0.1 -p 20128
```

---

*Terakhir diupdate: 2026-08-21 — Status: OpenCode Free aktif via 9Router + proxy pool round-robin*

## 🚨 UPDATE IMPORTANT - Model Availability & Privacy Reality (2026-08-21)

### ⚠️ Yang Berubah:
| Old Status | New Reality |
|------------|-------------|
| ✅ `qwen3.6-plus-free` available | ❌ **REMOVED** by OpenCode (promo ended!) |
| ✅ `minimax-m3-free` available | ❌ **REMOVED** by OpenCode (quota changed!) |
| ❓ `muse-spark-1.2-contributor` | ⚡ POWERFUL but USE WITH CAUTION |
| ✅ `mimo-v2.5-free`, `hy3-free` | ✅ Still available (safe to use) |
| ✅ `nemotron-3-lightning` | ✅ New addition (try cautiously) |

### 🔒 HONEST PRIVACY REALITY:

**SEMUA Free Tier sama saja:**
- TIDAK ada yang 100% secure untuk data sensitive
- HTTPS protect traffic, tapi provider still bisa log/prompts storage
- Training policies unclear across ALL providers
- You CANNOT get both "free" AND "guaranteed privacy"

**Best practices tetap sama:**
- Never send credentials/secrets to ANY cloud AI
- Sanitize prompts before sending
- Assume everything COULD be stored/logged
- Use test/sample data only for production projects

---

## 🎯 CONCLUSION - Should You Continue Using This System?

**YES, IF YOU ACCEPT THESE TRADEOFFS:**
✅ Accept that no free AI is truly private
✅ Use proxy rotation to hide your IP
✅ Sanitize all prompts (no secrets!)
✅ Understand it's for learning/testing, NOT sensitive work

**NO, IF YOU NEED:**
❌ Complete privacy/anonymity  
❌ Protected sensitive data handling
❌ Guaranteed no-training policy

**Bottom Line:** Worth continuing for general coding/learning if you follow best practices! 😊

