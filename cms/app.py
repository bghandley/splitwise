from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models import db, User, Post, Category, Tag, Media, Podcast
from forms import PostForm, CategoryForm, TagForm, UserForm, PodcastForm
import whisper
from pydub import AudioSegment
import tempfile
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
PODCAST_FOLDER = os.path.join(UPLOAD_FOLDER, 'podcasts')

# Create upload directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PODCAST_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max file size

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/admin')
@login_required
def admin_dashboard():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin/dashboard.html', posts=posts)

@app.route('/admin/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    form.tags.choices = [(t.id, t.name) for t in Tag.query.all()]

    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            excerpt=form.excerpt.data,
            category_id=form.category.data,
            meta_description=form.meta_description.data,
            meta_keywords=form.meta_keywords.data,
            published=form.published.data,
            author_id=current_user.id
        )

        if form.featured_image.data:
            filename = secure_filename(form.featured_image.data.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.featured_image.data.save(filepath)
            post.featured_image = filename

        selected_tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
        post.tags.extend(selected_tags)

        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/post_form.html', form=form, title='New Post')

@app.route('/admin/post/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    form = PostForm(obj=post)
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    form.tags.choices = [(t.id, t.name) for t in Tag.query.all()]

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.excerpt = form.excerpt.data
        post.category_id = form.category.data
        post.meta_description = form.meta_description.data
        post.meta_keywords = form.meta_keywords.data
        post.published = form.published.data
        post.updated_at = datetime.utcnow()

        if form.featured_image.data:
            filename = secure_filename(form.featured_image.data.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.featured_image.data.save(filepath)
            post.featured_image = filename

        post.tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()

        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    form.tags.data = [tag.id for tag in post.tags]
    return render_template('admin/post_form.html', form=form, post=post, title='Edit Post')

@app.route('/admin/post/<int:id>/delete', methods=['POST'])
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/categories')
@login_required
def categories():
    categories = Category.query.all()
    form = CategoryForm()  
    return render_template('admin/categories.html', categories=categories, form=form)

@app.route('/admin/category/new', methods=['POST'])
@login_required
def new_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data, description=form.description.data)
        db.session.add(category)
        db.session.commit()
        flash('Category created successfully!', 'success')
        return redirect(url_for('categories'))
    flash('Error creating category. Please check the form.', 'danger')
    return redirect(url_for('categories'))

@app.route('/admin/category/<int:id>/edit', methods=['POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    form = CategoryForm()
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        db.session.commit()
        flash('Category updated successfully!', 'success')
    else:
        flash('Error updating category. Please check the form.', 'danger')
    return redirect(url_for('categories'))

@app.route('/admin/category/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('categories'))

@app.route('/admin/tags')
@login_required
def tags():
    tags = Tag.query.all()
    form = TagForm()  
    return render_template('admin/tags.html', tags=tags, form=form)

@app.route('/admin/tag/new', methods=['POST'])
@login_required
def new_tag():
    form = TagForm()
    if form.validate_on_submit():
        tag = Tag(name=form.name.data)
        db.session.add(tag)
        db.session.commit()
        flash('Tag created successfully!', 'success')
        return redirect(url_for('tags'))
    flash('Error creating tag. Please check the form.', 'danger')
    return redirect(url_for('tags'))

@app.route('/admin/tag/<int:id>/edit', methods=['POST'])
@login_required
def edit_tag(id):
    tag = Tag.query.get_or_404(id)
    form = TagForm()
    if form.validate_on_submit():
        tag.name = form.name.data
        db.session.commit()
        flash('Tag updated successfully!', 'success')
    else:
        flash('Error updating tag. Please check the form.', 'danger')
    return redirect(url_for('tags'))

@app.route('/admin/tag/<int:id>/delete', methods=['POST'])
@login_required
def delete_tag(id):
    tag = Tag.query.get_or_404(id)
    db.session.delete(tag)
    db.session.commit()
    flash('Tag deleted successfully!', 'success')
    return redirect(url_for('tags'))

@app.route('/admin/podcasts')
@login_required
def podcasts():
    podcasts = Podcast.query.order_by(Podcast.published_at.desc()).all()
    form = PodcastForm()
    return render_template('admin/podcasts.html', podcasts=podcasts, form=form)

def analyze_audio_file(file_path):
    """Analyze audio file to get duration and transcribe content"""
    # Get duration
    audio = AudioSegment.from_file(file_path)
    duration_minutes = len(audio) / 1000 / 60  # Convert milliseconds to minutes

    # Load Whisper model and transcribe
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    
    # Generate title and description from transcription
    transcript = result["text"]
    # Use the first sentence as title (up to 100 chars)
    title = transcript.split('.')[0][:100].strip()
    # Use the full transcript as description
    description = transcript.strip()
    
    return {
        'duration': duration_minutes,
        'title': title,
        'description': description,
        'transcript': transcript
    }

@app.route('/admin/podcast/analyze', methods=['POST'])
@login_required
def analyze_podcast():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if not allowed_audio_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed types: mp3, wav, m4a, ogg'}), 400
        
    # Save to temporary file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, secure_filename(file.filename))
    
    try:
        file.save(temp_path)
        logging.info(f"Saved temp file to {temp_path}")
        
        # Analyze the audio
        result = analyze_audio_file(temp_path)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error analyzing audio: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            os.remove(temp_path)
            os.rmdir(temp_dir)
        except Exception as e:
            logging.error(f"Error cleaning up temp files: {str(e)}")

def allowed_audio_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'mp3', 'wav', 'm4a', 'ogg'}

@app.route('/admin/podcast/new', methods=['POST'])
@login_required
def new_podcast():
    form = PodcastForm()
    if form.validate_on_submit():
        try:
            audio_file = form.audio_file.data
            if not audio_file:
                flash('No audio file provided', 'danger')
                return redirect(url_for('podcasts'))
                
            filename = secure_filename(audio_file.filename)
            if not allowed_audio_file(filename):
                flash('Invalid file type. Allowed types: mp3, wav, m4a, ogg', 'danger')
                return redirect(url_for('podcasts'))
                
            file_path = os.path.join(PODCAST_FOLDER, filename)
            logging.info(f"Saving podcast to {file_path}")
            audio_file.save(file_path)
            
            # Analyze the audio if no title/description provided
            if not form.title.data or not form.description.data:
                try:
                    analysis = analyze_audio_file(file_path)
                    title = form.title.data or analysis['title']
                    description = form.description.data or analysis['description']
                    duration = form.duration.data or analysis['duration']
                except Exception as e:
                    logging.error(f"Error analyzing audio: {str(e)}")
                    title = form.title.data or filename
                    description = form.description.data or ''
                    duration = form.duration.data or 0
            else:
                title = form.title.data
                description = form.description.data
                duration = form.duration.data
                
            podcast = Podcast(
                title=title,
                description=description,
                audio_file=filename,
                duration=duration,
                published_at=form.published_at.data or datetime.utcnow()
            )
            db.session.add(podcast)
            db.session.commit()
            flash('Podcast created successfully!', 'success')
            
        except Exception as e:
            logging.error(f"Error creating podcast: {str(e)}")
            flash(f'Error creating podcast: {str(e)}', 'danger')
            
        return redirect(url_for('podcasts'))
        
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{field}: {error}', 'danger')
    return redirect(url_for('podcasts'))

@app.route('/admin/podcast/<int:id>/edit', methods=['POST'])
@login_required
def edit_podcast(id):
    podcast = Podcast.query.get_or_404(id)
    form = PodcastForm()
    if form.validate_on_submit():
        if form.audio_file.data:
            audio_file = form.audio_file.data
            filename = secure_filename(audio_file.filename)
            audio_file.save(os.path.join(PODCAST_FOLDER, filename))
            podcast.audio_file = filename
        
        podcast.title = form.title.data
        podcast.description = form.description.data
        podcast.duration = form.duration.data
        podcast.published_at = form.published_at.data
        db.session.commit()
        flash('Podcast updated successfully!', 'success')
    else:
        flash('Error updating podcast. Please check the form.', 'danger')
    return redirect(url_for('podcasts'))

@app.route('/admin/podcast/<int:id>/delete', methods=['POST'])
@login_required
def delete_podcast(id):
    podcast = Podcast.query.get_or_404(id)
    # Delete the audio file
    try:
        os.remove(os.path.join(PODCAST_FOLDER, podcast.audio_file))
    except:
        pass  # File might not exist
    db.session.delete(podcast)
    db.session.commit()
    flash('Podcast deleted successfully!', 'success')
    return redirect(url_for('podcasts'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid email or password', 'error')
    return render_template('admin/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# API endpoints for frontend integration
@app.route('/api/posts')
def api_posts():
    posts = Post.query.filter_by(published=True).order_by(Post.created_at.desc()).all()
    return jsonify([{
        'id': post.id,
        'title': post.title,
        'slug': post.slug,
        'excerpt': post.excerpt,
        'featured_image': post.featured_image,
        'author': post.author.username,
        'category': post.category.name if post.category else None,
        'tags': [tag.name for tag in post.tags],
        'created_at': post.created_at.isoformat(),
        'views': post.views,
        'share_count': post.share_count
    } for post in posts])

@app.route('/api/post/<slug>')
def api_post(slug):
    post = Post.query.filter_by(slug=slug, published=True).first_or_404()
    post.increment_view()
    return jsonify({
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'featured_image': post.featured_image,
        'author': post.author.username,
        'category': post.category.name if post.category else None,
        'tags': [tag.name for tag in post.tags],
        'created_at': post.created_at.isoformat(),
        'updated_at': post.updated_at.isoformat(),
        'views': post.views,
        'share_count': post.share_count
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
