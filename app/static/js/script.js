document.addEventListener('DOMContentLoaded', function() {
    // Form submission handling
    const analysisForm = document.getElementById('analysis-form');
    const submitBtn = document.getElementById('submit-btn');
    const loadingIndicator = document.getElementById('loading');
    
    // Main tab navigation
    const navLinks = document.querySelectorAll('.nav-tabs-link');

    const GLOBAL_TIMEOUT = 25000;

    const forceHideLoadingTimer = setTimeout(() => {
        console.log("TIMEOUT GLOBAL: Menghapus loading overlay secara paksa");
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay && loadingOverlay.style.display !== 'none') {
            loadingOverlay.style.opacity = '0';
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 500);
        }
    }, GLOBAL_TIMEOUT)

    // Chatbot elements
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotSend = document.getElementById('chatbot-send');
    const chatbotMessages = document.getElementById('chatbot-messages');
    const chatbotTopicButtons = document.getElementById('chatbot-topic-buttons');
    
    // Sentiment filter, search and pagination
    const sentimentFilter = document.getElementById('sentiment-filter');
    const tweetSearch = document.getElementById('tweet-search');
    const itemsPerPage = document.getElementById('items-per-page');
    const paginationContainer = document.getElementById('pagination-container');

    const downloadReportBtn = document.getElementById('download-report-btn');
    if (downloadReportBtn) {
        downloadReportBtn.addEventListener('click', function(e) {
            // Cek apakah sudah ada analisis yang dilakukan
            if (!analysisResults) {
                // e.preventDefault();
                // showAlert('Silakan upload dan analisis data terlebih dahulu sebelum mengunduh laporan.', 'warning');
            } else {
                // Tambahkan loading state selama proses download
                this.innerHTML = `
                    <div class="spinner-border spinner-border-sm me-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    Menyiapkan Laporan...
                `;
                
                // Kembalikan tampilan semula setelah beberapa saat
                setTimeout(() => {
                    this.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        Unduh Report
                    `;
                }, 3000);
            }
        });
    }
    
    // Global variables
    let allTweets = [];
    let currentPage = 1;
    let tweetsPerPage = 10;
    let filteredTweets = [];
    let searchQuery = '';
    let analysisResults = null;
    
    // Chart instances to allow for updates
    let sentimentByHashtagChart = null;
    let sentimentByLocationChart = null;
    let sentimentByLanguageChart = null;
    let sentimentTrendChart = null;
    let positiveWordsChart = null;
    let neutralWordsChart = null;
    let negativeWordsChart = null;


    // Variabel flag untuk mencegah multiple submission
    let isSubmitting = false;
    
    // Variabel untuk retry dan backoff
    const maxRetries = 3;
    let retryCount = 0;
    let retryTimeout = 2000; // ms

    if (window.location.pathname === '/hasil-analisis') {
        console.log("Memulai proses pengambilan data analisis...");
        fetchAnalysisDataWithRetry();
    }
    
    // Tangkap event saat halaman sudah dimuat sepenuhnya
    window.addEventListener('load', function() {
        console.log("Window.load event terpicu, memeriksa status loading...");
        
        // Periksa status loading overlay setelah 3 detik
        setTimeout(() => {
            const loadingOverlay = document.getElementById('loading-overlay');
            if (loadingOverlay && loadingOverlay.style.display !== 'none') {
                console.log("Loading masih aktif setelah window.load, memeriksa data...");
                if (isDataLoaded()) {
                    console.log("Data terdeteksi sudah dimuat, menghapus loading overlay...");
                    hideLoadingOverlay();
                } else {
                    console.log("Data belum dimuat, menunggu proses fetch selesai...");
                }
            }
        }, 3000);
    });
    
    if (analysisForm) {
        analysisForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Cek apakah sedang dalam proses submit
            if (isSubmitting) {
                console.log('Form sedang diproses, mencegah submit ganda');
                return false;
            }
            
            // Reset retry count pada submit baru
            retryCount = 0;
            
            // Mulai proses submit
            submitFormWithRetry();
        });
    }
    
    // Initialize Charts.js with global defaults
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.color = '#333333';
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 6;
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        Chart.defaults.animation.duration = 1000;
        Chart.defaults.animation.easing = 'easeOutQuart';
    }
    
    // Cek pada halaman hasil-analisis, ambil data analisis dari API
    if (window.location.pathname === '/hasil-analisis') {
        // Fetch analysis data
        fetch('/api/analysis-data')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Gagal mengambil data analisis');
                }
                return response.json();
            })
            .then(data => {
                // Store global analysis results
                analysisResults = data;
                allTweets = data.tweets || [];
                
                // Update UI with analysis results
                updateAnalysisResults(data);
                
                // Initialize pagination
                initializePagination();
                
                // Generate topics automatically
                generateTopics(data);
                
                // Create word cloud
                createImprovedWordCloud(data);
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('Gagal memuat data analisis: ' + error.message, 'danger');
            });
    }
    
    // Analysis form submission
    if (analysisForm) {
        analysisForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Tambahkan flag untuk mencegah submit berulang
            if (submitBtn.disabled) return;
            
            // Show loading indicator and disable submit button
            loadingIndicator.classList.remove('d-none');
            submitBtn.disabled = true;
            
            // Get form data
            const formData = new FormData();
            formData.append('title', document.getElementById('title').value);
            formData.append('description', document.getElementById('description')?.value || '');
            
            const csvFile = document.getElementById('csv-file').files[0];
            if (!csvFile) {
                showAlert('Silakan unggah file CSV terlebih dahulu.', 'warning');
                loadingIndicator.classList.add('d-none');
                submitBtn.disabled = false;
                return;
            }
            
            formData.append('csv-file', csvFile);
            
            // Send to server
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading indicator and enable submit button
                loadingIndicator.classList.add('d-none');
                submitBtn.disabled = false;
                
                if (data.error) {
                    showAlert('Error: ' + data.error, 'danger');
                    return;
                }
                
                // Store global analysis results
                analysisResults = data;
                allTweets = data.tweets || [];
                
                // Arahkan ke halaman hasil analisis
                window.location.href = '/hasil-analisis';
            })
            .catch(error => {
                loadingIndicator.classList.add('d-none');
                submitBtn.disabled = false;
                showAlert('Error: ' + error.message, 'danger');
            });
        });
    }
    
    // Topic button click
    if (chatbotTopicButtons) {
        chatbotTopicButtons.addEventListener('click', function(e) {
            if (e.target.classList.contains('topic-button') || e.target.closest('.topic-button')) {
                const topicButton = e.target.classList.contains('topic-button') ? e.target : e.target.closest('.topic-button');
                const topic = topicButton.getAttribute('data-topic') || topicButton.textContent.trim();
                chatbotInput.value = `Berikan evaluasi kebijakan terkait ${topic}`;
                sendChatbotMessage();
            }
        });
    }
    
    // Sentiment filter change
    if (sentimentFilter) {
        sentimentFilter.addEventListener('change', function() {
            currentPage = 1;
            filterAndDisplayTweets();
        });
    }
    
    // Tweet search functionality
    if (tweetSearch) {
        tweetSearch.addEventListener('input', function() {
            searchQuery = this.value.trim().toLowerCase();
            currentPage = 1;
            filterAndDisplayTweets();
        });
    }
    
    // Items per page change
    if (itemsPerPage) {
        itemsPerPage.addEventListener('change', function() {
            tweetsPerPage = parseInt(this.value);
            currentPage = 1;
            filterAndDisplayTweets();
        });
    }
    
    // Initialize pagination
    function initializePagination() {
        filteredTweets = [...allTweets];
        filterAndDisplayTweets();
    }
    
    // Filter tweets and update display
    function filterAndDisplayTweets() {
        if (!sentimentFilter) return;
        
        const selectedSentiment = sentimentFilter.value;
        
        // First filter by sentiment
        let tempFilteredTweets = [...allTweets];
        
        if (selectedSentiment !== 'all') {
            tempFilteredTweets = tempFilteredTweets.filter(tweet => tweet.predicted_sentiment === selectedSentiment);
        }
        
        // Then filter by search query if present
        if (searchQuery) {
            tempFilteredTweets = tempFilteredTweets.filter(tweet => {
                // Search in content, username or hashtags
                return (
                    tweet.content?.toLowerCase().includes(searchQuery) || 
                    tweet.username?.toLowerCase().includes(searchQuery)
                );
            });
        }
        
        filteredTweets = tempFilteredTweets;
        
        // Update pagination
        updatePagination();
        
        // Display current page
        displayTweets();
    }
    
    // Update pagination controls
    function updatePagination() {
        if (!paginationContainer) return;
        
        const totalPages = Math.ceil(filteredTweets.length / tweetsPerPage);
        
        // Adjust current page if needed
        if (currentPage > totalPages) {
            currentPage = totalPages > 0 ? totalPages : 1;
        }
        
        // Clear pagination container
        paginationContainer.innerHTML = '';
        
        // Create pagination element
        const pagination = document.createElement('ul');
        pagination.className = 'pagination';
        
        // Previous button
        const prevLi = document.createElement('li');
        prevLi.className = 'page-item' + (currentPage === 1 ? ' disabled' : '');
        const prevLink = document.createElement('a');
        prevLink.className = 'page-link';
        prevLink.href = '#';
        prevLink.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>';
        prevLink.setAttribute('aria-label', 'Previous');
        prevLink.addEventListener('click', function(e) {
            e.preventDefault();
            if (currentPage > 1) {
                currentPage--;
                displayTweets();
                updatePagination();
            }
        });
        prevLi.appendChild(prevLink);
        pagination.appendChild(prevLi);
        
        // Page numbers
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        
        if (endPage - startPage < 4 && startPage > 1) {
            startPage = Math.max(1, endPage - 4);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = 'page-item' + (i === currentPage ? ' active' : '');
            const pageLink = document.createElement('a');
            pageLink.className = 'page-link';
            pageLink.href = '#';
            pageLink.textContent = i;
            pageLink.addEventListener('click', function(e) {
                e.preventDefault();
                currentPage = i;
                displayTweets();
                updatePagination();
            });
            pageLi.appendChild(pageLink);
            pagination.appendChild(pageLi);
        }
        
        // Next button
        const nextLi = document.createElement('li');
        nextLi.className = 'page-item' + (currentPage === totalPages || totalPages === 0 ? ' disabled' : '');
        const nextLink = document.createElement('a');
        nextLink.className = 'page-link';
        nextLink.href = '#';
        nextLink.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>';
        nextLink.setAttribute('aria-label', 'Next');
        nextLink.addEventListener('click', function(e) {
            e.preventDefault();
            if (currentPage < totalPages) {
                currentPage++;
                displayTweets();
                updatePagination();
            }
        });
        nextLi.appendChild(nextLink);
        pagination.appendChild(nextLi);
        
        // Append pagination to container
        paginationContainer.appendChild(pagination);
        
        // Show pagination info
        const paginationInfo = document.createElement('div');
        paginationInfo.className = 'text-muted mt-2 text-center';
        
        if (filteredTweets.length === 0) {
            paginationInfo.textContent = "Tidak ada tweet yang ditemukan";
        } else {
            const start = (currentPage - 1) * tweetsPerPage + 1;
            const end = Math.min(currentPage * tweetsPerPage, filteredTweets.length);
            paginationInfo.textContent = `Menampilkan ${start} sampai ${end} dari ${filteredTweets.length} tweets`;
        }
        
        paginationContainer.appendChild(paginationInfo);
    }

    function isDataLoaded() {
        // Periksa elemen-elemen kunci untuk memastikan data sudah dimuat
        const totalTweets = document.getElementById('total-tweets');
        const positiveCount = document.getElementById('positive-count');
        const neutralCount = document.getElementById('neutral-count');
        const negativeCount = document.getElementById('negative-count');
        const topHashtags = document.getElementById('top-hashtags');
        const mainTopics = document.getElementById('main-topics');
        
        if (!totalTweets || !positiveCount || !neutralCount || !negativeCount) {
            console.log("Elemen data belum ditemukan di DOM");
            return false;
        }
        
        // Periksa apakah nilai sudah diisi (bukan 0 atau string kosong)
        const totalValue = parseInt(totalTweets.textContent) || 0;
        const positiveValue = parseInt(positiveCount.textContent) || 0;
        const neutralValue = parseInt(neutralCount.textContent) || 0;
        const negativeValue = parseInt(negativeCount.textContent) || 0;
        
        // Periksa status visualisasi
        const wordCloudLoaded = checkWordCloudLoaded();
        const chartsLoaded = checkChartsLoaded();
        
        console.log("Memeriksa data: ", {
            total: totalValue,
            positive: positiveValue,
            neutral: neutralValue,
            negative: negativeValue,
            hashtagsLoaded: topHashtags && topHashtags.children.length > 0,
            mainTopicsLoaded: mainTopics && mainTopics.children.length > 0,
            wordCloudLoaded: wordCloudLoaded,
            chartsLoaded: chartsLoaded
        });
        
        // Data dianggap sudah dimuat jika:
        // 1. Total tweets lebih dari 0, DAN
        // 2. Setidaknya salah satu dari sentimen sudah diisi dengan nilai valid, DAN
        // 3. Hashtags atau topik sudah dimuat
        const basicDataLoaded = totalValue > 0 && 
                               (positiveValue > 0 || neutralValue > 0 || negativeValue > 0) &&
                               ((topHashtags && topHashtags.children.length > 0) || 
                                (mainTopics && mainTopics.children.length > 0));
        
        // Beritahu reload.js bahwa data sudah dimuat jika sebelumnya belum terinformasi
        if (basicDataLoaded && window.notifyDataLoaded && !window.dataLoaded) {
            console.log("Memberitahu reload.js bahwa data sudah dimuat");
            window.notifyDataLoaded();
        }
        
        // Untuk pengecekan yang lebih lengkap, kita perlu semua data dasar dimuat
        return basicDataLoaded;
    }
    

    function checkWordCloudLoaded() {
        const wordCloudContainer = document.getElementById('word-cloud-container');
        if (!wordCloudContainer) return false;
        
        // Jika masih ada loading spinner, word cloud belum selesai
        if (wordCloudContainer.querySelector('.spinner-border')) {
            return false;
        }
        
        // Jika ada konten SVG atau elemen kata, word cloud sudah dimuat
        return !!wordCloudContainer.querySelector('svg') || 
               wordCloudContainer.querySelector('.word') ||
               !wordCloudContainer.querySelector('.text-muted');
    }


    // Fungsi untuk memeriksa apakah grafik sudah dimuat
    function checkChartsLoaded() {
        // Periksa beberapa container grafik
        const containers = [
            'sentiment-by-hashtag-chart',
            'sentiment-by-location-chart',
            'sentiment-by-language-chart'
        ];
        
        // Minimal satu grafik harus dimuat
        for (const id of containers) {
            const container = document.getElementById(id);
            if (container && container.querySelector('canvas') && !container.querySelector('.spinner-border')) {
                return true;
            }
        }
        
        return false;
    }
    
    
    // Fungsi untuk menyembunyikan overlay loading
    function hideLoadingOverlay() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (!loadingOverlay) return;
        
        // Variabel untuk melacak status pemeriksaan
        let checkCount = 0;
        const maxChecks = 30; // Tingkatkan maksimal pemeriksaan menjadi 30 kali (15 detik total)
        
        // Cek rekursif dengan batas waktu yang ditingkatkan
        function checkDataAndHideOverlay() {
            checkCount++;
            
            // Periksa apakah data sudah dimuat, atau batas maksimum pemeriksaan tercapai
            if (isDataLoaded() || checkCount >= maxChecks) {
                // Jika data berhasil dimuat atau batas pemeriksaan tercapai, sembunyikan overlay
                console.log(`Loading overlay dihapus: ${isDataLoaded() ? 'Data terdeteksi' : 'Batas waktu tercapai'} (Percobaan ke-${checkCount})`);
                
                // Jika data belum dimuat tapi batas waktu tercapai, tampilkan pesan berbeda
                const message = isDataLoaded() ? 
                    "Analisis berhasil dimuat!" : 
                    "Beberapa data mungkin belum selesai dimuat, silakan tunggu...";
                
                // Tampilkan step terakhir
                updateLoadingStatus(4, message);
                
                // Tunggu lebih lama jika data berhasil dimuat, untuk memastikan visualisasi muncul
                const delayTime = isDataLoaded() ? 2000 : 500;
                
                // Tunggu sebentar lalu fade out
                setTimeout(() => {
                    loadingOverlay.classList.add('fade-out');
                    setTimeout(() => {
                        loadingOverlay.style.display = 'none';
                        
                        // Jika data belum dimuat sepenuhnya, tampilkan pesan peringatan
                        if (!isDataLoaded() && checkCount >= maxChecks) {
                            showAlert('Beberapa data mungkin belum selesai dimuat. Jika visualisasi tidak muncul, silakan refresh halaman.', 'warning');
                        }
                    }, 500);
                }, delayTime);
                
                // Beritahu reload.js bahwa data sudah dimuat
                if (window.notifyDataLoaded && !window.dataLoaded) {
                    window.notifyDataLoaded();
                }
            } else {
                // Jika data belum dimuat dan belum mencapai batas pemeriksaan, periksa lagi
                console.log(`Data belum terdeteksi, menunggu... (Percobaan ke-${checkCount})`);
                
                // Update status loading berdasarkan jumlah percobaan
                if (checkCount <= 5) {
                    updateLoadingStatus(1, "Mengunduh dan menyiapkan data...");
                } else if (checkCount <= 15) {
                    updateLoadingStatus(2, "Memproses data analisis sentimen...");
                } else {
                    updateLoadingStatus(3, "Menyiapkan visualisasi dan grafik...");
                }
                
                setTimeout(checkDataAndHideOverlay, 500); // Cek setiap 500ms
            }
        }
        
        // Mulai pemeriksaan setelah jeda untuk memberi waktu DOM diperbarui
        setTimeout(() => {
            checkDataAndHideOverlay();
        }, 1500); // Tunggu 1.5 detik sebelum mulai pemeriksaan
    }
    
    // Display tweets for current page
    function displayTweets() {
        const tweetContainer = document.getElementById('tweet-container');
        if (!tweetContainer) return;
        
        tweetContainer.innerHTML = '';
        
        if (!filteredTweets || filteredTweets.length === 0) {
            if (searchQuery) {
                tweetContainer.innerHTML = '<p class="text-center text-muted my-5">Tidak ada tweet yang sesuai dengan pencarian.</p>';
            } else {
                tweetContainer.innerHTML = '<p class="text-center text-muted my-5">Tidak ada tweet yang ditemukan.</p>';
            }
            return;
        }
        
        // Calculate start and end index
        const startIndex = (currentPage - 1) * tweetsPerPage;
        const endIndex = Math.min(startIndex + tweetsPerPage, filteredTweets.length);
        
        // Display tweets for current page with animation
        for (let i = startIndex; i < endIndex; i++) {
            const tweet = filteredTweets[i];
            const tweetCard = document.createElement('div');
            tweetCard.className = 'tweet-card animate-fade-in';
            tweetCard.style.animationDelay = `${(i - startIndex) * 0.05}s`;
            
            const sentimentClass = tweet.predicted_sentiment === 'Positif' ? 'badge-positive' : 
                                  tweet.predicted_sentiment === 'Netral' ? 'badge-neutral' : 'badge-negative';
            
            // Process tweet content to make links clickable
            const linkifiedContent = linkifyText(tweet.content);
            
            // Format date to be more readable
            const formattedDate = formatDate(tweet.date);
            
            tweetCard.innerHTML = `
                <div class="tweet-header">
                    <span class="tweet-username">
                        <a href="https://twitter.com/${tweet.username}" target="_blank">@${tweet.username}</a>
                    </span>
                    <span class="tweet-date">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                        ${formattedDate}
                    </span>
                </div>
                <div class="tweet-content">
                    ${linkifiedContent}
                </div>
                ${tweet.image_url ? `<div class="tweet-image mt-2 mb-2">
                    <a href="${tweet.image_url}" target="_blank">
                        <img src="${tweet.image_url}" alt="Tweet image" class="img-fluid rounded" style="max-height: 200px;">
                    </a>
                </div>` : ''}
                <div class="tweet-stats">
                    <span title="Likes"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg> ${formatNumber(tweet.likes)}</span>
                    <span title="Retweets"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg> ${formatNumber(tweet.retweets)}</span>
                    <span title="Replies"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg> ${formatNumber(tweet.replies)}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <div>
                        <span class="tweet-badge ${sentimentClass}">${tweet.predicted_sentiment}</span>
                    </div>
                    ${tweet.tweet_url ? `
                        <a href="${tweet.tweet_url}" class="btn btn-sm btn-outline-dark" target="_blank">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z"></path></svg>
                            View on X
                        </a>` : ''}
                </div>
            `;
            
            tweetContainer.appendChild(tweetCard);
        }
    }
    
    // Helper function to format numbers (e.g., 1000 -> 1K)
    function formatNumber(num) {
        if (!num) return 0;
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num;
    }
    
    // Helper function to format date
    function formatDate(dateStr) {
        if (!dateStr) return '';
        
        const months = {
            'Jan': 'Januari',
            'Feb': 'Februari',
            'Mar': 'Maret',
            'Apr': 'April',
            'May': 'Mei',
            'Jun': 'Juni',
            'Jul': 'Juli',
            'Aug': 'Agustus',
            'Sep': 'September',
            'Oct': 'Oktober',
            'Nov': 'November',
            'Dec': 'Desember'
        };
        
        // Check if date is in format "DD MMM YYYY"
        const dateParts = dateStr.split(' ');
        if (dateParts.length === 3) {
            const day = dateParts[0];
            const month = months[dateParts[1]] || dateParts[1];
            const year = dateParts[2];
            return `${day} ${month} ${year}`;
        }
        
        return dateStr;
    }
    
    // Make links, hashtags and mentions clickable
    function linkifyText(text) {
        if (!text) return '';
        
        // URL pattern
        const urlPattern = /https?:\/\/[^\s]+/g;
        // Hashtag pattern
        const hashtagPattern = /#(\w+)/g;
        // Mention pattern
        const mentionPattern = /@(\w+)/g;
        
        // Replace URLs with clickable links
        let processedText = text.replace(urlPattern, url => 
            `<a href="${url}" target="_blank">${url.length > 30 ? url.substring(0, 27) + '...' : url}</a>`
        );
        
        // Replace hashtags with clickable links
        processedText = processedText.replace(hashtagPattern, (match, hashtag) => 
            `<a href="https://twitter.com/hashtag/${hashtag}" target="_blank" class="hashtag-link">${match}</a>`
        );
        
        // Replace mentions with clickable links
        processedText = processedText.replace(mentionPattern, (match, username) => 
            `<a href="https://twitter.com/${username}" target="_blank" class="mention-link">${match}</a>`
        );
        
        return processedText;
    }
    
    // Generate topics automatically based on analysis results
    function generateTopics(data) {
        if (!chatbotTopicButtons) return;
        
        chatbotTopicButtons.innerHTML = '';
        
        // Base topics on hashtags, top words, and key program areas
        const topics = new Set();
        
        // Add from hashtags
        if (data.top_hashtags && data.top_hashtags.length > 0) {
            data.top_hashtags.slice(0, 7).forEach(hashtag => {
                const topic = hashtag.tag ? hashtag.tag.replace('#', '') : (typeof hashtag === 'string' ? hashtag.replace('#', '') : '');
                if (topic) topics.add(topic);
            });
        }
        
        // Add from topics
        if (data.topics && data.topics.length > 0) {
            data.topics.slice(0, 7).forEach(topic => {
                const topicText = typeof topic === 'object' ? topic.topic : topic;
                if (topicText) topics.add(topicText);
            });
        }
        
        // Get words from each sentiment category
        if (data.sentiment_words) {
            // Add top positive words
            if (data.sentiment_words.positive && data.sentiment_words.positive.length > 0) {
                data.sentiment_words.positive.slice(0, 3).forEach(item => {
                    const word = typeof item === 'object' ? item.word : item;
                    if (word && word.length > 3) {
                        topics.add(word);
                    }
                });
            }
            
            // Add top negative words
            if (data.sentiment_words.negative && data.sentiment_words.negative.length > 0) {
                data.sentiment_words.negative.slice(0, 3).forEach(item => {
                    const word = typeof item === 'object' ? item.word : item;
                    if (word && word.length > 3) {
                        topics.add(word);
                    }
                });
            }
        }
        
        const keyPolicyAreas = [
        ];
        
        keyPolicyAreas.forEach(topic => {
            topics.add(topic);
        });
        
        const topicIcons = {
            'default': ''
        };
        
        Array.from(topics).forEach(topic => {
            const button = document.createElement('button');
            button.className = 'topic-button animate-fade-in';
            button.setAttribute('data-topic', topic);
            
            // Select icon based on topic or use default
            const iconHtml = topicIcons[topic] || topicIcons['default'];
            
            button.innerHTML = `${iconHtml} ${topic}`;
            chatbotTopicButtons.appendChild(button);
        });
        
        // Add a message to indicate these are suggested topics
        const messageDiv = document.createElement('div');
        messageDiv.className = 'text-center w-100 mt-2 mb-2 animate-fade-in';
        messageDiv.innerHTML = '<small class="text-muted">Topik diatas dibuat otomatis dari data yang dianalisa</small>';
        chatbotTopicButtons.appendChild(messageDiv);
    }

    function createSentimentByHashtagChart(hashtagSentimentData) {
        const chartContainer = document.getElementById('sentiment-by-hashtag-chart');
        if (!chartContainer || !hashtagSentimentData || hashtagSentimentData.length === 0) return;
        
        // Tambahkan loading indicator
        chartContainer.innerHTML = '<div class="chart-loader"><div class="spinner"></div></div>';
        
        // Ambil top 5 hashtag berdasarkan total count
        const top5Hashtags = hashtagSentimentData
            .sort((a, b) => b.total - a.total)
            .slice(0, 5);
        
        const labels = top5Hashtags.map(item => item.tag);
        const positiveData = top5Hashtags.map(item => item.positive);
        const neutralData = top5Hashtags.map(item => item.neutral);
        const negativeData = top5Hashtags.map(item => item.negative);
        
        // Buat chart
        const ctx = document.createElement('canvas');
        chartContainer.innerHTML = '';
        chartContainer.appendChild(ctx);
        
        // Destroy previous chart instance if exists
        if (sentimentByHashtagChart) {
            sentimentByHashtagChart.destroy();
        }
        
        // Buat chart baru
        sentimentByHashtagChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Positif',
                        data: positiveData,
                        backgroundColor: '#ffffff',
                        borderColor: '#dddddd',
                        borderWidth: 1
                    },
                    {
                        label: 'Netral',
                        data: neutralData,
                        backgroundColor: '#9e9e9e',
                        borderColor: '#757575',
                        borderWidth: 1
                    },
                    {
                        label: 'Negatif',
                        data: negativeData,
                        backgroundColor: '#000000',
                        borderColor: '#000000',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Hashtag',
                            font: {
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Persentase (%)',
                            font: {
                                weight: 'bold'
                            }
                        },
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Sentimen Berdasarkan Hashtag (Top 5)',
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        padding: {
                            bottom: 15
                        }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.raw + '%';
                            }
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }
    
    // Fungsi untuk membuat chart sentimen berdasarkan lokasi
    function createSentimentByLocationChart(tweetsData) {
        const chartContainer = document.getElementById('sentiment-by-location-chart');
        if (!chartContainer || !tweetsData || tweetsData.length === 0) return;
        
        // Tambahkan loading indicator
        chartContainer.innerHTML = '<div class="chart-loader"><div class="spinner"></div></div>';
        
        // Group tweets berdasarkan lokasi dan sentimen
        const locationData = {};
        
        tweetsData.forEach(tweet => {
            if (tweet.location) {
                if (!locationData[tweet.location]) {
                    locationData[tweet.location] = {
                        Positif: 0,
                        Netral: 0,
                        Negatif: 0,
                        total: 0
                    };
                }
                
                locationData[tweet.location][tweet.predicted_sentiment]++;
                locationData[tweet.location].total++;
            }
        });
        
        // Convert to array dan sort berdasarkan total
        const locationArray = Object.entries(locationData)
            .map(([location, data]) => ({
                location,
                ...data,
                positivePercent: (data.Positif / data.total * 100).toFixed(1),
                neutralPercent: (data.Netral / data.total * 100).toFixed(1),
                negativePercent: (data.Negatif / data.total * 100).toFixed(1)
            }))
            .filter(item => item.total >= 2) // Filter lokasi dengan minimal 2 tweets
            .sort((a, b) => b.total - a.total)
            .slice(0, 5); // Ambil top 5
        
        if (locationArray.length === 0) {
            chartContainer.innerHTML = '<p class="text-center text-muted my-5">Data lokasi tidak cukup untuk menampilkan grafik.</p>';
            return;
        }
        
        const labels = locationArray.map(item => item.location);
        const positiveData = locationArray.map(item => parseFloat(item.positivePercent));
        const neutralData = locationArray.map(item => parseFloat(item.neutralPercent));
        const negativeData = locationArray.map(item => parseFloat(item.negativePercent));
        
        // Buat chart
        const ctx = document.createElement('canvas');
        chartContainer.innerHTML = '';
        chartContainer.appendChild(ctx);
        
        // Destroy previous chart instance if exists
        if (sentimentByLocationChart) {
            sentimentByLocationChart.destroy();
        }
        
        // Buat chart baru
        sentimentByLocationChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Positif',
                        data: positiveData,
                        backgroundColor: '#ffffff',
                        borderColor: '#dddddd',
                        borderWidth: 1
                    },
                    {
                        label: 'Netral',
                        data: neutralData,
                        backgroundColor: '#9e9e9e',
                        borderColor: '#757575',
                        borderWidth: 1
                    },
                    {
                        label: 'Negatif',
                        data: negativeData,
                        backgroundColor: '#000000',
                        borderColor: '#000000',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Lokasi',
                            font: {
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Persentase (%)',
                            font: {
                                weight: 'bold'
                            }
                        },
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Sentimen Berdasarkan Lokasi (Top 5)',
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        padding: {
                            bottom: 15
                        }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.raw + '%';
                            },
                            afterLabel: function(context) {
                                const index = context.dataIndex;
                                const locationItem = locationArray[index];
                                return 'Total tweets: ' + locationItem.total;
                            }
                        }
                    }
                },
                animation: {
                    duration: 1200,
                    easing: 'easeOutQuart'
                }
            }
        });
    }
    
    // Fungsi untuk membuat chart sentimen berdasarkan bahasa
    function createSentimentByLanguageChart(tweetsData) {
        const chartContainer = document.getElementById('sentiment-by-language-chart');
        if (!chartContainer || !tweetsData || tweetsData.length === 0) return;
        
        // Tambahkan loading indicator
        chartContainer.innerHTML = '<div class="chart-loader"><div class="spinner"></div></div>';
        
        // Group tweets berdasarkan bahasa dan sentimen
        const languageData = {};
        const languageNames = {
            'in': 'Indonesia',
            'en': 'English',
            'id': 'Indonesia',
            'qme': 'Quechua',
            'und': 'Undefined',
            'ar': 'Arabic',
            'fr': 'French',
            'es': 'Spanish',
            'de': 'German'
        };
        
        tweetsData.forEach(tweet => {
            if (tweet.lang) {
                if (!languageData[tweet.lang]) {
                    languageData[tweet.lang] = {
                        Positif: 0,
                        Netral: 0,
                        Negatif: 0,
                        total: 0
                    };
                }
                
                languageData[tweet.lang][tweet.predicted_sentiment]++;
                languageData[tweet.lang].total++;
            }
        });
        
        // Convert to array dan sort berdasarkan total
        const languageArray = Object.entries(languageData)
            .map(([lang, data]) => ({
                lang,
                langName: languageNames[lang] || lang,
                ...data,
                positivePercent: (data.Positif / data.total * 100).toFixed(1),
                neutralPercent: (data.Netral / data.total * 100).toFixed(1),
                negativePercent: (data.Negatif / data.total * 100).toFixed(1)
            }))
            .sort((a, b) => b.total - a.total)
            .slice(0, 5); // Ambil top 5
        
        if (languageArray.length === 0) {
            chartContainer.innerHTML = '<p class="text-center text-muted my-5">Data bahasa tidak cukup untuk menampilkan grafik.</p>';
            return;
        }
        
        const labels = languageArray.map(item => item.langName);
        const positiveData = languageArray.map(item => parseFloat(item.positivePercent));
        const neutralData = languageArray.map(item => parseFloat(item.neutralPercent));
        const negativeData = languageArray.map(item => parseFloat(item.negativePercent));
        
        // Buat chart
        const ctx = document.createElement('canvas');
        chartContainer.innerHTML = '';
        chartContainer.appendChild(ctx);
        
        // Destroy previous chart instance if exists
        if (sentimentByLanguageChart) {
            sentimentByLanguageChart.destroy();
        }
        
        // Buat chart baru
        sentimentByLanguageChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Positif',
                        data: positiveData,
                        backgroundColor: '#ffffff',
                        borderColor: '#dddddd',
                        borderWidth: 1
                    },
                    {
                        label: 'Netral',
                        data: neutralData,
                        backgroundColor: '#9e9e9e',
                        borderColor: '#757575',
                        borderWidth: 1
                    },
                    {
                        label: 'Negatif',
                        data: negativeData,
                        backgroundColor: '#000000',
                        borderColor: '#000000',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Bahasa',
                            font: {
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Persentase (%)',
                            font: {
                                weight: 'bold'
                            }
                        },
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Sentimen Berdasarkan Bahasa (Top 5)',
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        padding: {
                            bottom: 15
                        }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.raw + '%';
                            },
                            afterLabel: function(context) {
                                const index = context.dataIndex;
                                const languageItem = languageArray[index];
                                return 'Total tweets: ' + languageItem.total;
                            }
                        }
                    }
                },
                animation: {
                    duration: 1400,
                    easing: 'easeOutQuart'
                }
            }
        });
    }
    
    // Fungsi untuk membuat chart frequensi kata
    function createWordFrequencyChart(containerId, wordFrequencies, title, color) {
        const chartContainer = document.getElementById(containerId);
        if (!chartContainer || !wordFrequencies || wordFrequencies.length === 0) {
            if (chartContainer) {
                chartContainer.innerHTML = '<p class="text-center text-muted my-5">Tidak cukup data untuk menampilkan grafik ini.</p>';
            }
            return;
        }
        
        // Tambah loading indicator
        chartContainer.innerHTML = '<div class="chart-loader"><div class="spinner"></div></div>';
        
        // Siapkan data untuk chart
        const wordsArray = wordFrequencies
            .map(item => ({ word: item.word, count: item.count }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 10);
        
        const labels = wordsArray.map(item => item.word);
        const data = wordsArray.map(item => item.count);
        
        // Buat chart
        const ctx = document.createElement('canvas');
        chartContainer.innerHTML = '';
        chartContainer.appendChild(ctx);
        
        // Tentukan warna teks berdasarkan warna background
        let textColor = '#000000';
        if (color === '#000000') {
            textColor = '#ffffff';
        }
        
        // Get chart instance berdasarkan containerId
        let chartInstance;
        if (containerId === 'positive-words-chart') {
            // Destroy previous chart instance if exists
            if (positiveWordsChart) {
                positiveWordsChart.destroy();
            }
            
            // Buat chart baru
            chartInstance = positiveWordsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Frekuensi',
                            data: data,
                            backgroundColor: color,
                            borderColor: '#333333',
                            borderWidth: 1
                        }
                    ]
                },
                options: getWordChartOptions(title, textColor)
            });
        } else if (containerId === 'neutral-words-chart') {
            // Destroy previous chart instance if exists
            if (neutralWordsChart) {
                neutralWordsChart.destroy();
            }
            
            // Buat chart baru
            chartInstance = neutralWordsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Frekuensi',
                            data: data,
                            backgroundColor: color,
                            borderColor: '#333333',
                            borderWidth: 1
                        }
                    ]
                },
                options: getWordChartOptions(title, textColor)
            });
        } else if (containerId === 'negative-words-chart') {
            // Destroy previous chart instance if exists
            if (negativeWordsChart) {
                negativeWordsChart.destroy();
            }
            
            // Buat chart baru
            chartInstance = negativeWordsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Frekuensi',
                            data: data,
                            backgroundColor: color,
                            borderColor: '#333333',
                            borderWidth: 1
                        }
                    ]
                },
                options: getWordChartOptions(title, textColor)
            });
        }
        
        return chartInstance;
    }
    
    // Helper function untuk opsi chart frekuensi kata
    function getWordChartOptions(title, textColor) {
        return {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Frekuensi',
                        font: {
                            weight: 'bold'
                        }
                    },
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    title: {
                        display: false
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: {
                        bottom: 15
                    }
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Frekuensi: ' + context.raw;
                        }
                    }
                }
            },
            animation: {
                delay: function(context) {
                    return context.dataIndex * 100;
                },
                duration: 1000,
                easing: 'easeOutQuart'
            }
        };
    }

    function createImprovedWordCloud(data) {
        const wordCloudContainer = document.getElementById('word-cloud-container');
        if (!wordCloudContainer || !data || !data.tweets || data.tweets.length === 0) return;
        
        // Add loading indicator
        wordCloudContainer.innerHTML = '<div class="chart-loader"><div class="spinner"></div></div>';
        
        // Check if d3 is available
        if (typeof d3 === 'undefined') {
            wordCloudContainer.innerHTML = '<p class="text-center text-muted my-5">D3.js library is not available. Word cloud cannot be generated.</p>';
            return;
        }
        
        // Create word frequency counts
        const wordFrequencies = {};
        
        // Stopwords to filter out (expanded list)
        const stopwords = [
            'yang', 'dan', 'di', 'dengan', 'untuk', 'pada', 'adalah', 'ini', 'itu', 'atau', 'juga',
            'dari', 'akan', 'ke', 'karena', 'oleh', 'saat', 'dalam', 'secara', 'telah', 'sebagai',
            'bahwa', 'dapat', 'para', 'harus', 'namun', 'seperti', 'hingga', 'tak', 'tidak', 'tapi',
            'kita', 'kami', 'saya', 'mereka', 'dia', 'http', 'https', 'co', 't', 'a', 'amp', 'rt',
            'nya', 'yg', 'dgn', 'utk', 'dr', 'pd', 'jd', 'sdh', 'tdk', 'bisa', 'ada', 'kalo', 'bgt',
            'aja', 'gitu', 'gak', 'mau', 'biar', 'kan', 'klo', 'deh', 'sih', 'nya', 'nih', 'loh'
        ];
        
        // Process each tweet to extract words
        data.tweets.forEach(tweet => {
            if (!tweet || !tweet.content) return;
            
            // Extract words from content
            let content = tweet.content.toLowerCase();
            
            // Remove URLs
            content = content.replace(/https?:\/\/[^\s]+/g, '');
            
            // Remove special characters and emoji
            content = content.replace(/[^\w\s]/g, ' ');
            
            // Split into words
            const words = content.split(/\s+/);
            
            // Filter words
            const filteredWords = words.filter(word => 
                word && 
                word.length > 3 &&  // Filter words with length > 3
                !stopwords.includes(word) &&  // Filter out stopwords
                !/^\d+$/.test(word)  // Filter out numbers
            );
            
            // Count word frequencies
            filteredWords.forEach(word => {
                wordFrequencies[word] = (wordFrequencies[word] || 0) + 1;
            });
        });
        
        // Convert to array for word cloud
        const wordsArray = Object.entries(wordFrequencies)
            .map(([text, value]) => ({ text, value }))
            .filter(item => item.value > 1)  // Filter words that appear more than once
            .sort((a, b) => b.value - a.value)
            .slice(0, 100);  // Limit to top 100 words
        
        if (wordsArray.length === 0) {
            wordCloudContainer.innerHTML = '<p class="text-center text-muted my-5">Tidak cukup data untuk menampilkan word cloud.</p>';
            return;
        }
        
        // Normalize word sizes between minSize and maxSize
        const minCount = Math.min(...wordsArray.map(w => w.value));
        const maxCount = Math.max(...wordsArray.map(w => w.value));
        const minSize = 12;
        const maxSize = 60;
        
        // Adjust word sizes
        wordsArray.forEach(word => {
            // Normalize size
            const size = minSize + ((word.value - minCount) / (maxCount - minCount || 1)) * (maxSize - minSize);
            word.size = size;
            
            // Assign a color based on sentiment association
            // Use a black/gray scale for the monochrome theme
            const intensity = Math.round((word.value - minCount) / (maxCount - minCount || 1) * 200);
            word.color = `rgb(${intensity}, ${intensity}, ${intensity})`;
        });
        
        try {
            // Create SVG element
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '100%');
            svg.setAttribute('height', '100%');
            svg.style.opacity = 0;
            wordCloudContainer.innerHTML = '';
            wordCloudContainer.appendChild(svg);
            
            // Set up word cloud layout
            const width = wordCloudContainer.clientWidth || 500;
            const height = wordCloudContainer.clientHeight || 400;
            
            // Check if d3.layout.cloud is available
            if (typeof d3.layout.cloud !== 'function') {
                wordCloudContainer.innerHTML = '<p class="text-center text-muted my-5">d3-cloud library is not available. Word cloud cannot be generated.</p>';
                return;
            }
            
            // Use d3.layout.cloud for the word cloud
            const layout = d3.layout.cloud()
                .size([width, height])
                .words(wordsArray)
                .padding(5)
                .rotate(() => Math.random() < 0.5 ? 0 : 90)
                .font('Inter')
                .fontSize(d => d.size)
                .on('end', draw);
            
            layout.start();
            
            function draw(words) {
                // Remove loading spinner
                const loadingIndicator = wordCloudContainer.querySelector('.chart-loader');
                if (loadingIndicator) {
                    wordCloudContainer.removeChild(loadingIndicator);
                }
                
                d3.select(svg)
                    .attr('width', layout.size()[0])
                    .attr('height', layout.size()[1])
                    .append('g')
                    .attr('transform', `translate(${layout.size()[0] / 2},${layout.size()[1] / 2})`)
                    .selectAll('text')
                    .data(words)
                    .enter()
                    .append('text')
                    .style('font-size', d => `${d.size}px`)
                    .style('font-family', 'Inter, sans-serif')
                    .style('font-weight', d => Math.min(900, 300 + Math.floor(d.size * 10)))
                    .style('fill', d => d.color)
                    .attr('text-anchor', 'middle')
                    .attr('transform', d => `translate(${d.x},${d.y}) rotate(${d.rotate})`)
                    .text(d => d.text)
                    .style('opacity', 0)
                    .transition()
                    .duration(1000)
                    .style('opacity', 1);
                
                // Fade in the SVG
                svg.style.transition = 'opacity 1s ease';
                svg.style.opacity = 1;
            }
        } catch (error) {
            console.error("Error creating word cloud:", error);
            // Fallback to simple word display
            wordCloudContainer.innerHTML = '';
            
            const wordCloudFallback = document.createElement('div');
            wordCloudFallback.className = 'd-flex flex-wrap justify-content-center align-items-center h-100';
            
            wordsArray.slice(0, 50).forEach((word, index) => {
                const wordSpan = document.createElement('span');
                wordSpan.textContent = word.text;
                wordSpan.style.fontSize = `${word.size / 10}rem`;
                wordSpan.style.fontWeight = Math.min(900, 300 + Math.floor(word.size * 10));
                wordSpan.style.color = word.color;
                wordSpan.style.padding = '5px';
                wordSpan.style.display = 'inline-block';
                wordSpan.style.transition = 'all 0.3s ease';
                wordSpan.style.opacity = 0;
                wordSpan.style.transform = 'translateY(20px)';
                
                wordSpan.addEventListener('mouseover', function() {
                    this.style.transform = 'scale(1.2)';
                    this.style.color = '#000000';
                });
                
                wordSpan.addEventListener('mouseout', function() {
                    this.style.transform = 'scale(1)';
                    this.style.color = word.color;
                });
                
                wordCloudFallback.appendChild(wordSpan);
                
                // Animate entrance with delay based on index
                setTimeout(() => {
                    wordSpan.style.opacity = 1;
                    wordSpan.style.transform = 'translateY(0)';
                }, 50 * index);
            });
            
            wordCloudContainer.appendChild(wordCloudFallback);
        }
    }
    
    
    function updateAnalysisResults(data) {
        // Update judul dan deskripsi
        const titleElement = document.getElementById('title-placeholder');
        if (titleElement) titleElement.textContent = data.title;
        
        // Update jumlah dan persentase
        const totalTweetsElement = document.getElementById('total-tweets');
        const positiveCountElement = document.getElementById('positive-count');
        const neutralCountElement = document.getElementById('neutral-count');
        const negativeCountElement = document.getElementById('negative-count');
        
        const positivePercentElement = document.getElementById('positive-percent');
        const neutralPercentElement = document.getElementById('neutral-percent');
        const negativePercentElement = document.getElementById('negative-percent');
        
        if (totalTweetsElement) totalTweetsElement.textContent = data.total_tweets;
        if (positiveCountElement) positiveCountElement.textContent = data.positive_count;
        if (neutralCountElement) neutralCountElement.textContent = data.neutral_count;
        if (negativeCountElement) negativeCountElement.textContent = data.negative_count;
        
        if (positivePercentElement) positivePercentElement.textContent = data.positive_percent + '%';
        if (neutralPercentElement) neutralPercentElement.textContent = data.neutral_percent + '%';
        if (negativePercentElement) negativePercentElement.textContent = data.negative_percent + '%';
        
        // Update distribusi sentimen dengan animasi
        const positiveSegment = document.getElementById('positive-segment');
        const neutralSegment = document.getElementById('neutral-segment');
        const negativeSegment = document.getElementById('negative-segment');
        
        if (positiveSegment && neutralSegment && negativeSegment) {
            // Reset width dulu
            positiveSegment.style.width = '0%';
            neutralSegment.style.width = '0%';
            negativeSegment.style.width = '0%';
            
            // Kemudian animasikan ke nilai baru
            setTimeout(() => {
                positiveSegment.style.width = data.positive_percent + '%';
                positiveSegment.textContent = data.positive_percent + '%';
                neutralSegment.style.width = data.neutral_percent + '%';
                neutralSegment.textContent = data.neutral_percent + '%';
                negativeSegment.style.width = data.negative_percent + '%';
                negativeSegment.textContent = data.negative_percent + '%';
            }, 100);
        }
        
        // Update top hashtags dengan animasi
        const topHashtags = document.getElementById('top-hashtags');
        if (topHashtags) {
            topHashtags.innerHTML = '';
            
            if (data.top_hashtags && data.top_hashtags.length > 0) {
                data.top_hashtags.forEach((hashtag, index) => {
                    const tag = document.createElement('div');
                    tag.className = 'tag animate-fade-in';
                    tag.style.animationDelay = `${index * 0.1}s`;
                    
                    const tagText = hashtag.tag ? hashtag.tag : (typeof hashtag === 'string' ? hashtag : '');
                    const count = hashtag.count ? hashtag.count : '';
                    
                    tag.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h16"></path><path d="M4 15h16"></path><path d="M10 3L8 21"></path><path d="M16 3l-2 18"></path></svg> ${tagText} ${count ? `(${count})` : ''}`;
                    topHashtags.appendChild(tag);
                });
            }
        }
        
        // Update all hashtags
        const allHashtags = document.getElementById('all-hashtags');
        if (allHashtags) {
            allHashtags.innerHTML = '';
            
            if (data.top_hashtags && data.top_hashtags.length > 0) {
                data.top_hashtags.forEach((hashtag, index) => {
                    const tag = document.createElement('div');
                    tag.className = 'tag animate-fade-in';
                    tag.style.animationDelay = `${index * 0.05}s`;
                    
                    const tagText = hashtag.tag ? hashtag.tag : (typeof hashtag === 'string' ? hashtag : '');
                    const count = hashtag.count ? hashtag.count : '';
                    
                    tag.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h16"></path><path d="M4 15h16"></path><path d="M10 3L8 21"></path><path d="M16 3l-2 18"></path></svg> ${tagText} ${count ? `(${count})` : ''}`;
                    allHashtags.appendChild(tag);
                });
            }
        }
        
        // Update top users
        const topUsers = document.getElementById('top-users');
        if (topUsers) {
            topUsers.innerHTML = '';
            
            if (data.top_users && data.top_users.length > 0) {
                data.top_users.forEach(user => {
                    const row = document.createElement('tr');
                    row.className = 'animate-fade-in';
                    
                    const sentimentClass = user.dominant_sentiment === 'Positif' ? 'sentiment-positive' : 
                                          user.dominant_sentiment === 'Netral' ? 'sentiment-neutral' : 'sentiment-negative';
                    
                    row.innerHTML = `
                        <td><a href="https://twitter.com/${user.username}" target="_blank">@${user.username}</a></td>
                        <td>${user.count}</td>
                        <td><span class="${sentimentClass}">${user.dominant_sentiment}</span></td>
                    `;
                    
                    topUsers.appendChild(row);
                });
            }
        }
        
        // Update main topics
        const mainTopics = document.getElementById('main-topics');
        if (mainTopics) {
            mainTopics.innerHTML = '';
            
            if (data.topics && data.topics.length > 0) {
                data.topics.forEach((topic, index) => {
                    const row = document.createElement('tr');
                    row.className = 'animate-fade-in';
                    row.style.animationDelay = `${index * 0.1}s`;
                    
                    const topicText = typeof topic === 'object' ? topic.topic : topic;
                    const frequency = typeof topic === 'object' ? topic.frequency : '';
                    
                    row.innerHTML = `
                        <td>${topicText}</td>
                        <td>${frequency}</td>
                    `;
                    
                    mainTopics.appendChild(row);
                });
            }
        }
        
        // Update topik utama
        const topikUtama = document.getElementById('topik-utama');
        if (topikUtama) {
            topikUtama.innerHTML = '';
            
            if (data.topics && data.topics.length > 0) {
                data.topics.forEach((topic, index) => {
                    const row = document.createElement('tr');
                    row.className = 'animate-fade-in';
                    row.style.animationDelay = `${index * 0.1}s`;
                    
                    const topicText = typeof topic === 'object' ? topic.topic : topic;
                    const frequency = typeof topic === 'object' ? topic.frequency : '';
                    
                    row.innerHTML = `
                        <td>${topicText}</td>
                        <td>${frequency}</td>
                    `;
                    
                    topikUtama.appendChild(row);
                });
            }
        }
        
        // Update hashtag sentiment
        const hashtagSentiment = document.getElementById('hashtag-sentiment');
        if (hashtagSentiment) {
            hashtagSentiment.innerHTML = '';
            
            if (data.hashtag_sentiment && data.hashtag_sentiment.length > 0) {
                data.hashtag_sentiment.forEach((stat, index) => {
                    const row = document.createElement('tr');
                    row.className = 'animate-fade-in';
                    row.style.animationDelay = `${index * 0.1}s`;
                    
                    row.innerHTML = `
                        <td>${stat.tag}</td>
                        <td>${stat.positive}%</td>
                        <td>${stat.neutral}%</td>
                        <td>${stat.negative}%</td>
                        <td>${stat.total}</td>
                    `;
                    
                    hashtagSentiment.appendChild(row);
                });
            }
        }
        
        // Initialize all charts
        if (data.hashtag_sentiment) {
            try {
                createSentimentByHashtagChart(data.hashtag_sentiment);
            } catch (e) {
                console.error("Error creating hashtag sentiment chart:", e);
            }
        }
        
        if (data.tweets) {
            try {
                createSentimentByLocationChart(data.tweets);
                createSentimentByLanguageChart(data.tweets);
            } catch (e) {
                console.error("Error creating location/language charts:", e);
            }
        }
        
        if (data.sentiment_words) {
            // Create top words charts for each sentiment
            try {
                if (data.sentiment_words.positive) {
                    createWordFrequencyChart('positive-words-chart', data.sentiment_words.positive, 'Kata Umum dalam Sentimen Positif', '#ffffff');
                }
                
                if (data.sentiment_words.neutral) {
                    createWordFrequencyChart('neutral-words-chart', data.sentiment_words.neutral, 'Kata Umum dalam Sentimen Netral', '#9e9e9e');
                }
                
                if (data.sentiment_words.negative) {
                    createWordFrequencyChart('negative-words-chart', data.sentiment_words.negative, 'Kata Umum dalam Sentimen Negatif', '#000000');
                }
            } catch (e) {
                console.error("Error creating word frequency charts:", e);
            }
        }
        
        // Update word cloud
        try {
            createImprovedWordCloud(data);
        } catch (e) {
            console.error("Error creating word cloud:", e);
        }
        
        // Update sentiment plot
        const sentimentPlot = document.getElementById('sentiment-plot');
        if (sentimentPlot) {
            if (data.sentiment_plot) {
                sentimentPlot.src = 'data:image/png;base64,' + data.sentiment_plot;
                sentimentPlot.classList.remove('d-none');
                sentimentPlot.classList.add('animate-fade-in');
                
                // Hapus loading indicator jika ada
                const loadingEl = document.querySelector('.sentiment-plot-loading');
                if (loadingEl) {
                    loadingEl.style.display = 'none';
                }
            } else {
                sentimentPlot.classList.add('d-none');
            }
        }
        
        // Initialize the welcome message in chatbot
        initializeChatbot(data);
    }
    
    // Function to update analysis results in UI
    window.updateAnalysisResults = function(data) {
        // Update title and description
        const titleElement = document.getElementById('title-placeholder');
        if (titleElement) titleElement.textContent = data.title;
        
        // Update counts and percentages
        const totalTweetsElement = document.getElementById('total-tweets');
        const positiveCountElement = document.getElementById('positive-count');
        const neutralCountElement = document.getElementById('neutral-count');
        const negativeCountElement = document.getElementById('negative-count');
        
        const positivePercentElement = document.getElementById('positive-percent');
        const neutralPercentElement = document.getElementById('neutral-percent');
        const negativePercentElement = document.getElementById('negative-percent');
        
        if (totalTweetsElement) totalTweetsElement.textContent = data.total_tweets;
        if (positiveCountElement) positiveCountElement.textContent = data.positive_count;
        if (neutralCountElement) neutralCountElement.textContent = data.neutral_count;
        if (negativeCountElement) negativeCountElement.textContent = data.negative_count;
        
        if (positivePercentElement) positivePercentElement.textContent = data.positive_percent + '%';
        if (neutralPercentElement) neutralPercentElement.textContent = data.neutral_percent + '%';
        if (negativePercentElement) negativePercentElement.textContent = data.negative_percent + '%';
        
        // Update sentiment distribution with animation
        const positiveSegment = document.getElementById('positive-segment');
        const neutralSegment = document.getElementById('neutral-segment');
        const negativeSegment = document.getElementById('negative-segment');
        
        if (positiveSegment && neutralSegment && negativeSegment) {
            // Reset widths first
            positiveSegment.style.width = '0%';
            neutralSegment.style.width = '0%';
            negativeSegment.style.width = '0%';
            
            // Then animate to new values
            setTimeout(() => {
                positiveSegment.style.width = data.positive_percent + '%';
                positiveSegment.textContent = data.positive_percent + '%';
                neutralSegment.style.width = data.neutral_percent + '%';
                neutralSegment.textContent = data.neutral_percent + '%';
                negativeSegment.style.width = data.negative_percent + '%';
                negativeSegment.textContent = data.negative_percent + '%';
            }, 100);
        }
        
        // Make sure the stats cards have appropriate classes and icons
        const positiveStats = document.getElementById('positive-stats');
        const neutralStats = document.getElementById('neutral-stats');
        const negativeStats = document.getElementById('negative-stats');
        
        if (positiveStats) {
            positiveStats.className = 'stats-card positive animate-fade-in';
            const iconElement = positiveStats.querySelector('.icon');
            if (iconElement) {
                iconElement.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>';
            }
        }
        
        if (neutralStats) {
            neutralStats.className = 'stats-card neutral animate-fade-in';
            const iconElement = neutralStats.querySelector('.icon');
            if (iconElement) {
                iconElement.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>';
            }
        }
        
        if (negativeStats) {
            negativeStats.className = 'stats-card negative animate-fade-in';
            const iconElement = negativeStats.querySelector('.icon');
            if (iconElement) {
                iconElement.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path></svg>';
            }
        }
        
        // Update top hashtags with animation
        const topHashtags = document.getElementById('top-hashtags');
        if (topHashtags) {
            topHashtags.innerHTML = '';
            
            if (data.top_hashtags && data.top_hashtags.length > 0) {
                data.top_hashtags.forEach((hashtag, index) => {
                    const tag = document.createElement('div');
                    tag.className = 'tag animate-fade-in';
                    tag.style.animationDelay = `${index * 0.1}s`;
                    
                    const tagText = hashtag.tag ? hashtag.tag : (typeof hashtag === 'string' ? hashtag : '');
                    const count = hashtag.count ? hashtag.count : '';
                    
                    tag.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h16"></path><path d="M4 15h16"></path><path d="M10 3L8 21"></path><path d="M16 3l-2 18"></path></svg> ${tagText} ${count ? `(${count})` : ''}`;
                    topHashtags.appendChild(tag);
                });
            }
        }
        
        // Update all hashtags
        const allHashtags = document.getElementById('all-hashtags');
        if (allHashtags) {
            allHashtags.innerHTML = '';
            
            if (data.top_hashtags && data.top_hashtags.length > 0) {
                data.top_hashtags.forEach((hashtag, index) => {
                    const tag = document.createElement('div');
                    tag.className = 'tag animate-fade-in';
                    tag.style.animationDelay = `${index * 0.05}s`;
                    
                    const tagText = hashtag.tag ? hashtag.tag : (typeof hashtag === 'string' ? hashtag : '');
                    const count = hashtag.count ? hashtag.count : '';
                    
                    tag.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h16"></path><path d="M4 15h16"></path><path d="M10 3L8 21"></path><path d="M16 3l-2 18"></path></svg> ${tagText} ${count ? `(${count})` : ''}`;
                    allHashtags.appendChild(tag);
                });
            }
        }
        
        // Update top users
        const topUsers = document.getElementById('top-users');
        if (topUsers) {
            topUsers.innerHTML = '';
            
            if (data.top_users && data.top_users.length > 0) {
                data.top_users.forEach(user => {
                    const row = document.createElement('tr');
                    row.className = 'animate-fade-in';
                    
                    const sentimentClass = user.dominant_sentiment === 'Positif' ? 'sentiment-positive' : 
                                          user.dominant_sentiment === 'Netral' ? 'sentiment-neutral' : 'sentiment-negative';
                    
                    row.innerHTML = `
                        <td><a href="https://twitter.com/${user.username}" target="_blank">@${user.username}</a></td>
                        <td>${user.count}</td>
                        <td><span class="${sentimentClass}">${user.dominant_sentiment}</span></td>
                    `;
                    
                    topUsers.appendChild(row);
                });
            }
        }
        
        // Update main topics
        const mainTopics = document.getElementById('main-topics');
        if (mainTopics) {
            mainTopics.innerHTML = '';
            
            if (data.topics && data.topics.length > 0) {
                data.topics.forEach((topic, index) => {
                    const row = document.createElement('tr');
                    row.className = 'animate-fade-in';
                    row.style.animationDelay = `${index * 0.1}s`;
                    
                    const topicText = typeof topic === 'object' ? topic.topic : topic;
                    const frequency = typeof topic === 'object' ? topic.frequency : '';
                    
                    row.innerHTML = `
                        <td>${topicText}</td>
                        <td>${frequency}</td>
                    `;
                    
                    mainTopics.appendChild(row);
                });
            }
        }
        
        // Update topics in topik-utama
        const topikUtama = document.getElementById('topik-utama');
        if (topikUtama) {
            topikUtama.innerHTML = '';
            
            if (data.topics && data.topics.length > 0) {
                data.topics.forEach((topic, index) => {
                    const row = document.createElement('tr');
                    row.className = 'animate-fade-in';
                    row.style.animationDelay = `${index * 0.1}s`;
                    
                    const topicText = typeof topic === 'object' ? topic.topic : topic;
                    const frequency = typeof topic === 'object' ? topic.frequency : '';
                    
                    row.innerHTML = `
                        <td>${topicText}</td>
                        <td>${frequency}</td>
                    `;
                    
                    topikUtama.appendChild(row);
                });
            }
        }
        
        // Update hashtag sentiment
        const hashtagSentiment = document.getElementById('hashtag-sentiment');
        if (hashtagSentiment) {
            hashtagSentiment.innerHTML = '';
            
            if (data.hashtag_sentiment && data.hashtag_sentiment.length > 0) {
                data.hashtag_sentiment.forEach((stat, index) => {
                    const row = document.createElement('tr');
                    row.className = 'animate-fade-in';
                    row.style.animationDelay = `${index * 0.1}s`;
                    
                    row.innerHTML = `
                        <td>${stat.tag}</td>
                        <td>${stat.positive}%</td>
                        <td>${stat.neutral}%</td>
                        <td>${stat.negative}%</td>
                        <td>${stat.total}</td>
                    `;
                    
                    hashtagSentiment.appendChild(row);
                });
            }
        }
        
        // Update sentiment plot
        const sentimentPlot = document.getElementById('sentiment-plot');
        if (sentimentPlot) {
            if (data.sentiment_plot) {
                sentimentPlot.src = 'data:image/png;base64,' + data.sentiment_plot;
                sentimentPlot.classList.remove('d-none');
                sentimentPlot.classList.add('animate-fade-in');
            } else {
                sentimentPlot.classList.add('d-none');
            }
        }
        
        // Initialize the welcome message in chatbot
        initializeChatbot(data);
    };
    
    // Initialize chatbot with welcome message
    function initializeChatbot(data) {
        const chatbotMessages = document.getElementById('chatbot-messages');
        if (!chatbotMessages) return;
        
        // Clear any existing messages
        chatbotMessages.innerHTML = '';
        
        // Create welcome message
        const welcomeMessage = document.createElement('div');
        welcomeMessage.className = 'message message-bot animate-fade-in';
        
        // Build the welcome message with data from analysis
        let messageContent = `
            <div class="mb-2"><strong>Selamat datang di Chatbot Evaluasi Kebijakan!</strong></div>
            <p>Saya akan membantu Anda menganalisis data sentimen X tentang ${data.title}.</p>
            <div class="mb-2"><strong>Ringkasan Analisis:</strong></div>
            <ul>
                <li>Total tweets: ${data.total_tweets}</li>
                <li>Sentimen Positif: ${data.positive_count} tweets (${data.positive_percent}%)</li>
                <li>Sentimen Netral: ${data.neutral_count} tweets (${data.neutral_percent}%)</li>
                <li>Sentimen Negatif: ${data.negative_count} tweets (${data.negative_percent}%)</li>
            </ul>
            <p>Silakan pilih topik di bawah ini atau ajukan pertanyaan Anda sendiri.</p>
        `;
        
        welcomeMessage.innerHTML = messageContent;
        chatbotMessages.appendChild(welcomeMessage);
        
        // Scroll to bottom
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }
    
    // Function to send message to chatbot
    function sendChatbotMessage() {
        if (!chatbotInput || !chatbotMessages) return;
        
        const messageText = chatbotInput.value.trim();
        
        if (!messageText) return;
        
        // Add user message to chat
        const userMessage = document.createElement('div');
        userMessage.className = 'message message-user animate-fade-in';
        userMessage.textContent = messageText;
        chatbotMessages.appendChild(userMessage);
        
        // Clear input
        chatbotInput.value = '';
        
        // Add loading indicator
        const loadingMessage = document.createElement('div');
        loadingMessage.className = 'message message-bot animate-fade-in';
        loadingMessage.innerHTML = '<div class="d-flex align-items-center"><div class="spinner-grow spinner-grow-sm me-2" role="status"></div><span>Menganalisis data dan menyusun respons...</span></div>';
        chatbotMessages.appendChild(loadingMessage);
        
        // Scroll to bottom
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        
        // Send to server
        fetch('/chatbot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({message: messageText})
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            chatbotMessages.removeChild(loadingMessage);
            
            // Format the response text with proper line breaks and formatting
            const formattedResponse = formatChatbotResponse(data.response);
            
            // Add bot response with animation
            const botMessage = document.createElement('div');
            botMessage.className = 'message message-bot animate-fade-in';
            botMessage.innerHTML = formattedResponse;
            chatbotMessages.appendChild(botMessage);
            
            // Scroll to bottom
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        })
        .catch(error => {
            // Remove loading message
            chatbotMessages.removeChild(loadingMessage);
            
            // Add error message
            const errorMessage = document.createElement('div');
            errorMessage.className = 'message message-bot animate-fade-in';
            errorMessage.textContent = 'Maaf, terjadi kesalahan dalam berkomunikasi dengan chatbot. Silakan coba lagi.';
            chatbotMessages.appendChild(errorMessage);
            
            // Scroll to bottom
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        });
    }
    
    // Format chatbot response with proper HTML formatting
    function formatChatbotResponse(text) {
        if (!text) return '';
        
        // Convert line breaks to <br>
        let formatted = text.replace(/\n/g, '<br>');
        
        // Format numbered lists (1. Item)
        formatted = formatted.replace(/(\d+\.\s+[^\n<]+)(<br>|$)/g, '<li>$1</li>');
        
        // Format bullet points (- Item or • Item)
        formatted = formatted.replace(/([-•]\s+[^\n<]+)(<br>|$)/g, '<li>$1</li>');
        
        // Wrap lists in <ul> tags
        formatted = formatted.replace(/<li>([^<]+)<\/li>(<li>)/g, '<li>$1</li>$2');
        formatted = formatted.replace(/<li>([^<]+)<\/li>(?!<li>)/g, '<ul><li>$1</li></ul>');
        formatted = formatted.replace(/<\/ul><ul>/g, '');
        
        // Bold text between asterisks (*text*)
        formatted = formatted.replace(/\*([^*]+)\*/g, '<strong>$1</strong>');
        
        // Italic text between underscores (_text_)
        formatted = formatted.replace(/_([^_]+)_/g, '<em>$1</em>');
        
        // Create paragraphs for text blocks
        formatted = '<p>' + formatted.replace(/<br><br>/g, '</p><p>') + '</p>';
        
        // Clean up empty paragraphs
        formatted = formatted.replace(/<p><\/p>/g, '');
        
        return formatted;
    }

    function forceCleanupLock() {
        fetch('/clean-lock')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showAlert(data.message, 'success');
                
                // Tambahkan countdown sebelum re-enable tombol
                const waitTime = 3;
                let countdown = waitTime;
                
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Melanjutkan dalam ${countdown}...`;
                
                const countdownInterval = setInterval(() => {
                    countdown--;
                    if (countdown <= 0) {
                        clearInterval(countdownInterval);
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Mulai Analisis`;
                        isSubmitting = false;
                        retryCount = 0;
                    } else {
                        submitBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Melanjutkan dalam ${countdown}...`;
                    }
                }, 1000);
                
            } else {
                showAlert('Gagal membersihkan lock: ' + data.message, 'warning');
            }
        })
        .catch(error => {
            console.error('Error cleaning lock:', error);
            showAlert('Error: ' + error.message, 'danger');
        });
    }
    
    
    if (response.status === 429) {
        // Too Many Requests - implementasi retry dengan backoff
        return response.json().then(errorData => {
            retryCount++;
            
            // Jika ada kode LOCK_EXISTS, tawarkan untuk membersihkan lock
            if (errorData.code === 'LOCK_EXISTS') {
                console.log("Lock error terdeteksi");
                
                // Tampilkan pesan dengan opsi clean lock
                const message = `
                    <div>Proses sebelumnya masih berjalan. 
                    <button onclick="forceCleanupLock()" class="btn btn-sm btn-outline-warning ms-2">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                            <line x1="9" y1="9" x2="15" y2="15"></line>
                            <line x1="15" y1="9" x2="9" y2="15"></line>
                        </svg>
                        Bersihkan Lock
                    </button></div>
                `;
                showAlert(message, 'warning', false); // Parameter false agar tidak auto-hide
                
                // Reset submit button
                resetSubmitButton();
                return null;
            }
            
            function handleLockError(errorData) {
                retryCount++;
                
                // Jika ada kode LOCK_EXISTS, tawarkan untuk membersihkan lock
                if (errorData.code === 'LOCK_EXISTS') {
                    console.log("Lock error terdeteksi");
                    
                    // Tampilkan modal dengan opsi clean lock
                    showCleanLockModal(errorData.user_id || current_user.id);
                    
                    // Reset submit button
                    resetSubmitButton();
                    return null;
                }
                
                // Standar retry untuk error lain
                let waitTime = retryTimeout * Math.pow(2, retryCount - 1); // Exponential backoff
                
                if (retryCount <= maxRetries) {
                    showAlert(`Server sedang sibuk. Mencoba lagi dalam ${Math.round(waitTime/1000)} detik... (Percobaan ${retryCount}/${maxRetries})`, 'warning');
                    
                    // Update tombol
                    submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Menunggu (${Math.round(waitTime/1000)}s)...`;
                    
                    setTimeout(() => {
                        // Coba lagi setelah backoff
                        submitFormWithRetry();
                    }, waitTime);
                    
                    return null; // Skip processing response
                } else {
                    // Gagal setelah beberapa kali retry
                    throw new Error('Server sedang sibuk. Silakan coba lagi nanti.');
                }
            }
        });
    }
    
    // Function to show alert
    function showAlert(message, type, autoHide = true) {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;
        
        const alertId = 'alert-' + Date.now();
        const alert = document.createElement('div');
        alert.id = alertId;
        alert.className = `alert alert-${type} alert-dismissible fade show animate-fade-in`;
        alert.role = 'alert';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        alertContainer.appendChild(alert);
        
        // Auto remove after 5 seconds if autoHide is true
        if (autoHide) {
            setTimeout(() => {
                const existingAlert = document.getElementById(alertId);
                if (existingAlert) {
                    existingAlert.classList.remove('show');
                    setTimeout(() => existingAlert.remove(), 300);
                }
            }, 5000);
        }
        
        return alertId;
    }

    // Fungsi untuk penanganan fetch dengan retry dan timeout
    function fetchWithRetry(url, options, maxRetries = 3, timeout = 90000) {
        // Tampilkan animasi loading 
        updateLoadingStatus(1, "Mengunduh dan menyiapkan data...");
        
        return new Promise((resolve, reject) => {
            // Tambahkan timeout yang lebih panjang
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout);
            
            const makeRequest = (retries) => {
                const fetchOptions = {
                    ...options,
                    signal: controller.signal
                };
                
                fetch(url, fetchOptions)
                    .then(response => {
                        clearTimeout(timeoutId); // Clear timeout if successful
                        
                        if (response.status === 429) {
                            // Too Many Requests - implementasi retry dengan backoff
                            return response.json().then(errorData => {
                                const retryDelay = Math.min(2000 * Math.pow(2, maxRetries - retries), 10000);
                                updateLoadingStatus(Math.round((maxRetries - retries + 1) / maxRetries * 50), 
                                                `Server sibuk, mencoba lagi dalam ${Math.round(retryDelay/1000)} detik...`);
                                
                                if (retries <= 0) {
                                    throw new Error(`Terlalu banyak permintaan. Silakan coba lagi nanti.`);
                                }
                                
                                return new Promise(resolve => {
                                    setTimeout(() => resolve(makeRequest(retries - 1)), retryDelay);
                                });
                            });
                        }
                        
                        if (!response.ok) {
                            throw new Error(`Server error: ${response.status} ${response.statusText}`);
                        }
                        
                        updateLoadingStatus(3, "Memproses data yang diterima...");
                        return response.json();
                    })
                    .then(data => {
                        updateLoadingStatus(3, "Menampilkan hasil analisis...");
                        resolve(data);
                    })
                    .catch(error => {
                        clearTimeout(timeoutId);
                        
                        if (error.name === 'AbortError') {
                            error = new Error('Permintaan timeout. Server mungkin sibuk, silakan coba lagi.');
                        }
                        
                        if (error.message && error.message.includes('ChunkedEncodingError')) {
                            error = new Error('Koneksi terputus. Silakan periksa koneksi internet Anda dan coba lagi.');
                        }
                        
                        if (retries <= 0) {
                            reject(error);
                            return;
                        }
                        
                        // Exponential backoff
                        const waitTime = 2000 * Math.pow(2, maxRetries - retries);
                        console.log(`Retry attempt ${maxRetries - retries + 1}/${maxRetries} after ${waitTime}ms: ${error.message}`);
                        updateLoadingStatus(2, `Mencoba lagi (${maxRetries - retries + 1}/${maxRetries})...`);
                        
                        setTimeout(() => {
                            makeRequest(retries - 1);
                        }, waitTime);
                    });
            };
            
            makeRequest(maxRetries);
        });
    }

    // Fungsi untuk update loading status
    function updateLoadingStatus(step, message) {
        const loadingProgress = document.getElementById('loading-progress');
        const loadingStatus = document.getElementById('loading-status');
        
        if (loadingProgress) {
            // Hapus semua kelas progress sebelumnya
            loadingProgress.classList.remove('progress-step-1', 'progress-step-2', 'progress-step-3', 'progress-step-4');
            // Tambahkan kelas progress baru
            loadingProgress.classList.add(`progress-step-${step}`);
        }
        
        if (loadingStatus) {
            // Animasi fade out/in untuk perubahan pesan
            loadingStatus.style.opacity = '0';
            setTimeout(() => {
                loadingStatus.textContent = message;
                loadingStatus.style.opacity = '1';
            }, 300);
        }
        
        console.log(`Loading status update: Step ${step} - ${message}`);
    }

    // Fungsi untuk menampilkan overlay loading
    function showLoadingOverlay(message = "Memuat data analisis...") {
        const existingOverlay = document.getElementById('loading-overlay');
        
        if (existingOverlay) {
            // Update pesan jika overlay sudah ada
            const statusElement = document.getElementById('loading-status');
            if (statusElement) statusElement.textContent = message;
            
            existingOverlay.classList.remove('fade-out');
            existingOverlay.style.display = 'flex';
            
            // Reset progress bar
            const loadingProgress = document.getElementById('loading-progress');
            if (loadingProgress) {
                loadingProgress.classList.remove('progress-step-1', 'progress-step-2', 'progress-step-3', 'progress-step-4');
                loadingProgress.classList.add('progress-step-1');
            }
        } else {
            // Buat overlay baru jika belum ada
            const overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay';
            overlay.style.zIndex = '1000';
            
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="spinner-border loading-spinner text-dark" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <h5 class="loading-title">Memuat Data</h5>
                    <p class="loading-message">${message}</p>
                    <div class="loading-progress-container">
                        <div id="loading-progress" class="loading-progress-bar progress-step-1"></div>
                    </div>
                    <small class="loading-status" id="loading-status">Mengunduh dan menyiapkan data...</small>
                </div>
            `;
            
            document.body.appendChild(overlay);
        }
    }

    // Fungsi untuk menyembunyikan overlay loading
    function hideLoadingOverlay() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (!loadingOverlay) return;
        
        // Tampilkan step terakhir sejenak sebelum menghilang
        updateLoadingStatus(4, "Analisis berhasil dimuat!");
        
        // Tunggu lebih lama untuk memberi waktu user membaca pesan sukses
        setTimeout(() => {
            // Animasi fade-out yang halus
            loadingOverlay.style.transition = 'opacity 0.8s ease';
            loadingOverlay.style.opacity = '0';
            
            // Hapus dari DOM setelah animasi selesai
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
                console.log("Loading overlay removed");
            }, 800);
        }, 1000);
    }

    // Fungsi untuk menampilkan pesan error
    function showErrorMessage(message) {
        const errorContainer = document.createElement('div');
        errorContainer.className = 'alert alert-danger animate-fade-in';
        errorContainer.innerHTML = `
            <div class="d-flex align-items-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="me-3"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                <div>
                    <h5 class="mb-1">Terjadi Kesalahan</h5>
                    <p class="mb-2">${message}</p>
                    <div class="mt-2">
                        <button class="btn btn-sm btn-outline-danger me-2" onclick="fetchAnalysisDataWithRetry()">Coba Lagi</button>
                        <a href="/input-data" class="btn btn-sm btn-dark">Kembali ke Input Data</a>
                    </div>
                </div>
            </div>
        `;
        
        // Tampilkan error di berbagai tab untuk memastikan user melihatnya
        const contentContainers = [
            document.getElementById('dashboard-content'),
            document.getElementById('tweets-content'),
            document.getElementById('topics-content'),
            document.getElementById('charts-content')
        ];
        
        contentContainers.forEach(container => {
            if (container) {
                container.innerHTML = '';
                container.appendChild(errorContainer.cloneNode(true));
            }
        });
        
        // Tambahkan juga sebagai alert di bagian atas
        const alertContainer = document.getElementById('alert-container');
        if (alertContainer) {
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger alert-dismissible fade show animate-fade-in';
            alert.role = 'alert';
            alert.innerHTML = `
                <strong>Error!</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            
            alertContainer.appendChild(alert);
        }
    }

    // Fungsi untuk mencoba fetch analysis data dengan retry
    function fetchAnalysisDataWithRetry() {
        // Update status loading
        updateLoadingStatus(1, "Menginisialisasi dan menghubungkan ke server...");
        
        // Tambah timeout yang lebih panjang (3 menit)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000); // 3 menit
        
        fetch('/api/analysis-data', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache' // Hindari caching
            },
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }
            
            // Update status loading
            updateLoadingStatus(2, "Data berhasil diterima, memproses hasil...");
            
            return response.json();
        })
        .then(data => {
            // Update status loading
            updateLoadingStatus(3, "Menampilkan hasil analisis...");
            
            console.log("Data analisis berhasil dimuat:", data.title);
            
            // Tetapkan variabel global untuk data analisis
            analysisResults = data;
            allTweets = data.tweets || [];
            
            // Tambahkan log tambahan untuk debugging
            console.log("Jumlah tweet dimuat:", allTweets.length);
            console.log("Data hashtag:", data.top_hashtags ? data.top_hashtags.length : 0);
            console.log("Data topik:", data.topics ? data.topics.length : 0);
            
            // Update UI dengan hasil analisis
            updateAnalysisResults(data);
            
            // Inisialisasi pagination
            initializePagination();
            
            // Generate topics otomatis
            generateTopics(data);
            
            // Buat word cloud
            createImprovedWordCloud(data);
            
            // Beri waktu untuk DOM diperbarui sebelum memeriksa data
            setTimeout(() => {
                // Beritahu bahwa data sudah dimuat jika fungsi tersedia
                if (window.notifyDataLoaded && !window.dataLoaded) {
                    window.notifyDataLoaded();
                }
                
                // Cek status dan sembunyikan loading overlay
                hideLoadingOverlay();
            }, 2500);
        })
        .catch(error => {
            clearTimeout(timeoutId);
            console.error('Error:', error);
            
            // Update status loading untuk menunjukkan error
            updateLoadingStatus(1, `Error: ${error.message}`);
            
            // Tambahkan tombol retry pada overlay loading
            const loadingContent = document.querySelector('.loading-content');
            if (loadingContent) {
                const retryButton = document.createElement('button');
                retryButton.className = 'btn btn-dark mt-3';
                retryButton.textContent = 'Coba Lagi';
                retryButton.onclick = () => window.location.reload();
                loadingContent.appendChild(retryButton);
            }
        });
    }

    function submitFormWithRetry() {
        // Set flag submission
        isSubmitting = true;
        
        // Show loading indicator and disable submit button
        loadingIndicator.classList.remove('d-none');
        submitBtn.disabled = true;
        
        // Ubah teks tombol
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Sedang Memproses...';
        
        // Get form data
        const formData = new FormData();
        formData.append('title', document.getElementById('title').value);
        formData.append('description', document.getElementById('description')?.value || '');
        
        const csvFile = document.getElementById('csv-file').files[0];
        if (!csvFile) {
            showAlert('Silakan unggah file CSV terlebih dahulu.', 'warning');
            resetSubmitButton();
            return;
        }
        
        formData.append('csv-file', csvFile);
        
        // Log information
        console.log('Memulai analisis file...');
        
        // Tambahkan parameter force_cleanup untuk mengatasi lock error jika ini retry
        let uploadUrl = '/upload';
        if (retryCount > 0) {
            uploadUrl += '?force_cleanup=true';
        }
        
        // Send to server with increased timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 menit timeout (ditambah)
        
        fetch(uploadUrl, {
            method: 'POST',
            body: formData,
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            
            if (response.status === 429) {
                // Too Many Requests - implementasi retry dengan backoff
                return response.json().then(errorData => {
                    retryCount++;
                    
                    // Khusus untuk lock error, tunda lebih lama
                    let waitTime = retryTimeout * Math.pow(2, retryCount - 1); // Exponential backoff
                    
                    // Jika ada kode LOCK_EXISTS, beri retryTimeout lebih lama dan tampilkan opsi untuk clean lock
                    if (errorData.code === 'LOCK_EXISTS') {
                        console.log("Lock error terdeteksi, menunggu lebih lama");
                        waitTime = Math.max(waitTime, 8000); // Minimal 8 detik untuk lock error
                        
                        // Tampilkan pesan dengan opsi clean lock
                        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Proses sebelumnya masih berjalan`;
                        
                        // Tambahkan tombol clean lock
                        const cleanLockBtn = document.createElement('button');
                        cleanLockBtn.className = 'btn btn-sm btn-warning ms-2';
                        cleanLockBtn.innerHTML = 'Bersihkan Lock';
                        cleanLockBtn.onclick = forceCleanupLock;
                        
                        // Tambahkan setelah tombol submit
                        submitBtn.parentNode.appendChild(cleanLockBtn);
                        
                        showAlert(`Proses sebelumnya masih berjalan. Harap tunggu beberapa saat atau gunakan tombol "Bersihkan Lock" untuk mengatasi masalah.`, 'warning');
                        loadingIndicator.classList.add('d-none');
                        return null;
                    }
                    
                    function handleLockError(errorData) {
                        retryCount++;
                        
                        // Jika ada kode LOCK_EXISTS, tawarkan untuk membersihkan lock
                        if (errorData.code === 'LOCK_EXISTS') {
                            console.log("Lock error terdeteksi");
                            
                            // Tampilkan modal dengan opsi clean lock
                            showCleanLockModal(errorData.user_id || current_user.id);
                            
                            // Reset submit button
                            resetSubmitButton();
                            return null;
                        }
                        
                        // Standar retry untuk error lain
                        let waitTime = retryTimeout * Math.pow(2, retryCount - 1); // Exponential backoff
                        
                        if (retryCount <= maxRetries) {
                            showAlert(`Server sedang sibuk. Mencoba lagi dalam ${Math.round(waitTime/1000)} detik... (Percobaan ${retryCount}/${maxRetries})`, 'warning');
                            
                            // Update tombol
                            submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Menunggu (${Math.round(waitTime/1000)}s)...`;
                            
                            setTimeout(() => {
                                // Coba lagi setelah backoff
                                submitFormWithRetry();
                            }, waitTime);
                            
                            return null; // Skip processing response
                        } else {
                            // Gagal setelah beberapa kali retry
                            throw new Error('Server sedang sibuk. Silakan coba lagi nanti.');
                        }
                    }
                });
            }
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }
            
            return response.json();
        })
        .then(data => {
            if (!data) return; // Skip if null (during retry)
            
            // Reset flag dan counter
            isSubmitting = false;
            retryCount = 0;
            
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
            
            if (data.error) {
                showAlert('Error: ' + data.error, 'danger');
                resetSubmitButton();
                return;
            }
            
            // Menampilkan informasi sukses sebelum redirect
            showAlert('Analisis selesai! Mengalihkan ke halaman hasil...', 'success');
            
            // Delay redirect untuk memungkinkan pesan dilihat
            setTimeout(() => {
                // Redirect to hasil-analisis page
                window.location.href = '/hasil-analisis';
            }, 1000);
        })
        .catch(error => {
            console.error('Error during form submission:', error);
            
            // Reset flag
            isSubmitting = false;
            
            // Show error message
            loadingIndicator.classList.add('d-none');
            
            if (error.name === 'AbortError') {
                showAlert('Error: Waktu permintaan habis. File mungkin terlalu besar atau server sedang sibuk.', 'danger');
            } else if (error.toString().includes('ChunkedEncodingError')) {
                showAlert('Error: Koneksi terputus. Silakan periksa koneksi internet Anda dan coba lagi.', 'danger');
            } else {
                showAlert('Error: ' + error.message, 'danger');
            }
            
            // Reset submit button
            resetSubmitButton();
        });
    }
    
    // Tambahkan fungsi untuk membersihkan lock melalui UI jika diperlukan
    function forceCleanupLock() {
        fetch('/clean-lock', {
            method: 'GET'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showAlert(data.message, 'success');
                
                // Hapus tombol clean lock jika ada
                const cleanLockBtn = document.querySelector('.btn-warning');
                if (cleanLockBtn) cleanLockBtn.remove();
                
                // Reset submit button setelah delay singkat
                setTimeout(resetSubmitButton, 1000);
            } else {
                showAlert(data.message || 'Gagal membersihkan lock.', 'danger');
            }
        })
        .catch(error => {
            console.error('Error cleaning lock:', error);
            showAlert('Error: ' + error.message, 'danger');
        });
    }
    
    function resetSubmitButton() {
        // Re-enable button with original text
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Mulai Analisis';
        isSubmitting = false;
    }
    
    // Add support for example questions in chatbot.html
    const exampleQuestions = document.querySelectorAll('.example-question');
    if (exampleQuestions.length > 0) {
        exampleQuestions.forEach(question => {
            question.addEventListener('click', function() {
                if (chatbotInput) {
                    chatbotInput.value = this.textContent.trim();
                    if (chatbotSend) {
                        chatbotSend.click();
                    }
                }
            });
        });
    }
});