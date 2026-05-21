import sys
import os
import itertools
from PyQt6.QtCore import QCoreApplication, QEventLoop
from downloader import Downloader, AUDIO_FORMATS, VIDEO_FORMATS, AUDIO_QUALITIES, VIDEO_QUALITIES

def run_test(name, url, **kwargs):
    print(f"\n[{name}] Testi baslatiliyor...")
    
    app = QCoreApplication.instance()
    if not app:
        app = QCoreApplication(sys.argv)
        
    dl = Downloader()
    loop = QEventLoop()
    result = {}
    
    def on_complete(info):
        result['status'] = 'OK'
        loop.quit()
        
    def on_error(err):
        result['status'] = 'ERROR'
        result['error'] = err
        loop.quit()
        
    dl.complete.connect(on_complete)
    dl.error.connect(on_error)
    
    output_dir = os.path.abspath("test_downloads")
    os.makedirs(output_dir, exist_ok=True)
    
    quality = kwargs.get('quality', 'Best Quality')
    fmt = kwargs.get('fmt', 'mp4')
    subtitles = kwargs.get('subtitles', False)
    audio_quality = kwargs.get('audio_quality', '192')
    playlist_items = kwargs.get('playlist_items', None)
    embed_thumbnail = kwargs.get('embed_thumbnail', False)
    write_description = kwargs.get('write_description', False)
    concurrent_fragments = kwargs.get('concurrent_fragments', 4)
    start_time = kwargs.get('start_time', '')
    end_time = kwargs.get('end_time', '')
    embed_metadata = kwargs.get('embed_metadata', False)
    
    dl.start(
        url, quality, fmt, output_dir, subtitles, audio_quality,
        playlist_items, embed_thumbnail, write_description, concurrent_fragments,
        start_time, end_time, embed_metadata
    )
    
    loop.exec()
    
    if result.get('status') == 'OK':
        print(f"  --> [OK] İndirme tamamlandı.")
    else:
        err = result.get('error', 'Bilinmeyen Hata')
        print(f"  --> [ERROR] Hata oluştu: {err}")

def run_search_test():
    print(f"\n[Arama (Search) Simülasyonu] Testi baslatiliyor...")
    app = QCoreApplication.instance()
    if not app:
        app = QCoreApplication(sys.argv)
        
    dl = Downloader()
    loop = QEventLoop()
    result = {}
    
    def on_complete(results):
        result['status'] = 'OK'
        result['count'] = len(results)
        loop.quit()
        
    def on_error(err):
        result['status'] = 'ERROR'
        result['error'] = err
        loop.quit()
        
    dl.search_complete.connect(on_complete)
    dl.search_error.connect(on_error)
    
    dl.search("test", limit=3)
    loop.exec()
    
    if result.get('status') == 'OK':
        print(f"  --> [OK] Arama tamamlandı. Sonuç sayısı: {result.get('count')}")
    else:
        err = result.get('error', 'Bilinmeyen Hata')
        print(f"  --> [ERROR] Hata oluştu: {err}")


if __name__ == "__main__":
    # Daha kısa bir test süresi için çok kısa ve varsayılan bir video
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" 
    
    print("YT-DLP Media Tool - Kapsamlı (Matris) Test Suite")
    print(f"Hedef URL: {url}")
    print("=" * 50)
    
    video_qualities = [q for q in VIDEO_QUALITIES if q != "Audio Only"]
    test_idx = 1
    
    print("\n--- VIDEO TESTLERİ ---")
    for vq in video_qualities:
        for fmt in VIDEO_FORMATS:
            name = f"Test {test_idx} - Video [{vq}] format [{fmt}]"
            run_test(name, url, quality=vq, fmt=fmt)
            test_idx += 1
            
    print("\n--- AUDIO TESTLERİ ---")
    for aq in AUDIO_QUALITIES:
        for fmt in AUDIO_FORMATS:
            name = f"Test {test_idx} - Ses [{aq} kbps] format [{fmt}]"
            run_test(name, url, quality="Audio Only", fmt=fmt, audio_quality=aq)
            test_idx += 1
            
    print("\n--- ÖZEL SENARYOLAR ---")
    
    # Zaman Aralığı (Trimming)
    run_test(f"Test {test_idx} - Zaman Aralığı (00:00-00:05)", url, start_time="00:00", end_time="00:05")
    test_idx += 1
    
    # Meta Verili İndirme
    run_test(f"Test {test_idx} - Meta Verili Ses (ID3 Tags)", url, quality="Audio Only", fmt="mp3", embed_metadata=True)
    test_idx += 1
    
    # Altyazılı İndirme
    run_test(f"Test {test_idx} - Altyazılı Video", url, subtitles=True)
    test_idx += 1
    
    # Arama Testi
    run_search_test()
    
    print("\nTüm matris testleri tamamlandı! Dosyalar 'test_downloads' klasöründe kontrol edilebilir.")
