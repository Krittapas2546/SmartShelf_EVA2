/**
 * ui/notify.js - Notification & Popup Functions
 * จัดการการแจ้งเตือนและ popup ต่างๆ
 */

/**
 * แสดง notification ทั่วไป
 */
function showNotification(message, type = 'info', options = {}) {
    console.log(`📢 ${type.toUpperCase()}: ${message}`);
    
    // ลบ notification เก่าทั้งหมดก่อน (ยกเว้น persistent notifications ถ้าไม่ใช่ persistent notification ใหม่)
    if (!options.persistent) {
        const existingNotifications = document.querySelectorAll('.notification:not(.persistent):not(#persistent-correct-shelf):not([data-persistent="true"])');
        existingNotifications.forEach(notification => {
            notification.remove();
        });
    } else {
        // ถ้าเป็น persistent notification ให้ลบ persistent เก่าก่อน
        const existingPersistent = document.querySelectorAll('.notification.persistent, #persistent-correct-shelf');
        existingPersistent.forEach(notification => {
            notification.remove();
        });
    }
    
    const notification = document.createElement('div');
    notification.className = `notification ${type} ${options.persistent ? 'persistent' : ''}`;
    notification.textContent = message;
    
    // Basic styling with larger text for persistent notifications
    const fontSize = options.persistent ? '18px' : '14px';
    const fontWeight = options.persistent ? '900' : 'bold';
    const padding = options.persistent ? '20px 25px' : '15px 20px';
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: ${padding};
        border-radius: 8px;
        color: white;
        font-weight: ${fontWeight};
        font-size: ${fontSize};
        z-index: 1000;
        opacity: 0;
        transition: all 0.3s ease-in-out;
        transform: translateX(100%);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        max-width: 350px;
        word-wrap: break-word;
    `;
    
    // Colors based on type
    switch (type) {
        case 'success': 
            notification.style.backgroundColor = '#28a745';
            break;
        case 'error': 
            notification.style.backgroundColor = '#dc3545';
            break;
        case 'warning': 
            notification.style.backgroundColor = '#ffc107';
            notification.style.color = '#212529';
            break;
        case 'info': 
            notification.style.backgroundColor = '#17a2b8';
            break;
        default: 
            notification.style.backgroundColor = '#6c757d';
    }
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto-remove only if not persistent
    if (!options.persistent) {
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

/**
 * ล้าง persistent notifications
 */
function clearPersistentNotifications() {
    // ล้าง notification แบบเก่าและแบบใหม่
    const persistentNotifications = document.querySelectorAll('.notification.persistent, #persistent-correct-shelf, [data-persistent="true"]');
    persistentNotifications.forEach(notification => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    });
    console.log('🧹 Cleared persistent notifications');
}

/**
 * แสดง Rich Notification พร้อมรายละเอียด LMS
 */
function showLMSNotification(lmsData, type = 'success') {
    console.log(`📋 LMS Notification:`, lmsData);
    
    // ลบ notification เก่าทั้งหมดก่อน (ยกเว้น persistent notifications)
    const existingNotifications = document.querySelectorAll('.notification:not(.persistent):not(#persistent-correct-shelf)');
    existingNotifications.forEach(notification => {
        notification.remove();
    });
    
    const notification = document.createElement('div');
    notification.className = `notification lms-notification ${type}`;
    
    // สร้าง HTML สำหรับ rich notification
    notification.innerHTML = `
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 16px; margin-right: 8px;">📋</span>
            <strong>ข้อมูลจาก LMS</strong>
        </div>
        <div style="font-size: 14px; line-height: 1.4;">
            <div>• LOT: <strong>${lmsData.lotNo}</strong></div>
            <div>• ชั้นวาง: <strong>${lmsData.correctShelf}</strong></div>
            <div>• ประเภท: <strong>${lmsData.placeFlg === "1" ? "วางของ" : "หยิบของ"}</strong></div>
        </div>
    `;
    
    // Styling
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 20px;
        border-radius: 12px;
        color: white;
        z-index: 1000;
        opacity: 0;
        transition: all 0.3s ease-in-out;
        transform: translateX(100%);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        max-width: 380px;
        min-width: 300px;
        border-left: 4px solid rgba(255,255,255,0.3);
    `;
    
    // Colors based on type
    switch (type) {
        case 'success': 
            notification.style.background = 'linear-gradient(135deg, #28a745, #20c997)';
            break;
        case 'error': 
            notification.style.background = 'linear-gradient(135deg, #dc3545, #e74c3c)';
            break;
        case 'warning': 
            notification.style.background = 'linear-gradient(135deg, #ffc107, #f39c12)';
            notification.style.color = '#212529';
            break;
        case 'info': 
            notification.style.background = 'linear-gradient(135deg, #17a2b8, #3498db)';
            break;
        default: 
            notification.style.background = 'linear-gradient(135deg, #6c757d, #95a5a6)';
    }
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Animate out and remove (longer duration for rich content)
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, 5000); // 5 seconds for rich notification
}

/**
 * แสดง Location Popup สำหรับ LMS
 */
function showLMSLocationPopup(lotNo, location, type = 'warning', duration = 0) {
    // ลบ popup เก่าถ้ามี
    const existingPopup = document.getElementById('lmsLocationPopup');
    if (existingPopup) {
        existingPopup.remove();
    }

    // เพิ่ม CSS animations ถ้ายังไม่มี
    if (!document.getElementById('lmsLocationPopupStyles')) {
        const style = document.createElement('style');
        style.id = 'lmsLocationPopupStyles';
        style.textContent = `
            @keyframes lmsLocationFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @keyframes lmsLocationSlideInDown {
                from { 
                    transform: translateY(-50px) scale(0.9);
                    opacity: 0;
                }
                to { 
                    transform: translateY(0) scale(1);
                    opacity: 1;
                }
            }
            @keyframes lmsLocationPulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
        `;
        document.head.appendChild(style);
    }

    // สร้าง overlay
    const overlay = document.createElement('div');
    overlay.id = 'lmsLocationPopup';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.8);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: lmsLocationFadeIn 0.3s ease-in-out;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
    `;

    // กำหนดสีตาม type
    let backgroundColor, borderColor;
    switch (type) {
        case 'success':
            backgroundColor = 'linear-gradient(135deg, #28a745, #20c997)';
            borderColor = '#20c997';
            break;
        case 'error':
            backgroundColor = 'linear-gradient(135deg, #dc3545, #e74c3c)';
            borderColor = '#e74c3c';
            break;
        case 'info':
            backgroundColor = 'linear-gradient(135deg, #17a2b8, #3498db)';
            borderColor = '#3498db';
            break;
        case 'warning':
        default:
            backgroundColor = 'linear-gradient(135deg, #ffc107, #f39c12)';
            borderColor = '#f39c12';
    }

    // สร้าง popup content
    const popup = document.createElement('div');
    popup.style.cssText = `
        background: ${backgroundColor};
        color: white;
        padding: 40px 50px;
        border-radius: 15px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
        max-width: 500px;
        width: 90%;
        text-align: center;
        position: relative;
        animation: lmsLocationSlideInDown 0.5s ease-out;
        border: 3px solid ${borderColor};
        font-weight: bold;
    `;

    // สร้าง Lot No.
    const lotElement = document.createElement('div');
    lotElement.textContent = `Lot No. ${lotNo}`;
    lotElement.style.cssText = `
        margin: 0 0 30px 0;
        font-size: 28px;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        line-height: 1.2;
    `;

    // สร้าง "GO TO:" label
    const goToLabel = document.createElement('div');
    goToLabel.textContent = 'GO TO:';
    goToLabel.style.cssText = `
        margin: 0 0 15px 0;
        font-size: 20px;
        font-weight: bold;
        opacity: 0.9;
    `;

    // สร้าง location
    const locationElement = document.createElement('div');
    locationElement.textContent = location;
    locationElement.style.cssText = `
        margin: 0 0 35px 0;
        font-size: 32px;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        line-height: 1.2;
        letter-spacing: 1px;
    `;

    // สร้างปุ่ม OK
    const okButton = document.createElement('button');
    okButton.textContent = 'OK';
    okButton.style.cssText = `
        background: rgba(255, 255, 255, 0.9);
        color: ${backgroundColor.includes('gradient') ? '#333' : backgroundColor};
        border: none;
        padding: 12px 40px;
        border-radius: 8px;
        font-size: 18px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        min-width: 120px;
    `;

    // เพิ่ม hover effect สำหรับปุ่ม OK
    okButton.addEventListener('mouseenter', () => {
        okButton.style.background = 'rgba(255, 255, 255, 1)';
        okButton.style.transform = 'translateY(-2px)';
        okButton.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.3)';
    });

    okButton.addEventListener('mouseleave', () => {
        okButton.style.background = 'rgba(255, 255, 255, 0.9)';
        okButton.style.transform = 'translateY(0)';
        okButton.style.boxShadow = '0 4px 15px rgba(0, 0, 0, 0.2)';
    });

    // Close popup function
    const closePopup = () => {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 300);
    };

    // Click event สำหรับปุ่ม OK
    okButton.addEventListener('click', closePopup);

    // ประกอบ popup
    popup.appendChild(lotElement);
    popup.appendChild(goToLabel);
    popup.appendChild(locationElement);
    popup.appendChild(okButton);

    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // Auto hide after duration (ถ้ากำหนด duration > 0)
    if (duration > 0) {
        setTimeout(closePopup, duration);
    }

    // Click overlay to close
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closePopup();
        }
    });

    // ESC to close
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            closePopup();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);

    // Focus ปุ่ม OK เพื่อให้สามารถกด Enter ได้
    setTimeout(() => {
        okButton.focus();
    }, 100);

    // Enter to close
    okButton.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            closePopup();
        }
    });
}

/**
 * แสดง Alert Popup สำหรับ LMS response
 */
function showLMSAlertPopup(title, message, details = null, type = 'warning', duration = 0) {
    // ลบ popup เก่าถ้ามี
    const existingPopup = document.getElementById('lmsAlertPopup');
    if (existingPopup) {
        existingPopup.remove();
    }

    // เพิ่ม CSS animations ถ้ายังไม่มี
    if (!document.getElementById('lmsPopupStyles')) {
        const style = document.createElement('style');
        style.id = 'lmsPopupStyles';
        style.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @keyframes slideInDown {
                from { 
                    transform: translateY(-50px) scale(0.9);
                    opacity: 0;
                }
                to { 
                    transform: translateY(0) scale(1);
                    opacity: 1;
                }
            }
            @keyframes bounce {
                0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                40% { transform: translateY(-10px); }
                60% { transform: translateY(-5px); }
            }
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
        `;
        document.head.appendChild(style);
    }

    // สร้าง overlay
    const overlay = document.createElement('div');
    overlay.id = 'lmsAlertPopup';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.8);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: fadeIn 0.3s ease-in-out;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    `;

    // กำหนดสีตาม type
    let backgroundColor, borderColor, iconColor, icon;
    switch (type) {
        case 'success':
            backgroundColor = 'linear-gradient(135deg, #28a745, #20c997)';
            borderColor = '#20c997';
            iconColor = '#ffffff';
            icon = '✅';
            break;
        case 'error':
            backgroundColor = 'linear-gradient(135deg, #dc3545, #e74c3c)';
            borderColor = '#e74c3c';
            iconColor = '#ffffff';
            icon = '❌';
            break;
        case 'info':
            backgroundColor = 'linear-gradient(135deg, #17a2b8, #3498db)';
            borderColor = '#3498db';
            iconColor = '#ffffff';
            icon = 'ℹ️';
            break;
        case 'warning':
        default:
            backgroundColor = 'linear-gradient(135deg, #ffc107, #f39c12)';
            borderColor = '#f39c12';
            iconColor = '#212529';
            icon = '⚠️';
    }

    // สร้าง popup content
    const popup = document.createElement('div');
    popup.style.cssText = `
        background: ${backgroundColor};
        color: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 25px 80px rgba(0, 0, 0, 0.3);
        max-width: 600px;
        width: 90%;
        text-align: center;
        position: relative;
        animation: slideInDown 0.5s ease-out;
        border: 4px solid ${borderColor};
        ${type === 'error' ? 'animation: slideInDown 0.5s ease-out, pulse 2s infinite;' : ''}
    `;

    // สร้าง icon
    const iconElement = document.createElement('div');
    iconElement.innerHTML = icon;
    iconElement.style.cssText = `
        font-size: 80px;
        margin-bottom: 20px;
        animation: bounce 1s ease-in-out infinite;
        filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));
    `;

    // สร้าง title
    const titleElement = document.createElement('h2');
    titleElement.textContent = title;
    titleElement.style.cssText = `
        margin: 0 0 20px 0;
        font-size: 32px;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        line-height: 1.2;
    `;

    // สร้าง message
    const messageElement = document.createElement('p');
    messageElement.textContent = message;
    messageElement.style.cssText = `
        margin: 0 0 25px 0;
        font-size: 20px;
        line-height: 1.5;
        font-weight: 500;
    `;

    // สร้าง details ถ้ามี
    let detailsElement = null;
    if (details) {
        detailsElement = document.createElement('div');
        detailsElement.textContent = details;
        detailsElement.style.cssText = `
            margin: 0 0 25px 0;
            font-size: 16px;
            opacity: 0.9;
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 8px;
            line-height: 1.4;
        `;
    }

    // Close popup function
    const closePopup = () => {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 300);
    };

    // สร้าง countdown และ progress bar เฉพาะเมื่อ duration > 0
    let countdownElement = null;
    let progressBar = null;
    let progressFill = null;
    let countdownInterval = null;

    if (duration > 0) {
        // Countdown text
        countdownElement = document.createElement('div');
        countdownElement.style.cssText = `
            margin: 20px 0 0 0;
            font-size: 16px;
            opacity: 0.8;
        `;
        
        // Progress bar container
        progressBar = document.createElement('div');
        progressBar.style.cssText = `
            width: 100%;
            height: 4px;
            background: rgba(255,255,255,0.3);
            border-radius: 2px;
            margin: 15px 0 0 0;
            overflow: hidden;
        `;
        
        // Progress fill
        progressFill = document.createElement('div');
        progressFill.style.cssText = `
            width: 100%;
            height: 100%;
            background: rgba(255,255,255,0.8);
            transition: width ${duration}ms linear;
        `;
        progressBar.appendChild(progressFill);
    } else {
        // Click to close message
        const clickMessage = document.createElement('div');
        clickMessage.textContent = 'Click anywhere to close';
        clickMessage.style.cssText = `
            margin: 20px 0 0 0;
            font-size: 14px;
            opacity: 0.7;
        `;
        countdownElement = clickMessage;
    }

    // ประกอบ popup
    popup.appendChild(iconElement);
    popup.appendChild(titleElement);
    popup.appendChild(messageElement);
    if (detailsElement) popup.appendChild(detailsElement);
    if (countdownElement) popup.appendChild(countdownElement);
    if (progressBar) popup.appendChild(progressBar);

    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // เริ่ม countdown และ progress bar เฉพาะเมื่อ duration > 0
    if (duration > 0 && progressFill) {
        let timeLeft = Math.floor(duration / 1000);
        countdownElement.textContent = `Auto-close in ${timeLeft} seconds`;
        
        // เริ่ม progress bar animation
        setTimeout(() => {
            progressFill.style.width = '0%';
        }, 100);
        
        // Countdown timer
        countdownInterval = setInterval(() => {
            timeLeft--;
            countdownElement.textContent = `Auto-close in ${timeLeft} seconds`;
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
            }
        }, 1000);
    }

    // Auto hide after duration (เฉพาะเมื่อ duration > 0)
    if (duration > 0) {
        setTimeout(() => {
            if (countdownInterval) {
                clearInterval(countdownInterval);
            }
            closePopup();
        }, duration);
    }

    // Click to close
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            if (countdownInterval) {
                clearInterval(countdownInterval);
            }
            closePopup();
        }
    });

    // ESC to close
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            if (countdownInterval) {
                clearInterval(countdownInterval);
            }
            closePopup();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

/**
 * แสดง popup ยืนยันการเปลี่ยน job
 */
function showJobConfirmationPopup(currentJob, newJob, scannedLot, onYesCallback, onNoCallback) {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.6);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: fadeIn 0.3s ease-in-out;
    `;

    const popup = document.createElement('div');
    popup.style.cssText = `
        background: linear-gradient(135deg, #17a2b8, #3498db);
        border: none;
        border-radius: 20px;
        padding: 40px;
        max-width: 650px;
        width: 90%;
        text-align: center;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        animation: slideIn 0.4s ease-in-out;
        position: relative;
        overflow: hidden;
    `;

    popup.innerHTML = `
        <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
        <div style="font-size: 28px; font-weight: bold; color: white; margin-bottom: 15px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
            Job Confirmation Required
        </div>
        <div style="font-size: 20px; color: white; margin-bottom: 25px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
            Current job: <strong>${currentJob.lot_no}</strong><br>
            Scanned lot: <strong>${scannedLot}</strong>
        </div>
        <div style="font-size: 18px; color: white; margin-bottom: 30px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
            Is job <strong>${currentJob.lot_no}</strong> completed?
        </div>
        <div style="display: flex; gap: 20px; justify-content: center; margin-top: 30px;">
            <button id="confirmYes" style="
                padding: 15px 30px;
                font-size: 18px;
                font-weight: bold;
                background: #28a745;
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                transition: all 0.2s;
            ">✅ Yes, Complete</button>
            <button id="confirmNo" style="
                padding: 15px 30px;
                font-size: 18px;
                font-weight: bold;
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                transition: all 0.2s;
            ">❌ No, Continue</button>
        </div>
    `;

    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // เพิ่ม CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideIn {
            from { transform: scale(0.7) translateY(-30px); opacity: 0; }
            to { transform: scale(1) translateY(0); opacity: 1; }
        }
        @keyframes fadeOut {
            from { opacity: 1; transform: scale(1); }
            to { opacity: 0; transform: scale(0.8); }
        }
    `;
    document.head.appendChild(style);

    const closePopup = () => {
        overlay.style.animation = 'fadeOut 0.3s ease-in-out';
        setTimeout(() => {
            overlay.remove();
            style.remove();
        }, 300);
    };

    // จัดการเมื่อกดปุ่ม Yes
    const yesBtn = popup.querySelector('#confirmYes');
    yesBtn.addEventListener('click', () => {
        closePopup();
        if (onYesCallback) onYesCallback();
    });

    // จัดการเมื่อกดปุ่ม No
    const noBtn = popup.querySelector('#confirmNo');
    noBtn.addEventListener('click', () => {
        closePopup();
        if (onNoCallback) onNoCallback();
    });

    // เพิ่ม hover effects
    yesBtn.addEventListener('mouseenter', () => {
        yesBtn.style.background = '#218838';
        yesBtn.style.transform = 'translateY(-2px)';
    });
    yesBtn.addEventListener('mouseleave', () => {
        yesBtn.style.background = '#28a745';
        yesBtn.style.transform = 'translateY(0)';
    });

    noBtn.addEventListener('mouseenter', () => {
        noBtn.style.background = '#c82333';
        noBtn.style.transform = 'translateY(-2px)';
    });
    noBtn.addEventListener('mouseleave', () => {
        noBtn.style.background = '#dc3545';
        noBtn.style.transform = 'translateY(0)';
    });

    // กด Escape เพื่อปิด (เหมือนกด No)
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            closePopup();
            if (onNoCallback) onNoCallback();
        }
    };
    document.addEventListener('keydown', escapeHandler);
}

/**
 * แสดง popup เตือนรูปแบบ LOT number
 */
function showLotFormatWarningPopup(invalidLotNo = '') {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.6);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: fadeIn 0.3s ease-in-out;
    `;

    const popup = document.createElement('div');
    popup.style.cssText = `
        background: linear-gradient(135deg, #FF8C00, #FFA500, #FFD700);
        border: none;
        border-radius: 20px;
        padding: 40px;
        max-width: 600px;
        width: 90%;
        text-align: center;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        animation: slideIn 0.4s ease-in-out;
        position: relative;
        overflow: hidden;
    `;

    // สร้าง progress bar
    const progressBar = document.createElement('div');
    progressBar.style.cssText = `
        position: absolute;
        bottom: 0;
        left: 0;
        height: 4px;
        background-color: rgba(255,255,255,0.8);
        width: 100%;
        transform-origin: left;
        animation: progressBarAnimation 3s linear forwards;
    `;

    // แสดงข้อความแตกต่างกันตาม LOT ที่ป้อน
    const displayLot = invalidLotNo || 'ABC123DEF.01';
    const titleText = invalidLotNo ? 'Invalid LOT Format' : 'LOT Not in Job Queue';
    const messageText = invalidLotNo 
        ? 'Please scan only Lot No. data (Format: xxxxxxxxx.xx)' 
        : `LOT ${displayLot} not found in current job queue`;

    popup.innerHTML = `
        <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
        <div style="font-size: 32px; font-weight: bold; color: white; margin-bottom: 15px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
            ${titleText}
        </div>
        <div style="font-size: 22px; color: white; margin-bottom: 25px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
            ${messageText}
        </div>
        <div style="font-size: 18px; color: white; margin-bottom: 30px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
            This window will close in <span id="countdown">3</span> seconds
        </div>
    `;

    popup.appendChild(progressBar);
    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // เพิ่ม CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideIn {
            from { transform: scale(0.7) translateY(-30px); opacity: 0; }
            to { transform: scale(1) translateY(0); opacity: 1; }
        }
        @keyframes progressBarAnimation {
            from { transform: scaleX(1); }
            to { transform: scaleX(0); }
        }
        @keyframes fadeOut {
            from { opacity: 1; transform: scale(1); }
            to { opacity: 0; transform: scale(0.8); }
        }
    `;
    document.head.appendChild(style);

    // Countdown และ auto-close
    let countdown = 3;
    const countdownElement = popup.querySelector('#countdown');
    
    const closePopup = () => {
        overlay.style.animation = 'fadeOut 0.3s ease-in-out';
        setTimeout(() => {
            overlay.remove();
            style.remove();
        }, 300);
    };

    // เริ่ม countdown
    const countdownInterval = setInterval(() => {
        countdown--;
        if (countdownElement) {
            countdownElement.textContent = countdown;
        }
        if (countdown <= 0) {
            clearInterval(countdownInterval);
            closePopup();
        }
    }, 1000);

    // Click เพื่อปิดก่อนเวลา
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            clearInterval(countdownInterval);
            closePopup();
        }
    });

    // กด Escape เพื่อปิด
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            clearInterval(countdownInterval);
            closePopup();
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
}

/**
 * Export functions for module usage
 */
if (typeof window !== 'undefined') {
    window.ShelfNotifications = {
        showNotification,
        clearPersistentNotifications,
        showLMSNotification,
        showLMSLocationPopup,
        showLMSAlertPopup,
        showJobConfirmationPopup,
        showLotFormatWarningPopup
    };
}