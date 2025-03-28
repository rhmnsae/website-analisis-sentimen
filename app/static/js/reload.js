// Script untuk menangani reload halaman saat berpindah tab/halaman
document.addEventListener('DOMContentLoaded', function() {
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
                    
                // Tambahkan loading overlay sebelum reload
                addLoadingOverlay();
            }
        });
    });
    
    // Fungsi untuk menambahkan loading overlay
    function addLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="spinner-border text-light" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        `;
        document.body.appendChild(overlay);
        
        // Tambahkan style untuk overlay
        const style = document.createElement('style');
        style.textContent = `
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                animation: fadeIn 0.3s ease;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Hapus loading overlay saat halaman sudah dimuat sepenuhnya
    window.addEventListener('load', function() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.classList.add('fade-out');
            setTimeout(() => {
                overlay.remove();
            }, 300);
        }
    });
});