from datetime import datetime
import os
import json
import magic
from flask import send_file, abort, request
from werkzeug.utils import secure_filename
import hashlib
import boto3
from threading import Lock

class ResourceTracker:
    def __init__(self, app):
        self.app = app
        self.download_lock = Lock()
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=app.config['AWS_ACCESS_KEY'],
            aws_secret_access_key=app.config['AWS_SECRET_KEY']
        )
        self.bucket = app.config['AWS_RESOURCE_BUCKET']

    def track_download(self, resource_id, user=None):
        """Track a resource download"""
        with self.download_lock:
            try:
                download = ResourceDownload(
                    resource_id=resource_id,
                    user_id=user.id if user else None,
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string,
                    timestamp=datetime.utcnow()
                )
                db.session.add(download)
                db.session.commit()
                
                # Update resource download count
                resource = Resource.query.get(resource_id)
                if resource:
                    resource.download_count += 1
                    db.session.commit()
                
                return True
            except Exception as e:
                print(f"Error tracking download: {e}")
                db.session.rollback()
                return False

    def get_download_stats(self, resource_id=None, start_date=None, end_date=None):
        """Get download statistics"""
        try:
            query = ResourceDownload.query
            
            if resource_id:
                query = query.filter_by(resource_id=resource_id)
            if start_date:
                query = query.filter(ResourceDownload.timestamp >= start_date)
            if end_date:
                query = query.filter(ResourceDownload.timestamp <= end_date)
            
            downloads = query.all()
            
            stats = {
                'total_downloads': len(downloads),
                'unique_users': len(set(d.user_id for d in downloads if d.user_id)),
                'unique_ips': len(set(d.ip_address for d in downloads)),
                'daily_downloads': {},
                'user_agents': {}
            }
            
            # Calculate daily downloads
            for download in downloads:
                date = download.timestamp.date().isoformat()
                stats['daily_downloads'][date] = stats['daily_downloads'].get(date, 0) + 1
                
                # Track user agents
                ua = download.user_agent
                stats['user_agents'][ua] = stats['user_agents'].get(ua, 0) + 1
            
            return stats
        except Exception as e:
            print(f"Error getting download stats: {e}")
            return None

    def serve_resource(self, resource_id, user=None):
        """Serve a resource file with tracking"""
        try:
            resource = Resource.query.get(resource_id)
            if not resource:
                abort(404)
            
            # Check if user has access
            if resource.premium and (not user or not user.has_access(resource)):
                abort(403)
            
            # Track the download
            self.track_download(resource_id, user)
            
            # Get file from S3 or local storage
            if self.app.config.get('USE_S3'):
                return self._serve_from_s3(resource)
            else:
                return self._serve_from_local(resource)
        except Exception as e:
            print(f"Error serving resource: {e}")
            abort(500)

    def _serve_from_s3(self, resource):
        """Serve file from S3"""
        try:
            # Generate presigned URL
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': resource.file_path
                },
                ExpiresIn=300  # URL expires in 5 minutes
            )
            return url
        except Exception as e:
            print(f"Error serving from S3: {e}")
            abort(500)

    def _serve_from_local(self, resource):
        """Serve file from local storage"""
        try:
            file_path = os.path.join(self.app.root_path, 'media', 'resources', resource.file_path)
            if not os.path.exists(file_path):
                abort(404)
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=resource.original_filename
            )
        except Exception as e:
            print(f"Error serving from local: {e}")
            abort(500)

    def upload_resource(self, file, metadata):
        """Upload a new resource"""
        try:
            filename = secure_filename(file.filename)
            file_hash = self._generate_file_hash(file)
            
            # Check if file already exists
            existing = Resource.query.filter_by(file_hash=file_hash).first()
            if existing:
                return existing
            
            # Save file
            if self.app.config.get('USE_S3'):
                file_path = self._upload_to_s3(file, filename)
            else:
                file_path = self._save_to_local(file, filename)
            
            # Create resource record
            resource = Resource(
                title=metadata.get('title'),
                description=metadata.get('description'),
                file_path=file_path,
                original_filename=filename,
                file_hash=file_hash,
                file_size=self._get_file_size(file),
                mime_type=self._get_mime_type(file),
                premium=metadata.get('premium', False)
            )
            
            db.session.add(resource)
            db.session.commit()
            
            return resource
        except Exception as e:
            print(f"Error uploading resource: {e}")
            db.session.rollback()
            return None

    def _generate_file_hash(self, file):
        """Generate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)
        file.seek(0)
        return sha256_hash.hexdigest()

    def _get_file_size(self, file):
        """Get file size in bytes"""
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        return size

    def _get_mime_type(self, file):
        """Get MIME type of file"""
        mime = magic.Magic(mime=True)
        return mime.from_buffer(file.read(1024))

    def _upload_to_s3(self, file, filename):
        """Upload file to S3"""
        try:
            key = f"resources/{datetime.utcnow().strftime('%Y/%m/%d')}/{filename}"
            self.s3.upload_fileobj(file, self.bucket, key)
            return key
        except Exception as e:
            print(f"Error uploading to S3: {e}")
            raise

    def _save_to_local(self, file, filename):
        """Save file to local storage"""
        try:
            path = os.path.join(
                self.app.root_path,
                'media',
                'resources',
                datetime.utcnow().strftime('%Y/%m/%d')
            )
            os.makedirs(path, exist_ok=True)
            
            file_path = os.path.join(path, filename)
            file.save(file_path)
            
            return os.path.relpath(
                file_path,
                os.path.join(self.app.root_path, 'media', 'resources')
            )
        except Exception as e:
            print(f"Error saving to local: {e}")
            raise

# Example usage:
"""
# Initialize tracker
resource_tracker = ResourceTracker(app)

# Upload new resource
with open('example.pdf', 'rb') as f:
    resource = resource_tracker.upload_resource(f, {
        'title': 'Example PDF',
        'description': 'An example PDF resource',
        'premium': False
    })

# Serve resource
@app.route('/download/<int:resource_id>')
def download_resource(resource_id):
    return resource_tracker.serve_resource(resource_id, current_user)

# Get stats
stats = resource_tracker.get_download_stats(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
"""
