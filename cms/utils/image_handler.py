import os
from PIL import Image
from werkzeug.utils import secure_filename
import uuid

class ImageHandler:
    def __init__(self, app):
        self.app = app
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        self.sizes = {
            'thumbnail': (300, 300),
            'medium': (800, 800),
            'large': (1200, 1200)
        }

    def allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def save_image(self, file, subfolder=''):
        if not file or not self.allowed_file(file.filename):
            return None

        # Generate unique filename
        original_filename = secure_filename(file.filename)
        filename = f"{str(uuid.uuid4())}-{original_filename}"
        
        # Create subfolder if it doesn't exist
        upload_path = os.path.join(self.app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_path, exist_ok=True)

        # Save original file
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)

        # Create different sizes
        self.create_image_sizes(file_path, subfolder)

        return filename

    def create_image_sizes(self, original_path, subfolder=''):
        try:
            with Image.open(original_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Create different sizes
                for size_name, dimensions in self.sizes.items():
                    size_folder = os.path.join(self.app.config['UPLOAD_FOLDER'], subfolder, size_name)
                    os.makedirs(size_folder, exist_ok=True)

                    # Calculate new dimensions maintaining aspect ratio
                    width, height = dimensions
                    img_copy = img.copy()
                    img_copy.thumbnail((width, height), Image.Resampling.LANCZOS)

                    # Save resized image
                    size_path = os.path.join(size_folder, os.path.basename(original_path))
                    img_copy.save(size_path, 'JPEG', quality=85)

        except Exception as e:
            print(f"Error processing image: {e}")
            return False

        return True

    def delete_image(self, filename, subfolder=''):
        try:
            # Delete original
            original_path = os.path.join(self.app.config['UPLOAD_FOLDER'], subfolder, filename)
            if os.path.exists(original_path):
                os.remove(original_path)

            # Delete all sizes
            for size_name in self.sizes.keys():
                size_path = os.path.join(self.app.config['UPLOAD_FOLDER'], subfolder, size_name, filename)
                if os.path.exists(size_path):
                    os.remove(size_path)

            return True
        except Exception as e:
            print(f"Error deleting image: {e}")
            return False

    def get_image_url(self, filename, size='medium', subfolder=''):
        if not filename:
            return None
            
        if size in self.sizes:
            return f"/uploads/{subfolder}/{size}/{filename}"
        return f"/uploads/{subfolder}/{filename}"
