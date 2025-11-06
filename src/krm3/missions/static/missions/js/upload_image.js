document.addEventListener('DOMContentLoaded', function() {
    let selectedFile = null;
    let stream = null;
    let isFromCamera = false;

    const fileInput = document.getElementById('fileInput');
    const fileSelectBtn = document.getElementById('fileSelectBtn');
    const cameraBtn = document.getElementById('cameraBtn');
    const captureBtn = document.getElementById('captureBtn');
    const video = document.getElementById('video');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const submitBtn = document.getElementById('submitBtn');
    const removeBtn = document.getElementById('removeBtn');
    const recaptureBtn = document.getElementById('recaptureBtn');
    const message = document.getElementById('message');
    const spinner = document.getElementById('spinner');
    const otpValue = document.querySelector('meta[name="otp"]').getAttribute('content');

    // File selection handler
    fileSelectBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            selectedFile = file;
            isFromCamera = false;
            displayPreview(file);
            stopCamera();
        }
    });

    // Camera handler
    cameraBtn.addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' }
            });
            video.srcObject = stream;
            video.style.display = 'block';
            captureBtn.style.display = 'block';
            imagePreview.style.display = 'none';
            submitBtn.style.display = 'none';
        } catch (err) {
            showMessage('Error accessing camera: ' + err.message, 'error');
        }
    });

    // Capture photo from camera
    captureBtn.addEventListener('click', () => {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        canvas.toBlob((blob) => {
            selectedFile = new File([blob], 'camera-photo.png', { type: 'image/png' });
            isFromCamera = true;
            displayPreview(selectedFile);
            stopCamera();
        }, 'image/png');
    });

    // Display image preview
    function displayPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            imagePreview.style.display = 'block';
            submitBtn.style.display = 'block';

            // Show recapture button only if image is from camera
            if (isFromCamera) {
                recaptureBtn.style.display = 'flex';
            } else {
                recaptureBtn.style.display = 'none';
            }
        };
        reader.readAsDataURL(file);
    }

    // Stop camera stream
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            video.style.display = 'none';
            captureBtn.style.display = 'none';
        }
    }

    // Remove image handler
    removeBtn.addEventListener('click', () => {
        selectedFile = null;
        isFromCamera = false;
        previewImg.src = '';
        imagePreview.style.display = 'none';
        submitBtn.style.display = 'none';
        recaptureBtn.style.display = 'none';
        fileInput.value = '';
        message.style.display = 'none';
    });

    // Toggle all buttons enabled/disabled state
    function toggleAllButtons(disabled) {
        fileSelectBtn.disabled = disabled;
        cameraBtn.disabled = disabled;
        captureBtn.disabled = disabled;
        submitBtn.disabled = disabled;
        removeBtn.disabled = disabled;
    }

    // Submit image via PATCH
    submitBtn.addEventListener('click', async () => {
        if (!selectedFile) {
            showMessage('No image selected', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('otp', otpValue);

        try {
            // Disable all buttons and show spinner
            toggleAllButtons(true);
            submitBtn.textContent = 'Uploading...';
            spinner.style.display = 'block';
            message.style.display = 'none';

            const response = await fetch(window.location.pathname, {
                method: 'PATCH',
                body: formData
            });

            // Hide spinner
            spinner.style.display = 'none';

            if (response.ok || response.status === 204) {
                showMessage('Image uploaded successfully!', 'success');
                submitBtn.textContent = 'Submitted';
            } else {
                showMessage('Upload error', 'error');
                toggleAllButtons(false);
                submitBtn.textContent = 'Submit Image';
            }
        } catch (err) {
            // Hide spinner
            spinner.style.display = 'none';
            showMessage('Upload error', 'error');
            toggleAllButtons(false);
            submitBtn.textContent = 'Submit Image';
        }
    });

    // Show message
    function showMessage(text, type) {
        message.textContent = text;
        message.className = 'upload-image-message ' + type;
        message.style.display = 'block';
    }

    // Recapture image handler
    recaptureBtn.addEventListener('click', async () => {
        // Clear current preview
        selectedFile = null;
        previewImg.src = '';
        imagePreview.style.display = 'none';
        submitBtn.style.display = 'none';
        recaptureBtn.style.display = 'none';
        message.style.display = 'none';

        // Restart camera
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' }
            });
            video.srcObject = stream;
            video.style.display = 'block';
            captureBtn.style.display = 'block';
        } catch (err) {
            showMessage('Error accessing camera: ' + err.message, 'error');
        }
    });
});
