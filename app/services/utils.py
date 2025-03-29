import os
import time
import threading
import datetime
import logging
import random
import shutil
from functools import wraps
from flask import abort, jsonify, request, current_app, g

# Dictionary untuk menyimpan status lock per user
_user_locks = {}
_global_lock = threading.Lock()

# Setup logging
logger = logging.getLogger(__name__)

class UserLock:
    """
    Implementasi lock berbasis file untuk mencegah proses duplikasi
    """
    def __init__(self, user_id):
        self.user_id = user_id
        self.lock_time = datetime.datetime.now()
        self.lock_file = None
        
        # Buat direktori untuk lock file jika belum ada
        self.lock_dir = os.path.join(os.getcwd(), 'locks')
        os.makedirs(self.lock_dir, exist_ok=True)
        
        # Gunakan file sebagai indikator lock
        self.lock_file = os.path.join(self.lock_dir, f'user_{user_id}.lock')
    
    def acquire(self):
        """Mendapatkan lock"""
        try:
            # Cek apakah file lock sudah ada
            if os.path.exists(self.lock_file):
                # Cek apakah lock sudah kadaluarsa (lebih dari 5 menit)
                file_mtime = os.path.getmtime(self.lock_file)
                current_time = time.time()
                
                # Jika lock lebih dari 5 menit, anggap sudah kadaluarsa
                if current_time - file_mtime > 300:  # 5 menit
                    try:
                        os.remove(self.lock_file)
                        logger.info(f"Lock kadaluarsa untuk user {self.user_id} dihapus")
                    except Exception as e:
                        logger.error(f"Gagal menghapus lock kadaluarsa: {e}")
                        return False
                else:
                    logger.warning(f"User {self.user_id} memiliki lock aktif, tidak bisa mendapatkan lock baru")
                    return False
            
            # Buat file lock baru
            with open(self.lock_file, 'w') as f:
                f.write(f"Lock created at {self.lock_time}")
                
            logger.info(f"Lock berhasil dibuat untuk user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saat acquire lock: {e}")
            return False
    
    def release(self):
        """Melepaskan lock"""
        try:
            if self.lock_file and os.path.exists(self.lock_file):
                os.remove(self.lock_file)
                logger.info(f"Lock berhasil dilepaskan untuk user {self.user_id}")
                return True
            else:
                logger.warning(f"Tidak ada lock file untuk dilepaskan untuk user {self.user_id}")
                return False
        except Exception as e:
            logger.error(f"Error saat release lock: {e}")
            return False
    
    def force_cleanup(self):
        """Paksa membersihkan lock apapun yang mungkin tersisa"""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
                logger.info(f"Lock untuk user {self.user_id} dibersihkan secara paksa")
                return True
            return True  # Kembalikan true bahkan jika file tidak ada
        except Exception as e:
            logger.error(f"Gagal membersihkan lock secara paksa: {e}")
            return False

def cleanup_all_locks():
    """Fungsi untuk membersihkan semua lock yang ada"""
    try:
        lock_dir = os.path.join(os.getcwd(), 'locks')
        if os.path.exists(lock_dir):
            # Hapus folder locks dan buat ulang
            shutil.rmtree(lock_dir)
            os.makedirs(lock_dir, exist_ok=True)
            logger.info("Semua lock berhasil dibersihkan")
            
            # Reset user_locks dictionary
            with _global_lock:
                _user_locks.clear()
        return True
    except Exception as e:
        logger.error(f"Gagal membersihkan semua lock: {e}")
        return False

def acquire_user_lock(user_id, timeout=10):  # Kurangi timeout ke 10 detik
    """
    Mencoba mendapatkan lock untuk user tertentu dengan retry
    
    Args:
        user_id: ID user yang ingin mendapatkan lock
        timeout: Waktu maksimal tunggu dalam detik
    
    Returns:
        True jika berhasil mendapatkan lock, False jika gagal
    """
    with _global_lock:
        # Coba membersihkan lock terlebih dahulu jika ada
        # Ini membantu mengatasi skenario dimana lock sebelumnya tidak dilepaskan dengan benar
        lock_obj = UserLock(user_id)
        
        # PERBAIKAN: Jika parameter force_cleanup ada di URL, bersihkan lock
        if request and request.args.get('force_cleanup', 'false').lower() == 'true':
            lock_obj.force_cleanup()
            logger.info(f"Lock untuk user {user_id} dibersihkan dari parameter URL")
        
        lock_file = lock_obj.lock_file
        
        # Jika file lock ada, cek apakah sudah kadaluarsa
        if os.path.exists(lock_file):
            file_mtime = os.path.getmtime(lock_file)
            current_time = time.time()
            
            # Jika lock lebih dari 3 menit (lebih cepat dari sebelumnya), anggap kadaluarsa dan hapus
            if current_time - file_mtime > 180:  # 3 menit, lebih pendek dari sebelumnya (5 menit)
                try:
                    os.remove(lock_file)
                    logger.info(f"Lock kadaluarsa untuk user {user_id} dihapus otomatis (auto-expire)")
                except Exception as e:
                    logger.error(f"Gagal menghapus lock kadaluarsa: {e}")
                    # Return True karena kita menganggap lock sudah kadaluarsa
                    # meskipun gagal menghapus file
                    return True
            else:
                # PERBAIKAN: Jika lock belum terlalu lama (kurang dari 30 detik), coba paksa hapus
                if current_time - file_mtime < 30:
                    try:
                        os.remove(lock_file)
                        logger.info(f"Lock untuk user {user_id} dibersihkan (baru dibuat)")
                        # Jeda singkat untuk memastikan file benar-benar dihapus
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Gagal menghapus lock baru: {e}")
                else:
                    # Lock masih aktif, kemungkinan proses lain sedang berjalan
                    logger.warning(f"User {user_id} sudah memiliki lock aktif")
                    return False
        
        # Coba dapatkan lock dengan retry exponential backoff
        start_time = time.time()
        retry_count = 0
        max_retries = 3  # Kurangi retry dari 5 ke 3
        
        while time.time() - start_time < timeout and retry_count < max_retries:
            if lock_obj.acquire():
                _user_locks[user_id] = lock_obj
                return True
            
            # Exponential backoff dengan jitter lebih pendek
            retry_count += 1
            wait_time = min(1 + random.uniform(0, 0.5), timeout / 3)  # Jeda lebih pendek
            logger.info(f"Mencoba acquire lock lagi dalam {wait_time:.2f} detik (retry {retry_count}/{max_retries})")
            time.sleep(wait_time)
        
        logger.error(f"Gagal mendapatkan lock setelah {retry_count} percobaan")
        return False

def release_user_lock(user_id):
    """
    Melepaskan lock untuk user tertentu
    
    Args:
        user_id: ID user yang ingin melepaskan lock
    """
    with _global_lock:
        if user_id in _user_locks:
            success = _user_locks[user_id].release()
            del _user_locks[user_id]
            logger.info(f"Lock untuk user {user_id} berhasil dilepaskan: {success}")
            return success
        else:
            # Coba bersihkan file lock jika ada, meskipun tidak ada entry di dictionary
            lock_obj = UserLock(user_id)
            success = lock_obj.force_cleanup()
            logger.warning(f"Tidak ada lock di memory untuk user {user_id}, mencoba bersihkan file lock: {success}")
            return success

def check_force_cleanup_parameter(user_id):
    """Fungsi untuk mengecek parameter force_cleanup di URL"""
    try:
        # Jika ada parameter force_cleanup, bersihkan lock sebelum mencoba
        force_cleanup = request.args.get('force_cleanup', 'false').lower() == 'true'
        if force_cleanup:
            lock_obj = UserLock(user_id)
            success = lock_obj.force_cleanup()
            logger.info(f"Lock untuk user {user_id} dibersihkan secara paksa dari URL parameter: {success}")
            return success
        return False
    except:
        return False

# Decorator berbasis class untuk lebih banyak kontrol
class UserLockRequired:
    """Decorator berbasis class yang lebih kuat untuk mengontrol lock per user"""
    
    def __init__(self, f):
        self.f = f
        wraps(f)(self)
    
    def __call__(self, *args, **kwargs):
        from flask_login import current_user
        
        if not current_user.is_authenticated:
            abort(401, description="User tidak terautentikasi")
        
        user_id = current_user.id
        
        # Bersihkan lock jika diminta
        check_force_cleanup_parameter(user_id)
        
        # PERBAIKAN: Auto cleanup lock yang berusia lebih dari 3 menit
        lock_obj = UserLock(user_id)
        if os.path.exists(lock_obj.lock_file):
            file_mtime = os.path.getmtime(lock_obj.lock_file)
            if time.time() - file_mtime > 180:  # 3 menit
                lock_obj.force_cleanup()
                logger.info(f"Lock kadaluarsa untuk user {user_id} dibersihkan otomatis")
        
        # Coba dapatkan lock
        if not acquire_user_lock(user_id):
            # PERBAIKAN: Buat response dengan opsi clean lock lebih jelas
            g.lock_error = True
            g.lock_user_id = user_id
            
            # Gunakan Flask abort untuk benar-benar menghentikan eksekusi function
            response = jsonify({
                'error': 'Proses sebelumnya masih berjalan. Harap tunggu beberapa saat atau gunakan tombol "Bersihkan Lock".',
                'code': 'LOCK_EXISTS',
                'user_id': user_id
            })
            response.status_code = 429
            abort(response)
        
        try:
            # Jalankan fungsi yang dibungkus
            return self.f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Error saat menjalankan fungsi: {e}")
            # Pastikan lock dilepaskan sebelum meneruskan exception
            release_user_lock(user_id)
            raise
        finally:
            # Pastikan lock selalu dilepaskan setelah selesai
            release_user_lock(user_id)
            current_app.logger.info(f"Lock untuk user {user_id} dilepaskan setelah fungsi selesai")

# Backward compatibility dengan decorator style lama
def user_lock_required(f):
    return UserLockRequired(f)