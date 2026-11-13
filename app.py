import os
import re
import sys
import time
import tempfile
import requests
import json
import base64
import urllib.parse
import urllib.parse
import random
import time
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response, session, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from sqlalchemy import text

# Enable unbuffered output for immediate logging
sys.stdout.flush()
sys.stderr.flush()

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENWEB_NINJA_API_KEY = os.getenv("OPENWEB_NINJA_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_VISION_API_KEY = os.getenv("GEMINI_VISION_API_KEY") or GEMINI_API_KEY
GEMINI_IMAGE_API_KEY = os.getenv("GEMINI_IMAGE_API_KEY") or GEMINI_API_KEY
HF_TOKEN = os.getenv("HF_TOKEN")
HF_TOKENS_RAW = os.getenv("HF_TOKENS")
HF_TOKENS = [t.strip() for t in HF_TOKENS_RAW.split(",") if t.strip()] if HF_TOKENS_RAW else ([HF_TOKEN] if HF_TOKEN else [])
PROMPT_REFINE_API_KEY = (os.getenv("PROMPT_REFINE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
POLLINATIONS_API_KEY = (os.getenv("POLLINATIONS_API_KEY") or os.getenv("POLLINATION_API_KEY") or "").strip()

# AWS Rekognition Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_REKOGNITION_CUSTOM_MODEL_ARN = os.getenv("AWS_REKOGNITION_CUSTOM_MODEL_ARN")


from datetime import timedelta

# Trigger Reload for Template Update 5
_data_dir = os.environ.get('DESH_DATA_DIR')
app = Flask(__name__, instance_path=os.path.abspath(_data_dir)) if _data_dir else Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Session Configuration for Better Persistence
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # Remember me for 30 days
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Regular sessions last 7 days
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS attacks
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# Vercel-specific DB handling (Read-only file system workarounds)
is_vercel = os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME')
if is_vercel:
    # Use /tmp for writable SQLite db (Ephemeral, but works for demo)
    db_path = "/tmp/site.db"
    # Optional: copy existing DB if we want pre-populated data (not doing it here to keep it simple/safe)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

try:
    from models import db, User
    # Import Data
    from data.products_heritage import HERITAGE_DATA
    db.init_app(app)
    print("[OK] Database and Models loaded successfully")
except Exception as e:
    print(f"[ERROR] CRITICAL IMPORT ERROR: {e}")
    # Define dummy objects to prevents NameError later in code
    db = None
    User = None
    HERITAGE_DATA = {}

# --- Global Naming Pools for Artisans ---
STATE_NAMING = {
    "Andhra Pradesh": {
        "male": ["Ramesh", "Suresh", "Venkatesh", "Srinivas", "Nagarjuna", "Chandra", "Kishore"],
        "female": ["Lakshmi", "Padma", "Sunita", "Anjali", "Swathi", "Deepa", "Sravani"],
        "last": ["Reddy", "Rao", "Naidu", "Chowdary", "Gupta", "Murthy", "Goud"]
    },
    "Arunachal Pradesh": {
        "male": ["Tashi", "Dorjee", "Karsang", "Passang", "Jampa", "Sangey", "Wangchu"],
        "female": ["Pema", "Sonam", "Tsering", "Diki", "Yangchen", "Rinchin", "Dechen"],
        "last": ["Lama", "Dorjee", "Tsering", "Khandu", "Wangsa", "Libang", "Perme"]
    },
    "Assam": {
        "male": ["Manas", "Pranjal", "Dipankar", "Bishal", "Utpal", "Gautam", "Rahul"],
        "female": ["Barsha", "Priyanka", "Mousumi", "Pompy", "Nayanmoni", "Gayatri", "Daisy"],
        "last": ["Baruah", "Gogoi", "Saikia", "Bora", "Kalita", "Sarma", "Das"]
    },
    "Bihar": {
        "male": ["Mukesh", "Rajesh", "Sanjay", "Amit", "Alok", "Prakash", "Ravi"],
        "female": ["Pooja", "Neha", "Suman", "Kiran", "Rekha", "Rani", "Shila"],
        "last": ["Kumar", "Singh", "Yadav", "Mishra", "Jha", "Prasad", "Gupta"]
    },
    "Chhattisgarh": {
        "male": ["Rakesh", "Vijay", "Anil", "Dinesh", "Suresh", "Manish", "Pawan"],
        "female": ["Meena", "Geeta", "Sita", "Lalita", "Kavita", "Anita", "Radha"],
        "last": ["Baghel", "Sahu", "Baghel", "Verma", "Dewangan", "Netam", "Kashyap"]
    },
    "Goa": {
        "male": ["Mario", "Pedro", "Anthony", "Francisco", "Joao", "Caitan", "Savio"],
        "female": ["Maria", "Fatima", "Isabella", "Rosie", "Ana", "Josephine", "Carmina"],
        "last": ["Fernandes", "D'Souza", "Rodrigues", "Pereira", "Gomes", "Dias", "Costa"]
    },
    "Gujarat": {
        "male": ["Hitesh", "Jignesh", "Viral", "Chirag", "Hardik", "Mayur", "Pratik"],
        "female": ["Bhumika", "Dhara", "Kinjal", "Peral", "Falguni", "Jigisha", "Mittal"],
        "last": ["Patel", "Shah", "Mehta", "Dave", "Joshi", "Bhatt", "Ammani"]
    }
}

GENERIC_NAMING = {
    "male": ["Ramesh", "Abdul", "Gopal", "Mohammad", "Satish", "Vikram"],
    "female": ["Sunita", "Meenakshi", "Priya", "Lakshmi", "Anjali"],
    "last": ["Kumar", "Devi", "Khan", "Sharma", "Singh", "Das"]
}


# Separate API keys for different services (with fallback to main key)
# Prompt refinement: use this key first so refine has its own quota; if unset, falls back to GEMINI_API_KEY
# Pollinations AI: optional key for prompt refine (text chat completions)

# Configure Gemini AI for chatbot
# Configure Gemini AI for chatbot (Lightweight Vercel Version)
# import google.generativeai as genai (REMOVED: Too heavy for Vercel)
class GeminiClient:
    """Lightweight wrapper for Gemini API to avoid 150MB+ grpc dependencies."""
    def __init__(self, api_key, model="gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def generate_content(self, prompt, timeout=12):
        if not self.api_key:
            return type('obj', (object,), {'text': "Error: AI key missing."})
        
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": str(prompt)}]}]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            # mimic genai response object
            text_result = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            return type('obj', (object,), {'text': text_result})
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return type('obj', (object,), {'text': f"AI Error: {e}"})

class GeminiImageClient:
    """Client for generating images using Gemini Imagen 3 (via REST)."""
    def __init__(self, api_key):
        self.api_key = api_key
        # Using Imagen 4.0 Fast endpoint
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-fast-generate-001:predict"

    def generate_image(self, prompt):
        if not self.api_key:
            return None, "Gemini API Key missing"

        
        headers = {"Content-Type": "application/json"}
        payload = {
            "instances": [
                {"prompt": prompt}
            ],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "1:1"
            }
        }
        
        try:
            print(f"Generating image with Gemini Imagen 3: {prompt[:50]}...")
            resp = requests.post(
                f"{self.url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if resp.status_code != 200:
                print(f"Gemini Image Error {resp.status_code}: {resp.text}")
                return None, f"Gemini Error {resp.status_code}: {resp.text[:200]}"
                
            result = resp.json()
            # Response format: { "predictions": [ { "bytesBase64Encoded": "..." } ] }
            predictions = result.get('predictions')
            if not predictions:
                # Sometimes it might be directly in bytesBase64Encoded if the format differs
                print(f"Unexpected Gemini response: {str(result)[:200]}")
                return None, "No image predictions returned"
                
            b64_data = predictions[0].get('bytesBase64Encoded')
            if b64_data:
                # Return data URI
                return f"data:image/jpeg;base64,{b64_data}", None
                
            return None, "No base64 data in response"
            
        except Exception as e:
            print(f"Gemini Image Exception: {e}")
            return None, str(e)

class HFImageClient:
    """Client for generating images via Hugging Face Inference API with fallback tokens."""
    def __init__(self, tokens, model="black-forest-labs/FLUX.1-schnell"):
        self.tokens = tokens if isinstance(tokens, list) else ([tokens] if tokens else [])
        self.model = model
        self.url = f"https://router.huggingface.co/hf-inference/models/{model}"

    def generate_image(self, prompt):
        if not self.tokens:
            return None, "HF Token(s) missing"
        
        last_err = "Unknown error"
        
        for token in self.tokens:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {"inputs": prompt}
            
            try:
                print(f"Generating image with HF ({self.model}) using token {token[:8]}...")
                
                # Implementation of retry logic for 503 (Model Loading)
                import time
                max_retries = 3
                for i in range(max_retries):
                    resp = requests.post(self.url, headers=headers, json=payload, timeout=90)
                    
                    if resp.status_code == 200:
                        # HF returns raw bytes of the image
                        import base64
                        b64_data = base64.b64encode(resp.content).decode("utf-8")
                        return f"data:image/jpeg;base64,{b64_data}", None
                    
                    if resp.status_code == 503:
                        # Model is loading, wait and retry
                        wait_time = resp.json().get('estimated_time', 20)
                        print(f"HF Model loading, waiting {wait_time}s (try {i+1}/{max_retries})...")
                        time.sleep(min(wait_time, 30))
                        continue
                    
                    # If token is invalid or quota exceeded, try next token
                    if resp.status_code in (401, 403, 429):
                        print(f"HF Token {token[:8]} failed with {resp.status_code}. Trying next...")
                        last_err = f"HF Error {resp.status_code}: {resp.text[:200]}"
                        break # Break retry loop to try next token
                    
                    print(f"HF Image Error {resp.status_code}: {resp.text}")
                    return None, f"HF Error {resp.status_code}: {resp.text[:200]}"
                
                # If we exhausted retries for THIS token and it wasn't a token error, it might be a model issue
                # But we'll continue to next token just in case
                
            except Exception as e:
                print(f"HF Image Exception with token {token[:8]}: {e}")
                last_err = str(e)
                continue
                
        return None, f"HF Error: All tokens failed. Last error: {last_err}"

# Initialize Image Clients
gemini_img_client = GeminiImageClient(GEMINI_IMAGE_API_KEY)
hf_img_client = HFImageClient(HF_TOKENS)


if GEMINI_API_KEY:
    # genai.configure(api_key=GEMINI_API_KEY)
    chatbot_model = GeminiClient(GEMINI_API_KEY, model='gemini-pro')
else:
    chatbot_model = None

login_manager = LoginManager(app)
login_manager.login_view = 'entry'  # /entry = splash (video + auth)
login_manager.login_message = 'Please sign in to continue.'

# Configure Upload Folder
# Configure Upload Folder
if is_vercel:
    app.config['UPLOAD_FOLDER'] = os.path.join('/tmp', 'uploads', 'profiles')
else:
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'profiles')

try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except OSError as e:
    print(f"⚠️ Warning: Could not create upload folder {app.config['UPLOAD_FOLDER']}: {e}")

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None


def _migrate_add_missing_columns():
    """Add missing columns to existing tables (SQLite-safe)."""
    conn = db.engine.connect()
    try:
            # Users: ensure profile columns exist
            if db.engine.dialect.name == "sqlite":
                r = conn.execute(text("PRAGMA table_info(users)"))
                existing = {row[1] for row in r}
                for col, spec in [
                    ("phone", "VARCHAR(20)"),
                    ("profile_image", "VARCHAR(255)"),
                    ("address", "TEXT"),
                    ("city", "VARCHAR(100)"),
                    ("state", "VARCHAR(100)"),
                    ("pincode", "VARCHAR(10)"),
                ]:
                    if col not in existing:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {spec}"))
                        conn.commit()
    finally:
        conn.close()


with app.app_context():
    try:
        db.create_all()
        _migrate_add_missing_columns()
    except Exception as e:
        print(f"DATABASE ERROR (Non-fatal): {e}")

# --- Core Routes ---


# --- Product Routes ---



@app.route('/about')
def about():
    return render_template('about.html')

# --- Profile & Orders Routes ---

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Update details
        current_user.name = request.form.get('name')
        current_user.phone = request.form.get('phone')
        current_user.address = request.form.get('address')
        current_user.city = request.form.get('city')
        current_user.state = request.form.get('state')
        current_user.pincode = request.form.get('pincode')
        
        # Handle Profile Image Upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '':
                from werkzeug.utils import secure_filename
                filename = secure_filename(f"user_{current_user.id}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_image = filename
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=current_user)





# --- Computer Vision: Indian Craft Identification ---
# fal-ai text-to-image model (use one that supports HF token: e.g. zai-org/GLM-Image)
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "zai-org/GLM-Image")

# Pollinations image models to try in order; first successful response is used. Override with POLLINATIONS_IMAGE_MODEL=flux,kontext,klein
POLLINATIONS_IMAGE_MODELS = [
    m.strip() for m in os.getenv("POLLINATIONS_IMAGE_MODEL", "flux,kontext,klein,klein-large,gptimage").split(",") if m.strip()
]
if not POLLINATIONS_IMAGE_MODELS:
    POLLINATIONS_IMAGE_MODELS = ["flux"]


def generate_image_pollinations(prompt_text):
    """Generate an image through the current authenticated Pollinations API."""
    if not POLLINATIONS_API_KEY:
        return None, "Pollinations", "Pollinations requires a server-side API key and available Pollen balance."
    model_name = os.getenv('POLLINATIONS_IMAGE_MODEL', 'black-forest-labs/flux.1.1-pro')
    target_url = f"https://gen.pollinations.ai/image/{urllib.parse.quote(prompt_text)}"
    try:
        response = requests.get(
            target_url,
            params={'model': model_name, 'width': 1024, 'height': 1024, 'nologo': 'true', 'seed': random.randint(0, 999999)},
            headers={'Authorization': f'Bearer {POLLINATIONS_API_KEY}', 'Accept': 'image/*'},
            timeout=(8, 90),
        )
        response.raise_for_status()
        mime_type = response.headers.get('Content-Type', 'image/jpeg').split(';', 1)[0]
        valid_image = response.content.startswith((b'\xff\xd8\xff', b'\x89PNG\r\n\x1a\n', b'RIFF'))
        if not mime_type.startswith('image/') or not valid_image:
            return None, 'Pollinations', 'Provider response was not a valid image.'
        encoded_image = base64.b64encode(response.content).decode('ascii')
        return f'data:{mime_type};base64,{encoded_image}', 'Pollinations', None
    except requests.RequestException as exc:
        return None, 'Pollinations', str(exc)

def _build_catalog_products():
    products = []
    for state, data in HERITAGE_DATA.items():
        for item in data['items']:
            product_id = f"{state.replace(' ', '_')}_{item['name'].replace(' ', '_')}"
            price_range = item['price_range']
            price = price_range[0] + (len(item['name']) % 10) * (price_range[1] - price_range[0]) // 10
            img_query = item.get('image_query', f"{state} {item['name']} Indian handicraft")
            image_url = item.get('local_image') or f"https://image.pollinations.ai/prompt/{urllib.parse.quote(img_query)}?width=800&height=800&nologo=true&seed={len(item['name'])}"
            products.append({
                'id': product_id, 'name': item['name'], 'state': state,
                'category': item['category'], 'price': price,
                'fun_fact': item.get('fun_fact', ''), 'image_url': image_url,
                'model_3d': item.get('model_3d')
            })
    products.sort(key=lambda product: (not product.get('model_3d'), product['name']))
    return products


@app.route('/', methods=['GET', 'HEAD'])
def index():
    """Home page - Public Access."""
    return render_template('index.html', featured_products=_build_catalog_products()[:4])


@app.route('/entry')
def entry():
    """Keep sign-in optional for the public project demo."""
    return redirect(url_for('index'))


@app.route('/demo-login', methods=['POST'])
def demo_login():
    """Create or reuse a clearly labelled local demo account for the project review."""
    demo_email = 'review-demo@deshkehaath.local'
    user = User.query.filter_by(email=demo_email).first()
    if not user:
        user = User(email=demo_email, name='Project Reviewer')
        user.set_password(os.urandom(24).hex())
        db.session.add(user)
        db.session.commit()
    login_user(user, remember=False)
    return redirect(request.form.get('next') or url_for('index'))


@app.route('/splash')
def splash():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('splash.html')


@app.route('/home')
def home():
    """Alias for index"""
    return redirect(url_for('index'))


@app.route('/api/auth/sync', methods=['POST'])
def api_auth_sync():
    """Bridge localStorage session to Flask-Login (creates DB user if needed)."""
    if not db or not User:
        return jsonify({'ok': False, 'error': 'Database unavailable'}), 503
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or '').strip()
    if not email:
        return jsonify({'ok': False, 'error': 'Email required'}), 400
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, name=name or email.split('@')[0])
            user.set_password(f'local-storage-{email}')
            db.session.add(user)
            db.session.commit()
        elif name and user.name != name:
            user.name = name
            db.session.commit()
        login_user(user, remember=True)
        session.permanent = True
        return jsonify({'ok': True, 'id': user.id, 'name': user.name, 'email': user.email})
    except Exception as e:
        db.session.rollback()
        print(f"Auth sync error: {e}")
        return jsonify({'ok': False, 'error': 'Could not sync session'}), 500


@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    logout_user()
    return jsonify({'ok': True})


@app.route('/login', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user, remember=True)  # Enable remember me for 30 days
        session.permanent = True  # Make session persistent
        return redirect(url_for('index'))
    flash('Invalid email or password.', 'error')
    return redirect(url_for('entry'))


@app.route('/signup', methods=['POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    email = request.form.get('email', '').strip().lower()
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '')
    if not email or not name or not password:
        flash('All fields are required.', 'error')
    elif User.query.filter_by(email=email).first():
        flash('An account with this email already exists.', 'error')
    elif len(password) < 6:
        flash('Password must be at least 6 characters.', 'error')
    else:
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)  # Auto-login after signup
        session.permanent = True  # Make session persistent
        flash('Account created successfully! Welcome!', 'success')
        return redirect(url_for('index'))
    return redirect(url_for('entry'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('entry'))


@app.route('/reset')
def reset_session():
    """Clear session and show splash - useful when stuck or testing."""
    logout_user()
    return redirect(url_for('entry'))


from data.products_heritage import HERITAGE_DATA

STATE_POPULAR_CRAFTS = {
    "Andhra Pradesh": ["Kondapalli Toys", "Uppada Silk", "Temple Jewellery"],
    "Arunachal Pradesh": ["Bamboo Crafts", "Bead Jewellery", "Wooden Masks"],
    "Assam": ["Jaapi Hat", "Muga Silk", "Bell Metal Crafts"],
    "Bihar": ["Madhubani Painting", "Tussar Silk", "Sikki Grass Crafts"],
    "Chhattisgarh": ["Dhokra Metal", "Kosa Silk", "Wrought Iron"],
    "Goa": ["Coconut Shell Crafts", "Azulejos Tiles", "Kunbi Saree"],
    "Gujarat": ["Bandhani Textile", "Patola Saree", "Kutch Embroidery"],
    "Haryana": ["Phulkari", "Jhajjar Pottery", "Brass Utensils"],
    "Himachal Pradesh": ["Kullu Shawls", "Chamba Rumal", "Silver Jewellery"],
    "Jharkhand": ["Sohrai Painting", "Tussar Silk", "Bamboo Crafts"],
    "Karnataka": ["Mysore Silk", "Channapatna Toys", "Sandalwood Carvings"],
    "Kerala": ["Kasavu Saree", "Coir Crafts", "Nettur Petti"],
    "Madhya Pradesh": ["Gond Art", "Chanderi Saree", "Maheshwari Fabric"],
    "Maharashtra": ["Warli Art", "Paithani Saree", "Kolhapuri Jewellery"],
    "Meghalaya": ["Bamboo Bowls", "Eri Silk", "Black Pottery"],
    "Mizoram": ["Puan Saree", "Bamboo Hats", "Beadwork"],
    "Nagaland": ["Warrior Shawls", "Hornbill Art", "Beaded Necklaces"],
    "Odisha": ["Pattachitra", "Sambalpuri Saree", "Silver Filigree"],
    "Punjab": ["Phulkari", "Punjabi Jutti", "Parandi"],
    "Rajasthan": ["Blue Pottery", "Bandhani", "Thewa Jewellery"],
    "Sikkim": ["Thangka Painting", "Lepcha Weaving", "Wooden Tables"],
    "Tamil Nadu": ["Kanchipuram Silk", "Tanjore Painting", "Temple Jewellery"],
    "Telangana": ["Pochampally Ikat", "Bidriware", "Nirmal Paintings"],
    "Tripura": ["Bamboo Art", "Handloom", "Cane Furniture"],
    "Uttar Pradesh": ["Chikan Embroidery", "Banarasi Silk", "Brassware"],
    "Uttarakhand": ["Pichora Saree", "Ringaal Basketry", "Aipan Art"],
    "West Bengal": ["Baluchari Silk", "Terracotta Horse", "Kantha Embroidery"],
    "Jammu and Kashmir": ["Pashmina Shawl", "Papier Mache", "Walnut Carving"],
    "Ladakh": ["Tibetan Jewelry", "Woolen Rugs", "Prayer Wheels"]
}

@app.route('/products')
def products():
    search_query = request.args.get('search', '').lower().strip()
    search_aliases = {
        'bommalu': 'toys', 'kondapalli bommalu': 'kondapalli toys',
        'muga silk': 'muga silk', 'assam silk': 'assam',
        'banarasi saree': 'banarasi silk saree', 'pattachitra': 'pattachitra art',
        'kalamkari': 'kalamkari textile', 'channapatna': 'channapatna toys',
    }
    for phrase, replacement in search_aliases.items():
        search_query = search_query.replace(phrase, replacement)
    sort_by = request.args.get('sort', 'default')
    category_filter = request.args.get('category', 'All')
    state_filter = request.args.get('state', 'all')
    
    all_products = []
    for state, data in HERITAGE_DATA.items():
        if state_filter != 'all' and state.lower() != state_filter.lower():
            continue
            
        for item in data['items']:
            if category_filter != 'All' and item['category'] != category_filter:
                continue
            # Improved Search Logic: Token-based (stop words, all keywords); include image_query
            if search_query:
                q_tokens = search_query.replace(',', ' ').replace('.', ' ').split()
                stop_words = {'show', 'me', 'find', 'the', 'a', 'an', 'please', 'i', 'want', 'looking', 'for', 'in', 'from', 'of', 'with', 'ka', 'ki', 'ke', 'se', 'aur', 'mein', 'traditional', 'tradition'}
                keywords = [w for w in q_tokens if w not in stop_words]
                if keywords:
                    product_text = f"{item['name']} {state} {item['category']} {item.get('fun_fact','')} {item.get('image_query','')}".lower()
                    if not all(k in product_text for k in keywords):
                        continue

            product_id = f"{state.replace(' ', '_')}_{item['name'].replace(' ', '_')}"
            price = item['price_range'][0] + (len(item['name']) % 10) * (item['price_range'][1] - item['price_range'][0]) // 10
            
            # Use local_image if available, otherwise generate Pollinations URL
            if 'local_image' in item:
                image_url = item['local_image']
            else:
                img_query = item.get('image_query', f"{state} {item['name']} Indian handicraft")
                image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(img_query)}?width=800&height=800&nologo=true&seed={len(item['name'])}"
            
            # Check if this product is popular in its state (for GI tag)
            popular_list = STATE_POPULAR_CRAFTS.get(state, [])
            is_popular = any(p_name.lower() in item['name'].lower() for p_name in popular_list)

            # Get story from state data
            story = data.get('stories', {}).get(item['name'], "Deeply rooted in Indian heritage, this craft represents centuries of tradition.")

            all_products.append({
                "id": product_id,
                "name": item['name'],
                "state": state,
                "category": item['category'],
                "price": price,
                "fun_fact": item['fun_fact'],
                "story": story,
                "rating": 4.0 + (len(item['name']) % 10) / 10,
                "reviews": 10 + (len(item['name']) % 50),
                "image_url": image_url,
                "is_popular": is_popular,
                "model_3d": item.get('model_3d')
            })
    
    # Sort
    if sort_by == 'price_low':
        all_products.sort(key=lambda x: x['price'])
    elif sort_by == 'price_high':
        all_products.sort(key=lambda x: x['price'], reverse=True)
    elif sort_by == 'rating':
        all_products.sort(key=lambda x: x['rating'], reverse=True)
    else:
        # Default sort: Name, but prioritize 3D models at the very top
        all_products.sort(key=lambda x: (not x.get('model_3d'), x['name']))
        
    all_states = sorted(list(HERITAGE_DATA.keys()))
    all_categories = sorted(list(set(i['category'] for d in HERITAGE_DATA.values() for i in d['items'])))
        
    # Limit the initial HTML and image work while keeping filters and sort server-side.
    page_size = 24
    total_products = len(all_products)
    page_count = max(1, (total_products + page_size - 1) // page_size)
    page = min(max(request.args.get('page', 1, type=int) or 1, 1), page_count)
    def page_url(number):
        params = request.args.to_dict()
        params['page'] = number
        return url_for('products') + '?' + urllib.parse.urlencode(params)
    return render_template('products.html',
                         products=all_products[(page - 1) * page_size:page * page_size],
                         total_products=total_products,
                         page=page,
                         page_count=page_count,
                         previous_page_url=page_url(page - 1) if page > 1 else None,
                         next_page_url=page_url(page + 1) if page < page_count else None,
                         all_states=all_states,
                         all_categories=all_categories,
                         current_state=state_filter,
                         current_category=category_filter,
                         current_sort=sort_by,
                         search_query=search_query)

@app.route('/product/<product_id>')
def product_detail(product_id):
    # Parse ID: State_ItemName
    found_state = None
    found_item = None
    
    for state, data in HERITAGE_DATA.items():
        state_key = state.replace(' ', '_')
        if product_id.startswith(state_key):
            found_state = state
            item_name = product_id.replace(state_key + '_', '').replace('_', ' ')
            for item in data['items']:
                if item['name'] == item_name:
                    found_item = item
                    break
            if found_item:
                break
    
    if not found_item:
        return "Product not found", 404
        
    price = found_item['price_range'][0] + (len(found_item['name']) % 10) * (found_item['price_range'][1] - found_item['price_range'][0]) // 10
    story = HERITAGE_DATA[found_state]['stories'].get(found_item['name'], "Deeply rooted in Indian heritage, this craft represents centuries of tradition.")

    # Determine image query and URL
    img_query = found_item.get('image_query', f"{found_state} {found_item['name']} Indian handicraft")
    
    if 'local_image' in found_item:
        image_url = found_item['local_image']
    else:
        image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(img_query)}?width=1024&height=1024&nologo=true&seed={len(found_item['name'])}"

    product = {
        "id": product_id,
        "name": found_item['name'],
        "state": found_state,
        "category": found_item['category'],
        "price": price,
        "description": found_item['fun_fact'],
        "story": story,
        "rating": 4.0 + (len(found_item['name']) % 10) / 10,
        "reviews": 10 + (len(found_item['name']) % 50),
        "image_url": image_url,
        "image_query": img_query,
        "model_3d": found_item.get('model_3d')
    }
    
    # Related Products: Find 4 products from the same state or category
    related = []
    for s_name, s_data in HERITAGE_DATA.items():
        for i in s_data['items']:
            if i['name'] == found_item['name'] and s_name == found_state:
                continue # Skip current
            
            if s_name == found_state or i['category'] == found_item['category']:
                r_id = f"{s_name.replace(' ', '_')}_{i['name'].replace(' ', '_')}"
                r_price = i['price_range'][0] + (len(i['name']) % 10) * (i['price_range'][1] - i['price_range'][0]) // 10
                if 'local_image' in i:
                    r_image_url = i['local_image']
                else:
                    r_img_query = i.get('image_query', f"{s_name} {i['name']} Indian handicraft")
                    r_image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(r_img_query)}?width=400&height=400&nologo=true&seed={len(i['name'])}"
                
                related.append({
                    "id": r_id,
                    "name": i['name'],
                    "state": s_name,
                    "price": r_price,
                    "image_url": r_image_url
                })
                if len(related) >= 4:
                    break
        if len(related) >= 4:
            break

    return render_template('product_detail.html', product=product, related_products=related)





# Helper to generate artist profiles
def get_artists():
    import random
    
    # Real data from Google Sheet
    real_artisans = [
        {
            "craft": "Kondapalli Toys",
            "state": "Andhra Pradesh",
            "labor_time": "15 – 25 Hours",
            "price_range": "₹499 – ₹2,999",
            "why_price": "Carved from Tella Poniki (softwood) and hand-painted. Prices vary by set size (e.g., a \"Marriage Set\" vs. a single figurine).",
            "description": "Specialist in Kondapalli Toys. Carved from Tella Poniki (softwood) and hand-painted. Prices vary by set size (e.g., a \"Marriage Set\" vs. a single figurine). Approx labor: 15 – 25 Hours."
        },
        {
            "craft": "Uppada Silk Saree",
            "state": "Andhra Pradesh",
            "labor_time": "150 – 400 Hours",
            "price_range": "₹3,999 – ₹18,000",
            "why_price": "Uses the Jamdani weaving technique. A bridal saree with pure zari can take up to 2 months of non-stop hand-weaving.",
            "description": "Specialist in Uppada Silk Saree. Uses the Jamdani weaving technique. A bridal saree with pure zari can take up to 2 months of non-stop hand-weaving. Approx labor: 150 – 400 Hours."
        },
        {
            "craft": "Temple Jewellery",
            "state": "Andhra Pradesh",
            "labor_time": "40 – 120 Hours",
            "price_range": "₹1,299 – ₹8,500",
            "why_price": "Hand-crafted silver with 24k gold leaf plating (Kemp work). Complex bridal sets require weeks of intricate metalwork.",
            "description": "Specialist in Temple Jewellery. Hand-crafted silver with 24k gold leaf plating (Kemp work). Complex bridal sets require weeks of intricate metalwork. Approx labor: 40 – 120 Hours."
        },
        {
            "craft": "Kalamkari Textile",
            "state": "Andhra Pradesh",
            "labor_time": "60 – 80 Hours",
            "price_range": "₹899 – ₹4,500",
            "why_price": "Srikalahasti style involves 23 steps of natural dyeing and hand-painting with a bamboo pen (kalam) on cotton or silk.",
            "description": "Specialist in Kalamkari Textile. Srikalahasti style involves 23 steps of natural dyeing and hand-painting with a bamboo pen (kalam) on cotton or silk. Approx labor: 60 – 80 Hours."
        },
        {
            "craft": "Etikoppaka Toys",
            "state": "Andhra Pradesh",
            "labor_time": "8 – 12 Hours",
            "price_range": "₹299 – ₹1,499",
            "why_price": "Made from Ankudu wood and finished on a lathe with natural lacquer made from seeds and tree resins.",
            "description": "Specialist in Etikoppaka Toys. Made from Ankudu wood and finished on a lathe with natural lacquer made from seeds and tree resins. Approx labor: 8 – 12 Hours."
        },
        {
            "craft": "Folk Scrolls (Cheriyal)",
            "state": "Andhra Pradesh",
            "labor_time": "40 – 100 Hours",
            "price_range": "₹1,499 – ₹6,500",
            "why_price": "Hand-ground natural pigments on khadi canvas. A full narrative scroll depicting an epic can take several weeks.",
            "description": "Specialist in Folk Scrolls (Cheriyal). Hand-ground natural pigments on khadi canvas. A full narrative scroll depicting an epic can take several weeks. Approx labor: 40 – 100 Hours."
        },
        {
            "craft": "Bamboo Furniture",
            "state": "Arunachal Pradesh",
            "labor_time": "40 – 60 Hours",
            "price_range": "₹699 – ₹4,500",
            "why_price": "Includes deep-forest harvesting and \"curing\" (smoking/soaking) to make it termite-proof and water-strong.",
            "description": "Specialist in Bamboo Furniture. Includes deep-forest harvesting and \"curing\" (smoking/soaking) to make it termite-proof and water-strong. Approx labor: 40 – 60 Hours."
        },
        {
            "craft": "Tribal Wrap (Gale)",
            "state": "Arunachal Pradesh",
            "labor_time": "120 – 180 Hours",
            "price_range": "₹1,299 – ₹3,500",
            "why_price": "Woven on a \"Loin Loom\" (Backstrap loom). Each tribal motif is a \"secret code\" passed down through memory.",
            "description": "Specialist in Tribal Wrap (Gale). Woven on a \"Loin Loom\" (Backstrap loom). Each tribal motif is a \"secret code\" passed down through memory. Approx labor: 120 – 180 Hours."
        },
        {
            "craft": "Wancho Bead Jewelry",
            "state": "Arunachal Pradesh",
            "labor_time": "12 – 24 Hours",
            "price_range": "₹299 – ₹1,500",
            "why_price": "Recently GI-tagged. Authentic pieces use specific color codes (red, blue, orange) to signify bravery and status.",
            "description": "Specialist in Wancho Bead Jewelry. Recently GI-tagged. Authentic pieces use specific color codes (red, blue, orange) to signify bravery and status. Approx labor: 12 – 24 Hours."
        },
        {
            "craft": "Handwoven Textile",
            "state": "Arunachal Pradesh",
            "labor_time": "150 – 250 Hours",
            "price_range": "₹899 – ₹2,500",
            "why_price": "These are high-density weaves. Some ceremonial shawls take nearly 2 months of part-time weaving to complete.",
            "description": "Specialist in Handwoven Textile. These are high-density weaves. Some ceremonial shawls take nearly 2 months of part-time weaving to complete. Approx labor: 150 – 250 Hours."
        },
        {
            "craft": "Wooden Masks",
            "state": "Arunachal Pradesh",
            "labor_time": "50 – 80 Hours",
            "price_range": "₹999 – ₹2,999",
            "why_price": "Carved from Puma or Zokhu wood. Includes multiple layers of natural paint and manual chiseling for \"life-like\" detail.",
            "description": "Specialist in Wooden Masks. Carved from Puma or Zokhu wood. Includes multiple layers of natural paint and manual chiseling for \"life-like\" detail. Approx labor: 50 – 80 Hours."
        },
        {
            "craft": "Traditional Baskets",
            "state": "Arunachal Pradesh",
            "labor_time": "30 – 45 Hours",
            "price_range": "₹699 – ₹2,999",
            "why_price": "Woven with double-layered cane. The weave is so tight it creates surface tension that can briefly hold water.",
            "description": "Specialist in Traditional Baskets. Woven with double-layered cane. The weave is so tight it creates surface tension that can briefly hold water. Approx labor: 30 – 45 Hours."
        },
        {
            "craft": "Jaapi Hat (Fulam)",
            "state": "Assam",
            "labor_time": "12 – 18 Hours",
            "price_range": "₹600",
            "why_price": "Hand-knit from Tokou (palm) leaves and bamboo. Decorative versions (Fulam) require intricate velvet, wool, and sequin work.",
            "description": "Specialist in Jaapi Hat (Fulam). Hand-knit from Tokou (palm) leaves and bamboo. Decorative versions (Fulam) require intricate velvet, wool, and sequin work. Approx labor: 12 – 18 Hours."
        },
        {
            "craft": "Muga Silk Saree",
            "state": "Assam",
            "labor_time": "150 – 200 Hours",
            "price_range": "₹25,000 – ₹45,000",
            "why_price": "Exclusive to Assam. Price includes 2+ months of rearing rare golden silkworms. Hand-weaving a full saree takes 15–20 focused days.",
            "description": "Specialist in Muga Silk Saree. Exclusive to Assam. Price includes 2+ months of rearing rare golden silkworms. Hand-weaving a full saree takes 15–20 focused days. Approx labor: 150 – 200 Hours."
        },
        {
            "craft": "Bamboo Jewellery",
            "state": "Assam",
            "labor_time": "4 – 8 Hours",
            "price_range": "₹400 (Set)",
            "why_price": "Artisans must select 3-year-old \"mature\" bamboo, boil it to prevent cracks, and hand-carve it into lightweight, durable motifs.",
            "description": "Specialist in Bamboo Jewellery. Artisans must select 3-year-old \"mature\" bamboo, boil it to prevent cracks, and hand-carve it into lightweight, durable motifs. Approx labor: 4 – 8 Hours."
        },
        {
            "craft": "Mekhela Chador",
            "state": "Assam",
            "labor_time": "60 – 100 Hours",
            "price_range": "₹4,500 – ₹12,000",
            "why_price": "A two-piece set (skirt and wrap). Hand-weaving authentic motifs on a Taat Xaal (pit loom) is labor-intensive; sunlight \"shining through\" refers to the high thread count.",
            "description": "Specialist in Mekhela Chador. A two-piece set (skirt and wrap). Hand-weaving authentic motifs on a Taat Xaal (pit loom) is labor-intensive; sunlight \"shining through\" refers to the high thread count. Approx labor: 60 – 100 Hours."
        },
        {
            "craft": "Majuli Masks",
            "state": "Assam",
            "labor_time": "40 – 120 Hours",
            "price_range": "₹3,500 (Medium)",
            "why_price": "Made using a bamboo frame, clay, and cow dung layers. Each mask must dry naturally between coats before being painted with organic pigments.",
            "description": "Specialist in Majuli Masks. Made using a bamboo frame, clay, and cow dung layers. Each mask must dry naturally between coats before being painted with organic pigments. Approx labor: 40 – 120 Hours."
        },
        {
            "craft": "Bell Metal Crafts",
            "state": "Assam",
            "labor_time": "24 – 40 Hours",
            "price_range": "₹1,200 (per kg)",
            "why_price": "Made by Sarthebari artisans using an alloy of copper and tin. It involves manual hammering and heating—never machine-cast.",
            "description": "Specialist in Bell Metal Crafts. Made by Sarthebari artisans using an alloy of copper and tin. It involves manual hammering and heating—never machine-cast. Approx labor: 24 – 40 Hours."
        },
        {
            "craft": "Madhubani Painting",
            "state": "Bihar",
            "labor_time": "30 – 120 Hours",
            "price_range": "₹2,500 – ₹8,500",
            "why_price": "Painted with twigs and nibs using natural dyes (cow dung base, rice paste). Prices soar for \"Kachni\" (fine line) work vs \"Bharni\" (filled colors).",
            "description": "Specialist in Madhubani Painting. Painted with twigs and nibs using natural dyes (cow dung base, rice paste). Prices soar for \"Kachni\" (fine line) work vs \"Bharni\" (filled colors). Approx labor: 30 – 120 Hours."
        },
        {
            "craft": "Tussar Silk Saree",
            "state": "Bihar",
            "labor_time": "120 – 180 Hours",
            "price_range": "₹4,500 – ₹15,000",
            "why_price": "Sourced from wild silkworms in Bhagalpur. Includes boiling, hand-spinning, and hand-weaving. Real \"Peace Silk\" (non-violent) carries a premium.",
            "description": "Specialist in Tussar Silk Saree. Sourced from wild silkworms in Bhagalpur. Includes boiling, hand-spinning, and hand-weaving. Real \"Peace Silk\" (non-violent) carries a premium. Approx labor: 120 – 180 Hours."
        },
        {
            "craft": "Sikki Grass Crafts",
            "state": "Bihar",
            "labor_time": "10 – 40 Hours",
            "price_range": "₹600 – ₹2,500",
            "why_price": "Golden grass found in marshes is harvested and dyed. Boxes and dolls are woven so tightly they become sturdy structural items that last decades.",
            "description": "Specialist in Sikki Grass Crafts. Golden grass found in marshes is harvested and dyed. Boxes and dolls are woven so tightly they become sturdy structural items that last decades. Approx labor: 10 – 40 Hours."
        },
        {
            "craft": "Lac Bangles",
            "state": "Bihar",
            "labor_time": "4 – 10 Hours",
            "price_range": "₹200 – ₹500 (Set)",
            "why_price": "Muzaffarpur is the hub. Natural resin is heated on a furnace, colored with stone dyes, and hand-molded. Intricate \"Kundan\" inlay sets are pricier.",
            "description": "Specialist in Lac Bangles. Muzaffarpur is the hub. Natural resin is heated on a furnace, colored with stone dyes, and hand-molded. Intricate \"Kundan\" inlay sets are pricier. Approx labor: 4 – 10 Hours."
        },
        {
            "craft": "Manjusha Art",
            "state": "Bihar",
            "labor_time": "20 – 60 Hours",
            "price_range": "₹1,500 – ₹4,500",
            "why_price": "One of the world’s oldest scroll arts using only three colors (pink, green, yellow). Often painted on Jute/Silk boxes or handmade paper.",
            "description": "Specialist in Manjusha Art. One of the world’s oldest scroll arts using only three colors (pink, green, yellow). Often painted on Jute/Silk boxes or handmade paper. Approx labor: 20 – 60 Hours."
        },
        {
            "craft": "Mud Clay Toys",
            "state": "Bihar",
            "labor_time": "6 – 12 Hours",
            "price_range": "₹150 – ₹600",
            "why_price": "Unlike kiln-fired terracotta, these \"Mitti\" toys are often sun-dried and painted with organic colors, safe for children and eco-friendly.",
            "description": "Specialist in Mud Clay Toys. Unlike kiln-fired terracotta, these \"Mitti\" toys are often sun-dried and painted with organic colors, safe for children and eco-friendly. Approx labor: 6 – 12 Hours."
        },
        {
            "craft": "Dhokra Metal Craft",
            "state": "Chhattisgarh",
            "labor_time": "40 – 72 Hours",
            "price_range": "₹2,500 (10-12\" Figurine)",
            "why_price": "Uses the lost-wax technique. Since the clay mold must be broken to reveal the metal, every piece is a unique original that can never be replicated exactly.",
            "description": "Specialist in Dhokra Metal Craft. Uses the lost-wax technique. Since the clay mold must be broken to reveal the metal, every piece is a unique original that can never be replicated exactly. Approx labor: 40 – 72 Hours."
        },
        {
            "craft": "Kosa Silk Saree",
            "state": "Chhattisgarh",
            "labor_time": "120 – 180 Hours",
            "price_range": "₹7,500 – ₹12,000",
            "why_price": "Sourced from wild silkworms (Antheraea mylitta). The price reflects the rarity of the cocoons and the 10–15 days of painstaking hand-weaving on pit looms.",
            "description": "Specialist in Kosa Silk Saree. Sourced from wild silkworms (Antheraea mylitta). The price reflects the rarity of the cocoons and the 10–15 days of painstaking hand-weaving on pit looms. Approx labor: 120 – 180 Hours."
        },
        {
            "craft": "Wooden Tribal Masks",
            "state": "Chhattisgarh",
            "labor_time": "30 – 50 Hours",
            "price_range": "₹2,500 – ₹4,500",
            "why_price": "Carved from Teak or Shisham. Artisans use manual chisels to bring \"life\" to the wood, depicting gods and spirits with details that machine-carving cannot mimic.",
            "description": "Specialist in Wooden Tribal Masks. Carved from Teak or Shisham. Artisans use manual chisels to bring \"life\" to the wood, depicting gods and spirits with details that machine-carving cannot mimic. Approx labor: 30 – 50 Hours."
        },
        {
            "craft": "Wrought Iron Craft",
            "state": "Chhattisgarh",
            "labor_time": "12 – 20 Hours",
            "price_range": "₹800 – ₹1,800",
            "why_price": "Known as Loha Shilp. Blacksmiths from the Agaria community manually heat and beat scrap iron into slender, elegant tribal forms without using any joints or welding.",
            "description": "Specialist in Wrought Iron Craft. Known as Loha Shilp. Blacksmiths from the Agaria community manually heat and beat scrap iron into slender, elegant tribal forms without using any joints or welding. Approx labor: 12 – 20 Hours."
        },
        {
            "craft": "Bamboo Utility Items",
            "state": "Chhattisgarh",
            "labor_time": "15 – 30 Hours",
            "price_range": "₹300 – ₹900",
            "why_price": "Includes harvesting \"mature\" bamboo and hand-splitting it into thin strips. The \"precision\" comes from the tight weave used in traditional winnowing fans and baskets.",
            "description": "Specialist in Bamboo Utility Items. Includes harvesting \"mature\" bamboo and hand-splitting it into thin strips. The \"precision\" comes from the tight weave used in traditional winnowing fans and baskets. Approx labor: 15 – 30 Hours."
        },
        {
            "craft": "Terracotta Jewellery",
            "state": "Chhattisgarh",
            "labor_time": "10 – 15 Hours",
            "price_range": "₹250 – ₹700 (Set)",
            "why_price": "Each bead is hand-rolled from fine clay, etched with a needle, sun-dried, kiln-fired, and then hand-painted with earthy natural pigments.",
            "description": "Specialist in Terracotta Jewellery. Each bead is hand-rolled from fine clay, etched with a needle, sun-dried, kiln-fired, and then hand-painted with earthy natural pigments. Approx labor: 10 – 15 Hours."
        },
        {
            "craft": "Coconut Shell Crafts",
            "state": "Goa",
            "labor_time": "6 – 10 Hours",
            "price_range": "₹400 – ₹1,200",
            "why_price": "Involves removing fiber, sanding to a mirror finish, and seasoning with oils. Complex lamps with \"Jaali\" (perforated) work take more time.",
            "description": "Specialist in Coconut Shell Crafts. Involves removing fiber, sanding to a mirror finish, and seasoning with oils. Complex lamps with \"Jaali\" (perforated) work take more time. Approx labor: 6 – 10 Hours."
        },
        {
            "craft": "Kunbi Saree",
            "state": "Goa",
            "labor_time": "40 – 60 Hours",
            "price_range": "₹1,500 – ₹2,500",
            "why_price": "A traditional cotton weave with red/white checks. A skilled weaver takes about 5 days to complete one saree on a handloom.",
            "description": "Specialist in Kunbi Saree. A traditional cotton weave with red/white checks. A skilled weaver takes about 5 days to complete one saree on a handloom. Approx labor: 40 – 60 Hours."
        },
        {
            "craft": "Shell Jewellery",
            "state": "Goa",
            "labor_time": "4 – 12 Hours",
            "price_range": "₹200 – ₹800",
            "why_price": "Sourcing authentic local shells, cleaning, polishing, and delicate drilling/stringing. Price varies by the rarity of the shells used.",
            "description": "Specialist in Shell Jewellery. Sourcing authentic local shells, cleaning, polishing, and delicate drilling/stringing. Price varies by the rarity of the shells used. Approx labor: 4 – 12 Hours."
        },
        {
            "craft": "Azulejos Tile Art",
            "state": "Goa",
            "labor_time": "5 – 15 Hours",
            "price_range": "₹150 – ₹1,500",
            "why_price": "Hand-painted on ceramic and baked. Small 6x6 tiles are affordable, but large custom nameplates or Mario Miranda murals are premium.",
            "description": "Specialist in Azulejos Tile Art. Hand-painted on ceramic and baked. Small 6x6 tiles are affordable, but large custom nameplates or Mario Miranda murals are premium. Approx labor: 5 – 15 Hours."
        },
        {
            "craft": "Wooden Christian Icons",
            "state": "Goa",
            "labor_time": "20 – 50 Hours",
            "price_range": "₹1,500 – ₹5,500",
            "why_price": "Carved from seasoned wood (often Teak). Each figure is hand-chiseled and painted, reflecting the unique Goan-Baroque aesthetic.",
            "description": "Specialist in Wooden Christian Icons. Carved from seasoned wood (often Teak). Each figure is hand-chiseled and painted, reflecting the unique Goan-Baroque aesthetic. Approx labor: 20 – 50 Hours."
        },
        {
            "craft": "Handcrafted Lamps",
            "state": "Goa",
            "labor_time": "15 – 30 Hours",
            "price_range": "₹1,200 – ₹3,500",
            "why_price": "Made from brass or copper. Involves manual metal beating and intricate cut-work designs that cast geometric shadows.",
            "description": "Specialist in Handcrafted Lamps. Made from brass or copper. Involves manual metal beating and intricate cut-work designs that cast geometric shadows. Approx labor: 15 – 30 Hours."
        },
        {
            "craft": "Patan Patola Saree",
            "state": "Gujarat",
            "labor_time": "1,500 – 3,000 Hours",
            "price_range": "₹85,000 – ₹3,50,000",
            "why_price": "A \"Double Ikat\" masterpiece. Both warp and weft are dyed before weaving. Complex designs can take up to 2 years. It is an heirloom investment.",
            "description": "Specialist in Patan Patola Saree. A \"Double Ikat\" masterpiece. Both warp and weft are dyed before weaving. Complex designs can take up to 2 years. It is an heirloom investment. Approx labor: 1,500 – 3,000 Hours."
        },
        {
            "craft": "Bandhani Textile",
            "state": "Gujarat",
            "labor_time": "40 – 120 Hours",
            "price_range": "₹2,500 – ₹25,000",
            "why_price": "Price depends on the number of \"Bundi\" (knots). A high-end Jhankaar or Gharchola with 10,000+ tiny hand-tied knots justifies the premium.",
            "description": "Specialist in Bandhani Textile. Price depends on the number of \"Bundi\" (knots). A high-end Jhankaar or Gharchola with 10,000+ tiny hand-tied knots justifies the premium. Approx labor: 40 – 120 Hours."
        },
        {
            "craft": "Kutch Embroidery",
            "state": "Gujarat",
            "labor_time": "60 – 200 Hours",
            "price_range": "₹2,500 – ₹15,000",
            "why_price": "Includes various styles (Ahir, Mutwa, Rabari). Pricing is based on the density of silk thread work and real glass mirror integration.",
            "description": "Specialist in Kutch Embroidery. Includes various styles (Ahir, Mutwa, Rabari). Pricing is based on the density of silk thread work and real glass mirror integration. Approx labor: 60 – 200 Hours."
        },
        {
            "craft": "Rogan Art Painting",
            "state": "Gujarat",
            "labor_time": "20 – 60 Hours",
            "price_range": "₹1,800 – ₹7,500",
            "why_price": "Castor oil is boiled for 2 days to create a paste. Only one family in Nirona still practices the original technique. Price reflects this extreme rarity.",
            "description": "Specialist in Rogan Art Painting. Castor oil is boiled for 2 days to create a paste. Only one family in Nirona still practices the original technique. Price reflects this extreme rarity. Approx labor: 20 – 60 Hours."
        },
        {
            "craft": "Silver Tribal Jewellery",
            "state": "Gujarat",
            "labor_time": "20 – 40 Hours",
            "price_range": "₹3,500 – ₹25,000",
            "why_price": "Heavy 92.5 silver pieces (Kadas, necklaces). Priced by silver weight + \"making charges\" (approx. ₹150–₹300 per gram of labor).",
            "description": "Specialist in Silver Tribal Jewellery. Heavy 92.5 silver pieces (Kadas, necklaces). Priced by silver weight + \"making charges\" (approx. ₹150–₹300 per gram of labor). Approx labor: 20 – 40 Hours."
        },
        {
            "craft": "Lacquered Toys",
            "state": "Gujarat",
            "labor_time": "6 – 12 Hours",
            "price_range": "₹200 – ₹1,200",
            "why_price": "Made in Idar or Kutch. Wood is turned on a lathe and colored with natural shellac. They are lead-free, non-toxic, and incredibly durable.",
            "description": "Specialist in Lacquered Toys. Made in Idar or Kutch. Wood is turned on a lathe and colored with natural shellac. They are lead-free, non-toxic, and incredibly durable. Approx labor: 6 – 12 Hours."
        },
        # ... (Include all other parsed items here) ...
    ]
    
    artists = []
    
    for i, item in enumerate(real_artisans):
        # Use a local Random instance for thread-safety and determinism
        rng = random.Random(i + 5000)
        
        state = item.get('state', '')
        naming_pool = STATE_NAMING.get(state, GENERIC_NAMING)
        
        is_male = rng.random() > 0.4
        gender = 'male' if is_male else 'female'
        
        # Pick names from the specific state pool
        fname = rng.choice(naming_pool["male"]) if is_male else rng.choice(naming_pool["female"])
        lname = rng.choice(naming_pool["last"])
        
        # Keep the artisan directory self-contained and visually tied to each maker's craft.
        state_key = state.lower().replace(' ', '_').replace('&', 'and')
        craft_key = item['craft'].lower().replace(' ', '_')
        image_candidates = [
            f"/static/images/products/{state_key}_{craft_key}.png",
            f"/static/images/products/{state_key}_{craft_key}.jpeg",
            f"/static/images/products/{state_key}_{craft_key}.jpg",
            f"/static/images/products/{craft_key}.png",
        ]
        image_url = next((path for path in image_candidates if os.path.exists(os.path.join(os.path.dirname(__file__), path.lstrip('/').replace('/', os.sep)))), None)
        if not image_url:
            regional_items = HERITAGE_DATA.get(state, {}).get('items', [])
            regional_image = next((candidate.get('local_image') for candidate in regional_items if candidate.get('local_image') and os.path.exists(os.path.join(os.path.dirname(__file__), candidate['local_image'].lstrip('/').replace('/', os.sep)))), None)
            image_url = regional_image or '/static/images/logo_map.png'
        
        artists.append({
            'id': i + 1,
            'name': f"{fname} {lname}",
            'gender': gender,
            'style': item['craft'],
            'state': item['state'],
            'description': item['description'],
            'image': image_url,
            'experience': rng.randint(10, 45),
            'meta': {
               'labor': item['labor_time'],
               'price': item['price_range']
            }
        })
        
    return artists

@app.route('/artisans')
def artisans():
    artists_list = get_artists()
    return render_template('artisans.html', artists=artists_list)


@app.route('/api/generate-craft', methods=['POST'])
def generate_craft_concept():
    """Generate one product-focused image through the configured image provider."""
    payload = request.get_json(silent=True) or {}
    user_prompt = str(payload.get('prompt', '')).strip()
    if not user_prompt:
        return jsonify({'error': 'Describe the craft you want to create.'}), 400
    if len(user_prompt) > 500:
        return jsonify({'error': 'Keep the craft description under 500 characters.'}), 400

    prompt = (
        "Create a premium e-commerce product photograph of ONE Indian handmade craft item. "
        "Show the object alone, centered, fully visible, on a simple warm ivory studio background. "
        "No people, no models, no mannequin, no body, no room scene, no text, no watermark. "
        "Use accurate materials, construction, colors, and motifs from this design brief; do not substitute another product. "
        f"Design brief: {user_prompt}"
    )

    image_data, provider_error = None, None
    if os.environ.get('DESH_LOCAL_MODEL') == '1':
        import local_image
        image_data, provider_error = local_image.generate(prompt)
        provider = 'Local Mac model'
    elif GEMINI_IMAGE_API_KEY:
        image_data, provider_error = gemini_img_client.generate_image(prompt)
        provider = 'Gemini Imagen'
    elif HF_TOKENS:
        image_data, provider_error = hf_img_client.generate_image(prompt)
        provider = 'Hugging Face'
    else:
        image_data, provider, provider_error = generate_image_pollinations(prompt)

    if not image_data:
        app.logger.warning('Craft concept generation provider error: %s', provider_error)
        if os.environ.get('DESH_LOCAL_MODEL') == '1':
            return jsonify({'error': provider_error or 'Local image generation failed.'}), 503
        if provider_error and ('key' in provider_error.lower() or 'token' in provider_error.lower() or 'balance' in provider_error.lower()):
            return jsonify({'error': 'Image generation needs a server API key and available provider credits. Add POLLINATIONS_API_KEY to the local .env file, then restart the app. The key stays on this server.'}), 503
        if provider_error and ('402' in provider_error or 'payment required' in provider_error.lower()):
            return jsonify({'error': 'This image provider account needs available Pollen credits before it can generate. Add credits or claim eligible free Quest Pollen, then try again.'}), 402
        return jsonify({'error': 'Image generation did not return an image. Please try again shortly.'}), 502
    try:
        if image_data.startswith('data:'):
            mime_type, encoded = image_data.split(',', 1)
            mime_type = mime_type[5:].split(';', 1)[0]
            image_bytes = base64.b64decode(encoded)
        else:
            return jsonify({'error': 'The image provider returned an unsupported image format.'}), 502
        extension = 'png' if mime_type == 'image/png' else 'webp' if mime_type == 'image/webp' else 'jpg'
        filename = f'{uuid.uuid4().hex}.{extension}'
        output_directory = os.path.join(app.instance_path, 'generated')
        os.makedirs(output_directory, exist_ok=True)
        with open(os.path.join(output_directory, filename), 'wb') as generated_file:
            generated_file.write(image_bytes)
    except (ValueError, OSError) as exc:
        app.logger.exception('Could not save generated craft image: %s', exc)
        return jsonify({'error': 'The image was created but could not be saved on this computer.'}), 500
    return jsonify({'image': url_for('generated_craft_image', filename=filename), 'provider': provider})


@app.route('/generated/crafts/<path:filename>')
def generated_craft_image(filename):
    return send_from_directory(os.path.join(app.instance_path, 'generated'), filename)


@app.route('/api/local-model-status')
def local_model_status():
    if os.environ.get('DESH_LOCAL_MODEL') != '1':
        return jsonify({'state': 'disabled'})
    import local_image
    return jsonify(local_image.status())



@app.route('/data')
def data():
    return render_template('data.html')

def build_chatbot_context(user_query=""):
    """Build simple static context based on user query (no orders database)."""
    context = """
You are the Craft Assistant for Desh Ke Haath, India's premier heritage craft platform.
Your goal is to be a knowledgeable, warm, and culturally rich guide to Indian handicrafts and culture.

### CORE IDENTITY
- Name: Craft Assistant (Desh Ke Haath)
- Mission: "Prachin Kala, Adhunik Disha" (Ancient Art, Modern Direction).
- Tone: Warm, respectful (use "Namaste"), informative.

### GENERAL SITE INFO
- Platform: Desh Ke Haath (Heritage E-commerce Showcase)
- Shipping: India-wide (5-7 days), Free > ₹2000.
- Payment: UPI, Cards, COD.
- Authenticity: 100% Verified Artisans.

### STRICT GUIDELINES (SCOPE CONTROL)
1. **Site Only**: You ONLY answer questions about Desh Ke Haath, its products, its artisans, and site features.
2. **Order Tracking**: Order tracking and checkout are currently disabled in this static visual mockup. If asked about orders, shopping cart, or tracking, politely inform the user that the site is a visual frontend showcase and transactions are not supported.
3. **No Unrelated Topics**: If asked about anything else (tech, science, jokes, other platforms), refuse politely.
4. **Style**: Concise (2-3 sentences), warm, and professional.
"""
    return context

def call_groq_chat(user_message, context):
    """Fallback static AI response helper since database cart/orders are stripped."""
    m = user_message.lower()
    if any(x in m for x in ["hello", "hi", "namaste"]):
        return "Namaste! Welcome to Desh Ke Haath. I can help you explore unique handicrafts from across India. What are you looking for today?"
    if any(x in m for x in ["track", "order", "status", "buy", "checkout", "cart"]):
        return "Please note: Desh Ke Haath is currently configured as a static visual frontend mockup. Cart, checkout, and order tracking features are disabled."
    return "Thank you for asking! Desh Ke Haath is a premium showcase for Indian heritage handicrafts. Feel free to browse our handicrafts and artists catalog."

@app.route('/api/chat', methods=['POST'])
def chat():
    """AI-powered chatbot endpoint (Static fallback)"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        context = build_chatbot_context(user_message)
        ai_response = call_groq_chat(user_message, context)
        
        return jsonify({
            'reply': ai_response,
            'success': True
        })
        
    except Exception as e:
        print(f"AI Chat Error: {str(e)}")
        return jsonify({
            'error': str(e),
            'message': 'The assistant encountered a technical error. Please try again soon.'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0', threaded=True)
