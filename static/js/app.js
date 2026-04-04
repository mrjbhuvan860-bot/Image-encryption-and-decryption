/**
 * CipherVault — Frontend Interactions
 *
 * Handles:
 * - Mobile navbar toggle
 * - Drag-and-drop file upload with preview
 * - Mode selector radio toggle styling
 * - Form submission loading states
 * - Toast auto-dismiss
 */

document.addEventListener('DOMContentLoaded', () => {
    initNavbar();
    initDropzones();
    initModeSelector();
    initFormLoaders();
    initToasts();
});

/* ── Navbar Toggle ──────────────────────────────────────── */
function initNavbar() {
    const toggle = document.getElementById('nav-toggle');
    const links = document.getElementById('nav-links');

    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('open');
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!toggle.contains(e.target) && !links.contains(e.target)) {
                links.classList.remove('open');
            }
        });
    }
}

/* ── Dropzone File Upload ───────────────────────────────── */
function initDropzones() {
    const dropzones = document.querySelectorAll('.dropzone');

    dropzones.forEach(dropzone => {
        const inputId = dropzone.dataset.input;
        const fileInput = document.getElementById(inputId);
        if (!fileInput) return;

        const content = dropzone.querySelector('.dropzone-content');
        const preview = dropzone.querySelector('.dropzone-preview');
        const previewImg = dropzone.querySelector('.dropzone-preview img');
        const previewIcon = dropzone.querySelector('.file-icon-preview');
        const filenameEl = dropzone.querySelector('.dropzone-filename');
        const clearBtn = dropzone.querySelector('.dropzone-clear');

        // Drag events
        ['dragenter', 'dragover'].forEach(evt => {
            dropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('drag-over');
            });
        });

        ['dragleave', 'drop'].forEach(evt => {
            dropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('drag-over');
            });
        });

        // Handle drop
        dropzone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                showPreview(files[0]);
            }
        });

        // Handle file input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                showPreview(e.target.files[0]);
            }
        });

        // Clear button
        if (clearBtn) {
            clearBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                fileInput.value = '';
                hidePreview();
            });
        }

        function showPreview(file) {
            if (!content || !preview) return;

            content.style.display = 'none';
            preview.style.display = 'flex';

            if (filenameEl) {
                filenameEl.textContent = file.name;
            }

            // Show image preview for image files
            if (file.type.startsWith('image/') && previewImg) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImg.src = e.target.result;
                    previewImg.style.display = 'block';
                    if (previewIcon) previewIcon.style.display = 'none';
                };
                reader.readAsDataURL(file);
            } else {
                // Non-image file (e.g., .enc)
                if (previewImg) previewImg.style.display = 'none';
                if (previewIcon) previewIcon.style.display = 'block';
            }
        }

        function hidePreview() {
            if (content) content.style.display = 'flex';
            if (preview) preview.style.display = 'none';
            if (previewImg) {
                previewImg.src = '';
                previewImg.style.display = 'none';
            }
        }
    });
}

/* ── Mode Selector ──────────────────────────────────────── */
function initModeSelector() {
    const modeOptions = document.querySelectorAll('.mode-option');

    modeOptions.forEach(option => {
        const radio = option.querySelector('input[type="radio"]');
        if (!radio) return;

        radio.addEventListener('change', () => {
            // Remove active from all
            modeOptions.forEach(opt => opt.classList.remove('mode-option-active'));
            // Add active to selected
            if (radio.checked) {
                option.classList.add('mode-option-active');
            }
        });
    });
}

/* ── Form Loading States ────────────────────────────────── */
function initFormLoaders() {
    const forms = document.querySelectorAll('.tool-form, .auth-form');

    forms.forEach(form => {
        form.addEventListener('submit', () => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (!submitBtn) return;

            const btnText = submitBtn.querySelector('.btn-text');
            const btnLoader = submitBtn.querySelector('.btn-loader');

            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.7';

            if (btnText) btnText.textContent = 'Processing...';
            if (btnLoader) btnLoader.style.display = 'inline-block';
        });
    });
}

/* ── Toast Auto-Dismiss ─────────────────────────────────── */
function initToasts() {
    const toasts = document.querySelectorAll('.toast');

    toasts.forEach((toast, index) => {
        // Stagger animations
        toast.style.animationDelay = `${index * 0.1}s`;

        // Auto-dismiss after 6 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                toast.remove();
                // Clean up container if empty
                const container = document.getElementById('toast-container');
                if (container && container.children.length === 0) {
                    container.remove();
                }
            }, 300);
        }, 6000 + index * 500);
    });
}

// Add slideOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        to {
            opacity: 0;
            transform: translateX(40px);
        }
    }
`;
document.head.appendChild(style);
