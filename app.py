import os
import logging
import pdfplumber  # For handling PDFs
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set Adzuna API credentials
ADZUNA_API_ID = os.getenv("ADZUNA_API_ID", "1ca59225")
ADZUNA_API_KEY = os.getenv("ADZUNA_API_KEY", "d3033874025244ac808776f68334e616")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__)

# Set up database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max file size: 16 MB

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    skills = db.Column(db.String(255), nullable=True)

    def update_profile(self, name, phone, address, skills):
        self.name = name
        self.phone = phone
        self.address = address
        self.skills = skills
        db.session.commit()


# Function to fetch job insights from Adzuna API
def get_job_insights():
    try:
        url = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
        params = {
            "app_id": ADZUNA_API_ID,
            "app_key": ADZUNA_API_KEY,
            "results_per_page": 5,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        job_insights = [
            {
                "company": job.get("company", {}).get("display_name", "Unknown Company"),
                "title": job.get("title", "No Title"),
                "description": job.get("description", "No description available."),
                "location": job.get("location", {}).get("display_name", "Unknown Location"),
            }
            for job in data.get("results", [])
        ]
        logging.info("Fetched job insights successfully.")
        return job_insights
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching job insights: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return []


# Function to calculate resume score
def get_resume_score(resume_content):
    try:
        # Placeholder logic for scoring resumes
        score = len(resume_content.split()) % 100  # Example scoring
        return f"Resume score: {score}/100"
    except Exception as e:
        logging.error(f"Error in resume scoring: {e}")
        return "Unable to calculate score."


# Function to check allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Set up user loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Constant for template names
CHECK_SCORE_TEMPLATE = 'check_score.html'


# Routes
@app.route("/dashboard")
@login_required
def dashboard():
    job_insights = get_job_insights()
    return render_template("dashboard.html", job_insights=job_insights)


@app.route('/check_score', methods=['GET', 'POST'])
@login_required
def check_score():
    resume_score = None
    error_message = None  # To display any errors in the template

    if request.method == 'POST':
        file = request.files.get('resume')
        
        # Check if file is uploaded and valid
        error_message = validate_file(file)
        if error_message:
            return render_template(CHECK_SCORE_TEMPLATE, resume_score=resume_score, error_message=error_message)

        # Process the file if valid
        try:
            file_path = save_file(file)
            resume_content = extract_text_from_pdf(file_path)
            resume_score = get_resume_score(resume_content)
            os.remove(file_path)  # Clean up after processing
        except Exception as e:
            logging.error(f"Error processing resume: {e}")
            error_message = 'An error occurred while processing your resume. Please try again.'

        return render_template(CHECK_SCORE_TEMPLATE, resume_score=resume_score, error_message=error_message)

    # If the method is GET, just render the page without score or error message
    return render_template(CHECK_SCORE_TEMPLATE, resume_score=resume_score, error_message=error_message)


def validate_file(file):
    """Validates the uploaded file."""
    if 'resume' not in request.files or not file:
        return 'No file selected.'
    if file.filename == '':
        return 'No file selected.'
    if not allowed_file(file.filename):
        return 'Only PDF files are allowed.'
    return None


def save_file(file):
    """Secures and saves the file temporarily."""
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    return file_path


def extract_text_from_pdf(file_path):
    """Extracts text from the uploaded PDF file."""
    try:
        resume_content = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                resume_content += page.extract_text()  # Extract text from each page
        return resume_content
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        raise ValueError('Failed to extract text from PDF.')


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid credentials. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == "__main__":
    # Ensure the upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
