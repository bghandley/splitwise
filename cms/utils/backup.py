import boto3
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
import sqlite3
import tempfile
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler

class BackupManager:
    def __init__(self, app):
        self.app = app
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=app.config['AWS_ACCESS_KEY'],
            aws_secret_access_key=app.config['AWS_SECRET_KEY']
        )
        self.bucket = app.config['AWS_BACKUP_BUCKET']
        self.scheduler = BackgroundScheduler()
        self.setup_scheduler()

    def setup_scheduler(self):
        """Setup automated backup schedule"""
        self.scheduler.add_job(
            self.create_backup,
            'cron',
            hour=3,  # Run at 3 AM
            id='daily_backup'
        )
        self.scheduler.start()

    def create_backup(self):
        """Create a full backup of the CMS"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = tempfile.mkdtemp()
            
            # Backup database
            self._backup_database(backup_dir, timestamp)
            
            # Backup uploads
            self._backup_uploads(backup_dir, timestamp)
            
            # Create metadata
            self._create_metadata(backup_dir, timestamp)
            
            # Zip everything
            archive_path = self._create_archive(backup_dir, timestamp)
            
            # Upload to S3
            self._upload_to_s3(archive_path, timestamp)
            
            # Cleanup
            shutil.rmtree(backup_dir)
            os.remove(archive_path)
            
            return True
        except Exception as e:
            current_app.logger.error(f"Backup failed: {str(e)}")
            return False

    def _backup_database(self, backup_dir, timestamp):
        """Backup SQLite database"""
        db_path = self.app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        backup_db = os.path.join(backup_dir, f'database_{timestamp}.sqlite')
        
        with sqlite3.connect(db_path) as src, sqlite3.connect(backup_db) as dst:
            src.backup(dst)

    def _backup_uploads(self, backup_dir, timestamp):
        """Backup uploaded files"""
        uploads_dir = os.path.join(self.app.root_path, 'uploads')
        backup_uploads = os.path.join(backup_dir, 'uploads')
        
        if os.path.exists(uploads_dir):
            shutil.copytree(uploads_dir, backup_uploads)

    def _create_metadata(self, backup_dir, timestamp):
        """Create backup metadata"""
        metadata = {
            'timestamp': timestamp,
            'version': self.app.config.get('VERSION', '1.0.0'),
            'backup_type': 'full',
            'files': []
        }
        
        # List all files in backup
        for root, _, files in os.walk(backup_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, backup_dir)
                metadata['files'].append({
                    'path': rel_path,
                    'size': os.path.getsize(file_path)
                })
        
        # Write metadata
        with open(os.path.join(backup_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)

    def _create_archive(self, backup_dir, timestamp):
        """Create zip archive of backup"""
        archive_path = f'backup_{timestamp}.zip'
        shutil.make_archive(
            archive_path.replace('.zip', ''),
            'zip',
            backup_dir
        )
        return archive_path

    def _upload_to_s3(self, archive_path, timestamp):
        """Upload backup to S3"""
        key = f'backups/backup_{timestamp}.zip'
        self.s3.upload_file(archive_path, self.bucket, key)

    def restore_backup(self, backup_id):
        """Restore from a backup"""
        try:
            # Download backup from S3
            backup_dir = tempfile.mkdtemp()
            backup_zip = os.path.join(backup_dir, 'backup.zip')
            
            self.s3.download_file(
                self.bucket,
                f'backups/backup_{backup_id}.zip',
                backup_zip
            )
            
            # Extract backup
            shutil.unpack_archive(backup_zip, backup_dir)
            
            # Verify metadata
            with open(os.path.join(backup_dir, 'metadata.json')) as f:
                metadata = json.load(f)
            
            # Stop the application
            self.app.config['MAINTENANCE_MODE'] = True
            
            try:
                # Restore database
                db_backup = os.path.join(backup_dir, f'database_{metadata["timestamp"]}.sqlite')
                db_path = self.app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                
                with sqlite3.connect(db_backup) as src, sqlite3.connect(db_path) as dst:
                    src.backup(dst)
                
                # Restore uploads
                uploads_backup = os.path.join(backup_dir, 'uploads')
                uploads_dir = os.path.join(self.app.root_path, 'uploads')
                
                if os.path.exists(uploads_dir):
                    shutil.rmtree(uploads_dir)
                if os.path.exists(uploads_backup):
                    shutil.copytree(uploads_backup, uploads_dir)
                
                return True
            finally:
                # Resume the application
                self.app.config['MAINTENANCE_MODE'] = False
                
                # Cleanup
                shutil.rmtree(backup_dir)
        except Exception as e:
            current_app.logger.error(f"Restore failed: {str(e)}")
            return False

    def list_backups(self):
        """List available backups"""
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix='backups/'
            )
            
            backups = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.zip'):
                    backups.append({
                        'id': key.split('_')[1].replace('.zip', ''),
                        'timestamp': obj['LastModified'],
                        'size': obj['Size']
                    })
            
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
        except Exception as e:
            current_app.logger.error(f"Failed to list backups: {str(e)}")
            return []

# Initialize backup manager
backup_manager = BackupManager(current_app)
