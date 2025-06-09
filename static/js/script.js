document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，脚本开始执行！');
    
    // 获取DOM元素
    const parseButton = document.getElementById('parseButton');
    const youtubeUrlInput = document.getElementById('youtubeUrl');
    const messageArea = document.getElementById('messageArea');
    const videoInfoDiv = document.getElementById('video-info-section');
    const downloadButton = document.getElementById('downloadButton');
    const downloadProgressContainer = document.getElementById('progress-section');
    
    // 视频信息元素
    const videoThumbnail = document.getElementById('videoThumbnail');
    const videoTitle = document.getElementById('videoTitle');
    const videoDescription = document.getElementById('videoDescription');
    const videoUploadDate = document.getElementById('videoUploadDate');
    // const videoFileSize = document.getElementById('videoFileSize');

    // 检查按钮是否存在
    if (!parseButton) {
        console.error('解析按钮未找到');
        return;
    }

    // 添加解析按钮点击事件
    parseButton.addEventListener('click', function() {
        console.log('解析按钮被点击');
        
        // 获取URL
        const url = youtubeUrlInput.value.trim();
        if (!url) {
            showMessage('请输入YouTube视频URL！', 'danger');
            return;
        }

        // 显示正在解析的消息
        showMessage('正在解析视频，请稍候...', 'info', false);
        videoInfoDiv.style.display = 'none'; // 解析前隐藏旧信息
        downloadButton.style.display = 'none';

        // 发送请求
        fetch('/api/parse_video', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        })
        .then(response => response.json())
        .then(data => {
            console.log('后端返回的数据:', data);
            if (data.error) {
                showMessage(`解析失败: ${data.error}`, 'danger');
            } else {
                // 更新视频信息
                videoThumbnail.src = data.thumbnail_url || '';
                videoTitle.textContent = data.title || 'N/A';
                videoDescription.textContent = data.description || 'N/A';
                videoUploadDate.textContent = data.upload_date || 'N/A';
                // videoFileSize.textContent = data.file_size_approx || 'N/A';
                
                // 显示视频信息和下载按钮
                videoInfoDiv.style.display = 'block';
                downloadButton.style.display = 'block';
                downloadButton.dataset.videoId = data.video_id || url;

                showMessage('视频信息解析成功！', 'success');
            }
        })
        .catch(error => {
            console.error('解析请求失败:', error);
            showMessage('解析请求失败，请检查网络或稍后再试。', 'danger');
        });
    });

    // 下载按钮的逻辑
    if (downloadButton) {
        downloadButton.addEventListener('click', async function() {
            const videoIdentifier = this.dataset.videoId;
            if (!videoIdentifier) {
                showMessage('无法获取视频标识进行下载。', 'warning');
                return;
            }

            // 显示下载进度容器
            downloadProgressContainer.style.display = 'block';
            const progressBar = document.getElementById('progressBar');
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            
            // 显示下载中消息
            showMessage('开始下载视频...', 'info', false);

            try {
                // 发起下载请求
                const response = await fetch(`/api/download_video?url=${encodeURIComponent(videoIdentifier)}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });

                if (!response.ok) {
                    throw new Error('下载请求失败');
                }

                // 创建下载链接
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'video.mp4'; // 默认下载名，实际会从后端获取
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                // 记录下载历史
                const historyArea = document.getElementById('historyArea');
                const historyList = document.getElementById('historyList');
                const title = document.getElementById('videoTitle').textContent;
                const date = new Date().toLocaleString();
                
                const historyItem = document.createElement('li');
                historyItem.className = 'list-group-item';
                historyItem.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${title}</h6>
                            <small class="text-muted">${date}</small>
                        </div>
                        <button class="btn btn-sm btn-success">重新下载</button>
                    </div>
                `;
                historyList.insertBefore(historyItem, historyList.firstChild);
                historyArea.style.display = 'block';

                showMessage('视频下载成功！', 'success');
            } catch (error) {
                console.error('下载失败:', error);
                showMessage('下载失败，请稍后再试。', 'danger');
            } finally {
                // 隐藏下载进度容器
                downloadProgressContainer.style.display = 'none';
            }
        });
    }

    // 显示消息的辅助函数
    function showMessage(message, type = 'info', autoDismiss = true) {
        console.log('显示消息:', message);
        messageArea.innerHTML = `<div class="alert alert-${type}" role="alert">${message}</div>`;
        if (autoDismiss) {
            setTimeout(() => {
                messageArea.innerHTML = '';
            }, 5000);
        }
    }
});