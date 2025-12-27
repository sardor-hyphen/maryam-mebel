// Authentication Modal System
class AuthModal {
    constructor() {
        this.currentModal = null;
        this.init();
    }

    init() {
        this.createModalHTML();
        this.bindEvents();
    }

    createModalHTML() {
        const modalHTML = `
        <!-- Auth Modal -->
        <div id="authModal" class="auth-modal" style="display: none;">
            <div class="auth-modal-overlay" onclick="authModal.close()"></div>
            <div class="auth-modal-container">
                <button class="auth-modal-close" onclick="authModal.close()">&times;</button>
                
                <!-- Login Form -->
                <div id="loginForm" class="auth-form active">
                    <div class="auth-header">
                        <img src="/static/logo.png" alt="MARYAM MEBEL" class="auth-logo">
                        <h2 class="auth-title">Kirish</h2>
                        <p class="auth-subtitle">Hisobingizga kirib, davom eting</p>
                    </div>
                    
                    <form onsubmit="authModal.handleLogin(event)">
                        <div class="form-group">
                            <label>Foydalanuvchi nomi yoki Email</label>
                            <input type="text" name="username" required>
                        </div>
                        <div class="form-group">
                            <label>Parol</label>
                            <input type="password" name="password" required>
                        </div>
                        <div class="form-options">
                            <label class="remember-me">
                                <input type="checkbox" name="remember"> Meni eslab qol
                            </label>
                            <a href="#" onclick="authModal.showForgotPassword()">Parolni unutdingizmi?</a>
                        </div>
                        <button type="submit" class="auth-btn">Kirish</button>
                    </form>
                    
                    <div class="auth-divider">
                        <span>yoki</span>
                    </div>
                    
                    <p class="auth-switch">
                        Hisobingiz yo'qmi? 
                        <a href="#" onclick="authModal.switchToSignup()">Ro'yxatdan o'ting</a>
                    </p>
                </div>

                <!-- Signup Form -->
                <div id="signupForm" class="auth-form">
                    <div class="auth-header">
                        <img src="/static/logo.png" alt="MARYAM MEBEL" class="auth-logo">
                        <h2 class="auth-title">Ro'yxatdan o'tish</h2>
                        <p class="auth-subtitle">Yangi hisob yarating</p>
                    </div>
                    
                    <form onsubmit="authModal.handleSignup(event)">
                        <div class="form-row">
                            <div class="form-group">
                                <label>Ism</label>
                                <input type="text" name="first_name" required>
                            </div>
                            <div class="form-group">
                                <label>Familiya</label>
                                <input type="text" name="last_name" required>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Foydalanuvchi nomi</label>
                            <input type="text" name="username" required>
                            <div class="validation-feedback" id="usernameValidation"></div>
                        </div>
                        <div class="form-group">
                            <label>Email</label>
                            <input type="email" name="email" required>
                            <div class="validation-feedback" id="emailValidation"></div>
                        </div>
                        <div class="form-group">
                            <label>Telegram Username (ixtiyoriy)</label>
                            <input type="text" name="telegram_username" placeholder="@username">
                        </div>
                        <div class="form-group">
                            <label>Parol</label>
                            <input type="password" name="password" required>
                            <div class="password-strength" id="passwordStrength"></div>
                        </div>
                        <div class="form-group">
                            <label>Parolni tasdiqlang</label>
                            <input type="password" name="confirm_password" required>
                        </div>
                        <div class="form-group">
                            <label class="checkbox-label">
                                <input type="checkbox" name="terms" required>
                                Men <a href="#">shartlar</a>ga roziman
                            </label>
                        </div>
                        <button type="submit" class="auth-btn" disabled id="signupSubmit">Ro'yxatdan o'tish</button>
                    </form>
                    
                    <div class="auth-divider">
                        <span>yoki</span>
                    </div>
                    
                    <p class="auth-switch">
                        Hisobingiz bormi? 
                        <a href="#" onclick="authModal.switchToLogin()">Kirish</a>
                    </p>
                </div>

                <!-- Forgot Password Form -->
                <div id="forgotPasswordForm" class="auth-form">
                    <div class="auth-header">
                        <img src="/static/logo.png" alt="MARYAM MEBEL" class="auth-logo">
                        <h2 class="auth-title">Parolni tiklash</h2>
                        <p class="auth-subtitle">Telegram username yoki email kiriting</p>
                    </div>
                    
                    <form onsubmit="authModal.handleForgotPassword(event)">
                        <div class="form-group">
                            <label>Telegram Username yoki Email</label>
                            <input type="text" name="identifier" placeholder="@username yoki email@example.com" required>
                        </div>
                        <button type="submit" class="auth-btn">Kod yuborish</button>
                    </form>
                    
                    <div class="auth-divider">
                        <span>yoki</span>
                    </div>
                    
                    <p class="auth-switch">
                        <a href="#" onclick="authModal.switchToLogin()">Kirishga qaytish</a>
                    </p>
                </div>
            </div>
        </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    bindEvents() {
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.currentModal) {
                this.close();
            }
        });

        // Close modal when clicking outside
        document.addEventListener('click', (e) => {
            const modal = document.getElementById('authModal');
            if (modal && modal.style.display === 'flex' && e.target === modal) {
                this.close();
            }
        });

        // Real-time validation for signup
        this.setupSignupValidation();
    }

    setupSignupValidation() {
        const signupForm = document.querySelector('#signupForm form');
        if (!signupForm) return;

        const usernameInput = signupForm.querySelector('input[name="username"]');
        const emailInput = signupForm.querySelector('input[name="email"]');
        const passwordInput = signupForm.querySelector('input[name="password"]');
        const confirmPasswordInput = signupForm.querySelector('input[name="confirm_password"]');
        const termsCheckbox = signupForm.querySelector('input[name="terms"]');
        const submitBtn = document.getElementById('signupSubmit');

        let validationState = {
            username: false,
            email: false,
            password: false,
            confirmPassword: false,
            terms: false
        };

        // Debounce function
        const debounce = (func, wait) => {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        };

        // Username validation
        usernameInput.addEventListener('input', debounce(async (e) => {
            const username = e.target.value.trim();
            const validation = document.getElementById('usernameValidation');
            
            if (username.length < 3) {
                validation.textContent = 'Kamida 3 ta belgi kerak';
                validation.className = 'validation-feedback error';
                validationState.username = false;
            } else {
                try {
                    const response = await fetch('/auth/check-availability', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ field: 'username', value: username })
                    });
                    const data = await response.json();
                    
                    if (data.available) {
                        validation.textContent = 'Username mavjud ✓';
                        validation.className = 'validation-feedback success';
                        validationState.username = true;
                    } else {
                        validation.textContent = data.message;
                        validation.className = 'validation-feedback error';
                        validationState.username = false;
                    }
                } catch (error) {
                    validation.textContent = '';
                    validationState.username = false;
                }
            }
            this.updateSubmitButton(validationState, submitBtn);
        }, 500));

        // Email validation
        emailInput.addEventListener('input', debounce(async (e) => {
            const email = e.target.value.trim();
            const validation = document.getElementById('emailValidation');
            
            if (!email.includes('@')) {
                validation.textContent = 'Email formatini tekshiring';
                validation.className = 'validation-feedback error';
                validationState.email = false;
            } else {
                try {
                    const response = await fetch('/auth/check-availability', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ field: 'email', value: email })
                    });
                    const data = await response.json();
                    
                    if (data.available) {
                        validation.textContent = 'Email mavjud ✓';
                        validation.className = 'validation-feedback success';
                        validationState.email = true;
                    } else {
                        validation.textContent = data.message;
                        validation.className = 'validation-feedback error';
                        validationState.email = false;
                    }
                } catch (error) {
                    validation.textContent = '';
                    validationState.email = false;
                }
            }
            this.updateSubmitButton(validationState, submitBtn);
        }, 500));

        // Password strength
        passwordInput.addEventListener('input', (e) => {
            const password = e.target.value;
            const strength = document.getElementById('passwordStrength');
            
            let score = 0;
            if (password.length >= 8) score++;
            if (/[a-z]/.test(password)) score++;
            if (/[A-Z]/.test(password)) score++;
            if (/[0-9]/.test(password)) score++;
            if (/[^A-Za-z0-9]/.test(password)) score++;

            if (password.length === 0) {
                strength.textContent = '';
                validationState.password = false;
            } else if (score < 3) {
                strength.textContent = 'Zaif parol';
                strength.className = 'password-strength weak';
                validationState.password = false;
            } else if (score < 4) {
                strength.textContent = 'O\'rtacha parol';
                strength.className = 'password-strength medium';
                validationState.password = true;
            } else {
                strength.textContent = 'Kuchli parol';
                strength.className = 'password-strength strong';
                validationState.password = true;
            }
            this.updateSubmitButton(validationState, submitBtn);
        });

        // Confirm password
        confirmPasswordInput.addEventListener('input', (e) => {
            const password = passwordInput.value;
            const confirmPassword = e.target.value;
            
            validationState.confirmPassword = password === confirmPassword && password.length > 0;
            this.updateSubmitButton(validationState, submitBtn);
        });

        // Terms checkbox
        termsCheckbox.addEventListener('change', (e) => {
            validationState.terms = e.target.checked;
            this.updateSubmitButton(validationState, submitBtn);
        });
    }

    updateSubmitButton(validationState, submitBtn) {
        const allValid = Object.values(validationState).every(state => state === true);
        submitBtn.disabled = !allValid;
    }

    show(type = 'login') {
        const modal = document.getElementById('authModal');
        modal.style.display = 'flex';
        // Add class to body to prevent scrolling
        document.body.classList.add('auth-modal-open');
        this.currentModal = type;
        
        // Trigger animation
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
    }

    close() {
        const modal = document.getElementById('authModal');
        modal.style.display = 'none';
        // Remove class from body to re-enable scrolling
        document.body.classList.remove('auth-modal-open');
        this.currentModal = null;
    }

    switchTo(type) {
        // Hide all forms
        const forms = document.querySelectorAll('.auth-form');
        forms.forEach(form => form.classList.remove('active'));
        
        // Show selected form
        const targetForm = document.getElementById(type + 'Form');
        if (targetForm) {
            targetForm.classList.add('active');
            this.currentModal = type;
        }
    }

    switchToLogin() { this.switchTo('login'); }
    switchToSignup() { this.switchTo('signup'); }
    showForgotPassword() { this.switchTo('forgotPassword'); }

    async handleLogin(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // Close the auth modal first
                this.close();
                // Check if we're on the collection page
                if (window.location.pathname === '/collection') {
                    // Reload the page to remove the auth overlay
                    window.location.reload();
                } else {
                    // Redirect to collection page after successful login
                    window.location.href = '/collection';
                }
            } else {
                const data = await response.text();
                // Handle error - you might want to show error message
                alert('Login failed. Please check your credentials.');
            }
        } catch (error) {
            alert('Network error. Please try again.');
        }
    }

    async handleSignup(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        
        try {
            const response = await fetch('/auth/signup', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // Close the auth modal first
                this.close();
                // Show success message
                alert('Registration successful! Please login.');
                // Switch to login form
                this.switchToLogin();
            } else {
                const data = await response.text();
                alert('Registration failed. Please check your information.');
            }
        } catch (error) {
            alert('Network error. Please try again.');
        }
    }

    async handleForgotPassword(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        
        try {
            const response = await fetch('/auth/forgot-password', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                alert('Recovery code sent! Check your Telegram.');
                this.close();
                // Redirect to verification page
                window.location.href = '/auth/verify-code';
            } else {
                alert('Failed to send recovery code. Please check your information.');
            }
        } catch (error) {
            alert('Network error. Please try again.');
        }
    }
}

// Initialize auth modal when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.authModal = new AuthModal();
});

// Helper function to show auth modal when user needs to login
function requireAuth(action = 'login') {
    if (window.authModal) {
        window.authModal.show(action);
    }
    return false; // Prevent default action
}

