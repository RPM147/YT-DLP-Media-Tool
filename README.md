# 🎥 RPM's Media Tool

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-v6.4+-green?style=for-the-badge&logo=qt)
![yt-dlp](https://img.shields.io/badge/Powered%20By-yt--dlp-red?style=for-the-badge)

**RPM's Media Tool**, YouTube, Instagram, TikTok, Twitter (X) ve daha yüzlerce platformdan yüksek kalitede video ve ses indirmenize olanak tanıyan, modern arayüzlü ve çok gelişmiş bir masaüstü uygulamasıdır. Arka planda devasa bir `yt-dlp` ve `ffmpeg` motoru barındırır.

---

## ✨ Özellikler

- 🚀 **Geniş Platform Desteği:** YouTube, Instagram, TikTok, Twitch, Facebook, X (Twitter) vb.
- 📺 **Yüksek Çözünürlük ve Format:** 4K (2160p), 2K (1440p), 1080p, 720p (MP4, MKV) çözünürlükleri.
- 🎵 **Ses Dönüştürme:** Videoları doğrudan MP3, AAC, FLAC, WAV, OPUS, M4A formatlarına dönüştürme.
- 🔍 **Uygulama İçi Arama:** Doğrudan uygulama üzerinden YouTube'da arama yapma ve küçük resimleri (thumbnail) görerek kuyruğa ekleme.
- ▶️ **Uygulama İçi Oynatıcı:** Videoları indirmeden önce `ffplay` entegrasyonu sayesinde harici pencerede yüksek hızda izleme/önizleme.
- ✂️ **Video Kırpma:** Videoların sadece belirli zaman aralıklarını (Örn: 01:10:00 - 01:15:30) indirme.
- ⏳ **Gelişmiş Kuyruk ve Zamanlama:** Birden fazla videoyu sıraya ekleme veya indirmeyi ileri bir saate zamanlama.
- 📦 **Toplu İndirme:** `.txt` uzantılı bir metin belgesinden binlerce bağlantıyı tek seferde içe aktarıp otomatik indirme.
- 🏷️ **Gelişmiş Meta Veri Desteği:** İndirilen MP4, MP3 ve MKV dosyalarına video kapağını (thumbnail), YouTube alt yazılarını ve açıklamasını (description) doğrudan gömme.
- 🍪 **Çerez (Cookie) Desteği:** Kendi tarayıcınızın çerezlerini otomatik algılayarak "Yaş Kısıtlamalı" veya "Sadece Üyelere Özel" videoları indirme.
- 📝 **Transkript Arşivleme:** YouTube video, oynatma listesi ve kanallarından alt yazı/transkriptleri toplu olarak `txt`/`md` biçiminde arşivleme; zaman damgaları, yalnızca-meta veri modu, dil önceliği ve devam ettirilebilir (resume) işleme.
- 🎨 **Modern ve Temiz Arayüz:** Göz yormayan Catppuccin Mocha karanlık teması, canlı veri grafikleri ve estetik dizayn.

---

## 🛠 Kurulum ve Gereksinimler

Projenin sorunsuz çalışabilmesi için işletim sisteminizde **Python 3.10 veya üzeri** yüklü olmalıdır.

### 1. Dosyaları İndirin
Projeyi klonlayın veya `.zip` olarak bilgisayarınıza indirin:
```bash
git clone https://github.com/Furkan-FS/YT-DLP-Media-Tool.git
cd YT-DLP-Media-Tool
```

### 2. FFmpeg, FFplay ve FFprobe Kurulumu (ÖNEMLİ)
Uygulama; video birleştirme, kırpma, meta veri gömme ve uygulama içi oynatıcı özellikleri için `FFmpeg` altyapısına doğrudan ihtiyaç duyar. Github dosya boyutu sınırları gereği bu dosyalar depoda yer **almamaktadır**.

1. [FFmpeg Resmi Web Sitesinden](https://ffmpeg.org/download.html) işletim sisteminize uygun derlenmiş sürümü (Essentials veya Full) indirin.
2. Zip dosyasının içerisindeki `bin` klasöründe bulunan şu 3 dosyayı kopyalayın:
   - `ffmpeg.exe`
   - `ffplay.exe`
   - `ffprobe.exe`
3. Bu 3 dosyayı doğrudan projenizin ana dizinine (yani `main.py`'nin yanına) yapıştırın.

### 3. Python Kütüphanelerinin Kurulumu
Komut istemini (CMD veya Terminal) proje dizininde açarak gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```
*(Eğer requirements.txt kullanmak istemezseniz: `pip install PyQt6 yt-dlp` komutunu girebilirsiniz).*

### 4. Başlatın
Tüm adımları tamamladıktan sonra uygulamayı başlatmak için:
```bash
python main.py
```

---

## 📝 Transkript Arşivleme

Uygulama; YouTube videoları, oynatma listeleri ve kanallarından alt yazı/transkript arşivlemek için ayrı bir **Transkriptler** sayfası içerir. Medya indiriciyle aynı çerez (cookie) ayarlarını kullanır ve medya indirme kuyruğundan bağımsız çalışır.

**Desteklenen transkript çıktıları:**

- `both`: hem `txt` hem `md` transkript dosyalarını yazar.
- `txt`: yalnızca düz metin (`.txt`) yazar.
- `md`: frontmatter meta verisiyle birlikte Markdown (`.md`) yazar.
- `timestamps` (zaman damgaları): transkript metninde normalleştirilmiş `[SS:DD:SS]` cue zamanlarını korur.
- `metadata-only` (yalnızca meta veri): alt yazı dosyalarını indirmeden `videos.json` ve `videos.csv` yazar.

**Kullanışlı sınırlar ve denetimler:**

- `max_videos`: bir oynatma listesi veya kanaldaki ilk N videoyu sınırlar.
- `start_index` ve `end_index`: belirli bir indeks aralığını işler.
- `manual-only` (yalnızca elle): otomatik (auto) alt yazıları kullanmaz.
- Dil önceliği: `tr,en,en-US` gibi virgülle ayrılmış kodları kabul eder.
- `dry-run` (deneme çalıştırması): transkript/rapor dosyası yazmadan bir işleme planı döndürür.

**Transkript çıktı klasörleri şunları içerebilir:**

- `txt/` ve `md/` transkript klasörleri.
- `report.json`, `last_run_report.json`, `cumulative_report.json`.
- Devam ettirilebilir ilerleme görünürlüğü için `progress.json`.
- Oluşturulan transkript dosyalarına bağlantılar içeren `index.md`.
- Yalnızca-meta veri işleri için `videos.json` ve `videos.csv`.

> ⚠️ **Önemli yasal/telif notu:** Transkriptler de platform içeriğinden türetilir. Bu özelliği yalnızca size ait içerikler, kullanımınız için lisanslanmış içerikler veya ilgili platform şartları ile yerel mevzuatın izin verdiği durumlar için kullanın. Yalnızca-meta veri modunu, toplamanıza ya da yeniden yayımlamanıza izin verilmeyen içerikler için bir kazıma (scraping) yöntemi olarak kullanmayın.

Elle transkript doğrulama senaryoları `TRANSCRIPT_MANUAL_VERIFICATION.md` dosyasında belgelenmiştir.

---

## 🙏 Teşekkürler ve Krediler

Bu proje aşağıdaki açık kaynak çalışmalardan yararlanır:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — video/ses indirme ve alt yazı çıkarma motoru.
- **[FFmpeg](https://ffmpeg.org/)** — medya birleştirme, dönüştürme, kırpma ve oynatma altyapısı.
- **[yt-dlp-video-transcripts](https://github.com/aliyasinozyuksel/yt-dlp-video-transcripts)** (Ali Yasin Özyüksel) — Uygulamadaki **Transkript Arşivleme** özelliği bu projenin mantığı temel alınarak entegre edilmiştir. Entegrasyonda "Option A" yaklaşımı izlenmiş; yani upstream CLI alt süreç (subprocess) olarak çağrılmak yerine, davranışı iptal edilebilir ve test edilebilir bir servis katmanına (`core/transcripts/`) taşınmıştır. Orijinal davranış korunmaya çalışılmış ve Windows uyumluluğu gözetilmiştir.

Transkript özelliğiyle ilgili emeği için **Ali Yasin Özyüksel**'e teşekkür ederiz.

---

## ⚖️ Yasal Uyarı

Bu araç yalnızca eğitim, kişisel kullanım ve açık kaynak geliştirme mantığıyla tasarlanmıştır. İçerik indirmeden önce ilgili platformların (YouTube vb.) hizmet şartlarını ve telif haklarını kontrol etmeniz önerilir. Telif hakkıyla korunan içeriklerin izinsiz veya ticari amaçlı kullanımı ve indirilmesi yasal sorumluluk doğurabilir. Tüm sorumluluk son kullanıcıya aittir.
