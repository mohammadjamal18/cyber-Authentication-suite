from flask import Flask, request, render_template, redirect, session, url_for
import time
import hmac
import secrets
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# التوكن الخاص بالمختبر الثالث للاستعادة الآمنة
s = URLSafeTimedSerializer('my-super-secret-salt-key')

# قواعد البيانات الوهمية للمختبرات
users_db_lab1 = {"soso": "newnew#123", "carlos": "secret123", "administrator": "admin123"}
users_db_lab2 = {"carlos": "montoya","sara":"test_pass"}
users_db_lab3 = {"wiener": "old_pass", "carlos": "old_pass"}
users_db_lab4 = {"hana": "12345678", "wiener": "peter"}
users_db_lab5 = {"sami": "super_secret_password_123", "wiener": "peter"}
users_db_lab6 = {"wiener": "peter", "carlos": "ranger"}

# تتبع محاولات الفشل للمختبر السادس
failed_attempts_ip = {}
account_failed_attempts = {}
BLOCK_TIME = 60

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/my-account')
def my_account():
    # إذا لم يكتمل تسجيل الدخول نهائياً (لا يوجد user)
    if 'user' not in session:
        # إذا كان في مرحلة انتظار التحقق الثنائي، وجهه لصفحة الرمز حصراً
        if 'pending_user' in session:
            return redirect('/lab2/verify-secure')
        # وإلا قم بطرده للصفحة الرئيسية
        return redirect('/')
    
    user = session.get('user')
    return render_template('my_account.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ==================== المختبر الأول ====================
@app.route('/lab1', methods=['GET'])
def lab1_home():
    return render_template('labs/lab1.html', mode='vulnerable')

@app.route('/lab1/login-vulnerable', methods=['POST'])
def lab1_login_vulnerable():
    username = request.form.get('username')
    password = request.form.get('password')
    if username not in users_db_lab1:
        return "Invalid username", 200
    if users_db_lab1[username] != password:
        return "Incorrect password", 200
    session['user'] = username
    return redirect('/my-account')

@app.route('/lab1/login-secure', methods=['POST'])
def lab1_login_secure():
    username = request.form.get('username')
    password = request.form.get('password')
    generic_error = "Invalid username or password"
    user_exists = username in users_db_lab1
    password_correct = user_exists and (users_db_lab1[username] == password)
    if not password_correct:
        time.sleep(0.5)
        return generic_error, 200
    session['user'] = username
    return redirect('/my-account')


# ==================== المختبر الثاني ====================
@app.route('/lab2', methods=['GET'])
def lab2_home():
    return render_template('labs/lab2.html')

@app.route('/lab2/login-vulnerable', methods=['POST'])
def lab2_login_vulnerable():
    username = request.form.get('username')
    password = request.form.get('password')
    if users_db_lab2.get(username) == password:
        # الثغرة: منح الجلسة والاعتماد عليها مسبقاً رغم وجود خطوة ثانية شكلية
        session['user'] = username  
        return redirect('/lab2/verify-vulnerable') # توجيه لصفحة إدخال الرمز الشكلية
    return "Invalid credentials", 401

@app.route('/lab2/login-secure', methods=['POST'])
def lab2_login_secure():
    username = request.form.get('username')
    password = request.form.get('password')
    if users_db_lab2.get(username) == password:
        session['pending_user'] = username
        return redirect('/lab2/verify-secure')
    return "Invalid credentials", 401

@app.route('/lab2/verify-vulnerable', methods=['GET', 'POST'])
def lab2_verify_vulnerable():
    if request.method == 'POST':
        code = request.form.get('code')
        
        # وضعت شرط التحقق كما طلبت، لكن الثغرة الحقيقية تكمن في أن الجلسة منحت مسبقاً
        if code == "123456":
            return redirect('/my-account')
        
        return "Invalid 2FA code", 403   
    return render_template('labs/lab2_verify.html')

@app.route('/lab2/verify-secure', methods=['GET', 'POST'])
def lab2_verify_secure():
    if request.method == 'POST':
        code = request.form.get('code')
        if code == "123456" and 'pending_user' in session:
            session['user'] = session.pop('pending_user')
            session['2fa_verified'] = True
            return redirect('/my-account')
        return "Invalid 2FA code", 403
    return render_template('labs/lab2_verify.html')


# ==================== المختبر الثالث ====================
@app.route('/lab3', methods=['GET'])
def lab3_home():
    return render_template('labs/lab3.html')

@app.route('/lab3/forgot-vulnerable', methods=['POST'])
def lab3_forgot_vulnerable():
    username = request.form.get('username')
    pass1 = request.form.get('new-password-1')
    pass2 = request.form.get('new-password-2')
    if pass1 != pass2:
        return "Passwords do not match!", 400
    users_db_lab3[username] = pass1
    return redirect('/')

@app.route('/lab3/forgot-secure', methods=['POST'])
def lab3_forgot_secure():
    username = request.form.get('username')
    if username in users_db_lab3:
        token = s.dumps(username, salt='password-reset-salt')
        reset_link = url_for('lab3_reset_secure', token=token, _external=True)
        return f"تم إرسال رابط الاستعادة الآمن: <a href='{reset_link}'>{reset_link}</a>"
    return "المستخدم غير موجود", 404

@app.route('/lab3/reset/<token>', methods=['GET', 'POST'])
def lab3_reset_secure(token):
    try:
        username = s.loads(token, salt='password-reset-salt', max_age=900)
    except (SignatureExpired, BadSignature):
        return "رابط غير صالح أو منتهي الصلاحية!", 400
    if request.method == 'POST':
        pass1 = request.form.get('new-password-1')
        pass2 = request.form.get('new-password-2')
        if pass1 != pass2:
            return "كلمات المرور غير متطابقة!", 400
        users_db_lab3[username] = pass1
        return redirect('/')
    return render_template('labs/lab3_reset.html')


# ==================== المختبر الرابع ====================
@app.route('/lab4', methods=['GET'])
def lab4_home():
    return render_template('labs/lab4.html')

@app.route('/lab4/login-vulnerable', methods=['POST'])
def lab4_login_vulnerable():
    username = request.form.get('username')
    password = request.form.get('password')
    if username not in users_db_lab4:
        return "Invalid username or password.", 401
    if users_db_lab4[username] == password:
        session['user'] = username  # أضف هذا السطر لحفظ الجلسة
        return redirect('/my-account')
    else:
        return "Invalid username or password ", 401

@app.route('/lab4/login-secure', methods=['POST'])
def lab4_login_secure():
    username = request.form.get('username')
    password = request.form.get('password')
    time.sleep(0.5)
    user_exists = username in users_db_lab4
    password_correct = user_exists and (users_db_lab4[username] == password)
    if password_correct:
        session['user'] = username
        return redirect('/my-account')
    return "Invalid username or password.", 401


# ==================== المختبر الخامس ====================
@app.route('/lab5', methods=['GET'])
def lab5_home():
    return render_template('labs/lab5.html')

@app.route('/lab5/login-vulnerable', methods=['POST'])
def lab5_login_vulnerable():
    username = request.form.get('username')
    password = request.form.get('password')
    if username in users_db_lab5:
        time.sleep(0.8)
        if users_db_lab5[username] == password:
            session['user'] = username
            return redirect('/my-account')
        return "Invalid username or password.", 401
    return "Invalid username or password.", 401

@app.route('/lab5/login-secure', methods=['POST'])
def lab5_login_secure():
    username = request.form.get('username')
    password = request.form.get('password')
    dummy_password = "fake_password_hash_placeholder"
    stored_password = users_db_lab5.get(username, dummy_password)
    password_correct = hmac.compare_digest(stored_password.encode(), password.encode())
    time.sleep(0.8)
    if username in users_db_lab5 and password_correct:
        session['user'] = username
        return redirect('/my-account')
    return "Invalid username or password.", 401


# ==================== المختبر السادس ====================
@app.route('/lab6', methods=['GET'])
def lab6_home():
    return render_template('labs/lab6.html')

@app.route('/lab6/login-vulnerable', methods=['POST'])
def lab6_login_vulnerable():
    client_ip = request.remote_addr
    username = request.form.get('username')
    password = request.form.get('password')
    if failed_attempts_ip.get(client_ip, 0) >= 3:
        return "Too many failed attempts. IP blocked temporarily.", 429
    if username in users_db_lab6 and users_db_lab6[username] == password:
        failed_attempts_ip[client_ip] = 0
        session['user'] = username
        return redirect('/my-account')
    failed_attempts_ip[client_ip] = failed_attempts_ip.get(client_ip, 0) + 1
    return "Invalid username or password.", 401

@app.route('/lab6/login-secure', methods=['POST'])
def lab6_login_secure():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    current_time = time.time()
    lockout_data = account_failed_attempts.get(username, {"count": 0, "timer": 0.0})
    if lockout_data["count"] >= 3 and (current_time - lockout_data["timer"]) < BLOCK_TIME:
        return "Account temporarily locked.", 429
    if username in users_db_lab6 and users_db_lab6[username] == password:
        account_failed_attempts[username] = {"count": 0, "timer": 0.0}
        session['user'] = username
        return redirect('/my-account')
    new_count = lockout_data["count"] + 1
    account_failed_attempts[username] = {
        "count": new_count,
        "timer": current_time if new_count >= 3 else lockout_data["timer"]
    }
    return "Invalid username or password.", 401

if __name__ == '__main__':
    app.run(debug=True, port=5000)