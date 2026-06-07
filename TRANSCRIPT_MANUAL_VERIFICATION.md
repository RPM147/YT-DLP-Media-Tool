# Transkript Elle Doğrulama

Bu kontrolleri, masaüstü uygulamasını kaynaktan derledikten veya çalıştırdıktan
sonra kullanın. İşleme izniniz olmadığı sürece telif hakkıyla korunan veya özel
içerikleri kullanmayın. Kendi videolarınızı, herkese açık test videolarını veya
transkript kullanımına izin verilen kanalları tercih edin.

## Ön Koşullar

- `yt-dlp` kurulu olmalı ya da uygulama derlemesiyle birlikte paketlenmiş olmalı.
- `ffmpeg.exe`, `ffplay.exe` ve `ffprobe.exe`, `main.py` dosyasının yanında
  bulunmalı ya da mevcut medya özelliklerinin beklediği şekilde paketlenmiş
  uygulamanın içine gömülmüş olmalı.
- Uygulama, konsolda hata izi (traceback) olmadan başlamalı.
- Kenar çubuğunda **Transkriptler** sayfası görünür olmalı.
- Yazılabilir bir transkript çıktı klasörü seçilmiş olmalı.

## Senaryolar

1. Tek video, varsayılan çıktı
   - URL: İngilizce alt yazısı olan tek bir YouTube videosu.
   - Seçenekler: format `both`, varsayılan dil önceliği.
   - Beklenen: bir `.txt`, bir `.md`, `report.json`, `cumulative_report.json`,
     `progress.json` ve `index.md` dosyaları oluşturulur.

2. Oynatma listesi, en fazla 3
   - URL: en az üç video içeren bir oynatma listesi.
   - Seçenekler: `max_videos = 3`.
   - Beklenen: üçten fazla video işlenmez; rapor alanları `max_videos: 3`
     değerini içerir.

3. Kanal deneme çalıştırması (dry-run)
   - URL: bir kanal veya kullanıcı (handle) URL'si.
   - Seçenekler: `dry-run` etkinleştirilir.
   - Beklenen: Arayüz bir plan gösterir; transkript/rapor dosyaları yazılmaz.

4. Format `txt`
   - Seçenekler: çıktı formatı `txt`.
   - Beklenen: `txt/` klasörü transkript dosyalarını içerir; yeni çıktılar için
     `md/` boş kalır; `index.md` `.txt` dosyalarına bağlantı verir.

5. Format `md`
   - Seçenekler: çıktı formatı `md`.
   - Beklenen: `md/` klasörü transkript dosyalarını içerir; yeni çıktılar için
     `txt/` boş kalır; `index.md` `.md` dosyalarına bağlantı verir.

6. Zaman damgaları (timestamps)
   - Seçenekler: `timestamps` etkinleştirilir.
   - Beklenen: oluşturulan transkript metni `[SS:DD:SS]` önekleri içerir ve
     Markdown frontmatter'ı `timestamps: true` satırını içerir.

7. Yalnızca meta veri (metadata-only)
   - Seçenekler: `metadata-only` etkinleştirilir.
   - Beklenen: `videos.json` ve `videos.csv` yazılır; hiçbir alt yazı dosyası
     indirilmez; arayüzdeki sonuç eylemleri JSON ve CSV dosyalarını açar.

8. Yalnızca elle (manual-only)
   - URL: otomatik alt yazısı olan ama elle eklenmiş alt yazısı olmayan bir video.
   - Seçenekler: `manual-only` etkinleştirilir.
   - Beklenen: video, otomatik alt yazıları kullanmak yerine "elle alt yazı yok"
     gerekçesiyle atlanır.

9. Türkçe dil
   - URL: Türkçe alt yazısı veya altyazı (caption) olan bir video.
   - Seçenekler: dil önceliği `tr,en`.
   - Beklenen: İngilizce yedeğinden önce Türkçe alt yazı/altyazı seçilir.

10. Çerez gerektiren video
    - URL: tarayıcı çerezi gerektiren ve erişim izniniz olan bir video.
    - Seçenekler: ayarlarda tarayıcı çerezlerini veya bir çerez dosyasını
      yapılandırın.
    - Beklenen: transkript yt-dlp çağrıları yapılandırılan çerezleri kullanır.
      Tarayıcı çerez veritabanı kilitliyse, uygulama mevcut "tekrar dene/dosya
      seç" iletişim akışını gösterir.

11. Var olan transkriptlerde devam etme (resume)
    - Aynı başarılı işi iki kez çalıştırın.
    - Beklenen: ikinci çalıştırma, meta verinin mevcut olduğu yerlerde var olan
      dosyaları atlar ve transkript dosya adlarını çoğaltmaz.

12. İptal
    - Bir oynatma listesi veya kanal transkript işi başlatın ve **İptal**'e basın.
    - Beklenen: iş güvenli bir kontrol noktasında durur, arayüz boşta durumuna
      döner ve kısmi ilerleme/rapor durumu okunabilir kalır.

13. Eş zamanlı medya indirme
    - Önce bir medya indirmesi, ardından bir transkript işi başlatın.
    - Beklenen: uygulama, her iki işin de bağımsız çalıştığı konusunda uyarır;
      medya indirme kuyruğunun durumu transkript işi tarafından değiştirilmez.

14. Paketlenmiş derleme duman testi (smoke)
    - `YT-DLP Media Tool.spec` ile PyInstaller kullanarak derleyin.
    - Paketlenmiş çalıştırılabilir dosyayı başlatın.
    - Beklenen: uygulama açılır, **Transkriptler** sayfası açılır ve bir deneme
      (dry-run) transkript işi, `transcript_worker` veya `core.transcripts` için
      `ModuleNotFoundError` vermeden tamamlanır.
