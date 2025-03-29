// Script untuk menangani reload halaman saat berpindah tab/halaman
document.addEventListener('DOMContentLoaded', function() {
    // Variabel global untuk melacak status API
    window.apiRequestsInProgress = 0;
    window.dataLoaded = false;
    
    // Intercept semua fetch requests untuk mendeteksi API calls
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        // Cek apakah ini request ke API
        if (url && typeof url === 'string' && url.includes('/api/')) {
            window.apiRequestsInProgress++;
            console.log(`API request dimulai: ${url} (total: ${window.apiRequestsInProgress})`);
            
            return originalFetch(url, options)
                .then(response => {
                    // Tunggu sebentar untuk memastikan data diproses
                    setTimeout(() => {
                        window.apiRequestsInProgress--;
                        console.log(`API request selesai: ${url} (tersisa: ${window.apiRequestsInProgress})`);
                        checkAndRemoveOverlay();
                    }, 500);
                    return response;
                })
                .catch(error => {
                    window.apiRequestsInProgress--;
                    console.log(`API request error: ${url} (tersisa: ${window.apiRequestsInProgress})`);
                    checkAndRemoveOverlay();
                    throw error;
                });
        }
        
        // Request bukan ke API, lanjutkan seperti biasa
        return originalFetch(url, options);
    };
    
    // Menangani reload saat berpindah tab dari navbar
    const navLinks = document.querySelectorAll('nav a');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Jika link adalah logout, biarkan berpindah halaman secara normal
            if (this.getAttribute('href') && this.getAttribute('href').includes('logout')) {
                return;
            }
            
            // Jika link bukan dropdown toggle dan memiliki href yang bukan #
            if (!this.classList.contains('dropdown-toggle') && 
                this.getAttribute('href') && 
                this.getAttribute('href') !== '#' && 
                !this.getAttribute('href').startsWith('#')) {
                    
                // Jika kita beralih ke tab seperti 'input-data', 'hasil-analisis', 'history', 'profile'
                if (!this.classList.contains('disabled')) {
                    // Reset status global
                    window.apiRequestsInProgress = 0;
                    window.dataLoaded = false;
                    
                    // Tambahkan loading overlay sebelum pindah halaman
                    addLoadingOverlay();
                }
            }
        });
    });
    
    // Menangani reload saat mengklik link riwayat analisis
    const analysisLinks = document.querySelectorAll('.list-group-item');
    
    analysisLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.getAttribute('href') && 
                this.getAttribute('href') !== '#' && 
                !this.getAttribute('href').startsWith('#')) {
                
                // Reset status global
                window.apiRequestsInProgress = 0;
                window.dataLoaded = false;
                
                // Tambahkan loading overlay sebelum reload
                addLoadingOverlay();
            }
        });
    });
    
    // Fungsi untuk menambahkan loading overlay
    function addLoadingOverlay() {
        // Hapus overlay yang mungkin sudah ada
        const existingOverlay = document.querySelector('.loading-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }
        
        const overlay = document.createElement('div');
        overlay.id = 'page-loading-overlay';
        overlay.className = 'loading-overlay';
        // Ubah menjadi loading bulat sederhana saja
        overlay.innerHTML = `
            <div class="loading-content simple-loader">
                <div class="spinner-border text-light" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        
        // Tambahkan style untuk overlay
        if (!document.getElementById('loading-overlay-style')) {
            const style = document.createElement('style');
            style.id = 'loading-overlay-style';
            style.textContent = `
                .loading-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.7);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 9999;
                    animation: fadeIn 0.3s ease;
                    transition: opacity 0.5s ease;
                }
                
                .loading-overlay .loading-content {
                    text-align: center;
                }
                
                .loading-overlay .spinner-border {
                    width: 3rem;
                    height: 3rem;
                }
                
                /* Style untuk simple loader (hanya spinner) */
                .simple-loader {
                    background-color: transparent;
                    box-shadow: none;
                }
                
                .fade-out {
                    opacity: 0;
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    // Fungsi untuk memeriksa apakah data sudah dimuat
    function checkDataLoaded() {
        // Untuk halaman hasil analisis, periksa elemen-elemen kunci
        if (window.location.pathname.includes('hasil-analisis') || 
            window.location.pathname.includes('history/')) {
            
            const totalTweets = document.getElementById('total-tweets');
            const positiveCount = document.getElementById('positive-count');
            const topHashtags = document.getElementById('top-hashtags');
            
            // Pastikan elemen-elemen tersebut sudah terisi dengan data
            if (totalTweets && positiveCount && topHashtags) {
                // Periksa nilai
                const totalValue = parseInt(totalTweets.textContent) || 0;
                const positiveValue = parseInt(positiveCount.textContent) || 0;
                const hashtagsLoaded = topHashtags.children.length > 0;
                
                console.log("Pengecekan data:", {
                    total: totalValue,
                    positive: positiveValue,
                    hashtagsLoaded: hashtagsLoaded
                });
                
                return totalValue > 0 && (positiveValue > 0 || hashtagsLoaded);
            }
        }
        
        // Untuk halaman lain, cukup periksa jika konten utama sudah dimuat
        return document.getElementById('main-content') !== null;
    }
    
    // Fungsi untuk memeriksa dan menghapus overlay jika semua kondisi terpenuhi
    function checkAndRemoveOverlay() {
        const overlay = document.getElementById('page-loading-overlay');
        if (!overlay) return;
        
        // Jika tidak ada request API yang sedang berjalan,
        // atau data sudah dimuat, hilangkan overlay
        if (window.apiRequestsInProgress <= 0 || checkDataLoaded()) {
            console.log("Menghapus overlay karena:", {
                apiRequestsInProgress: window.apiRequestsInProgress,
                dataLoaded: checkDataLoaded()
            });
            
            // Tunggu sedikit lebih lama untuk memastikan UI diperbarui
            setTimeout(() => {
                overlay.classList.add('fade-out');
                setTimeout(() => {
                    overlay.remove();
                }, 500);
            }, 1000); // Tunggu 1 detik lagi setelah data dimuat
        } else {
            // Jika request API masih berjalan atau data belum dimuat,
            // periksa lagi setelah beberapa saat
            console.log("Menunggu data dimuat atau API selesai...");
            setTimeout(checkAndRemoveOverlay, 500);
        }
    }
    
    // Mendeteksi saat resource selesai dimuat
    window.addEventListener('load', function() {
        console.log("Window load event triggered");
        
        // Periksa apakah perlu menunggu request API
        if (window.location.pathname.includes('hasil-analisis') || 
            window.location.pathname.includes('history/')) {
            
            // Beri waktu yang lebih lama untuk halaman yang memerlukan loading data
            setTimeout(() => {
                // Periksa apakah ada request API yang sedang berjalan
                if (window.apiRequestsInProgress > 0) {
                    console.log(`Masih ada ${window.apiRequestsInProgress} API request berjalan, menunggu...`);
                    // Jangan hapus overlay, biarkan checkAndRemoveOverlay yang menanganinya
                } else {
                    // Periksa data sebelum menghapus overlay
                    checkAndRemoveOverlay();
                }
            }, 1500); // Tingkatkan delay untuk halaman hasil analisis
        } else {
            // Untuk halaman lain, cukup tunggu sebentar lalu hapus overlay
            setTimeout(() => {
                const overlay = document.querySelector('.loading-overlay');
                if (overlay) {
                    overlay.classList.add('fade-out');
                    setTimeout(() => {
                        overlay.remove();
                    }, 500);
                }
            }, 300);
        }
    });
    
    // Tambahkan listener untuk menangkap event selesai memuat dari script.js
    window.addEventListener('analysisDataLoaded', function(e) {
        console.log("Event analysisDataLoaded diterima");
        window.dataLoaded = true;
        checkAndRemoveOverlay();
    });
    
    // Tambahkan fungsi global untuk diakses dari script lain
    window.notifyDataLoaded = function() {
        window.dataLoaded = true;
        // Buat dan trigger event kustom
        const event = new CustomEvent('analysisDataLoaded');
        window.dispatchEvent(event);
    };
});